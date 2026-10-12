"""Parse public Play Store and Google Health community HTML. No login."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from html import unescape

from .textutil import parse_datetime, strip_html

_PLAY_BLOCK = re.compile(
    r'data-review-id="([^"]+)".{0,2500}?Rated (\d+) stars out of five stars'
    r'.{0,800}?<span class="bp9Aid">([^<]+)</span>'
    r'.{0,400}?<div class="h3YV2d">(.*?)</div>',
    re.I | re.S,
)
_PLAY_AUTHOR = re.compile(r"data-review-id=\"[^\"]+\">\s*([^<]{2,80})\s+", re.I)
_GHEALTH_THREAD = re.compile(
    r'\["(/googlehealth/thread/(\d+)[^"]*)","([^"]{8,240})","([^"]{0,800})"',
    re.I,
)
_TS_MS = re.compile(r"(1[6-8]\d{11,12})")


def parse_play_reviews(html: str) -> list[dict]:
    """Featured reviews on a public Play Store details page."""
    out: list[dict] = []
    seen: set[str] = set()
    for m in _PLAY_BLOCK.finditer(html or ""):
        rid, rating_s, date_s, body = m.group(1), m.group(2), m.group(3), m.group(4)
        if rid in seen:
            continue
        seen.add(rid)
        try:
            rating = int(rating_s)
        except ValueError:
            rating = None
        text = strip_html(unescape(body or ""))
        stamp = parse_datetime(date_s.strip()) or _parse_long_date(date_s)
        author = ""
        am = _PLAY_AUTHOR.search(html[max(0, m.start() - 80) : m.start() + 400])
        if am:
            author = strip_html(am.group(1))[:80]
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
            raw = ts.group(1)
            try:
                n = int(raw)
                if n > 10_000_000_000:
                    n = n / 1000.0
                stamp = datetime.fromtimestamp(n, tz=timezone.utc).isoformat()
            except (ValueError, OverflowError, OSError):
                stamp = None
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


def _parse_long_date(raw: str) -> str | None:
    raw = (raw or "").strip()
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y"):
        try:
            dt = datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except ValueError:
            continue
    return parse_datetime(raw)
