"""Public, date-bounded feed URLs. Built at scrape time so `after:` / `when:` / `t=` match the window."""

from __future__ import annotations

from urllib.parse import urlencode

from .window import google_date_ops, google_when_ops, hn_since_epoch, reddit_t_param, scrape_window_days


def _gnews(query: str, hl: str, gl: str, ceid: str, *, site: bool = False) -> str:
    # site: queries plus `after:` often return an empty RSS feed.
    q = f"{query} {google_when_ops() if site else google_date_ops()}"
    return "https://news.google.com/rss/search?" + urlencode(
        {"q": q, "hl": hl, "gl": gl, "ceid": ceid}
    )


def _reddit_search(path: str, query: str, restrict: bool, sort: str = "new") -> str:
    params = {"q": query, "sort": sort, "t": reddit_t_param(), "limit": "100"}
    if restrict:
        params["restrict_sr"] = "1"
    return f"https://www.reddit.com/{path}?" + urlencode(params)


def _bing_news(query: str, lang: str = "en-US", cc: str = "US") -> str:
    # Bing does not honor Google `when:` / `after:` operators; filter by pubDate later.
    return "https://www.bing.com/news/search?" + urlencode(
        {"q": query, "format": "rss", "setlang": lang, "cc": cc}
    )


BUG_EN = (
    "bug OR broken OR defect OR issue OR problem OR drain OR sync OR crash "
    "OR firmware OR recall OR battery OR gps OR charger OR screen OR outage "
    "OR forced OR migration OR headache"
)
BUG_ES = (
    "falla OR problema OR defectuoso OR batería OR bateria OR sincronización "
    "OR sobrecalentamiento OR recall OR pantalla OR correa OR forzado OR migración"
)
BUG_PT = "falha OR problema OR defeito OR quebrado OR bateria OR sincronização OR recall OR migração"
BUG_FR = "panne OR défaut OR probleme OR problème OR cassé OR bug OR batterie OR synchronisation OR forcé"
BUG_DE = "Defekt OR Fehler OR Problem OR kaputt OR Akku OR Sync OR Rückruf OR Zwang"
BUG_IT = "guasto OR difetto OR problema OR rotto OR batteria OR sincronizzazione OR richiamo"
BUG_JA = "故障 OR 不具合 OR バグ OR 電池 OR 外れた"
PRAISE = "love OR great OR fixed OR amazing OR recommend OR encanta OR excelente OR arreglado OR solucionado OR corrigido OR parfait OR behoben"

MODELS_EN = (
    "Charge 6", "Charge 5", "Charge 4", "Sense 2", "Inspire 3",
    "Versa 4", "Versa 3", "Fitbit Air", "Ace 3",
)

HN_QUERIES = [
    {"id": "hn_fitbit", "label": "Hacker News", "query": "fitbit", "lang": "en", "tags": "story"},
    {"id": "hn_fitbit_comments", "label": "Hacker News comentarios", "query": "fitbit", "lang": "en", "tags": "comment"},
    {"id": "hn_google_health", "label": "Hacker News Google Health", "query": 'fitbit "google health"', "lang": "en", "tags": "story"},
    {"id": "hn_fitbit_bug", "label": "Hacker News bugs", "query": "fitbit (bug OR battery OR recall OR sync OR outage OR forced)", "lang": "en", "tags": "story"},
]


def reddit_after_token(item: dict) -> str | None:
    """t3_xxx from a Reddit RSS entry, used as `after=` for the next page."""
    ident = str(item.get("id") or "")
    url = str(item.get("url") or "")
    blob = ident + " " + url
    if ident.startswith("t3_"):
        return ident.split()[0]
    import re

    m = re.search(r"(?:/comments/|t3_)([a-z0-9]+)", blob, re.I)
    if m:
        return "t3_" + m.group(1)
    return None


