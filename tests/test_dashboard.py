from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fitbit_scraper.generate_site import generate_site


class DashboardContractTests(unittest.TestCase):
    def test_run_button_and_seed_placeholder(self):
        html = Path("web/index.html").read_text(encoding="utf-8")
        self.assertIn("Ejecutar ahora", html)
        self.assertIn("Casos negativos", html)
        self.assertIn("Buenas noticias", html)
        self.assertIn("Gravedad", html)
        self.assertIn("sev-chart", html)
        self.assertIn("Agrupar por", html)
        self.assertIn('{"__SEED__":true}', html)
        self.assertIn("actions/workflows/daily.yml", html)
        self.assertIn("source-summary", html)
        self.assertIn("btn-export", html)
        self.assertIn("ops-strip", html)
        self.assertIn("chart-table", html)
        self.assertIn("<!--STATIC_CASES-->", html)
        self.assertLess(html.find('id="clusters"'), html.find("chart-panel"))
        self.assertLess(html.find('id="clusters"'), html.find('id="sev-chart"'))
        js = Path("web/assets/app.js").read_text(encoding="utf-8")
        self.assertIn("workflow_runs", js)
        self.assertIn("drawSevChart", js)
        self.assertIn("Impacto: n/d", js)
        self.assertIn("scrape_window_days", js)
        self.assertIn("limitado", js)
        self.assertIn("source-summary", js)
        self.assertIn("wrapAxisLabel", js)
        self.assertIn("padB = 140", js)
        self.assertIn("FitbitOps", js)
        self.assertIn("exportCsv", js)
        self.assertIn("clusterPolarity", js)
        self.assertIn("Confianza", js)
        self.assertIn("Ops.serializeState(state)", js)
        self.assertNotRegex(js, r"github_pat_|ghp_[A-Za-z0-9]|GITHUB_TOKEN")
        ops = Path("web/assets/ops.js").read_text(encoding="utf-8")
        self.assertNotRegex(ops, r"github_pat_|ghp_[A-Za-z0-9]|GITHUB_TOKEN")

    def test_generate_site_embeds_seed(self):
        payload = {
            "generated_at": "2026-08-26T08:00:00-03:00",
            "timezone": "America/Buenos_Aires",
            "run_id": "2026-08-26",
            "run_workflow_url": "https://github.com/itravaglino/scraper/actions/workflows/daily.yml",
            "summary": {"reports": 0, "clusters": 0, "by_polarity": {"mala": 0, "buena": 0}},
            "clusters": [],
            "sources": [],
            "reports": [{"id": "omit-me"}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            dest = generate_site(payload, dest=Path(tmp) / "site")
            html = (dest / "index.html").read_text(encoding="utf-8")
            self.assertIn("Ejecutar ahora", html)
            self.assertNotIn('{"__SEED__":true}', html)
            self.assertIn("window.FITBIT_SEED=", html)
            self.assertNotIn("omit-me", html)
            self.assertNotIn("<!--STATIC_CASES-->", html)
            self.assertIn("datetime=", html)
            latest = json.loads((dest / "data" / "latest.json").read_text(encoding="utf-8"))
            self.assertEqual(latest["run_id"], "2026-08-26")
            self.assertTrue((dest / "assets" / "ops.js").exists())

    def test_generate_site_paints_month_cases(self):
        payload = {
            "generated_at": "2026-08-26T08:00:00-03:00",
            "timezone": "America/Buenos_Aires",
            "run_id": "2026-08-26",
            "scrape_window_days": 90,
            "summary": {"reports": 2, "clusters": 1, "by_polarity": {"mala": 2}},
            "clusters": [
                {
                    "id": "c-battery",
                    "title": "Charge 6 se apaga",
                    "polarity": "mala",
                    "severity": "alta",
                    "count": 2,
                    "last_report_at": "2026-08-20T12:00:00-03:00",
                    "models": ["Charge 6"],
                    "category_label": "Batería",
                    "quotes": [{"text": "La batería no llega al mediodía."}],
                }
            ],
            "sources": [],
            "reports": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            dest = generate_site(payload, dest=Path(tmp) / "site")
            html = (dest / "index.html").read_text(encoding="utf-8")
            self.assertIn("Charge 6 se apaga", html)
            self.assertIn("26 ago 2026", html)
            self.assertIn('id="empty" class="empty" hidden', html)
            self.assertIn("ventana 90 días", html)


if __name__ == "__main__":
    unittest.main()
