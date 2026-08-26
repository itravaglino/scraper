"""Relevance, polarity, category, language, and severity scoring.

Polarity is first-class:
  mala    — problem / complaint / recall (default product-ops view)
  buena   — praise, fix, feature win (never gets a severity badge)
  revisar — mixed or ambiguous (do not dump into gravedad media)

Severity (alta/media/baja) is assigned only to mala items, and only when
confidence is high enough. Title cues outweigh body/footer noise.
"""

from __future__ import annotations

import re

from .config import (
    BRAND_CUES,
    CATEGORY_KEYWORDS,
    COMPARISON_TITLE_CUES,
    CONF_ALTA,
    CONF_MALA,
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
    STRONG_DEFECT_CUES,
    TUTORIAL_TITLE_CUES,
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
_PHRASE_CACHE: dict[str, re.Pattern[str]] = {}


def _phrase_in(text: str, phrase: str) -> bool:
    """Token hit. Short English words must not match inside longer tokens."""
    if not phrase or not text:
        return False
    p = phrase.lower()
    if not p.isascii():
        return p in text
    rx = _PHRASE_CACHE.get(p)
    if rx is None:
        rx = re.compile(rf"(?<![a-z0-9]){re.escape(p)}(?![a-z0-9])")
        _PHRASE_CACHE[p] = rx
    return rx.search(text) is not None


def _hits(text: str, phrases: list[str] | tuple[str, ...]) -> int:
    return sum(1 for p in phrases if p and _phrase_in(text, p))


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
        return "en"
    return hint if hint else "und"


def _weighted(title_low: str, body_low: str, phrases: list[str] | tuple[str, ...]) -> int:
    return 3 * _hits(title_low, phrases) + _hits(body_low, phrases)


def _is_comparison_title(title_low: str) -> bool:
    if _hits(title_low, COMPARISON_TITLE_CUES) > 0:
        return True
    return bool(
        re.search(
            r"\bvs\.?\b|\bversus\b|\balongside\b|\bi wore both\b|"
            r"\bafter \d+ days wearing\b|\bfinal verdict\b",
            title_low,
        )
    )


def _title_defect(title_low: str) -> bool:
    return (
        _hits(title_low, OPEN_DEFECT_CUES) > 0
        or _hits(title_low, STRONG_DEFECT_CUES) > 0
        or _hits(title_low, SEVERITY_HIGH) > 0
    )


def _decide_polarity(
    title_low: str,
    body_low: str,
    pos_body: int,
    neg_body: int,
    cat_scores: dict[str, int],
    star_rating: int | None,
) -> str:
    """Precision on mala: footer tokens and praise titles must not enter the queue."""
    title_fix = _hits(title_low, FIX_HEADLINE_CUES) > 0
    title_open = _hits(title_low, OPEN_DEFECT_CUES) > 0
    title_def = _title_defect(title_low)
    title_neg = _hits(title_low, NEGATIVE_CUES)
    title_pos = _hits(title_low, POSITIVE_CUES)
    w_pos = 3 * title_pos + pos_body
    w_neg = 3 * title_neg + neg_body
    comparison = _is_comparison_title(title_low)
    tutorial = _hits(title_low, TUTORIAL_TITLE_CUES) > 0
    mixed = _hits(title_low, MIXED_CUES) > 0 or _hits(body_low, MIXED_CUES) > 0

    if star_rating is not None and star_rating <= 2:
        if title_fix and star_rating >= 2 and w_pos > w_neg:
            return "buena"
        return "mala"
    if title_fix and not title_open:
        return "buena"
    if (comparison or tutorial) and not title_open:
        if w_pos > w_neg:
            return "buena"
        return "revisar"
    if title_def and not title_fix:
        return "mala"
    if star_rating is not None and star_rating >= 4 and w_pos >= w_neg:
        return "buena"
    if w_pos >= 6 and w_neg == 0:
        return "buena"
    if w_pos > w_neg and not title_def:
        return "buena"
    if w_neg >= 6 and w_pos == 0 and (title_neg or title_def):
        return "mala"
    if w_neg > w_pos and not title_fix:
        if title_neg or title_def or (neg_body >= 2 and cat_scores and title_pos == 0):
            return "mala"
        return "revisar"
    if mixed and (w_pos or w_neg or cat_scores):
        return "revisar"
    if title_pos and title_neg:
        return "revisar"
    if _hits(title_low, REVIEW_CUES) and not _hits(title_low, SEVERITY_HIGH) and w_neg <= 3:
        if w_pos > 0:
            return "buena"
        return "revisar"
    issue_signal = (
        title_neg
        or title_def
        or _hits(title_low, NEWS_ISSUE_CUES)
        or (neg_body >= 2 and title_pos == 0)
        or (star_rating is not None and star_rating <= 3)
    )
    if cat_scores and issue_signal and w_pos == 0:
        return "mala"
    if cat_scores and w_pos == 0 and w_neg == 0:
        return "revisar"
    return "revisar"


def _confidence(
    *,
    title_low: str,
    polarity: str,
    star_rating: int | None,
    topic_reason: str,
    title_def: bool,
    comparison: bool,
) -> float:
    c = 0.22
    if title_def:
        c += 0.4
    tn = _hits(title_low, NEGATIVE_CUES)
    c += 0.12 * min(tn, 2)
    if _hits(title_low, SEVERITY_HIGH) > 0:
        c += 0.15
    if star_rating is not None and star_rating <= 2:
        c += 0.2
    if (comparison or _hits(title_low, TUTORIAL_TITLE_CUES) > 0) and not title_def:
        c -= 0.35
    if _hits(title_low, POSITIVE_CUES) > tn:
        c -= 0.2
    if topic_reason == "comunidad_sin_producto" and star_rating is None:
        c -= 0.25
    if polarity == "revisar":
        c = min(c, 0.48)
    return round(max(0.0, min(1.0, c)), 2)


def _pack(
    *,
    keep: bool,
    models: list[str],
    lang: str,
    polarity: str,
    reason: str,
    categories: list[str] | None = None,
    primary: str | None = None,
    severity: str | None = None,
    sentiment: str = "neutral",
    badges: list[str] | None = None,
    cat_scores: dict | None = None,
    confidence: float = 0.0,
) -> dict:
    return {
        "keep": keep,
        "models": models,
        "categories": categories or [],
        "primary_category": primary,
        "severity": severity,
        "sentiment": sentiment,
        "polarity": polarity,
        "polarity_label": POLARITY_LABELS_ES[polarity],
        "language": lang,
        "language_label": LANG_LABELS_ES.get(lang, lang),
        "badges": badges or [],
        "reason": reason,
        "category_scores": cat_scores or {},
        "confidence": confidence,
    }


def classify(
    title: str,
    body: str,
    source_scoped: bool = True,
    star_rating: int | None = None,
    lang_hint: str | None = None,
    url: str = "",
) -> dict:
    title = title or ""
    body = body or ""
    title_low = title.lower()
    body_low = body.lower()
    low = f"{title_low}\n{body_low}"
    models = detect_models(f"{title}\n{body}")
    lang = detect_language(f"{title}\n{body}", hint=lang_hint)

    on_topic, topic_reason = is_fitbit_subject(
        title, body, url, source_scoped=source_scoped
    )
    if not on_topic:
        return _pack(
            keep=False,
            models=models,
            lang=lang,
            polarity="revisar",
            reason=topic_reason,
        )

    cat_scores: dict[str, int] = {}
    for cat, words in CATEGORY_KEYWORDS.items():
        score = 3 * _hits(title_low, words) + _hits(body_low, words)
        if score:
            cat_scores[cat] = score
    if any(_phrase_in(low, n) for n in SCREEN_NEGATIONS):
        cat_scores.pop("pantalla", None)

    brand_hit = any(_phrase_in(low, c) for c in BRAND_CUES) or bool(models)
    if not source_scoped and not brand_hit:
        return _pack(
            keep=False,
            models=[],
            lang=lang,
            polarity="revisar",
            reason="fuera_de_marca",
        )

    pos_body = _hits(body_low, POSITIVE_CUES)
    neg_body = _hits(body_low, NEGATIVE_CUES)
    pos = _weighted(title_low, body_low, POSITIVE_CUES)
    neg = _weighted(title_low, body_low, NEGATIVE_CUES)
    if star_rating is not None:
        if star_rating <= 2:
            neg_body += 2
            neg += 2
        elif star_rating >= 4:
            pos_body += 1
            pos += 1

    news_like = (
        _weighted(title_low, body_low, NEWS_ISSUE_CUES)
        or pos
        or _hits(title_low, FIX_HEADLINE_CUES)
        or neg
        or _weighted(title_low, body_low, SEVERITY_HIGH)
        or _weighted(title_low, body_low, SEVERITY_MEDIUM)
    )
    if not source_scoped and cat_scores and not news_like:
        cat_scores = {}

    polarity = _decide_polarity(
        title_low, body_low, pos_body, neg_body, cat_scores, star_rating
    )
    title_def = _title_defect(title_low)
    comparison = _is_comparison_title(title_low)

    if topic_reason == "comunidad_sin_producto" and star_rating is None:
        if polarity == "mala" and not title_def:
            polarity = "revisar"

    if cat_scores:
        primary = max(cat_scores, key=cat_scores.get)
        categories = sorted(cat_scores, key=lambda c: (-cat_scores[c], c))
        reason = (
            "incidencia"
            if polarity == "mala"
            else ("buena_noticia" if polarity == "buena" else "revisar")
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
    elif source_scoped and (brand_hit or topic_reason.startswith("comunidad")):
        primary = "opinion"
        categories = ["opinion"]
        reason = (
            "sin_incidencia"
            if polarity == "revisar"
            else ("buena_noticia" if polarity == "buena" else "incidencia")
        )
    else:
        return _pack(
            keep=False,
            models=models,
            lang=lang,
            polarity="revisar",
            reason="irrelevante",
        )

    if polarity == "mala":
        keep = bool(
            cat_scores
            or (star_rating is not None and star_rating <= 3)
            or title_def
            or _hits(title_low, NEWS_ISSUE_CUES)
            or _hits(title_low, NEGATIVE_CUES)
        )
    elif polarity == "buena":
        keep = brand_hit and (
            pos >= 1
            or _hits(title_low, FIX_HEADLINE_CUES) > 0
            or (star_rating is not None and star_rating >= 4)
        )
    else:
        keep = bool(
            (
                source_scoped
                and (brand_hit or topic_reason.startswith("comunidad"))
                and (cat_scores or pos or neg or star_rating is not None)
            )
            or (brand_hit and cat_scores)
        )

    conf = _confidence(
        title_low=title_low,
        polarity=polarity,
        star_rating=star_rating,
        topic_reason=topic_reason,
        title_def=title_def,
        comparison=comparison,
    )

    if polarity == "buena":
        sentiment = "positivo"
        severity = None
        badges = ["positivo", "buena noticia"]
    elif polarity == "mala":
        sentiment = "negativo"
        title_high = _hits(title_low, SEVERITY_HIGH) > 0
        if (
            conf >= CONF_ALTA
            and title_def
            and (title_high or _hits(title_low, OPEN_DEFECT_CUES) > 0 or _hits(title_low, STRONG_DEFECT_CUES) > 0)
        ):
            severity = "alta"
        elif _hits(title_low, SEVERITY_MEDIUM) or (
            star_rating is not None and star_rating <= 2
        ):
            severity = "media"
        elif _hits(body_low, SEVERITY_MEDIUM) and _hits(title_low, NEGATIVE_CUES):
            severity = "media"
        else:
            severity = "baja"
        if star_rating == 1 and severity == "baja":
            severity = "media"
        if conf < CONF_MALA:
            polarity = "revisar"
            severity = None
            sentiment = "mixto"
            badges = ["revisar", f"confianza {conf:.0%}"]
            reason = "baja_confianza"
        else:
            badges = [f"gravedad {severity}", f"confianza {conf:.0%}"]
    else:
        sentiment = "mixto"
        severity = None
        badges = ["revisar", f"confianza {conf:.0%}"]

    return _pack(
        keep=keep,
        models=models,
        lang=lang,
        polarity=polarity,
        reason=reason,
        categories=categories,
        primary=primary,
        severity=severity,
        sentiment=sentiment,
        badges=badges,
        cat_scores=cat_scores,
        confidence=conf,
    )