def reddit_listing_url(sub: str, listing: str, *, t: str | None = None, after: str | None = None) -> str:
    params = {"limit": "100"}
    if t:
        params["t"] = t
    if after:
        params["after"] = after
    path = f"r/{sub}/{listing}/.rss"
    return f"https://www.reddit.com/{path}?" + urlencode(params)


# Pixel Watch subs are NOT source_scoped — keep only Fitbit / Google Health posts.
REDDIT_LISTINGS = [
    {"id": "reddit_fitbit_new", "label": "Reddit r/fitbit new", "sub": "fitbit", "listing": "new", "pages": 3, "scoped": True},
    {"id": "reddit_fitbit_top_week", "label": "Reddit r/fitbit top semana", "sub": "fitbit", "listing": "top", "t": "week", "pages": 2, "scoped": True},
    {"id": "reddit_fitbit_top_month", "label": "Reddit r/fitbit top mes", "sub": "fitbit", "listing": "top", "t": "month", "pages": 2, "scoped": True},
    {"id": "reddit_googlehealthfitbit", "label": "Reddit r/GoogleHealthFitbit", "sub": "GoogleHealthFitbit", "listing": "new", "pages": 2, "scoped": True},
    {"id": "reddit_googlehealthapp", "label": "Reddit r/GoogleHealthApp", "sub": "GoogleHealthApp", "listing": "new", "pages": 2, "scoped": True},
    {"id": "reddit_fitbitair", "label": "Reddit r/FitbitAir", "sub": "FitbitAir", "listing": "new", "pages": 2, "scoped": True},
    {"id": "reddit_googlepixelwatch", "label": "Reddit r/GooglePixelWatch", "sub": "GooglePixelWatch", "listing": "new", "pages": 2, "scoped": False},
    {"id": "reddit_pixelwatch", "label": "Reddit r/PixelWatch", "sub": "PixelWatch", "listing": "new", "pages": 1, "scoped": False},
]

REDDIT_SEARCHES = [
    {"id": "reddit_q_sync", "label": "Reddit r/fitbit sync", "restrict": True, "sub": "fitbit",
     "query": 'sync OR "won\'t sync" OR "not syncing" OR sincroniza OR pairing'},
    {"id": "reddit_q_battery", "label": "Reddit r/fitbit battery", "restrict": True, "sub": "fitbit",
     "query": "battery OR drain OR draining OR batería OR bateria OR autonomía"},
    {"id": "reddit_q_crash", "label": "Reddit r/fitbit crash", "restrict": True, "sub": "fitbit",
     "query": 'crash OR bricked OR "not working" OR "won\'t open" OR freeze OR bootloop'},
    {"id": "reddit_q_update", "label": "Reddit r/fitbit update", "restrict": True, "sub": "fitbit",
     "query": "update OR firmware OR \"app update\" OR 5.0 OR migración OR migration"},
    {"id": "reddit_q_migration", "label": "Reddit r/fitbit Google Health", "restrict": True, "sub": "fitbit",
     "query": '"google health" OR forced OR holdout OR workaround OR migration'},
    {"id": "reddit_q_charge", "label": "Reddit r/fitbit Charge", "restrict": True, "sub": "fitbit",
     "query": '"Charge 6" OR "Charge 5" OR "Charge 4"'},
    {"id": "reddit_q_sense", "label": "Reddit r/fitbit Sense", "restrict": True, "sub": "fitbit",
     "query": '"Sense 2" OR "Fitbit Sense"'},
    {"id": "reddit_q_inspire", "label": "Reddit r/fitbit Inspire", "restrict": True, "sub": "fitbit",
     "query": '"Inspire 3" OR "Inspire 2"'},
    {"id": "reddit_q_versa", "label": "Reddit r/fitbit Versa", "restrict": True, "sub": "fitbit",
     "query": '"Versa 4" OR "Versa 3" OR "Versa 2"'},
    {"id": "reddit_q_air", "label": "Reddit r/fitbit Air", "restrict": True, "sub": "fitbit",
     "query": '"Fitbit Air" OR Air'},
    {"id": "reddit_global_search", "label": "Reddit (búsqueda Fitbit)", "restrict": False, "sub": "",
     "query": 'fitbit (bug OR broken OR drain OR sync OR crash OR battery OR firmware OR recall OR forced OR "google health" OR outage OR falla OR problema)'},
    {"id": "reddit_global_x", "label": "Reddit (Fitbit X/Twitter)", "restrict": False, "sub": "",
     "query": 'fitbit (hate OR forced OR "google health" OR outage) (site:x.com OR twitter)'},
]


