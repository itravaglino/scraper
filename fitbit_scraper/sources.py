"""Public source adapters. Each function returns (reports, source_status)."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from .classify import classify
from .config import ITUNES_APP_IDS, ITUNES_COUNTRIES
from .engagement import merge_engagement, pack_engagement, parse_engagement_text
from .feedlist import HN_QUERIES, hn_search_url, news_feeds, reddit_feeds, social_feeds
from .feeds import parse_feed
from .httputil import fetch_text
from .textutil import parse_datetime, sha1, strip_html
from .window import iso_in_window, parse_iso

log = logging.getLogger("fitbit_scraper.sources")

KIND_FROM_HINTS = (
    ("youtube.com", "youtube"),
    ("youtu.be", "youtube"),
    (" youtube", "youtube"),
    ("tiktok.com", "tiktok"),
    (" tiktok", "tiktok"),
    ("instagram.com", "instagram"),
    (" instagram", "instagram"),
    ("reddit.com", "reddit"),
    ("itunes.apple.com", "itunes"),
    ("apps.apple.com", "itunes"),
    ("ycombinator.com", "hackernews"),
)


def infer_source_kind(url: str, title: str = "", fallback: str = "web") -> str:
    blob = f"{url or ''} {title or ''}".lower()
    for needle, kind in KIND_FROM_HINTS:
        if needle in blob:
            return kind
    return fallback or "web"


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
    source_kind: str = "web",
    lang_hint: str | None = None,
    engagement: dict | None = None,
    meta: dict | None = None,
) -> dict | None:
    info = classify(
        title,
        text,
        source_scoped=source_scoped,
        star_rating=star_rating,
        lang_hint=lang_hint,
        url=url,
    )
    if not info["keep"]:
        return None
    stamp = parse_iso(created_at)
    if not iso_in_window(stamp):
        return None
    kind = infer_source_kind(url, title, source_kind)
    rid = sha1(source, extra_id or url, title)
    text_eng = parse_engagement_text(f"{title}\n{text}")
    eng = pack_engagement(**merge_engagement(engagement, text_eng))
    return {
        "id": rid,
        "source": source,
        "source_kind": kind,
        "source_label": source_label,
        "url": url,
        "title": (title or "")[:240],
        "text": (text or "")[:1800],
        "created_at": stamp,
        "published_at": stamp,
        "author": (author or "")[:80],
        "models": info["models"],
        "categories": info["categories"],
        "primary_category": info["primary_category"],
        "severity": info["severity"],
        "sentiment": info["sentiment"],
        "polarity": info.get("polarity") or "revisar",
        "polarity_label": info.get("polarity_label"),
        "language": info.get("language") or "und",
        "language_label": info.get("language_label"),
        "badges": info.get("badges") or [],
        "star_rating": star_rating,
        "engagement": eng,
        "engagement_label": eng.get("label"),
        "reason": info["reason"],
        "meta": meta or {},
    }


def _run_source(source_id: str, label: str, fn: Callable[[], tuple[list[dict], int]], kind: str = "web") -> dict:
    status: dict[str, Any] = {
        "id": source_id,
        "label": label,
        "kind": kind,
        "ok": False,
        "state": "error",
        "fetched": 0,
        "kept": 0,
        "error": None,
        "reports": [],
    }
    try:
        reports, fetched = fn()
        status["ok"] = True
        status["state"] = "ok"
        status["fetched"] = fetched
        status["kept"] = len(reports)
        status["reports"] = reports
    except Exception as exc:  # noqa: BLE001
        msg = f"{type(exc).__name__}: {exc}"
        status["error"] = msg
        low = msg.lower()
        # 403/429/blocked are expected; the rest of the run continues.
        if any(x in low for x in ("403", "429", "blocked", "forbidden", "401")):
            status["state"] = "skip"
        else:
            status["state"] = "error"
        log.warning("source failed %s: %s", source_id, exc)
    return status


def _scrape_rss_collection(feeds: list[dict], default_source: str, default_kind: str) -> list[dict]:
    results = []
    for feed in feeds:
        kind = feed.get("kind") or default_kind
        scoped = bool(feed.get("scoped", kind in {"reddit", "itunes"}))

        lang_hint = feed.get("lang")

        def _pull(feed=feed, kind=kind, scoped=scoped, lang_hint=lang_hint):
            xml, err = fetch_text(
                feed["url"],
                accept="application/atom+xml, application/rss+xml, application/xml, text/xml, */*",
            )
            if xml is None:
                raise RuntimeError(err or "sin respuesta")
            items = parse_feed(xml)
            kept = []
            for item in items:
                url = item.get("url") or ""
                if url.startswith("/r/"):
                    url = "https://www.reddit.com" + url
                rec = _report(
                    source=default_source,
                    source_label=feed["label"],
                    url=url,
                    title=item.get("title") or "",
                    text=item.get("text") or "",
                    created_at=item.get("created_at"),
                    author=item.get("author") or "",
                    extra_id=item.get("id") or url,
                    source_scoped=scoped,
                    source_kind=kind,
                    lang_hint=lang_hint,
                    engagement=item.get("engagement"),
                )
                if rec:
                    kept.append(rec)
            return kept, len(items)

        results.append(_run_source(feed["id"], feed["label"], _pull, kind=kind))
    return results


def scrape_reddit() -> list[dict]:
    feeds = [{**f, "kind": "reddit"} for f in reddit_feeds()]
    return _scrape_rss_collection(feeds, "reddit", "reddit")


def scrape_news() -> list[dict]:
    return _scrape_rss_collection(news_feeds(), "news", "news")


def scrape_social() -> list[dict]:
    """YouTube / TikTok / Instagram via public search-engine RSS, no login."""
    return _scrape_rss_collection(social_feeds(), "social", "web")


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
                    itunes_lang = {
                        "es": "es", "ar": "es", "mx": "es",
                        "br": "pt", "fr": "fr", "de": "de", "it": "it",
                    }.get(country, "en")
                    rec = _report(
                        source="itunes",
                        source_label=label,
                        url=link or url,
                        title=title,
                        text=body,
                        created_at=parse_datetime(_itunes_label(entry, "updated")),
                        author=author,
                        extra_id=_itunes_label(entry, "id"),
                        star_rating=rating,
                        source_scoped=True,
                        source_kind="itunes",
                        lang_hint=itunes_lang,
                        meta={"app": app_name, "country": country, "version": _itunes_label(entry, "im:version")},
                    )
                    if rec:
                        kept.append(rec)
                return kept, len(entries)

            results.append(_run_source(sid, label, _pull, kind="itunes"))
    return results


def scrape_hn() -> list[dict]:
    results = []
    for q in HN_QUERIES:
        url = hn_search_url(q["query"])

        def _pull(url=url, label=q["label"], lang_hint=q.get("lang") or "en"):
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
                    source_kind="hackernews",
                    lang_hint=lang_hint,
                    engagement={
                        "score": hit.get("points"),
                        "comments": hit.get("num_comments"),
                    },
                )
                if rec:
                    kept.append(rec)
            return kept, len(hits)

        results.append(_run_source(q["id"], q["label"], _pull, kind="hackernews"))
    return results


def scrape_all() -> list[dict]:
    batches = []
    batches.extend(scrape_reddit())
    batches.extend(scrape_social())
    batches.extend(scrape_news())
    batches.extend(scrape_itunes())
    batches.extend(scrape_hn())
    return batches
