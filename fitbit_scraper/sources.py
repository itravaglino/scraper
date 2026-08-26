"""Public source adapters. Each function returns (reports, source_status)."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable
from urllib.parse import urlencode

from .classify import classify
from .config import HN_QUERIES, ITUNES_APP_IDS, ITUNES_COUNTRIES, NEWS_FEEDS, REDDIT_FEEDS
from .feeds import parse_feed
from .httputil import fetch_text
from .textutil import sha1, strip_html

log = logging.getLogger("fitbit_scraper.sources")


def _report(
    *,
    source: str,
    source_label: str,
    url: str,
    title: str,
    text: str,
    created_at: str | None,
    author: str = "",
    extra_id: str = "",
    star_rating: int | None = None,
    source_scoped: bool = True,
    meta: dict | None = None,
) -> dict | None:
    info = classify(title, text, source_scoped=source_scoped, star_rating=star_rating)
    if not info["keep"]:
        return None
    rid = sha1(source, extra_id or url, title)
    return {
        "id": rid,
        "source": source,
        "source_label": source_label,
        "url": url,
        "title": (title or "")[:240],
        "text": (text or "")[:1800],
        "created_at": created_at,
        "author": (author or "")[:80],
        "models": info["models"],
        "categories": info["categories"],
        "primary_category": info["primary_category"],
        "severity": info["severity"],
        "sentiment": info["sentiment"],
        "star_rating": star_rating,
        "reason": info["reason"],
        "meta": meta or {},
    }


def _run_source(source_id: str, label: str, fn: Callable[[], tuple[list[dict], int]]) -> dict:
    status: dict[str, Any] = {
        "id": source_id,
        "label": label,
        "ok": False,
        "fetched": 0,
        "kept": 0,
        "error": None,
        "reports": [],
    }
    try:
        reports, fetched = fn()
        status["ok"] = True
        status["fetched"] = fetched
        status["kept"] = len(reports)
        status["reports"] = reports
    except Exception as exc:  # noqa: BLE001
        status["error"] = f"{type(exc).__name__}: {exc}"
        log.warning("source failed %s: %s", source_id, exc)
    return status


def scrape_reddit() -> list[dict]:
    results = []
    for feed in REDDIT_FEEDS:
        def _pull(feed=feed):
            xml, err = fetch_text(feed["url"], accept="application/atom+xml, application/rss+xml, application/xml, text/xml, */*")
            if xml is None:
                raise RuntimeError(err or "sin respuesta")
            items = parse_feed(xml)
            kept = []
            for item in items:
                url = item.get("url") or ""
                if url.startswith("/r/"):
                    url = "https://www.reddit.com" + url
                rec = _report(
                    source="reddit",
                    source_label=feed["label"],
                    url=url,
                    title=item.get("title") or "",
                    text=item.get("text") or "",
                    created_at=item.get("created_at"),
                    author=item.get("author") or "",
                    extra_id=item.get("id") or url,
                    # WearOS is mixed-brand; require a Fitbit/Pixel cue.
                    source_scoped=feed["id"] != "reddit_wearos",
                )
                if rec:
                    kept.append(rec)
            return kept, len(items)

        results.append(_run_source(feed["id"], feed["label"], _pull))
    return results


def _itunes_label(entry: dict, key: str) -> str:
    node = entry.get(key)
    if isinstance(node, dict):
        return str(node.get("label") or "")
    return str(node or "")


def scrape_itunes() -> list[dict]:
    results = []
    for app_id, app_name in ITUNES_APP_IDS.items():
        for country in ITUNES_COUNTRIES:
            sid = f"itunes_{country}_{app_id}"
            label = f"App Store {country.upper()} · {app_name}"
            url = (
                f"https://itunes.apple.com/{country}/rss/customerreviews/"
                f"page=1/id={app_id}/sortby=mostrecent/json"
            )

            def _pull(url=url, label=label, country=country, app_name=app_name):
                text, err = fetch_text(url, accept="application/json, text/javascript, */*")
                if text is None:
                    raise RuntimeError(err or "sin respuesta")
                data = json.loads(text)
                entries = data.get("feed", {}).get("entry") or []
                if isinstance(entries, dict):
                    entries = [entries]
                kept = []
                for entry in entries:
                    if not isinstance(entry, dict) or "im:rating" not in entry:
                        continue
                    rating_s = _itunes_label(entry, "im:rating")
                    try:
                        rating = int(rating_s)
                    except ValueError:
                        rating = None
                    title = _itunes_label(entry, "title")
                    body = _itunes_label(entry, "content")
                    author = ""
                    auth = entry.get("author")
                    if isinstance(auth, dict):
                        author = _itunes_label(auth, "name")
                    link = ""
                    link_node = entry.get("link")
                    if isinstance(link_node, dict):
                        link = (link_node.get("attributes") or {}).get("href") or ""
                    rec = _report(
                        source="itunes",
                        source_label=label,
                        url=link or url,
                        title=title,
                        text=body,
                        created_at=_itunes_label(entry, "updated") or None,
                        author=author,
                        extra_id=_itunes_label(entry, "id"),
                        star_rating=rating,
                        source_scoped=True,
                        meta={"app": app_name, "country": country, "version": _itunes_label(entry, "im:version")},
                    )
                    if rec:
                        kept.append(rec)
                return kept, len(entries)

            results.append(_run_source(sid, label, _pull))
    return results


def scrape_news() -> list[dict]:
    results = []
    for feed in NEWS_FEEDS:
        def _pull(feed=feed):
            xml, err = fetch_text(feed["url"], accept="application/rss+xml, application/xml, text/xml, */*")
            if xml is None:
                raise RuntimeError(err or "sin respuesta")
            items = parse_feed(xml)
            kept = []
            for item in items:
                rec = _report(
                    source="news",
                    source_label=feed["label"],
                    url=item.get("url") or "",
                    title=item.get("title") or "",
                    text=item.get("text") or "",
                    created_at=item.get("created_at"),
                    extra_id=item.get("id") or item.get("url") or "",
                    source_scoped=False,
                )
                if rec:
                    kept.append(rec)
            return kept, len(items)

        results.append(_run_source(feed["id"], feed["label"], _pull))
    return results


def scrape_hn() -> list[dict]:
    results = []
    for q in HN_QUERIES:
        params = urlencode(
            {
                "query": q["query"],
                "hitsPerPage": "30",
                "tags": "(story,comment)",
            }
        )
        url = f"https://hn.algolia.com/api/v1/search_by_date?{params}"

        def _pull(url=url, label=q["label"]):
            text, err = fetch_text(url, accept="application/json")
            if text is None:
                raise RuntimeError(err or "sin respuesta")
            data = json.loads(text)
            hits = data.get("hits") or []
            kept = []
            for hit in hits:
                title = hit.get("title") or hit.get("story_title") or ""
                comment = strip_html(hit.get("comment_text") or hit.get("story_text") or "")
                object_id = str(hit.get("objectID") or "")
                story_id = hit.get("story_id") or object_id
                link = hit.get("url") or hit.get("story_url") or f"https://news.ycombinator.com/item?id={story_id}"
                rec = _report(
                    source="hackernews",
                    source_label=label,
                    url=link,
                    title=title,
                    text=comment or title,
                    created_at=hit.get("created_at"),
                    author=hit.get("author") or "",
                    extra_id=object_id,
                    source_scoped=False,
                )
                if rec:
                    kept.append(rec)
            return kept, len(hits)

        results.append(_run_source(q["id"], q["label"], _pull))
    return results


def scrape_all() -> list[dict]:
    batches = []
    batches.extend(scrape_reddit())
    batches.extend(scrape_itunes())
    batches.extend(scrape_news())
    batches.extend(scrape_hn())
    return batches
