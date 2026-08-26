"""Relevance, category, sentiment, and severity scoring."""

from __future__ import annotations

from .config import (
    BRAND_CUES,
    CATEGORY_KEYWORDS,
    NEGATIVE_CUES,
    NEWS_ISSUE_CUES,
    POSITIVE_CUES,
    SCREEN_NEGATIONS,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
)
from .models import detect_models

CATEGORY_LABELS_ES = {
    "bateria": "Batería",
    "carga": "Carga",
    "sincronizacion": "Sincronización",
    "software": "Software / app",
    "pantalla": "Pantalla",
    "correa": "Correa",
    "ritmo_cardiaco": "Ritmo cardíaco",
    "gps": "GPS",
    "calidad": "Calidad / hardware",
    "piel": "Piel / alergia",
    "opinion": "Opinión",
}

SEVERITY_RANK = {"alta": 3, "media": 2, "baja": 1, "info": 0}


def _hits(text: str, phrases: list[str]) -> int:
    return sum(1 for p in phrases if p in text)


def classify(title: str, body: str, source_scoped: bool = True, star_rating: int | None = None) -> dict:
    text = f"{title or ''}\n{body or ''}"
    low = text.lower()
    models = detect_models(text)

    cat_scores: dict[str, int] = {}
    for cat, words in CATEGORY_KEYWORDS.items():
        score = _hits(low, words)
        if score:
            cat_scores[cat] = score
    if any(n in low for n in SCREEN_NEGATIONS):
        cat_scores.pop("pantalla", None)
    if not source_scoped and cat_scores and not _hits(low, NEWS_ISSUE_CUES):
        cat_scores = {}

    brand_hit = any(c in low for c in BRAND_CUES) or bool(models)
    if not source_scoped and not brand_hit:
        return {
            "keep": False,
            "models": [],
            "categories": [],
            "primary_category": None,
            "severity": "info",
            "sentiment": "neutral",
            "reason": "fuera_de_marca",
        }

    pos = _hits(low, POSITIVE_CUES)
    neg = _hits(low, NEGATIVE_CUES)
    if star_rating is not None:
        if star_rating <= 2:
            neg += 2
        elif star_rating >= 4:
            pos += 1

    if cat_scores:
        primary = max(cat_scores, key=cat_scores.get)
        categories = sorted(cat_scores, key=lambda c: (-cat_scores[c], c))
        sentiment = "negativo" if neg >= pos else ("positivo" if pos > neg else "negativo")
        keep = True
        reason = "incidencia"
    elif star_rating is not None and star_rating <= 3:
        primary = "software"
        categories = ["software"]
        sentiment = "negativo"
        keep = True
        reason = "reseña_baja"
    elif pos and brand_hit and source_scoped:
        primary = "opinion"
        categories = ["opinion"]
        sentiment = "positivo"
        keep = pos >= 2 or (star_rating is not None and star_rating >= 4)
        reason = "opinion_positiva"
    else:
        # Source-scoped Fitbit posts with no issue keywords: keep as weak opinion
        # only when the source is already a Fitbit community, otherwise drop.
        if source_scoped and brand_hit:
            primary = "opinion"
            categories = ["opinion"]
            sentiment = "neutral"
            keep = False
            reason = "sin_incidencia"
        else:
            return {
                "keep": False,
                "models": models,
                "categories": [],
                "primary_category": None,
                "severity": "info",
                "sentiment": "neutral",
                "reason": "irrelevante",
            }

    if _hits(low, SEVERITY_HIGH):
        severity = "alta"
    elif _hits(low, SEVERITY_MEDIUM) or (star_rating is not None and star_rating <= 2):
        severity = "media"
    elif primary == "opinion" and sentiment == "positivo":
        severity = "info"
    else:
        severity = "baja"

    if star_rating == 1 and severity == "baja":
        severity = "media"

    return {
        "keep": keep,
        "models": models,
        "categories": categories,
        "primary_category": primary,
        "severity": severity,
        "sentiment": sentiment,
        "reason": reason,
        "category_scores": cat_scores,
    }
