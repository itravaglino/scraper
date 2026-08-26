"""Product scope, sources, and scoring dictionaries.

All network access is unauthenticated and public. If a source starts
requiring a login or key, drop it rather than adding secrets.
"""

from __future__ import annotations

TIMEZONE = "America/Buenos_Aires"
USER_AGENT = (
    "FitbitIssueScraper/1.0 (+https://github.com/itravaglino/scraper; "
    "public-issue-dashboard; respectful-crawler)"
)

GITHUB_REPO = "itravaglino/scraper"
GITHUB_WORKFLOW_FILE = "daily.yml"

# Polite crawling: one request at a time, with extra pause for Reddit.
REQUEST_TIMEOUT_SEC = 25
REQUEST_RETRIES = 3
REQUEST_PAUSE_SEC = 1.2
REDDIT_PAUSE_SEC = 3.2

# Google Health (Fitbit) iOS app — the old id 462638147 was retired.
ITUNES_APP_IDS = {
    "462638897": "Google Health (Fitbit)",
    "1621113388": "Fitbit Ace",
}
ITUNES_COUNTRIES = ("us", "es", "ar", "br", "fr", "de", "it", "mx")

REDDIT_FEEDS = [
    {
        "id": "reddit_fitbit_search",
        "label": "Reddit r/fitbit",
        "scoped": True,
        "lang": "en",
        "url": (
            "https://www.reddit.com/r/fitbit/search.rss"
            "?q=battery+OR+sync+OR+broken+OR+bug+OR+charge+OR+crash+OR+gps"
            "+OR+band+OR+screen+OR+drain+OR+firmware+OR+scale+OR+aria"
            "+OR+falla+OR+problema+OR+defeito+OR+panne"
            "&restrict_sr=1&sort=new&t=month"
        ),
    },
    {
        "id": "reddit_fitbit_praise",
        "label": "Reddit r/fitbit (elogios / arreglos)",
        "scoped": True,
        "lang": "en",
        "url": (
            "https://www.reddit.com/r/fitbit/search.rss"
            "?q=love+OR+great+OR+fixed+OR+amazing+OR+recommend"
            "+OR+encanta+OR+excelente+OR+arreglado+OR+solucionado"
            "&restrict_sr=1&sort=new&t=month"
        ),
    },
    {
        "id": "reddit_global_search",
        "label": "Reddit (búsqueda Fitbit)",
        "scoped": False,
        "lang": "en",
        "url": (
            "https://www.reddit.com/search.rss"
            "?q=fitbit+(bug+OR+broken+OR+falla+OR+defect+OR+issue+OR+problem"
            "+OR+drain+OR+sync+OR+defeito+OR+panne+OR+defekt+OR+%E6%95%85%E9%9A%9C)"
            "&sort=new&t=month"
        ),
    },
    {
        "id": "reddit_pixel_watch",
        "label": "Reddit r/GooglePixelWatch",
        "scoped": True,
        "lang": "en",
        "url": (
            "https://www.reddit.com/r/GooglePixelWatch/search.rss"
            "?q=fitbit+OR+bug+OR+battery+OR+sync+OR+broken"
            "&restrict_sr=1&sort=new&t=month"
        ),
    },
    {
        "id": "reddit_wearos",
        "label": "Reddit r/WearOS",
        "scoped": False,
        "lang": "en",
        "url": (
            "https://www.reddit.com/r/WearOS/search.rss"
            "?q=fitbit+OR+%22pixel+watch%22+(bug+OR+battery+OR+broken+OR+sync)"
            "&restrict_sr=1&sort=new&t=month"
        ),
    },
    {
        "id": "reddit_smartwatch",
        "label": "Reddit r/smartwatch",
        "scoped": False,
        "lang": "en",
        "url": (
            "https://www.reddit.com/r/smartwatch/search.rss"
            "?q=fitbit+(bug+OR+broken+OR+battery+OR+sync+OR+falla)"
            "&restrict_sr=1&sort=new&t=month"
        ),
    },
    {
        "id": "reddit_fitness",
        "label": "Reddit r/fitness",
        "scoped": False,
        "lang": "en",
        "url": (
            "https://www.reddit.com/r/fitness/search.rss"
            "?q=fitbit+(broken+OR+bug+OR+stopped+OR+sync+OR+battery)"
            "&restrict_sr=1&sort=new&t=month"
        ),
    },
]

