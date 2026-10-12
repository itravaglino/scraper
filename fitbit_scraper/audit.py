"""Audit every report in a scrape payload for Fitbit / Google Health relevance.

Uses the production classifier plus community-URL scoping so Google News
mislabeled as community.fitbit.com is scored as news, not as a forum post.
Writes reports/relevance_audit.csv and a per-source count file.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from .classify import classify
from .pipeline import ROOT, _community_scoped

SAMPLE_PER_KIND = 6


def audit_item(
    title: str,
    body: str = "",
    url: str = "",
    *,
    source_scoped: bool = False,
    source_kind: str = "",
    star_rating: int | None = None,
) -> dict:
    info = classify(
        title,
        body,
        source_scoped=source_scoped,
        star_rating=star_rating,
        url=url,
    )
    if info.get("keep"):
        return {
            "verdict": "keep",
            "reason": info.get("reason") or "sujeto_fitbit",
            "polarity": info.get("polarity") or "revisar",
        }
    return {
        "verdict": "drop",
        "reason": info.get("reason") or "irrelevante",
        "polarity": info.get("polarity") or "revisar",
    }


def audit_payload(payload: dict) -> tuple[list[dict], dict]:
    rows = []
    by_source = defaultdict(lambda: Counter())
    reasons = Counter()
    polarity_keep = Counter()
    polarity_old = Counter()
    for r in payload.get("reports") or []:
        scoped = _community_scoped(r)
        verdict = audit_item(
            r.get("title") or "",
            r.get("text") or "",
            r.get("url") or "",
            source_scoped=scoped,
            source_kind=r.get("source_kind") or "",
            star_rating=r.get("star_rating"),
        )
        kind = r.get("source_kind") or r.get("source") or "web"
        label = r.get("source_label") or kind
        old_pol = r.get("polarity") or ""
        polarity_old[old_pol] += 1
        row = {
            "id": r.get("id") or "",
            "source_kind": kind,
            "source_label": label,
            "old_polarity": old_pol,
            "title": (r.get("title") or "").replace("\n", " ")[:240],
            "url": r.get("url") or "",
            "verdict": verdict["verdict"],
            "drop_reason": verdict["reason"] if verdict["verdict"] == "drop" else "",
            "keep_reason": verdict["reason"] if verdict["verdict"] == "keep" else "",
            "suggested_polarity": verdict["polarity"],
        }
        rows.append(row)
        key = f"{kind} | {label}"
        by_source[key][verdict["verdict"]] += 1
        if verdict["verdict"] == "drop":
            by_source[key][f"drop:{verdict['reason']}"] += 1
            reasons[verdict["reason"]] += 1
        else:
            polarity_keep[verdict["polarity"]] += 1
    summary = {
        "total": len(rows),
        "keep": sum(1 for x in rows if x["verdict"] == "keep"),
        "drop": sum(1 for x in rows if x["verdict"] == "drop"),
        "drop_reasons": dict(reasons),
        "old_polarity": dict(polarity_old),
        "suggested_polarity_kept": dict(polarity_keep),
        "by_source": {k: dict(v) for k, v in sorted(by_source.items())},
    }
    return rows, summary


def _write_samples(rows: list[dict], dest: Path) -> None:
    by_kind: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_kind[row["source_kind"]].append(row)
    lines = [
        "# Relevance audit samples",
        "",
        "Manual inspection of the 90-day scrape: a few kept and dropped titles per source kind.",
        "",
    ]
    for kind in sorted(by_kind):
        items = by_kind[kind]
        kept = [x for x in items if x["verdict"] == "keep"]
        dropped = [x for x in items if x["verdict"] == "drop"]
        lines.append(f"## {kind} ({len(items)} items, {len(kept)} keep / {len(dropped)} drop)")
        lines.append("")
        lines.append("### kept")
        for x in kept[:SAMPLE_PER_KIND]:
            lines.append(
                f"- [{x['suggested_polarity']}] {x['title'][:160]}  "
                f"({x['source_label']})"
            )
        if not kept:
            lines.append("- *(none)*")
        lines.append("")
        lines.append("### dropped")
        for x in dropped[:SAMPLE_PER_KIND]:
            lines.append(
                f"- `{x['drop_reason']}` {x['title'][:160]}  "
                f"({x['source_label']})"
            )
        if not dropped:
            lines.append("- *(none)*")
        lines.append("")
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_audit_csv(payload: dict, dest: Path) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    rows, summary = audit_payload(payload)
    fields = [
        "id",
        "source_kind",
        "source_label",
        "old_polarity",
        "verdict",
        "drop_reason",
        "keep_reason",
        "suggested_polarity",
        "title",
        "url",
    ]
    with dest.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    counts_path = dest.with_name(dest.stem + "_by_source.csv")
    with counts_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["source", "keep", "drop", "total"])
        w.writeheader()
        for source, counts in summary["by_source"].items():
            keep = counts.get("keep", 0)
            drop = counts.get("drop", 0)
            w.writerow({"source": source, "keep": keep, "drop": drop, "total": keep + drop})
    reason_path = dest.with_name(dest.stem + "_drop_reasons.csv")
    with reason_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["drop_reason", "count"])
        w.writeheader()
        for reason, n in sorted(summary["drop_reasons"].items(), key=lambda kv: (-kv[1], kv[0])):
            w.writerow({"drop_reason": reason, "count": n})
    _write_samples(rows, dest.with_name(dest.stem + "_samples.md"))
    summary_path = dest.with_name(dest.stem + "_summary.json")
    slim = {k: v for k, v in summary.items() if k != "by_source"}
    slim["by_source_count"] = len(summary["by_source"])
    summary_path.write_text(json.dumps(slim, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    src = Path(args[0]) if args else ROOT / "data" / "latest.json"
    dest = Path(args[1]) if len(args) > 1 else ROOT / "reports" / "relevance_audit.csv"
    payload = json.loads(src.read_text(encoding="utf-8"))
    summary = write_audit_csv(payload, dest)
    print(
        json.dumps(
            {
                "src": str(src),
                "dest": str(dest),
                "total": summary["total"],
                "keep": summary["keep"],
                "drop": summary["drop"],
                "drop_reasons": summary["drop_reasons"],
                "old_polarity": summary["old_polarity"],
                "suggested_polarity_kept": summary["suggested_polarity_kept"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
