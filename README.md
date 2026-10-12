# Panel de incidencias Fitbit

Scraper diario de **fallas, defectos, bugs y opiniones públicas** sobre productos Fitbit (Charge, Versa, Sense, Inspire, Luxe, Ace, Fitbit Air, básculas Aria y Pixel Watch cuando aplica). El resultado es un tablero web para que un equipo de producto vea **casos negativos** separados de **buenas noticias**, juzgue si un reporte se ve real y abra el enlace a la fuente.

**Tablero en vivo:** [https://itravaglino.github.io/scraper/](https://itravaglino.github.io/scraper/)

Zona horaria: `America/Buenos_Aires`. La corrida automática arranca todos los días a las **08:00** (11:00 UTC).

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
| Reddit `r/fitbit` (new + top semana/mes, paginado), `r/GoogleHealthFitbit`, `r/GoogleHealthApp`, `r/FitbitAir`; Pixel Watch filtrado a Fitbit/Google Health; búsquedas por sync/batería/crash/migración/modelo | RSS público, en serie, pausa 8s, reintento con backoff en HTTP 429 |
| RSS directo | The Verge, Android Authority, Android Police, 9to5Google, TechRadar, gadgetsandwearables, Wareable (filtrado a Fitbit / Google Health) |
| Soporte | `support.google.com/googlehealth/thread` (HTML + Google News) y community.fitbit.com |
| X / Twitter | RSS bridge si responde; si no, Google News `site:x.com` |
| YouTube, TikTok, Instagram | RSS de búsqueda pública (`site:`), sin login ni APIs no oficiales |
| App Store y Play Store | Reseñas de *Google Health (Fitbit)* y *Fitbit Ace*, más páginas y países |
| Google News / Bing News | Consultas por modelo y problema (EN, ES, PT, FR, DE, IT, JA) + outages |
| Hacker News | API pública de Algolia (stories y comentarios) |

Si una fuente falla (403/429), se marca **limitado** (no un RuntimeError) y el resto del reporte se genera igual. Reddit se consulta en serie (pausa 8s, varios reintentos con Retry-After); no se omiten las búsquedas restantes. El strip de salud muestra ítems conservados por tipo de fuente.

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