# Localized problem + praise queries. Google News RSS is public, no key.
NEWS_FEEDS = [
    {
        "id": "gnews_en",
        "label": "Noticias web (EN)",
        "kind": "news",
        "lang": "en",
        "url": (
            "https://news.google.com/rss/search?"
            "q=Fitbit+(battery+OR+recall+OR+defect+OR+problem+OR+issue"
            "+OR+broken+OR+sync+OR+firmware+OR+scale+OR+fixed+OR+praise)"
            "&hl=en-US&gl=US&ceid=US:en"
        ),
    },
    {
        "id": "gnews_es",
        "label": "Noticias web (ES)",
        "kind": "news",
        "lang": "es",
        "url": (
            "https://news.google.com/rss/search?"
            "q=Fitbit+(bater%C3%ADa+OR+falla+OR+problema+OR+defectuoso"
            "+OR+sincronizaci%C3%B3n+OR+sobrecalentamiento+OR+recall"
            "+OR+b%C3%A1scula+OR+arreglado+OR+solucionado)"
            "&hl=es-419&gl=AR&ceid=AR:es-419"
        ),
    },
    {
        "id": "gnews_pt",
        "label": "Noticias web (PT)",
        "kind": "news",
        "lang": "pt",
        "url": (
            "https://news.google.com/rss/search?"
            "q=Fitbit+(bateria+OR+falha+OR+problema+OR+defeito+OR+quebrado"
            "+OR+sincroniza%C3%A7%C3%A3o+OR+recall+OR+corrigido)"
            "&hl=pt-BR&gl=BR&ceid=BR:pt-419"
        ),
    },
    {
        "id": "gnews_fr",
        "label": "Noticias web (FR)",
        "kind": "news",
        "lang": "fr",
        "url": (
            "https://news.google.com/rss/search?"
            "q=Fitbit+(batterie+OR+panne+OR+d%C3%A9faut+OR+probl%C3%A8me"
            "+OR+cass%C3%A9+OR+bug+OR+synchronisation+OR+corrig%C3%A9)"
            "&hl=fr&gl=FR&ceid=FR:fr"
        ),
    },
    {
        "id": "gnews_de",
        "label": "Noticias web (DE)",
        "kind": "news",
        "lang": "de",
        "url": (
            "https://news.google.com/rss/search?"
            "q=Fitbit+(Akku+OR+Defekt+OR+Fehler+OR+Problem+OR+kaputt"
            "+OR+Sync+OR+R%C3%BCckruf+OR+behoben)"
            "&hl=de&gl=DE&ceid=DE:de"
        ),
    },
    {
        "id": "gnews_it",
        "label": "Noticias web (IT)",
        "kind": "news",
        "lang": "it",
        "url": (
            "https://news.google.com/rss/search?"
            "q=Fitbit+(batteria+OR+guasto+OR+difetto+OR+problema+OR+rotto"
            "+OR+sincronizzazione+OR+richiamo+OR+risolto)"
            "&hl=it&gl=IT&ceid=IT:it"
        ),
    },
    {
        "id": "gnews_ja",
        "label": "Noticias web (JA)",
        "kind": "news",
        "lang": "ja",
        "url": (
            "https://news.google.com/rss/search?"
            "q=Fitbit+(%E6%95%85%E9%9A%9C+OR+%E4%B8%8D%E5%85%B7%E5%90%88"
            "+OR+%E3%83%90%E3%82%B0+OR+%E5%A3%81+OR+%E5%A4%96%E3%82%8C)"
            "&hl=ja&gl=JP&ceid=JP:ja"
        ),
    },
    {
        "id": "gnews_forums",
        "label": "Foros / soporte (web)",
        "kind": "web",
        "lang": "en",
        "url": (
            "https://news.google.com/rss/search?"
            "q=Fitbit+(community+OR+forum+OR+support+OR+thread+OR+foro)"
            "+(bug+OR+broken+OR+problem+OR+issue+OR+falla)"
            "&hl=en-US&gl=US&ceid=US:en"
        ),
    },
]