def reddit_feeds() -> list[dict]:
    """First-page URLs for tests and docs. Live scrape paginates listings."""
    feeds = []
    for job in REDDIT_LISTINGS:
        feeds.append(
            {
                "id": job["id"],
                "label": job["label"],
                "scoped": job["scoped"],
                "lang": "en",
                "kind": "reddit",
                "url": reddit_listing_url(job["sub"], job["listing"], t=job.get("t")),
                "pages": job.get("pages") or 1,
                "sub": job["sub"],
                "listing": job["listing"],
                "t": job.get("t"),
            }
        )
    for job in REDDIT_SEARCHES:
        path = f"r/{job['sub']}/search.rss" if job.get("restrict") and job.get("sub") else "search.rss"
        feeds.append(
            {
                "id": job["id"],
                "label": job["label"],
                "scoped": bool(job.get("restrict")),
                "lang": "en",
                "kind": "reddit",
                "url": _reddit_search(path, job["query"], bool(job.get("restrict"))),
                "pages": 1,
                "query": job["query"],
            }
        )
    return feeds


def reddit_jobs() -> list[dict]:
    return reddit_feeds()


DIRECT_RSS = [
    {"id": "rss_verge", "label": "The Verge RSS", "url": "https://www.theverge.com/rss/index.xml"},
    {"id": "rss_androidauthority", "label": "Android Authority RSS", "url": "https://www.androidauthority.com/feed/"},
    {"id": "rss_androidpolice", "label": "Android Police RSS", "url": "https://www.androidpolice.com/feed/"},
    {"id": "rss_9to5google", "label": "9to5Google RSS", "url": "https://9to5google.com/feed/"},
    {"id": "rss_techradar", "label": "TechRadar RSS", "url": "https://www.techradar.com/rss"},
    {"id": "rss_gadgetsandwearables", "label": "gadgetsandwearables RSS", "url": "https://gadgetsandwearables.com/feed/"},
    {"id": "rss_wareable", "label": "Wareable RSS", "url": "https://www.wareable.com/rss"},
    {
        "id": "rss_androidcentral",
        "label": "Android Central RSS",
        "url": "https://www.androidcentral.com/feed",
        "fallbacks": ["https://www.androidcentral.com/rss.xml"],
    },
]


def direct_rss_feeds() -> list[dict]:
    return [
        {**f, "kind": "news", "lang": "en", "require_subject": True, "scoped": False}
        for f in DIRECT_RSS
    ]


X_NITTER_CANDIDATES = [
    "https://nitter.poast.org/search/rss?f=tweets&q=fitbit%20(google%20health%20OR%20sync%20OR%20battery%20OR%20forced%20OR%20hate)",
    "https://xcancel.com/search/rss?f=tweets&q=fitbit%20(google%20health%20OR%20forced%20OR%20sync)",
]


