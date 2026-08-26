"""Polite HTTP helpers: User-Agent, timeouts, retries, and pause between calls."""

from __future__ import annotations

import logging
import ssl
import threading
import time
import urllib.error
import urllib.request
from email.utils import parsedate_to_datetime
from typing import Optional

from .config import (
    REDDIT_429_BACKOFF_SEC,
    REDDIT_429_MAX_WAIT_SEC,
    REDDIT_PAUSE_SEC,
    REQUEST_PAUSE_SEC,
    REQUEST_RETRIES,
    REQUEST_TIMEOUT_SEC,
    USER_AGENT,
)

log = logging.getLogger("fitbit_scraper.http")

_SSL = ssl.create_default_context()
_last_call = 0.0
_reddit_cooldown_until = 0.0
_REDDIT_LOCK = threading.Lock()


def parse_retry_after(raw: Optional[str]) -> Optional[float]:
    """Seconds to wait from a Retry-After header, or None if missing/invalid."""
    if not raw:
        return None
    text = str(raw).strip()
    try:
        return max(0.0, float(text))
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(text)
        return max(0.0, dt.timestamp() - time.time())
    except (TypeError, ValueError, OverflowError):
        return None


def _is_reddit(url: str) -> bool:
    return "reddit.com" in (url or "").lower()


def _pause(url: str) -> None:
    global _last_call
    wait = REQUEST_PAUSE_SEC
    if _is_reddit(url):
        wait = REDDIT_PAUSE_SEC
        extra = _reddit_cooldown_until - time.monotonic()
        if extra > 0:
            wait += extra
    elapsed = time.monotonic() - _last_call
    if elapsed < wait:
        time.sleep(wait - elapsed)
    _last_call = time.monotonic()


def _note_reddit_429(wait_sec: float) -> None:
    global _reddit_cooldown_until
    _reddit_cooldown_until = max(_reddit_cooldown_until, time.monotonic() + wait_sec)


def _429_wait(exc: urllib.error.HTTPError, attempt: int) -> float:
    header = None
    if exc.headers:
        header = exc.headers.get("Retry-After")
    parsed = parse_retry_after(header)
    backoff = REDDIT_429_BACKOFF_SEC * attempt
    wait = parsed if parsed is not None else backoff
    return min(max(wait, 8.0), REDDIT_429_MAX_WAIT_SEC)


def fetch_bytes(url: str, accept: str = "*/*") -> tuple[Optional[bytes], Optional[str]]:
    """Return (body, error). Never raises for network/HTTP failures.

    Reddit is strictly serial (one in-flight request). 429 waits on Retry-After
    or exponential backoff, then retries once; the next Reddit call also cools down.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": accept,
        "Accept-Language": "es-AR,es;q=0.9,en;q=0.8,pt;q=0.7,fr;q=0.6,de;q=0.6,it;q=0.6,ja;q=0.5",
    }
    last_error: Optional[str] = None
    reddit = _is_reddit(url)
    lock = _REDDIT_LOCK if reddit else None
    if lock:
        lock.acquire()
    try:
        for attempt in range(1, REQUEST_RETRIES + 1):
            _pause(url)
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SEC, context=_SSL) as resp:
                    return resp.read(), None
            except urllib.error.HTTPError as exc:
                last_error = f"HTTP {exc.code} {exc.reason}"
                if exc.code == 429:
                    wait = _429_wait(exc, attempt)
                    if reddit:
                        _note_reddit_429(wait)
                    # One retry after backoff, then skip this source.
                    if attempt < 2:
                        log.info("HTTP 429 on %s — waiting %.0fs then one retry", url, wait)
                        time.sleep(wait)
                        continue
                    break
                if exc.code in {503, 502} and attempt < REQUEST_RETRIES:
                    time.sleep(4 * attempt)
                    continue
                if exc.code in {401, 403, 404}:
                    break
            except Exception as exc:  # noqa: BLE001 — sources must never crash the job
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt < REQUEST_RETRIES:
                    time.sleep(2 * attempt)
    finally:
        if lock:
            lock.release()
    log.warning("fetch failed %s — %s", url, last_error)
    return None, last_error


def fetch_text(url: str, accept: str = "*/*") -> tuple[Optional[str], Optional[str]]:
    body, err = fetch_bytes(url, accept=accept)
    if body is None:
        return None, err
    return body.decode("utf-8", "replace"), None
