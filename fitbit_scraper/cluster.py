"""Group reports by polarity × category × model × issue fingerprint.

Similar titles merge; a mega "Sin modelo" dumpster of unrelated stories does not.
Cluster severity is the majority of high-confidence malas, never max of junk.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from .classify import CATEGORY_LABELS_ES, SEVERITY_RANK
from .config import LANG_LABELS_ES, MAX_QUOTES_PER_CLUSTER, MAX_REPORTS_PER_CLUSTER, POLARITY_LABELS_ES
from .engagement import format_engagement
from .textutil import jaccard, normalize, sha1, tokens

POLARITY_RANK = {"mala": 3, "revisar": 2, "buena": 1}
MERGE_JACCARD = 0.28


def _bucket_key(report: dict) -> tuple[str, str, str]:
    polarity = report.get("polarity") or "revisar"
    cat = report.get("primary_category") or "opinion"
    models = report.get("models") or []
    model = models[0] if models else "Sin modelo"
    return polarity, cat, model


def _title_tokens(report: dict) -> set[str]:
    raw = report.get("title") or ""
    toks = tokens(raw)
    if toks:
        return toks
    parts = [p for p in normalize(raw).split() if len(p) >= 3]
    return set(parts[:6])


def _issue_stem(report: dict) -> str:
    toks = sorted(_title_tokens(report))[:5]
    return " ".join(toks) if toks else "misc"


def _split_issue_groups(group: list[dict]) -> list[list[dict]]:
    """Greedy Jaccard split so unrelated headlines do not share a bucket."""
    leftover = list(group)
    groups: list[list[dict]] = []
    while leftover:
        seed = leftover.pop(0)
        seed_toks = _title_tokens(seed)
        member = [seed]
        rest = []
        for r in leftover:
            other = _title_tokens(r)
            if seed_toks and other and jaccard(seed_toks, other) >= MERGE_JACCARD:
                member.append(r)
            elif not seed_toks and not other:
                member.append(r)
            else:
                rest.append(r)
        leftover = rest
        groups.append(member)
    return groups


def _severity_of(group: list[dict], polarity: str) -> str | None:
    if polarity != "mala":
        return None
    high = [
        r
        for r in group
        if (r.get("confidence") or 0) >= 0.7 and r.get("severity")
    ]
    pool = high or [r for r in group if r.get("severity")]
    if not pool:
        return "baja"
    counts = Counter(r.get("severity") or "baja" for r in pool)
    order = ("baja", "media", "alta")
    best = max(order, key=lambda s: (counts.get(s, 0), -order.index(s)))
    if not high and best == "alta":
        return "media"
    return best


def _cluster_confidence(group: list[dict]) -> float:
    vals = [float(r["confidence"]) for r in group if isinstance(r.get("confidence"), (int, float))]
    if not vals:
        return 0.0
    return round(sum(vals) / len(vals), 2)


def _eng_rank(report: dict) -> int:
    eng = report.get("engagement") or {}
    total = 0
    for key in ("score", "comments", "views"):
        val = eng.get(key)
        if isinstance(val, (int, float)):
            total += int(val) if key != "views" else int(val) // 100
    return total


def _sum_engagement(group: list[dict]) -> dict:
    score = comments = views = 0
    known_score = known_comments = known_views = False
    for r in group:
        eng = r.get("engagement") or {}
        if eng.get("score") is not None:
            score += int(eng["score"])
            known_score = True
        if eng.get("comments") is not None:
            comments += int(eng["comments"])
            known_comments = True
        if eng.get("views") is not None:
            views += int(eng["views"])
            known_views = True
    packed = {
        "score": score if known_score else None,
        "comments": comments if known_comments else None,
        "views": views if known_views else None,
    }
    packed["label"] = format_engagement(packed)
    return packed


def _cluster_title(polarity: str, cat: str, model: str, headline: str) -> str:
    cat_label = CATEGORY_LABELS_ES.get(cat, cat)
    if polarity == "buena":
        if cat == "opinion":
            base = f"Elogio · {model}"
        else:
            base = f"Buena noticia · {cat_label} · {model}"
    elif polarity == "revisar":
        base = f"Revisar · {cat_label} · {model}"
    else:
        base = f"{cat_label} · {model}"
    hint = (headline or "").strip()
    if not hint:
        return base
    # Drop source suffixes so the issue stays readable.
    hint = hint.split(" - ")[0].split(" | ")[0].strip()
    if len(hint) > 72:
        hint = hint[:69].rstrip() + "…"
    if hint.lower() in base.lower():
        return base
    return f"{base} · {hint}"


def cluster_reports(reports: list[dict], previous_index: dict | None = None) -> tuple[list[dict], dict]:
    previous_index = previous_index or {}
    prev_clusters = previous_index.get("clusters") or {}

    buckets: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for r in reports:
        buckets[_bucket_key(r)].append(r)

    clusters = []
    new_index = {"clusters": {}}
    for (polarity, cat, model), coarse in buckets.items():
        for group in _split_issue_groups(coarse):
            stem = _issue_stem(group[0])
            cid = sha1("v4", polarity, cat, model, stem)
            prev = prev_clusters.get(cid) or {}
            ranked = sorted(
                group,
                key=lambda x: (
                    -_eng_rank(x),
                    -float(x.get("confidence") or 0),
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
                        "created_at": r.get("created_at") or r.get("published_at"),
                        "language": r.get("language"),
                        "model": (r.get("models") or [None])[0],
                        "engagement": r.get("engagement"),
                        "engagement_label": (r.get("engagement") or {}).get("label") or r.get("engagement_label"),
                        "confidence": r.get("confidence"),
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
                    "created_at": r.get("created_at") or r.get("published_at"),
                    "published_at": r.get("published_at") or r.get("created_at"),
                    "severity": r.get("severity"),
                    "sentiment": r.get("sentiment"),
                    "polarity": r.get("polarity") or polarity,
                    "language": r.get("language"),
                    "language_label": r.get("language_label"),
                    "models": r.get("models") or [],
                    "star_rating": r.get("star_rating"),
                    "engagement": r.get("engagement"),
                    "engagement_label": (r.get("engagement") or {}).get("label") or r.get("engagement_label"),
                    "confidence": r.get("confidence"),
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
            sources = sorted(
                {
                    r.get("source_label") or r.get("source")
                    for r in group
                    if r.get("source_label") or r.get("source")
                }
            )
            kinds = []
            langs = []
            for r in group:
                k = r.get("source_kind") or r.get("source")
                if k and k not in kinds:
                    kinds.append(k)
                lg = r.get("language")
                if lg and lg not in langs:
                    langs.append(lg)
            dates = [
                r.get("created_at") or r.get("published_at")
                for r in group
                if r.get("created_at") or r.get("published_at")
            ]
            severity = _severity_of(group, polarity)
            conf = _cluster_confidence(group)
            engagement = _sum_engagement(group)
            cluster = {
                "id": cid,
                "title": _cluster_title(polarity, cat, model, ranked[0].get("title") or stem),
                "category": cat,
                "category_label": CATEGORY_LABELS_ES.get(cat, cat),
                "polarity": polarity,
                "polarity_label": POLARITY_LABELS_ES.get(polarity, polarity),
                "severity": severity,
                "confidence": conf,
                "issue_stem": stem,
                "models": models,
                "languages": langs,
                "language_labels": [LANG_LABELS_ES.get(x, x) for x in langs],
                "source_kinds": kinds,
                "count": len(group),
                "recurring": bool(prev),
                "first_seen": prev.get("first_seen"),
                "last_report_at": max(dates) if dates else None,
                "seen_runs": int(prev.get("seen_runs") or 0) + 1,
                "engagement": engagement,
                "engagement_label": engagement.get("label"),
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
            -_eng_rank({"engagement": c.get("engagement") or {}}),
            -c["count"],
            c["category_label"],
        )
    )
    return clusters, new_index
