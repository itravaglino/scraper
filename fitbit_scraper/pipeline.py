"""Daily scrape → cluster → write JSON → rebuild static site.

Failures in a single source never abort the run. The dashboard always
gets a valid latest.json, even if every source is empty or down.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .cluster import cluster_reports
from .config import HISTORY_KEEP_DAYS, TIMEZONE
from .generate_site import generate_site
from .sources import scrape_all
from .textutil import normalize

log = logging.getLogger("fitbit_scraper")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LATEST = DATA / "latest.json"
INDEX_PATH = DATA / "cluster_index.json"
HISTORY_DIR = DATA / "history"


def _tz():
    try:
        return ZoneInfo(TIMEZONE)
    except Exception:
        # Slim images may lack IANA tzdata; Argentina is permanently UTC-3.
        return timezone(timedelta(hours=-3))


def _now() -> datetime:
    return datetime.now(_tz())


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        log.warning("corrupt json at %s — starting fresh", path)
        return default


def _dedupe(reports: list[dict]) -> list[dict]:
    by_url: dict[str, dict] = {}
    by_title: dict[str, str] = {}
    ordered: list[str] = []
    for r in reports:
        url_key = (r.get("url") or r["id"]).split("?")[0]
        title_key = normalize(r.get("title") or "")[:120]
        if url_key in by_url:
            prev = by_url[url_key]
            if len(r.get("text") or "") > len(prev.get("text") or ""):
                by_url[url_key] = r
            continue
        if title_key and title_key in by_title:
            continue
        by_url[url_key] = r
        if title_key:
            by_title[title_key] = url_key
        ordered.append(url_key)
    return [by_url[k] for k in ordered]


def _summarize(reports: list[dict], clusters: list[dict]) -> dict:
    by_model = Counter()
    by_sev = Counter()
    by_cat = Counter()
    by_source = Counter()
    for r in reports:
        models = r.get("models") or ["Sin modelo"]
        for m in models:
            by_model[m] += 1
        by_sev[r.get("severity") or "info"] += 1
        by_cat[r.get("primary_category") or "opinion"] += 1
        by_source[r.get("source_label") or r.get("source")] += 1
    new_c = sum(1 for c in clusters if not c.get("recurring"))
    rec_c = sum(1 for c in clusters if c.get("recurring"))
    return {
        "reports": len(reports),
        "clusters": len(clusters),
        "new_clusters": new_c,
        "recurring_clusters": rec_c,
        "by_model": dict(by_model.most_common(12)),
        "by_severity": dict(by_sev),
        "by_category": dict(by_cat),
        "by_source": dict(by_source),
    }


def _write_csv(reports: list[dict], path: Path) -> None:
    fields = [
        "id", "created_at", "source", "source_label", "models", "primary_category",
        "severity", "sentiment", "star_rating", "title", "url",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in reports:
            row = {k: r.get(k) for k in fields}
            row["models"] = ", ".join(r.get("models") or [])
            w.writerow(row)


def _prune_history(keep_days: int) -> None:
    cutoff = _now().date() - timedelta(days=keep_days)
    if not HISTORY_DIR.exists():
        return
    for path in HISTORY_DIR.glob("*.json"):
        try:
            day = datetime.strptime(path.stem, "%Y-%m-%d").date()
        except ValueError:
            continue
        if day < cutoff:
            path.unlink()


def run(fetch: bool = True) -> dict:
    DATA.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    now = _now()
    utc = now.astimezone(timezone.utc)

    source_statuses = []
    reports: list[dict] = []
    if fetch:
        batches = scrape_all()
        for batch in batches:
            reports.extend(batch.pop("reports", []))
            source_statuses.append(batch)
    else:
        previous = _load_json(LATEST, {})
        reports = previous.get("reports") or []
        source_statuses = previous.get("sources") or []

    reports = _dedupe(reports)
    unique_by_label = Counter(r.get("source_label") for r in reports)
    for status in source_statuses:
        if status.get("ok"):
            status["kept"] = unique_by_label.get(status.get("label"), 0)
    prev_index = _load_json(INDEX_PATH, {"clusters": {}})
    clusters, new_index = cluster_reports(reports, prev_index)

    run_date = now.date().isoformat()
    for cid, meta in new_index["clusters"].items():
        if not meta.get("first_seen"):
            old = (prev_index.get("clusters") or {}).get(cid) or {}
            meta["first_seen"] = old.get("first_seen") or run_date
        meta["last_seen"] = run_date
    for c in clusters:
        idx = new_index["clusters"].get(c["id"]) or {}
        c["first_seen"] = idx.get("first_seen") or run_date

    payload = {
        "generated_at": now.isoformat(timespec="seconds"),
        "generated_at_utc": utc.isoformat(timespec="seconds"),
        "timezone": TIMEZONE,
        "run_id": run_date,
        "sources": source_statuses,
        "summary": _summarize(reports, clusters),
        "clusters": clusters,
        "reports": reports,
    }

    LATEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    INDEX_PATH.write_text(json.dumps(new_index, ensure_ascii=False, indent=2), encoding="utf-8")
    HISTORY_DIR.joinpath(f"{run_date}.json").write_text(
        json.dumps(
            {
                "run_id": run_date,
                "generated_at": payload["generated_at"],
                "summary": payload["summary"],
                "cluster_ids": [c["id"] for c in clusters],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_csv(reports, DATA / "latest.csv")
    _prune_history(HISTORY_KEEP_DAYS)
    generate_site(payload)
    ok = sum(1 for s in source_statuses if s.get("ok"))
    log.info(
        "run complete: %s reports, %s clusters, %s/%s sources ok",
        len(reports),
        len(clusters),
        ok,
        len(source_statuses),
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scraper diario de incidencias Fitbit")
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Rebuild the dashboard from data/latest.json without hitting the network",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        run(fetch=not args.skip_fetch)
    except Exception:
        log.exception("fatal error")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
