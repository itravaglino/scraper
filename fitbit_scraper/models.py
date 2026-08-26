"""Detect Fitbit / Pixel Watch model names in free text."""

from __future__ import annotations

import re

from .config import MODEL_PATTERNS, WEAK_MODEL_LABELS

_COMPILED = [(label, [re.compile(p, re.I) for p in pats]) for label, pats in MODEL_PATTERNS]


def detect_models(text: str) -> list[str]:
    """Return specific models mentioned, most specific first, no parent duplicates."""
    blob = text or ""
    found: list[str] = []
    for label, regexes in _COMPILED:
        if any(rx.search(blob) for rx in regexes):
            found.append(label)
    # Drop generic family tags when a numbered sibling is present (Charge 6 > Charge).
    families = {"Charge", "Versa", "Sense", "Inspire", "Ace", "Pixel Watch"}
    numbered = {m for m in found if m not in families}
    specific: list[str] = []
    for m in found:
        if m in families and any(s.startswith(m) for s in numbered):
            continue
        if m not in specific:
            specific.append(m)
    # Weak labels like a lone "Ace" need a Fitbit cue nearby.
    blob_l = blob.lower()
    has_brand = "fitbit" in blob_l or "pixel watch" in blob_l or "google health" in blob_l
    if not has_brand:
        specific = [m for m in specific if m not in WEAK_MODEL_LABELS]
    return specific
