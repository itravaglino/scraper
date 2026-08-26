"""Relevance, polarity, category, language, and severity scoring.

Polarity is first-class:
  mala    — problem / complaint / recall (default product-ops view)
  buena   — praise, fix, feature win (never gets a severity badge)
  revisar — mixed or ambiguous (do not dump into gravedad media)

Severity (alta/media/baja) is assigned only to mala items.
"""

from __future__ import annotations

import re

from .config import (
    BRAND_CUES,
    CATEGORY_KEYWORDS,
    FIX_HEADLINE_CUES,
    LANG_LABELS_ES,
    LANG_MARKERS,
    MIXED_CUES,
    NEGATIVE_CUES,
    NEWS_ISSUE_CUES,
    OPEN_DEFECT_CUES,
    POLARITY_LABELS_ES,
    POSITIVE_CUES,
    REVIEW_CUES,
    SCREEN_NEGATIONS,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
)
from .models import detect_models
from .relevance import is_fitbit_subject

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

_CJK_JA = re.compile(r"[\u3040-\u30ff]")
_CJK_HAN = re.compile(r"[\u4e00-\u9fff]")
_HANGUL = re.compile(r"[\uac00-\ud7af]")


def _hits(text: str, phrases: list[str] | tuple[str, ...]) -> int:
    return sum(1 for p in phrases if p and p in text)


def detect_language(text: str, hint: str | None = None) -> str:
    """Best-effort language from script + distinctive tokens. Never crashes."""
    blob = text or ""
    if _HANGUL.search(blob):
        return "ko"
    if _CJK_JA.search(blob):
        return "ja"
    if _CJK_HAN.search(blob):
        return "zh"
    low = blob.lower()
    scores: dict[str, int] = {}
    for lang, markers in LANG_MARKERS.items():
        n = _hits(low, markers)
        if n:
            scores[lang] = n
    if scores:
        best = max(scores, key=lambda k: (scores[k], 0 if k != "en" else -1))
        if scores[best] >= 1:
            return best
    if hint and hint not in {"", "und", "unknown"} and hint in LANG_LABELS_ES:
        return hint
    if re.search(r"[a-záéíóúüñ]{4,}", low, flags=re.I) and not re.search(
        r"[àèùâêîôûäëïöüÿßãõçáéíóúñ]", low
    ):
        # ASCII / English letters without other-language diacritics.
        return "en"
    return hint if hint else "und"


def _title_has(title_low: str, phrases: list[str]) -> bool:
    return _hits(title_low, phrases) > 0


def _decide_polarity(
    title_low: str,
    full_low: str,
    pos: int,
    neg: int,
    cat_scores: dict[str, int],
    star_rating: int | None,
) -> str:
    """Precision on mala: good news must not enter the problem queue."""
    title_fix = _title_has(title_low, FIX_HEADLINE_CUES)
    title_open = _title_has(title_low, OPEN_DEFECT_CUES)
    open_defect = _hits(full_low, OPEN_DEFECT_CUES) > 0
    mixed = _hits(full_low, MIXED_CUES) > 0

    if star_rating is not None and star_rating <= 2:
        if title_fix and star_rating >= 2 and pos > neg:
            return "buena"
        return "mala"
    if title_open or (open_defect and neg >= 1 and not title_fix):
        return "mala"
    if title_fix and not title_open:
        return "buena"
    if star_rating is not None and star_rating >= 4 and pos >= neg:
        return "buena"
    if pos >= 2 and neg == 0:
        return "buena"
    if pos > neg and not open_defect:
        return "buena"
    if neg >= 2 and pos == 0:
        return "mala"
    if neg > pos and not title_fix:
        return "mala"
    if mixed and (pos or neg or cat_scores):
        return "revisar"
    if pos and neg:
        return "revisar"
    if _hits(title_low, REVIEW_CUES) and not _hits(full_low, SEVERITY_HIGH) and neg <= 1:
        if pos > 0:
            return "buena"
        return "revisar"
    # Category keywords alone (e.g. "battery" in a feature article) are not a defect.
    issue_signal = (
        _hits(full_low, NEGATIVE_CUES)
        or _hits(full_low, NEWS_ISSUE_CUES)
        or _hits(full_low, SEVERITY_HIGH)
        or _hits(full_low, SEVERITY_MEDIUM)
        or (star_rating is not None and star_rating <= 3)
    )
    if cat_scores and issue_signal and pos == 0:
        return "mala"
    if cat_scores and pos == 0 and neg == 0:
        return "revisar"
    return "revisar"