# Public search-engine RSS pointing at social sites (no login, no unofficial APIs).
SOCIAL_SEARCH_FEEDS = [
    {
        "id": "youtube_gnews",
        "label": "YouTube (búsqueda pública)",
        "kind": "youtube",
        "lang": "en",
        "url": (
            "https://news.google.com/rss/search?"
            "q=Fitbit+(bug+OR+broken+OR+problem+OR+falla+OR+battery+OR+sync"
            "+OR+review+OR+fixed)+site:youtube.com&hl=en-US&gl=US&ceid=US:en"
        ),
    },
    {
        "id": "youtube_gnews_es",
        "label": "YouTube ES (búsqueda pública)",
        "kind": "youtube",
        "lang": "es",
        "url": (
            "https://news.google.com/rss/search?"
            "q=Fitbit+(falla+OR+problema+OR+bater%C3%ADa+OR+rese%C3%B1a"
            "+OR+arreglado)+site:youtube.com&hl=es-419&gl=MX&ceid=MX:es-419"
        ),
    },
    {
        "id": "tiktok_gnews",
        "label": "TikTok (búsqueda pública)",
        "kind": "tiktok",
        "lang": "en",
        "url": (
            "https://news.google.com/rss/search?"
            "q=Fitbit+(bug+OR+broken+OR+problem+OR+falla+OR+battery"
            "+OR+review)+site:tiktok.com&hl=en-US&gl=US&ceid=US:en"
        ),
    },
    {
        "id": "instagram_gnews",
        "label": "Instagram (búsqueda pública)",
        "kind": "instagram",
        "lang": "en",
        "url": (
            "https://news.google.com/rss/search?"
            "q=Fitbit+(bug+OR+broken+OR+problem+OR+falla+OR+battery)"
            "+site:instagram.com&hl=en-US&gl=US&ceid=US:en"
        ),
    },
]

SOURCE_KIND_LABELS_ES = {
    "reddit": "Reddit",
    "youtube": "YouTube",
    "tiktok": "TikTok",
    "instagram": "Instagram",
    "web": "Web / foros",
    "news": "Noticias",
    "itunes": "App Store",
    "hackernews": "Hacker News",
}

LANG_LABELS_ES = {
    "es": "Español",
    "en": "Inglés",
    "pt": "Portugués",
    "fr": "Francés",
    "de": "Alemán",
    "it": "Italiano",
    "ja": "Japonés",
    "zh": "Chino",
    "ko": "Coreano",
    "nl": "Neerlandés",
    "und": "Idioma n/d",
}

POLARITY_LABELS_ES = {
    "mala": "Mala noticia",
    "buena": "Buena noticia",
    "revisar": "Revisar",
}

HN_QUERIES = [
    {"id": "hn_fitbit", "label": "Hacker News", "query": "fitbit", "lang": "en"},
    {"id": "hn_pixel_watch", "label": "Hacker News Pixel Watch", "query": "pixel watch fitbit", "lang": "en"},
]

