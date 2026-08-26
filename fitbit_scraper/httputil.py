"""Polite HTTP helpers: User-Agent, timeouts, retries, and pause between calls."""

from __future__ import annotations

import logging
import ssl
import time
import urllib.error
import urllib.request
from typing import Optional

from .config import (
    REDDIT_PAUSE_SEC,
    REQUEST_PAUSE_SEC,
    REQUEST_RETRIES,
    REQUEST_TIMEOUT_SEC,
    USER_AGENT,
)

log = logging.getLogger("fitbit_scraper.http")

_SSL = ssl.create_default_context()
_last_call = 0.0


def _pause(url: str) -> None:
    global _last_call
    wait = REDDIT_PAUSE_SEC if "reddit.com" in url else REQUEST_PAUSE_SEC
    elapsed = time.monotonic() - _last_call
    if elapsed < wait:
        time.sleep(wait - elapsed)
    _last_call = time.monotonic()


def fetch_bytes(url: str, accept: str = "*/*") -> tuple[Optional[bytes], Optional[str]]:
    """Return (body, error). Never raises for network/HTTP failures."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": accept,
        "Accept-Language": "es-AR,es;q=0.9,en;q=0.8,pt;q=0.7,fr;q=0.6,de;q=0.6,it;q=0.6,ja;q=0.5",
    }
    last_error: Optional[str] = None
    for attempt in range(1, REQUEST_RETRIES + 1):
        _pause(url)
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SEC, context=_SSL) as resp:
                return resp.read(), None
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code} {exc.reason}"
            # Reddit rate-limits aggressively; back off and retry.
            if exc.code in {429, 503, 502} and attempt < REQUEST_RETRIES:
                time.sleep(4 * attempt)
                continue
            if exc.code in {401, 403, 404}:
                break
        except Exception as exc:  # noqa: BLE001 — sources must never crash the job
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < REQUEST_RETRIES:
                time.sleep(2 * attempt)
    log.warning("fetch failed %s — %s", url, last_error)
    return None, last_error


def fetch_text(url: str, accept: str = "*/*") -> tuple[Optional[str], Optional[str]]:
    body, err = fetch_bytes(url, accept=accept)
    if body is None:
        return None, err
    return body.decode("utf-8", "replace"), None