def classify(
    title: str,
    body: str,
    source_scoped: bool = True,
    star_rating: int | None = None,
    lang_hint: str | None = None,
    url: str = "",
) -> dict:
    text = f"{title or ''}\n{body or ''}"
    low = text.lower()
    title_low = (title or "").lower()
    models = detect_models(text)
    lang = detect_language(text, hint=lang_hint)

    on_topic, topic_reason = is_fitbit_subject(
        title, body, url, source_scoped=source_scoped
    )
    if not on_topic:
        return {
            "keep": False,
            "models": models,
            "categories": [],
            "primary_category": None,
            "severity": None,
            "sentiment": "neutral",
            "polarity": "revisar",
            "polarity_label": POLARITY_LABELS_ES["revisar"],
            "language": lang,
            "language_label": LANG_LABELS_ES.get(lang, lang),
            "badges": [],
            "reason": topic_reason,
        }

    cat_scores: dict[str, int] = {}
    for cat, words in CATEGORY_KEYWORDS.items():
        score = _hits(low, words)
        if score:
            cat_scores[cat] = score
    if any(n in low for n in SCREEN_NEGATIONS):
        cat_scores.pop("pantalla", None)

    brand_hit = any(c in low for c in BRAND_CUES) or bool(models)
    if not source_scoped and not brand_hit:
        return {
            "keep": False,
            "models": [],
            "categories": [],
            "primary_category": None,
            "severity": None,
            "sentiment": "neutral",
            "polarity": "revisar",
            "polarity_label": POLARITY_LABELS_ES["revisar"],
            "language": lang,
            "language_label": LANG_LABELS_ES.get(lang, lang),
            "badges": [],
            "reason": "fuera_de_marca",
        }

    pos = _hits(low, POSITIVE_CUES)
    neg = _hits(low, NEGATIVE_CUES)
    if star_rating is not None:
        if star_rating <= 2:
            neg += 2
        elif star_rating >= 4:
            pos += 1

    # Unscoped launch/deal posts: only keep if they look like an issue, a fix, or praise.
    news_like = (
        _hits(low, NEWS_ISSUE_CUES)
        or _hits(low, POSITIVE_CUES)
        or _hits(low, FIX_HEADLINE_CUES)
        or _hits(low, NEGATIVE_CUES)
        or _hits(low, SEVERITY_HIGH)
        or _hits(low, SEVERITY_MEDIUM)
    )
    if not source_scoped and cat_scores and not news_like:
        cat_scores = {}

    polarity = _decide_polarity(title_low, low, pos, neg, cat_scores, star_rating)

    if cat_scores:
        primary = max(cat_scores, key=cat_scores.get)
        categories = sorted(cat_scores, key=lambda c: (-cat_scores[c], c))
        reason = "incidencia" if polarity == "mala" else (
            "buena_noticia" if polarity == "buena" else "revisar"
        )
    elif star_rating is not None and star_rating <= 3:
        primary = "software"
        categories = ["software"]
        polarity = "mala" if polarity != "buena" else polarity
        reason = "reseña_baja"
    elif polarity == "buena" and brand_hit:
        primary = "opinion" if not cat_scores else max(cat_scores, key=cat_scores.get)
        categories = [primary]
        reason = "opinion_positiva"
    elif source_scoped and brand_hit:
        primary = "opinion"
        categories = ["opinion"]
        reason = "sin_incidencia" if polarity == "revisar" else (
            "buena_noticia" if polarity == "buena" else "incidencia"
        )
    else:
        return {
            "keep": False,
            "models": models,
            "categories": [],
            "primary_category": None,
            "severity": None,
            "sentiment": "neutral",
            "polarity": "revisar",
            "polarity_label": POLARITY_LABELS_ES["revisar"],
            "language": lang,
            "language_label": LANG_LABELS_ES.get(lang, lang),
            "badges": [],
            "reason": "irrelevante",
        }

    # Keep rules: prefer precision on the problem queue.
    if polarity == "mala":
        keep = bool(
            cat_scores
            or (star_rating is not None and star_rating <= 3)
            or _hits(low, NEWS_ISSUE_CUES)
            or _hits(low, NEGATIVE_CUES)
            or _hits(low, SEVERITY_HIGH)
        )
    elif polarity == "buena":
        keep = brand_hit and (
            pos >= 1
            or _hits(title_low, FIX_HEADLINE_CUES) > 0
            or (star_rating is not None and star_rating >= 4)
        )
    else:
        keep = bool(
            (source_scoped and brand_hit and (cat_scores or pos or neg or star_rating is not None))
            or (brand_hit and cat_scores)
        )

    if polarity == "buena":
        sentiment = "positivo"
        severity = None
        badges = ["positivo", "buena noticia"]
    elif polarity == "mala":
        sentiment = "negativo"
        if _hits(low, SEVERITY_HIGH):
            severity = "alta"
        elif _hits(low, SEVERITY_MEDIUM) or (star_rating is not None and star_rating <= 2):
            severity = "media"
        else:
            severity = "baja"
        if star_rating == 1 and severity == "baja":
            severity = "media"
        badges = [f"gravedad {severity}"]
    else:
        sentiment = "mixto"
        severity = None
        badges = ["revisar"]

    return {
        "keep": keep,
        "models": models,
        "categories": categories,
        "primary_category": primary,
        "severity": severity,
        "sentiment": sentiment,
        "polarity": polarity,
        "polarity_label": POLARITY_LABELS_ES[polarity],
        "language": lang,
        "language_label": LANG_LABELS_ES.get(lang, lang),
        "badges": badges,
        "reason": reason,
        "category_scores": cat_scores,
    }