# More specific patterns first. Brand-level fallback is applied later.
# 2026: Fitbit Air is a current model in public coverage.
MODEL_PATTERNS: list[tuple[str, list[str]]] = [
    ("Fitbit Air", [r"\bfitbit\s*air\b", r"\bthe air\b(?=.{0,40}fitbit)"]),
    ("Charge 6", [r"\bcharge\s*6\b", r"\bfitbit\s*c6\b"]),
    ("Charge 5", [r"\bcharge\s*5\b"]),
    ("Charge 4", [r"\bcharge\s*4\b"]),
    ("Charge 3", [r"\bcharge\s*3\b"]),
    ("Charge 2", [r"\bcharge\s*2\b"]),
    ("Charge", [r"\bfitbit\s*charge\b", r"\bcharge\s*hr\b"]),
    ("Versa 4", [r"\bversa\s*4\b"]),
    ("Versa 3", [r"\bversa\s*3\b"]),
    ("Versa 2", [r"\bversa\s*2\b"]),
    ("Versa Lite", [r"\bversa\s*lite\b"]),
    ("Versa", [r"\bfitbit\s*versa\b", r"(?<!vice )\bversa\b"]),
    ("Sense 2", [r"\bsense\s*2\b"]),
    # Avoid English "make sense" / "in a sense".
    ("Sense", [r"\bfitbit\s*sense\b", r"(?<!make )(?<!makes )(?<!made )(?<!a )\bsense\b(?!\s+of\b)(?!\s*\d)"]),
    ("Inspire 3", [r"\binspire\s*3\b"]),
    ("Inspire 2", [r"\binspire\s*2\b"]),
    ("Inspire", [r"\bfitbit\s*inspire\b", r"\binspire\b"]),
    ("Luxe", [r"\bfitbit\s*luxe\b", r"\bluxe\b"]),
    ("Ace 3", [r"\bace\s*3\b", r"\bace\s*lte\b"]),
    ("Ace", [r"\bfitbit\s*ace\b", r"\bace\b"]),
    ("Pixel Watch 3", [r"\bpixel\s*watch\s*3\b", r"\bpw3\b"]),
    ("Pixel Watch 2", [r"\bpixel\s*watch\s*2\b", r"\bpw2\b"]),
    ("Pixel Watch", [r"\bgoogle\s*pixel\s*watch\b", r"\bpixel\s*watch\b"]),
    ("Aria Air", [r"\baria\s*air\b"]),
    ("Aria 2", [r"\baria\s*2\b"]),
    ("Aria", [r"\bfitbit\s*aria\b", r"\baria\s*scale\b"]),
    ("Ionic", [r"\bfitbit\s*ionic\b"]),
    ("Alta", [r"\bfitbit\s*alta\b"]),
    ("Flex", [r"\bfitbit\s*flex\b"]),
]

# Generic "Charge" / "Versa" should not fire on every English sentence.
WEAK_MODEL_LABELS = {"Charge", "Versa", "Sense", "Inspire", "Ace"}

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "bateria": [
        "battery", "batería", "bateria", "drain", "drains", "draining",
        "dies", "died", "dead battery", "se agota", "se descarga",
        "battery life", "autonomía", "autonomia", "power saving",
        "hours of battery", "lasts only", "low power",
        "akku", "akkulaufzeit", "batterie", "pile",
        "se descarrega", "acaba rápido", "autonomia péssima",
        "バッテリー", "電池", "续航", "电池",
    ],
    "carga": [
        "charger", "charging", "charge port", "won't charge", "wont charge",
        "not charging", "dock", "cable", "usb", "cargador", "carga",
        "no carga", "no carga nada", "charging case",
        "chargeur", "ne charge pas", "ladegerät", "lädt nicht", "laedt nicht",
        "carregador", "não carrega", "nao carrega", "non si carica",
        "充電", "充电",
    ],
    "sincronizacion": [
        "sync", "syncing", "sincroniza", "sincronización", "sincronizacion",
        "bluetooth", "pair", "pairing", "unpair", "disconnect",
        "no conecta", "no sincroniza", "won't sync", "wont sync",
        "apple health", "google health", "phone app",
        "synchronisation", "synchronisierung", "sincronizzazione",
        "não sincroniza", "nao sincroniza", "ne se synchronise",
        "koppelt nicht", "non si sincronizza",
        "同期", "同步",
    ],
    "software": [
        "firmware", "crash", "crashes", "crashing", "bug", "bugs", "buggy",
        "glitch", "freeze", "frozen", "reboots", "rebooted", "restart loop", "bootloop",
        "se cierra", "actualización fall", "won't open", "wont open",
        "force close", "login failed", "can't log in", "watch face",
        "missing data", "lost data", "sleep data", "no registra",
        "plantage", "se bloque", "absturz", "stürzt", "travamento",
        "si blocca", "non si apre", "不具合", "闪退",
    ],
    "pantalla": [
        "screen", "display", "oled", "amoled", "dead pixel", "dead pixels",
        "crack", "cracked", "black screen", "blank screen", "ghost touch",
        "pantalla", "se apaga la pantalla", "touchscreen", "touch screen",
        "screen flickered", "parpadea",
        "écran", "ecran", "bildschirm", "tela", "schermo",
        "écran noir", "tela preta", "画面", "屏幕",
    ],
    "correa": [
        "band", "strap", "clasp", "buckle", "correa", "cierre",
        "broke the band", "band broke", "skin irritation from band",
        "watch band", "fastener",
        "bracelet", "armband", "pulseira", "cinturino", "cinghia",
        "バンド", "表带",
    ],
    "ritmo_cardiaco": [
        "heart rate", "heartrate", "hrv", "bpm", "optical sensor",
        "ritmo cardíaco", "ritmo cardiaco", "frecuencia cardíaca",
        "frecuencia cardiaca", "pulso", "ecg", "eda", "spo2", "oximeter",
        "inaccurate hr", "hr spike",
        "fréquence cardiaque", "frequenz cardiaca", "herzfrequenz",
        "frequência cardíaca", "frequencia cardiaca", "freq. cardiaca",
        "心拍", "心率",
    ],
    "gps": [
        "gps", "gnss", "gps drift", "no gps lock", "ubicacion", "ubicación",
        "distance wrong", "ruta mal", "gps lost",
        "localisation", "standort", "localização", "localizacao",
        "posizione", "GPSが", "定位",
    ],
    "calidad": [
        "defect", "defective", "quality", "build quality", "hardware",
        "broken", "broke", "crack", "warranty", "recall", "replacement",
        "defecto", "defectuoso", "garantía", "garantia", "se rompió",
        "se rompio", "water", "waterproof", "swim", "durability",
        "overheat", "overheating", "brick", "bricked", "won't turn on",
        "wont turn on", "dead on arrival", "doa",
        "défaut", "defaut", "cassé", "casse", "rappel",
        "defekt", "kaputt", "rückruf", "ruckruf",
        "defeito", "quebrado", "recall", "difetto", "rotto", "guasto",
        "故障", "壊れた", "召回", "质量",
    ],
    "piel": [
        "rash", "irritation", "allergy", "allergic", "nickel", "skin",
        "erupción", "erupcion", "alergia", "dermatitis", "burn", "itchy",
        "éruption", "eruption", "allergie", "hautausschlag", "allergia",
        "erupção", "erupcao", "irritazione", "発疹", "过敏",
    ],
}

