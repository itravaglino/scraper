"""Is this item actually about a Fitbit (or Google Health / Fitbit app) product?

Precision over recall: a passing mention in a brand list, a Wear OS app for
another watch, or an HN comment on an unrelated story must not enter the feed.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from .config import (
    BAND_PROMO_CUES,
    COMPETITOR_CUES,
    DEAL_CUES,
    REPAIR_AD_CUES,
    ROUNDUP_CUES,
)
from .models import detect_models

_FITBIT_SUBJECT = re.compile(
    r"\bfitbit\b|\bgoogle health\b|\bgoogle-health\b|\bgooglehealth\b",
    re.I,
)
_WHOOP = re.compile(r"\bwhoop\b", re.I)
_PIXEL_ONLY = re.compile(r"\bpixel watch\b", re.I)
_SHORTS = re.compile(r"#shorts\b|\bshorts\b", re.I)
_WATCH_BRANDS = (
    "fitbit",
    "apple watch",
    "garmin",
    "galaxy watch",
    "samsung",
    "huawei",
    "amazfit",
    "whoop",
    "agptek",
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


def _fitbit_models(text: str) -> list[str]:
    return [m for m in detect_models(text or "") if not str(m).startswith("Pixel Watch")]


def _title_has_fitbit_subject(title: str) -> bool:
    if _FITBIT_SUBJECT.search(title or ""):
        return True
    return bool(_fitbit_models(title or ""))


def _url_is_fitbit(url: str) -> bool:
    raw = (url or "").lower()
    if not raw:
        return False
    if any(
        n in raw
        for n in (
            "fitbit",
            "googlehealth",
            "google-health",
            "googlehealthfitbit",
            "fitbitair",
        )
    ):
        return True
    try:
        path = urlparse(raw).path or ""
    except ValueError:
        path = raw
    if any(
        p in path
        for p in (
            "/r/fitbit",
            "/r/googlehealth",
            "/r/fitbitair",
            "/googlehealth/thread",
        )
    ):
        return True
    return False


def _competitor_is_subject(title: str) -> bool:
    low = (title or "").lower()
    if not low:
        return False
    if "apple health" in low and "apple watch" not in low:
        return False
    for cue in COMPETITOR_CUES:
        if cue == "whoop":
            continue  # handled separately — drop even with Fitbit in the title
        if _contains(low, cue) and not _title_has_fitbit_subject(title):
            return True
    return False


def _is_brand_roundup(title: str) -> bool:
    low = (title or "").lower()
    if any(cue in low for cue in ROUNDUP_CUES):
        return True
    hits = sum(1 for b in _WATCH_BRANDS if b in low)
    return hits >= 3 and "fitbit" in low


def _is_deal_or_promo(title: str) -> bool:
    low = (title or "").lower()
    if any(cue in low for cue in DEAL_CUES):
        return True
    if re.search(r"\b(\d+\s*%\s*off|save\s+\$\d+)\b", low):
        return True
    return False


def _is_band_promo(title: str) -> bool:
    low = (title or "").lower()
    if any(cue in low for cue in BAND_PROMO_CUES):
        return True
    if re.search(r"\b(megathread|3rd party|third[- ]party|compatible)\b.*\bbands?\b", low):
        return True
    if re.search(r"\bbands?\b.*\b(buy|sale|collection|colors|affiliate)\b", low):
        return True
    return False


def _is_repair_ad_short(title: str) -> bool:
    low = (title or "").lower()
    if any(cue in low for cue in REPAIR_AD_CUES):
        return True
    if _SHORTS.search(low) and re.search(r"\b(repair|reemplazo|replacement|fix your)\b", low):
        return True
    return False


def is_noise_title(title: str) -> tuple[bool, str]:
    if _WHOOP.search(title or ""):
        return True, "whoop"
    if _is_deal_or_promo(title):
        return True, "promo"
    if _is_band_promo(title):
        return True, "promo_correa"
    if _is_repair_ad_short(title):
        return True, "anuncio_reparacion"
    return False, ""


def is_fitbit_subject(
    title: str,
    body: str = "",
    url: str = "",
    *,
    source_scoped: bool = False,
) -> tuple[bool, str]:
    """Return (ok, reason). source_scoped = r/fitbit family, Google Health community, or stores."""
    title = title or ""
    body = body or ""
    url = url or ""
    title_l = title.lower()

    noisy, why = is_noise_title(title)
    if noisy:
        return False, why
    if _competitor_is_subject(title):
        return False, "otra_marca"
    if _is_brand_roundup(title):
        return False, "comparativa_genérica"

    has_fitbit = bool(
        _FITBIT_SUBJECT.search(title)
        or _FITBIT_SUBJECT.search(body[:800] or "")
        or _url_is_fitbit(url)
        or _fitbit_models(title)
        or _fitbit_models(body[:500] or "")
    )
    product_cue = has_fitbit or bool(detect_models(title) or detect_models(body[:500] or ""))

    if source_scoped:
        return True, "comunidad" if product_cue else "comunidad_sin_producto"

    if not has_fitbit:
        return False, "sin_sujeto_fitbit"

    if _PIXEL_ONLY.search(title_l) and not _FITBIT_SUBJECT.search(title) and not _FITBIT_SUBJECT.search(body[:800]):
        if not _fitbit_models(title) and not _fitbit_models(body[:500]):
            return False, "pixel_watch_only"

    if "wear os" in title_l and "fitbit" not in title_l and "google health" not in title_l:
        if not _fitbit_models(title):
            return False, "wearos_genérico"

    return True, "sujeto_fitbit"
