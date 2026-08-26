"""Public, date-bounded feed URLs. Built at scrape time so `after:` / `when:` / `t=` match the window."""

from __future__ import annotations

from urllib.parse import urlencode

from .window import google_date_ops, hn_since_epoch, reddit_t_param, scrape_window_days


def _gnews(query: str, hl: str, gl: str, ceid: str) -> str:
    q = f"{query} {google_date_ops()}"
    return "https://news.google.com/rss/search?" + urlencode(
        {"q": q, "hl": hl, "gl": gl, "ceid": ceid}
    )


def _reddit(path: str, query: str, restrict: bool) -> str:
    params = {"q": query, "sort": "new", "t": reddit_t_param()}
    if restrict:
        params["restrict_sr"] = "1"
    return f"https://www.reddit.com/{path}?" + urlencode(params)


def _bing_news(query: str) -> str:
    # Public Bing News RSS. Items are still filtered by pubDate after parse.
    return "https://www.bing.com/news/search?" + urlencode(
        {"q": f"{query} {google_date_ops()}", "format": "rss"}
    )


BUG_EN = (
    "bug OR broken OR defect OR issue OR problem OR drain OR sync OR crash "
    "OR firmware OR recall OR battery OR gps OR charger OR screen"
)
BUG_ES = (
    "falla OR problema OR defectuoso OR batería OR bateria OR sincronización "
    "OR sobrecalentamiento OR recall OR pantalla OR correa"
)
BUG_PT = "falha OR problema OR defeito OR quebrado OR bateria OR sincronização OR recall"
BUG_FR = "panne OR défaut OR probleme OR problème OR cassé OR bug OR batterie OR synchronisation"
BUG_DE = "Defekt OR Fehler OR Problem OR kaputt OR Akku OR Sync OR Rückruf"
BUG_IT = "guasto OR difetto OR problema OR rotto OR batteria OR sincronizzazione OR richiamo"
BUG_JA = "故障 OR 不具合 OR バグ OR 電池 OR 外れた"
PRAISE = "love OR great OR fixed OR amazing OR recommend OR encanta OR excelente OR arreglado OR solucionado OR corrigido OR parfait OR behoben"

HN_QUERIES = [
    {"id": "hn_fitbit", "label": "Hacker News", "query": "fitbit", "lang": "en"},
    {"id": "hn_pixel_watch", "label": "Hacker News Pixel Watch", "query": "pixel watch fitbit", "lang": "en"},
    {"id": "hn_fitbit_bug", "label": "Hacker News bugs", "query": "fitbit (bug OR battery OR recall OR sync)", "lang": "en"},
]


def _reddit_sub_rss(sub: str) -> str:
    return f"https://www.reddit.com/r/{sub}/.rss"


def reddit_feeds() -> list[dict]:
    """Few serial Reddit calls. One scoped sub + one global search beats 12× 429."""
    global_q = (
        "fitbit (bug OR broken OR drain OR sync OR crash OR battery OR firmware "
        "OR recall OR falla OR problema OR defeito OR panne OR defekt OR "
        f"{PRAISE})"
    )
    return [
        {
            "id": "reddit_fitbit",
            "label": "Reddit r/fitbit",
            "scoped": True,
            "lang": "en",
            "url": _reddit_sub_rss("fitbit"),
        },
        {
            "id": "reddit_pixel_watch",
            "label": "Reddit r/GooglePixelWatch",
            "scoped": True,
            "lang": "en",
            "url": _reddit_sub_rss("GooglePixelWatch"),
        },
        {
            "id": "reddit_global_search",
            "label": "Reddit (búsqueda Fitbit)",
            "scoped": False,
            "lang": "en",
            "url": _reddit("search.rss", global_q, False),
        },
    ]