SEVERITY_HIGH = [
    "bricked", "brick", "won't turn on", "wont turn on", "dead on arrival",
    "overheat", "overheating", "recall", "injury", "burn", "fire",
    "shock", "data loss", "lost all data", "won't charge at all",
    "completely dead", "stopped working after a week", "skin burn",
    "no enciende", "se incend", "sobrecalent",
    "ne s'allume pas", "ne sallume pas", "rappel produit",
    "geht nicht an", "überhitz", "ueberhitz", "rückruf",
    "não liga", "nao liga", "superaquec", "não acende",
    "non si accende", "surriscald", "richiamo",
    "発火", "故障して起動", "召回",
]
SEVERITY_MEDIUM = [
    "drain", "dies after", "won't sync", "wont sync", "inaccurate",
    "crash", "crashes", "broken band", "cracked", "gps drift", "no gps",
    "gps lost", "not charging", "restart loop", "bootloop", "freeze",
    "keeps rebooting", "se descarga", "no sincroniza",
    "se bloque", "plante", "stürzt", "absturz", "não sincroniza",
    "si blocca", "non si sincronizza",
]

# Strong praise / fix language. If these dominate, it is NOT a problem report.
POSITIVE_CUES = [
    "love", "loved", "loves", "great", "awesome", "amazing", "excellent",
    "perfecto", "perfecta", "perfect", "me encanta", "encanta", "feliz",
    "happy", "recommend", "recomiendo", "best watch", "best tracker",
    "best fitbit", "worth it", "vale la pena", "improved", "improvement",
    "mejora", "mejoró", "mejoro", "works great", "works perfectly",
    "funciona bien", "funciona perfecto", "funciona de diez",
    "finally works", "fixed", "has been fixed", "was fixed", "resolved",
    "arreglado", "arreglaron", "solucionado", "solucionaron", "parche",
    "good news", "buena noticia", "buenas noticias", "praise",
    "review positivo", "positive review", "five star", "5 star",
    "5 estrellas", "cinco estrellas", "highly rated",
    # PT
    "amei", "adoro", "ótimo", "otimo", "excelente", "perfeito", "recomendo",
    "funciona bem", "corrigido", "resolvido", "vale a pena", "boa notícia",
    "boa noticia",
    # FR
    "j'adore", "j’adore", "excellent", "parfait", "génial", "genial",
    "je recommande", "fonctionne bien", "corrigé", "corrige", "résolu", "resolu",
    "bonne nouvelle",
    # DE
    "großartig", "grossartig", "super uhr", "empfehlenswert", "perfekt",
    "funktioniert super", "behoben", "gefixt", "gute nachricht", "liebe diese",
    # IT
    "adoro", "ottimo", "eccellente", "perfetto", "consiglio",
    "funziona benissimo", "risolto", "corretto", "buona notizia",
    # JA / ZH
    "最高", "素晴らしい", "直った", "修好", "好评", "喜欢",
]

