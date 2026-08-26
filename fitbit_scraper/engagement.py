"""Parse and format public engagement stats. Never invent a number."""

from __future__ import annotations

import re
from typing import Any

_VIEWS = re.compile(
    r"(\d[\d.,]*)\s*([kKmM])?\s*(?:views?|vistas?|visualizaciones?|vues?|aufrufe)",
    re.I,
)
_COMMENTS = re.compile(
    r"(\d[\d.,]*)\s*(?:comments?|comentarios?|commentaires?|kommentare)",
    re.I,
)
_SCORE = re.compile(
    r"(?:score[:\s]+|↑\s*)(\d+)\b|(\d+)\s*(?:points?|upvotes?|pts)\b",
    re.I,
)


def _to_int(raw: str, suffix: str = "") -> int | None:
    try:
        n = float(raw.replace(",", "").replace(" ", ""))
    except ValueError:
        return None
    if suffix.lower() == "k":
        n *= 1_000
    elif suffix.lower() == "m":
        n *= 1_000_000
    if n < 0:
        return None
    return int(n)


def parse_engagement_text(text: str) -> dict[str, int | None]:
    blob = text or ""
    views = comments = score = None
    vm = _VIEWS.search(blob)
    if vm:
        views = _to_int(vm.group(1), vm.group(2) or "")
    cm = _COMMENTS.search(blob)
    if cm:
        comments = _to_int(cm.group(1))
    sm = _SCORE.search(blob)
    if sm:
        score = _to_int(sm.group(1) or sm.group(2) or "")
    return {"score": score, "comments": comments, "views": views}


def merge_engagement(*parts: dict | None) -> dict[str, int | None]:
    out: dict[str, int | None] = {"score": None, "comments": None, "views": None}
    for part in parts:
        if not part:
            continue
        for key in out:
            val = part.get(key)
            if val is None:
                continue
            try:
                n = int(val)
            except (TypeError, ValueError):
                continue
            if out[key] is None:
                out[key] = n
            else:
                out[key] = max(out[key], n)
    return out


def format_engagement(eng: dict | None) -> str | None:
    """Spanish label, or None when every stat is unknown (UI shows n/d)."""
    if not eng:
        return None
    parts = []
    if eng.get("score") is not None:
        parts.append(f"{int(eng['score'])} pts")
    if eng.get("comments") is not None:
        n = int(eng["comments"])
        parts.append(f"{n} comentario{'s' if n != 1 else ''}")
    if eng.get("views") is not None:
        parts.append(f"{int(eng['views'])} vistas")
    return " · ".join(parts) if parts else None


def empty_engagement() -> dict[str, Any]:
    return {"score": None, "comments": None, "views": None, "label": None}


def pack_engagement(**kwargs) -> dict[str, Any]:
    eng = merge_engagement(kwargs)
    return {**eng, "label": format_engagement(eng)}
