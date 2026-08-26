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

# Polite crawling: one request at a time, with extra pause for Reddit.
REQUEST_TIMEOUT_SEC = 25
REQUEST_RETRIES = 3
REQUEST_PAUSE_SEC = 1.2
REDDIT_PAUSE_SEC = 2.6

# Google Health (Fitbit) iOS app — the old id 462638147 was retired.
ITUNES_APP_IDS = {
    "462638897": "Google Health (Fitbit)",
    "1621113388": "Fitbit Ace",
}
ITUNES_COUNTRIES = ("us", "es", "ar")

REDDIT_FEEDS = [
    {
        "id": "reddit_fitbit_search",
        "label": "Reddit r/fitbit (problemas)",
        "url": (
            "https://www.reddit.com/r/fitbit/search.rss"
            "?q=battery+OR+sync+OR+broken+OR+bug+OR+charge+OR+crash+OR+gps"
            "+OR+band+OR+screen+OR+%22heart+rate%22+OR+drain+OR+firmware"
            "&restrict_sr=1&sort=new&t=month"
        ),
    },
    {
        "id": "reddit_fitbit_new",
        "label": "Reddit r/fitbit (nuevos)",
        "url": "https://www.reddit.com/r/fitbit/new/.rss?limit=30",
    },
    {
        "id": "reddit_pixel_watch",
        "label": "Reddit r/GooglePixelWatch",
        "url": "https://www.reddit.com/r/GooglePixelWatch/new/.rss?limit=25",
    },
]

NEWS_FEEDS = [
    {
        "id": "gnews_en",
        "label": "Google News (EN)",
        "url": (
            "https://news.google.com/rss/search?"
            "q=Fitbit+(battery+OR+recall+OR+defect+OR+problem+OR+issue"
            "+OR+broken+OR+sync+OR+firmware)+watch&hl=en-US&gl=US&ceid=US:en"
        ),
    },
    {
        "id": "gnews_es",
        "label": "Google News (ES)",
        "url": (
            "https://news.google.com/rss/search?"
            "q=Fitbit+(bater%C3%ADa+OR+falla+OR+problema+OR+defectuoso"
            "+OR+sincronizaci%C3%B3n+OR+sobrecalentamiento+OR+recall)&hl=es-419&gl=AR&ceid=AR:es-419"
        ),
    },
]

HN_QUERIES = [
    {"id": "hn_fitbit", "label": "Hacker News", "query": "fitbit"},
    {"id": "hn_pixel_watch", "label": "Hacker News Pixel Watch", "query": "pixel watch fitbit"},
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
]

# Generic "Charge" / "Versa" should not fire on every English sentence.
WEAK_MODEL_LABELS = {"Charge", "Versa", "Sense", "Inspire", "Ace"}

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "bateria": [
        "battery", "batería", "bateria", "drain", "drains", "draining",
        "dies", "died", "dead battery", "se agota", "se descarga",
        "battery life", "autonomía", "autonomia", "power saving",
        "hours of battery", "lasts only", "low power",
    ],
    "carga": [
        "charger", "charging", "charge port", "won't charge", "wont charge",
        "not charging", "dock", "cable", "usb", "cargador", "carga",
        "no carga", "no carga nada", "charging case",
    ],
    "sincronizacion": [
        "sync", "syncing", "sincroniza", "sincronización", "sincronizacion",
        "bluetooth", "pair", "pairing", "unpair", "disconnect",
        "no conecta", "no sincroniza", "won't sync", "wont sync",
        "apple health", "google health", "phone app",
    ],
    "software": [
        "firmware", "crash", "crashes", "crashing", "bug", "bugs", "buggy",
        "glitch", "freeze", "frozen", "reboot", "restart loop", "bootloop",
        "se cierra", "actualización fall", "won't open", "wont open",
        "force close", "login failed", "can't log in", "watch face",
        "missing data", "lost data", "sleep data", "no registra",
    ],
    "pantalla": [
        "screen", "display", "oled", "amoled", "dead pixel", "dead pixels",
        "crack", "cracked", "black screen", "blank screen", "ghost touch",
        "pantalla", "se apaga la pantalla", "touchscreen", "touch screen",
        "screen flickered", "parpadea",
    ],
    "correa": [
        "band", "strap", "clasp", "buckle", "correa", "cierre",
        "broke the band", "band broke", "skin irritation from band",
        "watch band", "fastener",
    ],
    "ritmo_cardiaco": [
        "heart rate", "heartrate", "hrv", "bpm", "optical sensor",
        "ritmo cardíaco", "ritmo cardiaco", "frecuencia cardíaca",
        "frecuencia cardiaca", "pulso", "ecg", "eda", "spo2", "oximeter",
        "inaccurate hr", "hr spike",
    ],
    "gps": [
        "gps", "gnss", "gps drift", "no gps lock", "ubicacion", "ubicación",
        "distance wrong", "ruta mal", "gps lost",
    ],
    "calidad": [
        "defect", "defective", "quality", "build quality", "hardware",
        "broken", "broke", "crack", "warranty", "recall", "replacement",
        "defecto", "defectuoso", "garantía", "garantia", "se rompió",
        "se rompio", "water", "waterproof", "swim", "durability",
        "overheat", "overheating", "brick", "bricked", "won't turn on",
        "wont turn on", "dead on arrival", "doa",
    ],
    "piel": [
        "rash", "irritation", "allergy", "allergic", "nickel", "skin",
        "erupción", "erupcion", "alergia", "dermatitis", "burn", "itchy",
    ],
}

SEVERITY_HIGH = [
    "bricked", "brick", "won't turn on", "wont turn on", "dead on arrival",
    "overheat", "overheating", "recall", "injury", "burn", "fire",
    "shock", "data loss", "lost all data", "won't charge at all",
    "completely dead", "stopped working after a week", "skin burn",
    "no enciende", "se incend", "sobrecalent",
]
SEVERITY_MEDIUM = [
    "drain", "dies after", "won't sync", "wont sync", "inaccurate",
    "crash", "crashes", "broken band", "cracked", "gps", "not charging",
    "loop", "freeze", "rebooting", "se descarga", "no sincroniza",
]

POSITIVE_CUES = [
    "love", "great", "excellent", "fixed", "finally", "best", "amazing",
    "me encanta", "excelente", "por fin", "mejoró", "mejoro", "perfecto",
]
NEGATIVE_CUES = [
    "hate", "terrible", "awful", "worst", "refund", "useless", "broken",
    "horrible", "pésimo", "pesimo", "estafa", "decepcion", "decepción",
    "disappointed", "never again", "returning", "return it",
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
]
# News/HN must look like an incident, not a product launch or deal post.
NEWS_ISSUE_CUES = [
    "bug", "bugs", "buggy", "crash", "crashes", "outage", "recall", "retirada",
    "defect", "defective", "defectuoso", "broken", "broke", "falla", "falló",
    "problema", "problem", "won't", "wont", "not working", "no funciona",
    "overheat", "overheating", "burn", "quema", "multa", "lawsuit",
    "drain", "se descarga", "missing data", "lost data", "warning", "aviso",
    "fix for", "fixed the", "failed", "failure",
]

# Reports must look Fitbit/watch related unless the source is already scoped.
BRAND_CUES = [
    "fitbit", "google health", "pixel watch", "versa", "charge 5", "charge 6",
    "inspire", "sense 2", "sense", "luxe", "fitbit ace", "wear os",
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
