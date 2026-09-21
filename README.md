# Panel de incidencias Fitbit

Scraper diario de **fallas, defectos, bugs y opiniones públicas** sobre productos Fitbit (Charge, Versa, Sense, Inspire, Luxe, Ace, Fitbit Air, básculas Aria y Pixel Watch cuando aplica). El resultado es un tablero web para que un equipo de producto vea **casos negativos** separados de **buenas noticias**, juzgue si un reporte se ve real y abra el enlace a la fuente.

**Tablero en vivo:** [https://itravaglino.github.io/scraper/](https://itravaglino.github.io/scraper/)

Zona horaria: `America/Buenos_Aires`. No hay corrida automática diaria: el scrape se dispara a mano desde **Actions → “Scrape y dashboard Fitbit” → Run workflow** (o **Ejecutar ahora** en el tablero).

## Cómo usarlo

1. Abrí el tablero. El control **Ejecutar ahora** dispara el workflow de GitHub Actions (un clic en el panel; en GitHub confirmá *Run workflow*). No hay token en el frontend.
2. Las pestañas **Casos negativos** / **Buenas noticias** / **Revisar** son el corte principal. La gravedad alta/media/baja **solo** aplica a malas; una noticia positiva nunca lleva “gravedad media”.
3. Filtrá por **día / semana / mes / trimestre / año**. Cada grupo es un caso (modelo × tema × polaridad) con citas, fuente, fecha, idioma y link.
4. En este navegador podés marcar **Parece real**, **Hay que verificar** o **Descartar**. Eso se guarda en `localStorage`.
5. Los JSON/CSV históricos quedan en [`data/`](data/).

## Cómo disparar una corrida ahora

Desde el tablero: **Ejecutar ahora** → en GitHub, **Run workflow**.

O en el repo: **Actions → “Scrape y dashboard Fitbit” → Run workflow**.

Eso vuelve a scrapear fuentes públicas, regenera el sitio y lo publica en GitHub Pages. El panel se actualiza cuando termina el deploy. En el tablero, **Actualizar datos** relee `latest.json`.

En local (Python 3.11+; no hay dependencias de PyPI):

```bash
python3 -m unittest discover -s tests -v
python3 run.py
```

Luego serví la carpeta `site/` (por ejemplo `python3 -m http.server -d site 8000`).

## Qué recolecta

Solo fuentes **públicas**, sin login y sin API keys. Búsquedas en español, inglés, portugués, francés, alemán, italiano y japonés (términos localizados: bug, falla, problema, défaut, Defekt, 故障, etc.):

| Fuente | Cómo |
| --- | --- |
| Reddit `r/fitbit`, `r/GooglePixelWatch`, búsqueda global Fitbit | RSS público, 3 llamadas en serie |
| YouTube, TikTok, Instagram | RSS de búsqueda pública (`site:`), sin login ni APIs no oficiales |
| Web / foros | RSS de búsqueda pública |
| App Store | RSS de reseñas de *Google Health (Fitbit)* y *Fitbit Ace* (varios países) |
| Google News | RSS localizado (EN, ES, PT, FR, DE, IT, JA) |
| Hacker News | API pública de Algolia |

Si una fuente falla (403/429), se marca **limitado** (no un RuntimeError) y el resto del reporte se genera igual. Reddit se consulta en serie (pocas feeds, pausa 8s, un reintento con Retry-After).

**No** se entra a cuentas, **no** se evaden paywalls y **no** se piden secretos para v1.

## Cómo leer el tablero (ops)

| Control | Qué significa |
| --- | --- |
| **Ejecutar ahora** | Abre el workflow de Actions. No hay token en el frontend. |
| **Tiempo (Mes default)** | Filtra por **fecha del ítem**, no por cuándo corrimos el scrape. La corrida guarda ~90 días; Mes = 30. Recs de 2018 no aparecen en Mes. |
| **Casos negativos / Buenas / Revisar** | Polaridad. Malas con defecto claro en el título entran aunque la confianza sea ~30–50%. Solo se ocultan si confianza &lt; 25% **y** no hay patrón de defecto. Alta exige brick / no enciende / recall en el título. |
| **Confianza** | 0–100% en cada tarjeta. El título pesa más que el cuerpo (un “problem” en el footer de Reddit no alcanza). |
| **Exportar CSV** | Los casos de la vista filtrada (columnas: id, polarity, severity, models, category, published_at, source, title, url, count, language, impact). |
| **Copiar vista** | URL con `p` (polaridad), `t` (días), `s` (gravedad), `m` (modelo), `q` (búsqueda). |
| **ok / limitado / error** | Salud de fuentes de esta corrida. **limitado** = HTTP 429 (típico Reddit). Esa fuente se omitió; no tumba el job. |
| **Gráfico** | Al pie de página. Misma data en la tabla accesible debajo. |

La primera pintura del HTML ya trae casos del último mes (seed + preview). No debería verse “No hay casos” mientras carga el JSON.

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
