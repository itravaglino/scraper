"""Group reports by polarity + case (category × model).

A praise about GPS on Charge 6 never sits inside a Charge 6 battery-bug pile.
Severity is only meaningful on negative (mala) clusters.
"""

from __future__ import annotations

from collections import defaultdict

from .classify import CATEGORY_LABELS_ES, SEVERITY_RANK
from .config import LANG_LABELS_ES, MAX_QUOTES_PER_CLUSTER, MAX_REPORTS_PER_CLUSTER, POLARITY_LABELS_ES
from .textutil import sha1

POLARITY_RANK = {"mala": 3, "revisar": 2, "buena": 1}


def _bucket_key(report: dict) -> tuple[str, str, str]:
    polarity = report.get("polarity") or "revisar"
    cat = report.get("primary_category") or "opinion"
    models = report.get("models") or []
    model = models[0] if models else "Sin modelo"
    return polarity, cat, model


def _severity_of(group: list[dict], polarity: str) -> str | None:
    if polarity != "mala":
        return None
    best = None
    best_rank = -1
    for r in group:
        sev = r.get("severity")
        if not sev:
            continue
        rank = SEVERITY_RANK.get(sev, 0)
        if rank > best_rank:
            best = sev
            best_rank = rank
    return best or "baja"


def _cluster_title(polarity: str, cat: str, model: str) -> str:
    cat_label = CATEGORY_LABELS_ES.get(cat, cat)
    if polarity == "buena":
        if cat == "opinion":
            return f"Elogio · {model}"
        return f"Buena noticia · {cat_label} · {model}"
    if polarity == "revisar":
        return f"Revisar · {cat_label} · {model}"
    return f"{cat_label} · {model}"


def cluster_reports(reports: list[dict], previous_index: dict | None = None) -> tuple[list[dict], dict]:
    previous_index = previous_index or {}
    prev_clusters = previous_index.get("clusters") or {}

    buckets: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for r in reports:
        buckets[_bucket_key(r)].append(r)

    clusters = []
    new_index = {"clusters": {}}
    for (polarity, cat, model), group in buckets.items():
        cid = sha1("v3", polarity, cat, model)
        prev = prev_clusters.get(cid) or {}
        ranked = sorted(
            group,
            key=lambda x: (
                -SEVERITY_RANK.get(x.get("severity") or "info", 0),
                -(len(x.get("text") or "")),
            ),
        )
        quotes = []
        for r in ranked:
            snippet = (r.get("text") or r.get("title") or "").strip()
            if not snippet:
                continue
            quotes.append(
                {
                    "text": snippet[:280],
                    "url": r.get("url"),
                    "source": r.get("source_label"),
                    "source_kind": r.get("source_kind") or r.get("source"),
                    "title": r.get("title"),
                    "created_at": r.get("created_at"),
                    "language": r.get("language"),
                    "model": (r.get("models") or [None])[0],
                }
            )
            if len(quotes) >= MAX_QUOTES_PER_CLUSTER:
                break
        compact = [
            {
                "id": r["id"],
                "title": r.get("title"),
                "url": r.get("url"),
                "source": r.get("source_label"),
                "source_kind": r.get("source_kind") or r.get("source"),
                "created_at": r.get("created_at"),
                "severity": r.get("severity"),
                "sentiment": r.get("sentiment"),
                "polarity": r.get("polarity") or polarity,
                "language": r.get("language"),
                "language_label": r.get("language_label"),
                "models": r.get("models") or [],
                "star_rating": r.get("star_rating"),
            }
            for r in ranked[:MAX_REPORTS_PER_CLUSTER]
        ]
        models = []
        for r in group:
            for m in r.get("models") or []:
                if m not in models:
                    models.append(m)
        if model not in models:
            models.insert(0, model)
        sources = sorted({r.get("source_label") or r.get("source") for r in group if r.get("source_label") or r.get("source")})
        kinds = []
        langs = []
        for r in group:
            k = r.get("source_kind") or r.get("source")
            if k and k not in kinds:
                kinds.append(k)
            lg = r.get("language")
            if lg and lg not in langs:
                langs.append(lg)
        dates = [r.get("created_at") for r in group if r.get("created_at")]
        severity = _severity_of(group, polarity)
        cluster = {
            "id": cid,
            "title": _cluster_title(polarity, cat, model),
            "category": cat,
            "category_label": CATEGORY_LABELS_ES.get(cat, cat),
            "polarity": polarity,
            "polarity_label": POLARITY_LABELS_ES.get(polarity, polarity),
            "severity": severity,
            "models": models,
            "languages": langs,
            "language_labels": [LANG_LABELS_ES.get(x, x) for x in langs],
            "source_kinds": kinds,
            "count": len(group),
            "recurring": bool(prev),
            "first_seen": prev.get("first_seen"),
            "last_report_at": max(dates) if dates else None,
            "seen_runs": int(prev.get("seen_runs") or 0) + 1,
            "quotes": quotes,
            "sources": sources,
            "reports": compact,
        }
        clusters.append(cluster)
        new_index["clusters"][cid] = {
            "first_seen": prev.get("first_seen"),
            "seen_runs": cluster["seen_runs"],
            "peak_count": max(int(prev.get("peak_count") or 0), len(group)),
            "title": cluster["title"],
            "category": cat,
            "polarity": polarity,
        }

    clusters.sort(
        key=lambda c: (
            -POLARITY_RANK.get(c.get("polarity") or "revisar", 0),
            -SEVERITY_RANK.get(c.get("severity") or "info", 0),
            -c["count"],
            c["category_label"],
        )
    )
    return clusters, new_index