# Headlines about a fix/patch — polarity buena even if they mention a bug.
FIX_HEADLINE_CUES = [
    "fixed", "fix for", "fix is", "hotfix", "patched", "patch notes", "resolved",
    "resolution", "arreglado", "arreglan", "solucionado", "solucionan",
    "parche", "now working", "now works", "issue resolved", "bugfix",
    "bug fix", "google has fixed", "fitbit has fixed", "fitbit fixed",
    "update fixes", "update that fixes", "released a fix", "rolling out a fix",
    "corrigido", "corrigem", "resolvido", "correção", "correcao",
    "corrigé", "corrige le", "correctif", "résolu", "patch notes",
    "behoben", "gefixt", "update behebt", "fehlerbehebung",
    "risolto", "corretto", "aggiornamento risolve",
    "修正", "修复", "解決",
]

# If these appear WITH a problem cue, keep as mala (open defect).
OPEN_DEFECT_CUES = [
    "still broken", "still not", "not fixed", "unfixed", "never fixed",
    "hasn't been fixed", "hasnt been fixed", "waiting for a fix",
    "no lo arreglaron", "sigue sin", "todavia no", "todavía no",
    "esperando el parche", "after the update still", "update broke",
    "update ruined", "update caused", "new update broke", "bricked after",
    "worse after",
    "ainda não", "ainda nao", "não foi corrigido", "nao foi corrigido",
    "toujours pas", "pas encore corrigé", "toujours cassé",
    "immer noch", "immer noch kaputt", "nicht behoben",
    "ancora non", "non ancora risolto", "ancora rotto",
    "まだ直", "还没修",
]

REVIEW_CUES = [
    "review", "reviewed", "reseña", "resena", "unboxing", "hands-on", "hands on",
    "first look", "primeras impresiones", "vale la pena", "worth it",
    "test de la", "im test", "recensione",
]

MIXED_CUES = [
    "pros and cons", "pros & cons", "pros y contras", "mixed review",
    "review mixto", "hit or miss", "some users", "algunos usuarios",
    "worked for some", "works for some", "not sure", "no se si", "no sé si",
    "does anyone", "alguien mas", "alguien más", "is it worth",
    "vale la pena comprar",
    "prós e contras", "pros e contras", "pour et contre", "vor- und nachteile",
    "pro e contro", "avis mitigé", "recensione mista",
]

NEGATIVE_CUES = [
    "hate", "terrible", "awful", "worst", "refund", "useless", "broken",
    "horrible", "pésimo", "pesimo", "estafa", "decepcion", "decepción",
    "disappointed", "never again", "returning", "return it",
    "no funciona", "no anda", "no carga", "no enciende", "no sincroniza",
    "no conecta", "se apaga", "se cuelga", "se rompio", "se rompió",
    "won't", "wont", "doesn't work", "doesnt work", "not working",
    "stopped working", "failed", "failure", "falla", "fallo", "falló",
    "error", "bug", "glitch", "crash", "issue", "problem", "problema",
    "defect", "defecto", "faulty", "recall", "lawsuit", "frustrated",
    "frustrado", "scam",
    # PT
    "não funciona", "nao funciona", "quebrado", "péssimo", "pessimo",
    "defeito", "falha", "ódio", "odio isso", "decepcionado", "inútil", "inutil",
    # FR
    "ne fonctionne pas", "ne marche pas", "cassé", "casse", "nul",
    "horrible", "défaut", "defaut", "panne", "arnaque", "déçu", "decu",
    # DE
    "funktioniert nicht", "kaputt", "schrecklich", "nutzlos", "fehler",
    "defekt", "entäuscht", "enttaeuscht", "hasse",
    # IT
    "non funziona", "rotto", "pessimo", "inutile", "guasto", "difetto",
    "deluso", "odio",
    # JA / ZH
    "故障", "壊れた", "不具合", "最悪", "坏了", "问题", "差评",
]

