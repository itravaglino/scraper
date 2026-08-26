"""HTML stripping, dates, hashing, and tokenization."""

from __future__ import annotations

import hashlib
import html as html_lib
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

from .config import STOPWORDS

_TAG = re.compile(r"(?is)<(script|style).*?>.*?</\1>|<[^>]+>")
_WS = re.compile(r"\s+")
_WORD = re.compile(r"[a-záéíóúüñ0-9]{4,}", re.I)


def strip_html(text: str) -> str:
    if not text:
        return ""
    text = _TAG.sub(" ", text)
    text = html_lib.unescape(text)
    return _WS.sub(" ", text).strip()


def sha1(*parts: str) -> str:
    h = hashlib.sha1()
    for p in parts:
        h.update((p or "").encode("utf-8", "replace"))
        h.update(b"\0")
    return h.hexdigest()[:16]


def parse_datetime(value: Optional[str]) -> Optional[str]:
    """Return UTC ISO-8601 or None. Accepts Atom, RFC 2822, and ISO strings."""
    if not value:
        return None
    raw = value.strip()
    try:
        if raw.endswith("Z"):
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError):
        return None


def normalize(text: str) -> str:
    return re.sub(r"[^a-záéíóúüñ0-9]+", " ", (text or "").lower()).strip()


def tokens(text: str) -> set[str]:
    return {m.group(0).lower() for m in _WORD.finditer(text or "") if m.group(0).lower() not in STOPWORDS}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0
