"""Is this item actually about a Fitbit (or Fitbit-backed Pixel Watch) product?

Precision over recall: a passing mention in a brand list, a Wear OS app for
another watch, or an HN comment on an unrelated story must not enter the feed.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from .config import COMPETITOR_CUES, ROUNDUP_CUES
from .models import detect_models

_FITBIT_SUBJECT = re.compile(
    r"\bfitbit\b|\bgoogle health\b|\bgoogle-health\b|\bpixel watch\b",
    re.I,
)
_WATCH_BRANDS = (
    "fitbit",
    "apple watch",
    "garmin",
    "galaxy watch",
    "samsung",
    "huawei",
    "amazfit",
    "whoop",
    "oneplus",
    "pixel watch",
    "withings",
    "coros",
    "suunto",
    "xiaomi",
)


def _contains(text: str, phrase: str) -> bool:
    if not phrase:
        return False
    if " " in phrase or not phrase.isascii():
        return phrase in text
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text) is not None


def _title_has_fitbit_subject(title: str) -> bool:
    if _FITBIT_SUBJECT.search(title or ""):
        return True
    return bool(detect_models(title or ""))


def _url_is_fitbit(url: str) -> bool:
    raw = (url or "").lower()
    if not raw:
        return False
    if "fitbit" in raw or "pixelwatch" in raw or "pixel-watch" in raw or "googlepixelwatch" in raw:
        return True
    try:
        path = urlparse(raw).path or ""
    except ValueError:
        path = raw
    if "/r/fitbit" in path or "/r/googlepixelwatch" in path:
        return True
    return False


def _competitor_is_subject(title: str) -> bool:
    low = (title or "").lower()
    if not low:
        return False
    # Syncing Fitbit with Apple Health is on-topic, not an Apple Watch story.
    if "apple health" in low and "apple watch" not in low:
        return False
    for cue in COMPETITOR_CUES:
        if _contains(low, cue) and not _title_has_fitbit_subject(title):
            return True
    return False


def _is_brand_roundup(title: str) -> bool:
    low = (title or "").lower()
    if any(cue in low for cue in ROUNDUP_CUES):
        return True
    hits = sum(1 for b in _WATCH_BRANDS if b in low)
    # "Fitbit Air vs Galaxy Watch 7" is a real comparison (2 brands) — keep.
    # "Apple vs Garmin vs Fitbit vs Samsung" is a shopping pile — drop.
    return hits >= 3 and "fitbit" in low


def is_fitbit_subject(
    title: str,
    body: str = "",
    url: str = "",
    *,
    source_scoped: bool = False,
) -> tuple[bool, str]:
    """Return (ok, reason). source_scoped = r/fitbit, Pixel Watch sub, or App Store."""
    title = title or ""
    body = body or ""
    url = url or ""
    title_l = title.lower()

    if _competitor_is_subject(title):
        return False, "otra_marca"
    if _is_brand_roundup(title):
        return False, "comparativa_genérica"

    title_or_url = _title_has_fitbit_subject(title) or _url_is_fitbit(url)

    if source_scoped:
        return True, "comunidad"

    if not title_or_url:
        return False, "sin_sujeto_fitbit"

    # Unscoped Wear OS apps that name Fitbit only in a snippet, not the headline.
    if "wear os" in title_l and "fitbit" not in title_l and "pixel watch" not in title_l:
        if not detect_models(title):
            return False, "wearos_genérico"

    return True, "sujeto_fitbit"