def x_feeds() -> list[dict]:
    return [
        {"id": "gnews_x", "label": "X / Twitter (Google News)", "kind": "x", "lang": "en", "site": True,
         "url": _gnews('Fitbit (hate OR forced OR sync OR battery OR outage OR "google health" OR crash) site:x.com', "en-US", "US", "US:en", site=True)},
        {"id": "gnews_twitter", "label": "Twitter.com (Google News)", "kind": "x", "lang": "en", "site": True,
         "url": _gnews('Fitbit (hate OR forced OR "won\'t sync" OR drain OR "google health") site:twitter.com', "en-US", "US", "US:en", site=True)},
        {"id": "nitter_fitbit", "label": "X (RSS bridge)", "kind": "x", "lang": "en",
         "url": X_NITTER_CANDIDATES[0], "fallbacks": X_NITTER_CANDIDATES[1:]},
    ]


GHEALTH_SEARCHES = [
    "battery drain Charge",
    "Charge 5 battery",
    "Charge 6 battery",
    "Sense 2 battery",
    "won't sync",
    "Google Health app",
    "migration Fitbit",
    "crash update",
    "outage",
    "Inspire 3",
    "Fitbit Air",
]


def news_feeds() -> list[dict]:
    feeds = [
        {"id": "gnews_en", "label": "Noticias web (EN-US)", "kind": "news", "lang": "en",
         "url": _gnews(f"Fitbit ({BUG_EN} OR fixed OR praise OR \"google health\")", "en-US", "US", "US:en")},
        {"id": "gnews_uk", "label": "Noticias web (EN-GB)", "kind": "news", "lang": "en",
         "url": _gnews(f"Fitbit ({BUG_EN})", "en-GB", "GB", "GB:en")},
        {"id": "gnews_ca", "label": "Noticias web (EN-CA)", "kind": "news", "lang": "en",
         "url": _gnews(f"Fitbit ({BUG_EN})", "en-CA", "CA", "CA:en")},
        {"id": "gnews_au", "label": "Noticias web (EN-AU)", "kind": "news", "lang": "en",
         "url": _gnews(f"Fitbit ({BUG_EN})", "en-AU", "AU", "AU:en")},
        {"id": "gnews_in", "label": "Noticias web (EN-IN)", "kind": "news", "lang": "en",
         "url": _gnews(f"Fitbit ({BUG_EN})", "en-IN", "IN", "IN:en")},
        {"id": "gnews_es", "label": "Noticias web (ES-AR)", "kind": "news", "lang": "es",
         "url": _gnews(f"Fitbit ({BUG_ES} OR arreglado OR solucionado OR \"Google Health\")", "es-419", "AR", "AR:es-419")},
        {"id": "gnews_mx", "label": "Noticias web (ES-MX)", "kind": "news", "lang": "es",
         "url": _gnews(f"Fitbit ({BUG_ES} OR \"Google Health\")", "es-419", "MX", "MX:es-419")},
        {"id": "gnews_es_es", "label": "Noticias web (ES-ES)", "kind": "news", "lang": "es",
         "url": _gnews(f"Fitbit ({BUG_ES} OR \"Google Health\")", "es", "ES", "ES:es")},
        {"id": "gnews_pt", "label": "Noticias web (PT)", "kind": "news", "lang": "pt",
         "url": _gnews(f"Fitbit ({BUG_PT} OR corrigido OR \"Google Health\")", "pt-BR", "BR", "BR:pt-419")},
        {"id": "gnews_fr", "label": "Noticias web (FR)", "kind": "news", "lang": "fr",
         "url": _gnews(f"Fitbit ({BUG_FR} OR corrigé OR \"Google Health\")", "fr", "FR", "FR:fr")},
        {"id": "gnews_de", "label": "Noticias web (DE)", "kind": "news", "lang": "de",
         "url": _gnews(f"Fitbit ({BUG_DE} OR behoben OR \"Google Health\")", "de", "DE", "DE:de")},
        {"id": "gnews_it", "label": "Noticias web (IT)", "kind": "news", "lang": "it",
         "url": _gnews(f"Fitbit ({BUG_IT} OR risolto OR \"Google Health\")", "it", "IT", "IT:it")},
        {"id": "gnews_nl", "label": "Noticias web (NL)", "kind": "news", "lang": "nl",
         "url": _gnews("Fitbit (batterij OR defect OR probleem OR kapot OR bug OR storing OR \"Google Health\")", "nl", "NL", "NL:nl")},
        {"id": "gnews_ja", "label": "Noticias web (JA)", "kind": "news", "lang": "ja",
         "url": _gnews(f"Fitbit ({BUG_JA} OR Google Health)", "ja", "JP", "JP:ja")},
        {"id": "gnews_ko", "label": "Noticias web (KO)", "kind": "news", "lang": "ko",
         "url": _gnews("Fitbit (오류 OR 버그 OR 배터리 OR 불량 OR 리콜 OR Google Health)", "ko", "KR", "KR:ko")},
        {"id": "gnews_migration", "label": "Noticias migración Google Health", "kind": "news", "lang": "en",
         "url": _gnews('Fitbit ("Google Health" OR forced OR holdout OR workaround OR "Fitbit app")', "en-US", "US", "US:en")},
        {"id": "gnews_outage", "label": "Noticias outage Fitbit", "kind": "news", "lang": "en",
         "url": _gnews('Fitbit (outage OR "is down" OR "not working" OR downdetector OR "won\'t sync")', "en-US", "US", "US:en")},
        {"id": "gnews_forums", "label": "Foros / soporte (web)", "kind": "web", "lang": "en", "site": True,
         "url": _gnews(f"Fitbit (community OR forum OR support OR thread OR foro) ({BUG_EN} OR falla)", "en-US", "US", "US:en", site=True)},
        {"id": "gnews_community_fitbit", "label": "community.fitbit.com", "kind": "support", "lang": "en", "site": True,
         "scoped": False,
         "url": _gnews(f"Fitbit ({BUG_EN}) site:community.fitbit.com", "en-US", "US", "US:en", site=True)},
        {"id": "gnews_support_googlehealth", "label": "Soporte Google Health", "kind": "support", "lang": "en", "site": True,
         "url": _gnews('Fitbit (battery OR sync OR crash OR drain OR "Charge 5" OR "Charge 6" OR "Sense 2") site:support.google.com/googlehealth', "en-US", "US", "US:en", site=True)},
        {"id": "gnews_support_google", "label": "Soporte Google", "kind": "support", "lang": "en", "site": True,
         "url": _gnews(f"Fitbit ({BUG_EN}) site:support.google.com", "en-US", "US", "US:en", site=True)},
        {"id": "gnews_xda", "label": "XDA Forums", "kind": "web", "lang": "en", "site": True,
         "url": _gnews(f"Fitbit ({BUG_EN}) site:xdaforums.com", "en-US", "US", "US:en", site=True)},
        {"id": "gnews_9to5", "label": "9to5Google (News)", "kind": "news", "lang": "en", "site": True,
         "url": _gnews('Fitbit ("Google Health" OR battery OR sync OR forced OR Pixel) site:9to5google.com', "en-US", "US", "US:en", site=True)},
        {"id": "gnews_androidcentral", "label": "Android Central (News)", "kind": "news", "lang": "en", "site": True,
         "url": _gnews(f"Fitbit ({BUG_EN} OR \"Google Health\") site:androidcentral.com", "en-US", "US", "US:en", site=True)},
        {"id": "gnews_verge", "label": "The Verge (News)", "kind": "news", "lang": "en", "site": True,
         "url": _gnews('Fitbit ("Google Health" OR forced OR holdout OR battery OR sync OR app) site:theverge.com', "en-US", "US", "US:en", site=True)},
        {"id": "gnews_androidauthority", "label": "Android Authority (News)", "kind": "news", "lang": "en", "site": True,
         "url": _gnews('Fitbit ("Google Health" OR forced OR holdout OR battery) site:androidauthority.com', "en-US", "US", "US:en", site=True)},
        {"id": "gnews_techradar", "label": "TechRadar (News)", "kind": "news", "lang": "en", "site": True,
         "url": _gnews('Fitbit ("Google Health" OR hate OR forced OR app) site:techradar.com', "en-US", "US", "US:en", site=True)},
        {"id": "gnews_gadgets", "label": "gadgetsandwearables (News)", "kind": "news", "lang": "en", "site": True,
         "url": _gnews('Fitbit ("Google Health" OR battery OR forced) site:gadgetsandwearables.com', "en-US", "US", "US:en", site=True)},
        {"id": "gnews_downdetector", "label": "Downdetector / outage", "kind": "web", "lang": "en", "site": True,
         "url": _gnews("Fitbit (outage OR down) (site:downdetector.com OR site:isitdownrightnow.com OR site:outage.report)", "en-US", "US", "US:en", site=True)},
        {"id": "gnews_praise", "label": "Noticias positivas (EN)", "kind": "news", "lang": "en",
         "url": _gnews(f"Fitbit ({PRAISE} OR award)", "en-US", "US", "US:en")},
        {"id": "bing_news_en", "label": "Bing News (EN)", "kind": "news", "lang": "en",
         "url": _bing_news("Fitbit")},
        {"id": "bing_news_problem", "label": "Bing News problemas", "kind": "news", "lang": "en",
         "url": _bing_news("Fitbit problem")},
        {"id": "bing_news_es", "label": "Bing News (ES)", "kind": "news", "lang": "es",
         "url": _bing_news("Fitbit problema", "es", "ES")},
        {"id": "bing_news_de", "label": "Bing News (DE)", "kind": "news", "lang": "de",
         "url": _bing_news("Fitbit Problem", "de", "DE")},
        {"id": "bing_news_migration", "label": "Bing News migración", "kind": "news", "lang": "en",
         "url": _bing_news("Fitbit Google Health")},
    ]
    for model in MODELS_EN:
        slug = model.lower().replace(" ", "_")
        feeds.append(
            {
                "id": f"gnews_model_{slug}",
                "label": f"Noticias {model}",
                "kind": "news",
                "lang": "en",
                "url": _gnews(
                    f'"{model}" Fitbit (battery OR drain OR sync OR crash OR problem OR outage OR forced OR "google health")',
                    "en-US",
                    "US",
                    "US:en",
                ),
            }
        )
        feeds.append(
            {
                "id": f"gnews_model_{slug}_es",
                "label": f"Noticias {model} (ES)",
                "kind": "news",
                "lang": "es",
                "url": _gnews(
                    f'"{model}" Fitbit (problema OR batería OR falla OR sincroniza OR "Google Health")',
                    "es-419",
                    "MX",
                    "MX:es-419",
                ),
            }
        )
    for lang, hl, gl, ceid, extra in (
        ("pt", "pt-BR", "BR", "BR:pt-419", "bateria OR sincronização OR falha"),
        ("fr", "fr", "FR", "FR:fr", "batterie OR panne OR synchronisation"),
        ("de", "de", "DE", "DE:de", "Akku OR Defekt OR Problem"),
        ("it", "it", "IT", "IT:it", "batteria OR problema OR sincronizzazione"),
        ("ja", "ja", "JP", "JP:ja", "故障 OR 電池 OR 不具合"),
    ):
        feeds.append(
            {
                "id": f"gnews_gh_{lang}",
                "label": f"Noticias Google Health ({lang.upper()})",
                "kind": "news",
                "lang": lang,
                "url": _gnews(f'Fitbit "Google Health" ({extra})', hl, gl, ceid),
            }
        )
    return feeds