def news_feeds() -> list[dict]:
    return [
        {"id": "gnews_en", "label": "Noticias web (EN-US)", "kind": "news", "lang": "en",
         "url": _gnews(f"Fitbit ({BUG_EN} OR fixed OR praise)", "en-US", "US", "US:en")},
        {"id": "gnews_uk", "label": "Noticias web (EN-GB)", "kind": "news", "lang": "en",
         "url": _gnews(f"Fitbit ({BUG_EN})", "en-GB", "GB", "GB:en")},
        {"id": "gnews_ca", "label": "Noticias web (EN-CA)", "kind": "news", "lang": "en",
         "url": _gnews(f"Fitbit ({BUG_EN})", "en-CA", "CA", "CA:en")},
        {"id": "gnews_au", "label": "Noticias web (EN-AU)", "kind": "news", "lang": "en",
         "url": _gnews(f"Fitbit ({BUG_EN})", "en-AU", "AU", "AU:en")},
        {"id": "gnews_in", "label": "Noticias web (EN-IN)", "kind": "news", "lang": "en",
         "url": _gnews(f"Fitbit ({BUG_EN})", "en-IN", "IN", "IN:en")},
        {"id": "gnews_es", "label": "Noticias web (ES-AR)", "kind": "news", "lang": "es",
         "url": _gnews(f"Fitbit ({BUG_ES} OR arreglado OR solucionado)", "es-419", "AR", "AR:es-419")},
        {"id": "gnews_mx", "label": "Noticias web (ES-MX)", "kind": "news", "lang": "es",
         "url": _gnews(f"Fitbit ({BUG_ES})", "es-419", "MX", "MX:es-419")},
        {"id": "gnews_es_es", "label": "Noticias web (ES-ES)", "kind": "news", "lang": "es",
         "url": _gnews(f"Fitbit ({BUG_ES})", "es", "ES", "ES:es")},
        {"id": "gnews_pt", "label": "Noticias web (PT)", "kind": "news", "lang": "pt",
         "url": _gnews(f"Fitbit ({BUG_PT} OR corrigido)", "pt-BR", "BR", "BR:pt-419")},
        {"id": "gnews_fr", "label": "Noticias web (FR)", "kind": "news", "lang": "fr",
         "url": _gnews(f"Fitbit ({BUG_FR} OR corrigé)", "fr", "FR", "FR:fr")},
        {"id": "gnews_de", "label": "Noticias web (DE)", "kind": "news", "lang": "de",
         "url": _gnews(f"Fitbit ({BUG_DE} OR behoben)", "de", "DE", "DE:de")},
        {"id": "gnews_it", "label": "Noticias web (IT)", "kind": "news", "lang": "it",
         "url": _gnews(f"Fitbit ({BUG_IT} OR risolto)", "it", "IT", "IT:it")},
        {"id": "gnews_nl", "label": "Noticias web (NL)", "kind": "news", "lang": "nl",
         "url": _gnews("Fitbit (batterij OR defect OR probleem OR kapot OR bug OR storing)", "nl", "NL", "NL:nl")},
        {"id": "gnews_ja", "label": "Noticias web (JA)", "kind": "news", "lang": "ja",
         "url": _gnews(f"Fitbit ({BUG_JA})", "ja", "JP", "JP:ja")},
        {"id": "gnews_ko", "label": "Noticias web (KO)", "kind": "news", "lang": "ko",
         "url": _gnews("Fitbit (오류 OR 버그 OR 배터리 OR 불량 OR 리콜)", "ko", "KR", "KR:ko")},
        {"id": "gnews_forums", "label": "Foros / soporte (web)", "kind": "web", "lang": "en",
         "url": _gnews(f"Fitbit (community OR forum OR support OR thread OR foro) ({BUG_EN} OR falla)", "en-US", "US", "US:en")},
        {"id": "gnews_community_fitbit", "label": "community.fitbit.com", "kind": "web", "lang": "en",
         "url": _gnews(f"Fitbit ({BUG_EN}) site:community.fitbit.com", "en-US", "US", "US:en")},
        {"id": "gnews_xda", "label": "XDA Forums", "kind": "web", "lang": "en",
         "url": _gnews(f"Fitbit ({BUG_EN}) site:xdaforums.com", "en-US", "US", "US:en")},
        {"id": "gnews_9to5", "label": "9to5Google", "kind": "news", "lang": "en",
         "url": _gnews(f"Fitbit ({BUG_EN} OR Pixel Watch) site:9to5google.com", "en-US", "US", "US:en")},
        {"id": "gnews_androidcentral", "label": "Android Central", "kind": "news", "lang": "en",
         "url": _gnews(f"Fitbit ({BUG_EN}) site:androidcentral.com", "en-US", "US", "US:en")},
        {"id": "gnews_verge", "label": "The Verge", "kind": "news", "lang": "en",
         "url": _gnews(f"Fitbit ({BUG_EN} OR Pixel Watch) site:theverge.com", "en-US", "US", "US:en")},
        {"id": "gnews_support_google", "label": "Soporte Google", "kind": "web", "lang": "en",
         "url": _gnews(f"Fitbit ({BUG_EN}) site:support.google.com", "en-US", "US", "US:en")},
        {"id": "gnews_praise", "label": "Noticias positivas (EN)", "kind": "news", "lang": "en",
         "url": _gnews(f"Fitbit ({PRAISE} OR award OR best fitness)", "en-US", "US", "US:en")},
        {"id": "bing_news_en", "label": "Bing News (EN)", "kind": "news", "lang": "en",
         "url": _bing_news(f"Fitbit ({BUG_EN})")},
        {"id": "bing_news_es", "label": "Bing News (ES)", "kind": "news", "lang": "es",
         "url": _bing_news(f"Fitbit ({BUG_ES})")},
    ]