SCREEN_NEGATIONS = [
    "sin pantalla",
    "sin pantallas",
    "without a screen",
    "without screens",
    "screenless",
    "no screen",
    "no-screen",
    "screen-free",
    "screen free",
    "sans écran",
    "sans ecran",
    "ohne display",
    "ohne bildschirm",
    "sem tela",
    "senza schermo",
]
# News/HN must look like an incident, a fix, or a review — not a product launch.
NEWS_ISSUE_CUES = [
    "bug", "bugs", "buggy", "crash", "crashes", "outage", "recall", "retirada",
    "defect", "defective", "defectuoso", "broken", "broke", "falla", "falló",
    "problema", "problem", "won't", "wont", "not working", "no funciona",
    "overheat", "overheating", "burn", "quema", "multa", "lawsuit",
    "drain", "se descarga", "missing data", "lost data", "warning", "aviso",
    "fix for", "fixed the", "failed", "failure",
    "falha", "defeito", "quebrado", "panne", "défaut", "defaut", "cassé",
    "defekt", "kaputt", "fehler", "guasto", "difetto", "rotto",
    "ne fonctionne pas", "ne marche pas", "funktioniert nicht",
    "não funciona", "nao funciona", "non funziona",
    "arreglado", "solucionado", "corrigido", "corrigé", "behoben", "risolto",
    "故障", "不具合", "召回",
]

# Distinctive tokens for language detection (latin scripts).
LANG_MARKERS: dict[str, tuple[str, ...]] = {
    "es": (
        "sincronización", "batería", "no funciona", "falla", "aplicación",
        "queja", "correa", "me encanta", "porque", "también", "tambien",
        "está", "está fallando", "reseña", "gravedad",
    ),
    "pt": (
        "não funciona", "nao funciona", "aplicativo", "relógio", "relogio",
        "defeito", "você", "voce", "não", "sincronizar", "pulseira",
        "ótimo", "otimo", "muito bom",
    ),
    "fr": (
        "ne fonctionne", "batterie", "montre", "problème", "probleme",
        "défaut", "defaut", "synchronisation", "c'est", "bracelet",
        "écran", "ecran", "j'adore",
    ),
    "de": (
        "funktioniert nicht", "akku", "fehler", "defekt", "uhr",
        "synchronisation", "nicht", "armband", "bildschirm", "rückruf",
    ),
    "it": (
        "non funziona", "orologio", "batteria", "problema", "difetto",
        "sincronizzazione", "cinturino", "schermo", "guasto", "però",
    ),
    "nl": (
        "werkt niet", "batterij", "horloge", "probleem", "defect",
        "synchronisatie", "bandje",
    ),
    "en": (
        "doesn't", "doesnt", "battery drain", "won't sync", "firmware",
        "the watch", "my fitbit", "heart rate", "stopped working",
    ),
}

# Reports must look Fitbit/watch related unless the source is already scoped.
BRAND_CUES = [
    "fitbit", "google health", "pixel watch", "versa", "charge 5", "charge 6",
    "inspire", "sense 2", "luxe", "fitbit ace", "wear os", "aria",
    "fitbit scale", "báscula", "bascula", "fitbit ionic", "fitbit alta",
    "fitbit flex", "fitbit air",
]

STOPWORDS = {
    "about", "after", "again", "also", "and", "app", "are", "been", "being",
    "but", "can", "does", "fitbit", "for", "from", "google", "have", "health",
    "just", "like", "my", "not", "one", "only", "please", "really", "still",
    "that", "the", "this", "update", "very", "was", "watch", "when", "with",
    "para", "como", "este", "esta", "esto", "pero", "porque", "que", "una",
    "uno", "los", "las", "del", "por", "con", "sin", "más", "mas", "muy",
}

HISTORY_KEEP_DAYS = 30
MAX_QUOTES_PER_CLUSTER = 3
MAX_REPORTS_PER_CLUSTER = 40