def social_feeds() -> list[dict]:
    return [
        {"id": "youtube_gnews", "label": "YouTube (búsqueda pública)", "kind": "youtube", "lang": "en",
         "url": _gnews(f"Fitbit ({BUG_EN} OR review OR forced OR \"google health\") site:youtube.com", "en-US", "US", "US:en", site=True)},
        {"id": "youtube_gnews_es", "label": "YouTube ES", "kind": "youtube", "lang": "es",
         "url": _gnews(f"Fitbit ({BUG_ES} OR reseña OR arreglado) site:youtube.com", "es-419", "MX", "MX:es-419", site=True)},
        {"id": "youtube_gnews_pt", "label": "YouTube PT", "kind": "youtube", "lang": "pt",
         "url": _gnews(f"Fitbit ({BUG_PT} OR review) site:youtube.com", "pt-BR", "BR", "BR:pt-419", site=True)},
        {"id": "youtube_gnews_fr", "label": "YouTube FR", "kind": "youtube", "lang": "fr",
         "url": _gnews(f"Fitbit ({BUG_FR} OR test) site:youtube.com", "fr", "FR", "FR:fr", site=True)},
        {"id": "youtube_gnews_de", "label": "YouTube DE", "kind": "youtube", "lang": "de",
         "url": _gnews(f"Fitbit ({BUG_DE} OR Test) site:youtube.com", "de", "DE", "DE:de", site=True)},
        {"id": "youtube_gnews_ja", "label": "YouTube JA", "kind": "youtube", "lang": "ja",
         "url": _gnews(f"Fitbit ({BUG_JA}) site:youtube.com", "ja", "JP", "JP:ja", site=True)},
        {"id": "youtube_praise", "label": "YouTube elogios", "kind": "youtube", "lang": "en",
         "url": _gnews(f"Fitbit ({PRAISE}) site:youtube.com", "en-US", "US", "US:en", site=True)},
        {"id": "tiktok_gnews", "label": "TikTok (búsqueda pública)", "kind": "tiktok", "lang": "en",
         "url": _gnews(f"Fitbit ({BUG_EN} OR review) site:tiktok.com", "en-US", "US", "US:en", site=True)},
        {"id": "tiktok_gnews_es", "label": "TikTok ES", "kind": "tiktok", "lang": "es",
         "url": _gnews(f"Fitbit ({BUG_ES} OR reseña) site:tiktok.com", "es-419", "MX", "MX:es-419", site=True)},
        {"id": "tiktok_gnews_pt", "label": "TikTok PT", "kind": "tiktok", "lang": "pt",
         "url": _gnews(f"Fitbit ({BUG_PT}) site:tiktok.com", "pt-BR", "BR", "BR:pt-419", site=True)},
        {"id": "instagram_gnews", "label": "Instagram (búsqueda pública)", "kind": "instagram", "lang": "en",
         "url": _gnews(f"Fitbit ({BUG_EN}) site:instagram.com", "en-US", "US", "US:en", site=True)},
        {"id": "instagram_gnews_es", "label": "Instagram ES", "kind": "instagram", "lang": "es",
         "url": _gnews(f"Fitbit ({BUG_ES}) site:instagram.com", "es-419", "MX", "MX:es-419", site=True)},
        {"id": "instagram_gnews_pt", "label": "Instagram PT", "kind": "instagram", "lang": "pt",
         "url": _gnews(f"Fitbit ({BUG_PT}) site:instagram.com", "pt-BR", "BR", "BR:pt-419", site=True)},
    ]


def hn_search_url(query: str, tags: str = "story") -> str:
    params = {
        "query": query,
        "hitsPerPage": "50",
        "numericFilters": f"created_at_i>{hn_since_epoch()}",
    }
    if tags:
        params["tags"] = tags
    return f"https://hn.algolia.com/api/v1/search_by_date?{urlencode(params)}"


def feed_count() -> dict[str, int]:
    return {
        "window_days": scrape_window_days(),
        "reddit": len(reddit_feeds()),
        "news": len(news_feeds()),
        "social": len(social_feeds()),
        "direct_rss": len(direct_rss_feeds()),
        "x": len(x_feeds()),
        "hn": len(HN_QUERIES),
    }