def social_feeds() -> list[dict]:
    return [
        {"id": "youtube_gnews", "label": "YouTube (búsqueda pública)", "kind": "youtube", "lang": "en",
         "url": _gnews(f"Fitbit ({BUG_EN} OR review OR fixed) site:youtube.com", "en-US", "US", "US:en")},
        {"id": "youtube_gnews_es", "label": "YouTube ES", "kind": "youtube", "lang": "es",
         "url": _gnews(f"Fitbit ({BUG_ES} OR reseña OR arreglado) site:youtube.com", "es-419", "MX", "MX:es-419")},
        {"id": "youtube_gnews_pt", "label": "YouTube PT", "kind": "youtube", "lang": "pt",
         "url": _gnews(f"Fitbit ({BUG_PT} OR review) site:youtube.com", "pt-BR", "BR", "BR:pt-419")},
        {"id": "youtube_gnews_fr", "label": "YouTube FR", "kind": "youtube", "lang": "fr",
         "url": _gnews(f"Fitbit ({BUG_FR} OR test) site:youtube.com", "fr", "FR", "FR:fr")},
        {"id": "youtube_gnews_de", "label": "YouTube DE", "kind": "youtube", "lang": "de",
         "url": _gnews(f"Fitbit ({BUG_DE} OR Test) site:youtube.com", "de", "DE", "DE:de")},
        {"id": "youtube_gnews_ja", "label": "YouTube JA", "kind": "youtube", "lang": "ja",
         "url": _gnews(f"Fitbit ({BUG_JA}) site:youtube.com", "ja", "JP", "JP:ja")},
        {"id": "youtube_praise", "label": "YouTube elogios", "kind": "youtube", "lang": "en",
         "url": _gnews(f"Fitbit ({PRAISE}) site:youtube.com", "en-US", "US", "US:en")},
        {"id": "tiktok_gnews", "label": "TikTok (búsqueda pública)", "kind": "tiktok", "lang": "en",
         "url": _gnews(f"Fitbit ({BUG_EN} OR review) site:tiktok.com", "en-US", "US", "US:en")},
        {"id": "tiktok_gnews_es", "label": "TikTok ES", "kind": "tiktok", "lang": "es",
         "url": _gnews(f"Fitbit ({BUG_ES} OR reseña) site:tiktok.com", "es-419", "MX", "MX:es-419")},
        {"id": "tiktok_gnews_pt", "label": "TikTok PT", "kind": "tiktok", "lang": "pt",
         "url": _gnews(f"Fitbit ({BUG_PT}) site:tiktok.com", "pt-BR", "BR", "BR:pt-419")},
        {"id": "instagram_gnews", "label": "Instagram (búsqueda pública)", "kind": "instagram", "lang": "en",
         "url": _gnews(f"Fitbit ({BUG_EN}) site:instagram.com", "en-US", "US", "US:en")},
        {"id": "instagram_gnews_es", "label": "Instagram ES", "kind": "instagram", "lang": "es",
         "url": _gnews(f"Fitbit ({BUG_ES}) site:instagram.com", "es-419", "MX", "MX:es-419")},
        {"id": "instagram_gnews_pt", "label": "Instagram PT", "kind": "instagram", "lang": "pt",
         "url": _gnews(f"Fitbit ({BUG_PT}) site:instagram.com", "pt-BR", "BR", "BR:pt-419")},
    ]


def hn_search_url(query: str) -> str:
    params = urlencode(
        {
            "query": query,
            "hitsPerPage": "40",
            "tags": "story",
            "numericFilters": f"created_at_i>{hn_since_epoch()}",
        }
    )
    return f"https://hn.algolia.com/api/v1/search_by_date?{params}"


def feed_count() -> dict[str, int]:
    return {
        "window_days": scrape_window_days(),
        "reddit": len(reddit_feeds()),
        "news": len(news_feeds()),
        "social": len(social_feeds()),
        "hn": len(HN_QUERIES),
    }
