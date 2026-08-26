"""Group reports by issue category + model so the dashboard is glanceable."""

from __future__ import annotations

from collections import defaultdict

from .classify import CATEGORY_LABELS_ES, SEVERITY_RANK
from .config import MAX_QUOTES_PER_CLUSTER, MAX_REPORTS_PER_CLUSTER
from .textutil import sha1


def _bucket_key(report: dict) -> tuple[str, str]:
    cat = report.get("primary_category") or "opinion"
    models = report.get("models") or []
    model = models[0] if models else "Sin modelo"
    return cat, model


def _severity_of(group: list[dict]) -> str:
    best = "info"
    for r in group:
        if SEVERITY_RANK.get(r.get("severity") or "info", 0) > SEVERITY_RANK.get(best, 0):
            best = r["severity"]
    return best


def cluster_reports(reports: list[dict], previous_index: dict | None = None) -> tuple[list[dict], dict]:
    previous_index = previous_index or {}
    prev_clusters = previous_index.get("clusters") or {}

    buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in reports:
        buckets[_bucket_key(r)].append(r)

    clusters = []
    new_index = {"clusters": {}}
    for (cat, model), group in buckets.items():
        cid = sha1("v2", cat, model)
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
                    "title": r.get("title"),
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
                "created_at": r.get("created_at"),
                "severity": r.get("severity"),
                "sentiment": r.get("sentiment"),
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
        sources = sorted({r.get("source_label") or r.get("source") for r in group})
        cluster = {
            "id": cid,
            "title": f"{CATEGORY_LABELS_ES.get(cat, cat)} · {model}",
            "category": cat,
            "category_label": CATEGORY_LABELS_ES.get(cat, cat),
            "severity": _severity_of(group),
            "models": models,
            "count": len(group),
            "recurring": bool(prev),
            "first_seen": prev.get("first_seen"),
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
        }

    clusters.sort(
        key=lambda c: (
            -SEVERITY_RANK.get(c["severity"], 0),
            -c["count"],
            c["category_label"],
        )
    )
    return clusters, new_index
