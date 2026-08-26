# Panel de incidencias Fitbit

Scraper diario de **fallas, defectos, bugs y opiniones públicas** sobre relojes Fitbit (Charge, Versa, Sense, Inspire, Luxe, Ace, Fitbit Air y Pixel Watch cuando aplica). El resultado es un tablero web para que un equipo de producto vea patrones, juzgue si un reporte se ve real y abra el enlace a la fuente.

**Tablero en vivo:** [https://itravaglino.github.io/scraper/](https://itravaglino.github.io/scraper/)

Zona horaria: `America/Buenos_Aires`. La corrida automática arranca todos los días a las **08:00** (11:00 UTC).

## Cómo usarlo

1. Abrí el tablero. Arriba está la fecha de la última corrida, un resumen (nuevos vs recurrentes, modelos, gravedad) y los grupos de incidencias.
2. Cada grupo trae citas de ejemplo, etiquetas de modelo y links a Reddit, App Store, noticias o Hacker News.
3. En este navegador podés marcar **Parece real**, **Hay que verificar** o **Descartar** y dejar una nota. Eso se guarda en `localStorage` (no hay backend ni login).
4. Los JSON/CSV históricos quedan en [`data/`](data/).

## Cómo disparar una corrida ahora

En GitHub: **Actions → “Scrape y dashboard Fitbit” → Run workflow**.

Eso vuelve a scrapear fuentes públicas, regenera el sitio y lo publica en GitHub Pages. No hace falta dejar una computadora encendida.

En local (Python 3.11+; no hay dependencias de PyPI):

```bash
python3 -m unittest discover -s tests -v
python3 run.py
```

Luego serví la carpeta `site/` (por ejemplo `python3 -m http.server -d site 8000`).

## Qué recolecta

Solo fuentes **públicas**, sin login y sin API keys:

| Fuente | Cómo |
| --- | --- |
| Reddit `r/fitbit`, `r/GooglePixelWatch`, `r/WearOS` | RSS/Atom público (el JSON de Reddit suele devolver 403) |
| App Store | RSS de reseñas de *Google Health (Fitbit)* y *Fitbit Ace* |
| Google News | RSS de búsquedas EN/ES sobre fallas |
| Hacker News | API pública de Algolia |

Si una fuente falla, se saltea y el resto del reporte se genera igual. Hay pausa entre pedidos y un `User-Agent` identificable.

**No** se entra a cuentas, **no** se evaden paywalls y **no** se piden secretos para v1.

## Si Pages o Actions no publican

GitHub **no deja** que el `GITHUB_TOKEN` de Actions cree el sitio Pages
(`Resource not accessible by integration`). Por eso el primer deploy puede
fallar aunque el workflow tenga `enablement: true`.

**Un clic (alcanza):**

1. Abrí [Settings → Pages](https://github.com/itravaglino/scraper/settings/pages).
2. En *Build and deployment* → *Source* elegí **GitHub Actions**.
3. **Actions → “Scrape y dashboard Fitbit” → Run workflow** sobre `main`.

Alternativa: en la misma pantalla, Source = **Deploy from a branch**, rama
`gh-pages`, carpeta `/ (root)`. Ya hay un snapshot del tablero en esa rama.

URL esperada: `https://itravaglino.github.io/scraper/`

Si el entorno `github-pages` pide aprobación: Settings → Environments →
github-pages y aprobá el deploy.

## Estructura

```
fitbit_scraper/   código del scraper, clustering y generación del sitio
web/              plantilla del tablero (español)
site/             sitio estático publicado en Pages
data/             latest.json, latest.csv, índice de grupos, historial
.github/workflows/daily.yml
```

Hecho para Ignacio ([@itravaglino](https://github.com/itravaglino)).
