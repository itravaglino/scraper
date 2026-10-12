"""Public source adapters. Each function returns (reports, source_status)."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable

from .classify import classify
from .config import (
    ITUNES_APP_IDS,
    ITUNES_COUNTRIES,
    ITUNES_REVIEW_PAGES,
    PLAY_APP_IDS,
    PLAY_COUNTRIES,
)
from .engagement import merge_engagement, pack_engagement, parse_engagement_text
from .feedlist import (
    GHEALTH_SEARCHES,
    HN_QUERIES,
    direct_rss_feeds,
    hn_search_url,
    news_feeds,
    reddit_after_token,
    reddit_jobs,
    reddit_listing_url,
    social_feeds,
    x_feeds,
)
from .feeds import parse_feed
from .htmlparse import parse_google_health_threads, parse_play_reviews
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
    ("play.google.com", "playstore"),
    ("ycombinator.com", "hackernews"),
    ("x.com", "x"),
    ("twitter.com", "x"),
    ("nitter.", "x"),
    ("xcancel.com", "x"),
    ("support.google.com", "support"),
    ("community.fitbit.com", "support"),
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


def public_source_error(exc: BaseException) -> tuple[str, str]:
    """Map a fetch failure to (state, sidebar message). Never leak RuntimeError."""
    raw = str(exc)
    low = raw.lower()
    if "429" in low:
        return "skip", "Límite de peticiones (HTTP 429)"
    if "403" in low or "forbidden" in low:
        return "skip", "Fuente no disponible (HTTP 403)"
    if "401" in low:
        return "skip", "Fuente no disponible (HTTP 401)"
    if "404" in low:
        return "skip", "Fuente no encontrada (HTTP 404)"
    if "blocked" in low:
        return "skip", "Fuente bloqueó la consulta"
    return "error", raw[:180]


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
        "latency_ms": None,
        "reports": [],
    }
    t0 = time.monotonic()
    try:
        reports, fetched = fn()
        status["ok"] = True
        status["state"] = "ok"
        status["fetched"] = fetched
        status["kept"] = len(reports)
        status["reports"] = reports
    except Exception as exc:  # noqa: BLE001
        state, public = public_source_error(exc)
        status["error"] = public
        status["state"] = state
        log.warning("source failed %s: %s", source_id, public)
    status["latency_ms"] = int((time.monotonic() - t0) * 1000)
    return status


def _rss_pull(feed: dict, default_source: str, default_kind: str) -> Callable[[], tuple[list[dict], int]]:
    kind = feed.get("kind") or default_kind
    scoped = bool(feed.get("scoped", kind in {"reddit", "itunes", "playstore", "support"}))
    lang_hint = feed.get("lang")
    require_subject = bool(feed.get("require_subject"))
    fallbacks = [feed["url"]] + list(feed.get("fallbacks") or [])

    def _pull(
        feed=feed,
        kind=kind,
        scoped=scoped,
        lang_hint=lang_hint,
        require_subject=require_subject,
        fallbacks=fallbacks,
    ):
        xml = err = None
        for url in fallbacks:
            xml, err = fetch_text(
                url,
                accept="application/atom+xml, application/rss+xml, application/xml, text/xml, */*",
            )
            if xml:
                break
        if xml is None:
            raise RuntimeError(err or "sin respuesta")
        items = parse_feed(xml)
        kept = []
        for item in items:
            url = item.get("url") or ""
            if url.startswith("/r/"):
                url = "https://www.reddit.com" + url
            title = item.get("title") or ""
            text = item.get("text") or ""
            if require_subject:
                blob = f"{title}\n{text}\n{url}".lower()
                if "fitbit" not in blob and "google health" not in blob and "googlehealth" not in blob:
                    continue
            rec = _report(
                source=default_source,
                source_label=feed["label"],
                url=url,
                title=title,
                text=text,
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

    return _pull


def _scrape_rss_collection(feeds: list[dict], default_source: str, default_kind: str) -> list[dict]:
    results = []
    for feed in feeds:
        kind = feed.get("kind") or default_kind
        results.append(
            _run_source(feed["id"], feed["label"], _rss_pull(feed, default_source, default_kind), kind=kind)
        )
    return results


def _reddit_job_pull(job: dict) -> Callable[[], tuple[list[dict], int]]:
    scoped = bool(job.get("scoped"))
    pages = max(1, int(job.get("pages") or 1))

    def _pull(job=job, scoped=scoped, pages=pages):
        kept: list[dict] = []
        fetched = 0
        after = None
        last_err = None
        for page in range(pages):
            if job.get("sub") and job.get("listing"):
                url = reddit_listing_url(job["sub"], job["listing"], t=job.get("t"), after=after)
            else:
                url = job["url"]
                if after and "after=" not in url:
                    url += ("&" if "?" in url else "?") + f"after={after}"
            xml, err = fetch_text(
                url,
                accept="application/atom+xml, application/rss+xml, application/xml, text/xml, */*",
            )
            if xml is None:
                last_err = err
                if page == 0:
                    raise RuntimeError(err or "sin respuesta")
                break
            items = parse_feed(xml)
            fetched += len(items)
            for item in items:
                item_url = item.get("url") or ""
                if item_url.startswith("/r/"):
                    item_url = "https://www.reddit.com" + item_url
                rec = _report(
                    source="reddit",
                    source_label=job["label"],
                    url=item_url,
                    title=item.get("title") or "",
                    text=item.get("text") or "",
                    created_at=item.get("created_at"),
                    author=item.get("author") or "",
                    extra_id=item.get("id") or item_url,
                    source_scoped=scoped,
                    source_kind="reddit",
                    lang_hint=job.get("lang") or "en",
                    engagement=item.get("engagement"),
                )
                if rec:
                    kept.append(rec)
            if len(items) < 15:
                break
            after = reddit_after_token(items[-1])
            if not after:
                break
            if pages == 1:
                break
        if fetched == 0 and last_err:
            raise RuntimeError(last_err)
        return kept, fetched

    return _pull


def scrape_reddit() -> list[dict]:
    """Serial Reddit RSS with pagination. 429s back off and retry; later jobs still run."""
    results: list[dict] = []
    for job in reddit_jobs():
        results.append(
            _run_source(job["id"], job["label"], _reddit_job_pull(job), kind="reddit")
        )
    return results


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

            def _pull(label=label, country=country, app_name=app_name, app_id=app_id):
                kept = []
                fetched = 0
                last_err = None
                itunes_lang = {
                    "es": "es", "ar": "es", "mx": "es",
                    "br": "pt", "fr": "fr", "de": "de", "it": "it",
                    "jp": "ja", "nl": "nl",
                }.get(country, "en")
                for page in range(1, ITUNES_REVIEW_PAGES + 1):
                    url = (
                        f"https://itunes.apple.com/{country}/rss/customerreviews/"
                        f"page={page}/id={app_id}/sortby=mostrecent/json"
                    )
                    text, err = fetch_text(url, accept="application/json, text/javascript, */*")
                    if text is None:
                        last_err = err
                        if page == 1:
                            raise RuntimeError(err or "sin respuesta")
                        break
                    try:
                        data = json.loads(text)
                    except json.JSONDecodeError:
                        break
                    entries = data.get("feed", {}).get("entry") or []
                    if isinstance(entries, dict):
                        entries = [entries]
                    page_n = 0
                    for entry in entries:
                        if not isinstance(entry, dict) or "im:rating" not in entry:
                            continue
                        page_n += 1
                        fetched += 1
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
                            created_at=parse_datetime(_itunes_label(entry, "updated")),
                            author=author,
                            extra_id=_itunes_label(entry, "id"),
                            star_rating=rating,
                            source_scoped=True,
                            source_kind="itunes",
                            lang_hint=itunes_lang,
                            meta={
                                "app": app_name,
                                "country": country,
                                "page": page,
                                "version": _itunes_label(entry, "im:version"),
                            },
                        )
                        if rec:
                            kept.append(rec)
                    if page_n < 5:
                        break
                if fetched == 0 and last_err:
                    raise RuntimeError(last_err)
                return kept, fetched

            results.append(_run_source(sid, label, _pull, kind="itunes"))
    return results


def scrape_playstore() -> list[dict]:
    results = []
    for app_id, app_name in PLAY_APP_IDS.items():
        for country in PLAY_COUNTRIES:
            sid = f"play_{country.lower()}_{app_id.replace('.', '_')}"
            label = f"Play Store {country} · {app_name}"
            lang = {
                "ES": "es", "AR": "es", "MX": "es",
                "BR": "pt", "FR": "fr", "DE": "de", "IT": "it", "JP": "ja", "NL": "nl",
            }.get(country, "en")
            hl = {"ES": "es", "AR": "es", "MX": "es", "BR": "pt", "FR": "fr", "DE": "de",
                  "IT": "it", "JP": "ja", "NL": "nl"}.get(country, "en")
            url = f"https://play.google.com/store/apps/details?id={app_id}&hl={hl}&gl={country}"

            def _pull(url=url, label=label, country=country, app_name=app_name, lang=lang, app_id=app_id):
                html, err = fetch_text(url, accept="text/html, */*")
                if html is None:
                    raise RuntimeError(err or "sin respuesta")
                items = parse_play_reviews(html)
                kept = []
                for item in items:
                    rec = _report(
                        source="playstore",
                        source_label=label,
                        url=item.get("url") or url,
                        title=item.get("title") or "",
                        text=item.get("text") or "",
                        created_at=item.get("created_at"),
                        author=item.get("author") or "",
                        extra_id=item.get("id") or "",
                        star_rating=item.get("star_rating"),
                        source_scoped=True,
                        source_kind="playstore",
                        lang_hint=lang,
                        meta={"app": app_name, "country": country, "package": app_id},
                    )
                    if rec:
                        kept.append(rec)
                return kept, len(items)

            results.append(_run_source(sid, label, _pull, kind="playstore"))
    return results


def scrape_support() -> list[dict]:
    def _pull():
        kept = []
        fetched = 0
        urls = ["https://support.google.com/googlehealth/community?hl=en"]
        urls.extend(
            f"https://support.google.com/googlehealth/search?q={q.replace(' ', '+')}&hl=en"
            for q in GHEALTH_SEARCHES
        )
        last_err = None
        for url in urls:
            html, err = fetch_text(url, accept="text/html, */*")
            if html is None:
                last_err = err
                continue
            items = parse_google_health_threads(html)
            fetched += len(items)
            for item in items:
                rec = _report(
                    source="support",
                    source_label="Google Health Community",
                    url=item.get("url") or url,
                    title=item.get("title") or "",
                    text=item.get("text") or "",
                    created_at=item.get("created_at")
                    or datetime.now(timezone.utc).isoformat(),
                    extra_id=item.get("id") or "",
                    source_scoped=True,
                    source_kind="support",
                    lang_hint="en",
                )
                if rec:
                    kept.append(rec)
        if fetched == 0 and last_err and not kept:
            raise RuntimeError(last_err)
        return kept, fetched

    return [_run_source("ghealth_community_html", "Google Health Community", _pull, kind="support")]


def scrape_direct_rss() -> list[dict]:
    return _scrape_rss_collection(direct_rss_feeds(), "news", "news")


def scrape_x() -> list[dict]:
    return _scrape_rss_collection(x_feeds(), "x", "x")


def scrape_hn() -> list[dict]:
    results = []
    for q in HN_QUERIES:
        url = hn_search_url(q["query"], tags=q.get("tags") or "story")

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
    batches.extend(scrape_direct_rss())
    batches.extend(scrape_support())
    batches.extend(scrape_news())
    batches.extend(scrape_x())
    batches.extend(scrape_social())
    batches.extend(scrape_itunes())
    batches.extend(scrape_playstore())
    batches.extend(scrape_hn())
    # Reddit last: serial, long pause, retry on 429 so later jobs still run.
    batches.extend(scrape_reddit())
    return batches
