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
        js = Path("web/assets/app.js").read_text(encoding="utf-8")
        self.assertIn("workflow_runs", js)
        self.assertIn("drawSevChart", js)
        self.assertIn("Impacto: n/d", js)
        self.assertIn("scrape_window_days", js)
        self.assertNotRegex(js, r"github_pat_|ghp_[A-Za-z0-9]|GITHUB_TOKEN")

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
            latest = json.loads((dest / "data" / "latest.json").read_text(encoding="utf-8"))
            self.assertEqual(latest["run_id"], "2026-08-26")


if __name__ == "__main__":
    unittest.main()
