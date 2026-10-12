"""Parse public Play Store and Google Health community HTML. No login."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from html import unescape

from .textutil import parse_datetime, strip_html

_PLAY_TEXT = re.compile(r'<div class="h3YV2d">(.*?)</div>', re.I | re.S)
_PLAY_DATE = re.compile(r'<span class="bp9Aid">([^<]+)</span>', re.I)
_PLAY_RATED = re.compile(r"Rated (\d+) stars out of five stars", re.I)
_PLAY_RID = re.compile(r'data-review-id="([^"]+)"', re.I)
_PLAY_AUTHOR = re.compile(r'<div class="X5PpBb">([^<]+)</div>', re.I)
_GHEALTH_THREAD = re.compile(
    r'\["(/googlehealth/thread/(\d+)[^"]*)","([^"]{8,240})","([^"]{0,800})"',
    re.I,
)
# 13-digit unix milliseconds (16xx–18xx). 14+ digits are µs and become year 253x.
_TS_MS = re.compile(r"(1[6-8]\d{11})(?!\d)")


def parse_play_reviews(html: str) -> list[dict]:
    """Featured reviews on a public Play Store details page."""
    out: list[dict] = []
    seen: set[str] = set()
    blob = html or ""
    for m in _PLAY_TEXT.finditer(blob):
        text = strip_html(unescape(m.group(1) or ""))
        if len(text) < 12:
            continue
        before = blob[max(0, m.start() - 9000) : m.start()]
        after = blob[m.end() : m.end() + 600]
        rid_m = _PLAY_RID.search(after) or list(_PLAY_RID.finditer(before))
        if isinstance(rid_m, list):
            rid = rid_m[-1].group(1) if rid_m else text[:24]
        else:
            rid = rid_m.group(1)
        if rid in seen:
            continue
        seen.add(rid)
        date_m = _PLAY_DATE.search(before[-800:] if len(before) > 800 else before)
        stamp = _parse_long_date(date_m.group(1) if date_m else "")
        rated = list(_PLAY_RATED.finditer(before))
        rating = int(rated[-1].group(1)) if rated else None
        authors = list(_PLAY_AUTHOR.finditer(before))
        author = strip_html(authors[-1].group(1))[:80] if authors else ""
        title = (text.split(".")[0] or text)[:120]
        out.append(
            {
                "id": rid,
                "title": title,
                "text": text,
                "created_at": stamp,
                "author": author,
                "star_rating": rating,
                "url": f"https://play.google.com/store/apps/details?id=com.fitbit.FitbitMobile&reviewId={rid}",
            }
        )
    return out


def parse_google_health_threads(html: str) -> list[dict]:
    """Thread cards embedded in support.google.com/googlehealth HTML."""
    out: list[dict] = []
    seen: set[str] = set()
    blob = html or ""
    for m in _GHEALTH_THREAD.finditer(blob):
        path, tid, title, snippet = m.group(1), m.group(2), m.group(3), m.group(4)
        if tid in seen:
            continue
        seen.add(tid)
        title = unescape(title).replace("\\u003cb\\u003e", "").replace("\\u003c/b\\u003e", "")
        snippet = unescape(snippet).replace("\\u003cb\\u003e", "").replace("\\u003c/b\\u003e", "")
        title = strip_html(title)
        snippet = strip_html(snippet)
        tail = blob[m.end() : m.end() + 500]
        stamp = None
        ts = _TS_MS.search(tail)
        if ts:
            stamp = _unix_ms_to_iso(ts.group(1))
        url = path if path.startswith("http") else "https://support.google.com" + path.split("?")[0]
        out.append(
            {
                "id": tid,
                "title": title,
                "text": snippet or title,
                "created_at": stamp,
                "url": url,
                "author": "",
            }
        )
    return out


def _unix_ms_to_iso(raw: str) -> str | None:
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return None
    if n >= 10**14:
        n = n / 1_000_000.0
    elif n >= 10**11:
        n = n / 1000.0
    try:
        dt = datetime.fromtimestamp(n, tz=timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None
    now = datetime.now(timezone.utc)
    if dt.year < 2015 or dt.year > now.year + 1:
        return None
    return dt.isoformat()


def _parse_long_date(raw: str) -> str | None:
    raw = (raw or "").strip()
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y"):
        try:
            dt = datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except ValueError:
            continue
    return parse_datetime(raw)
