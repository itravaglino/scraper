"""Playwright: KPI/tabs/filters/header leave the viewport after scrolling.

Skipped unless Playwright is installed (CI sets this up on push/PR).
"""

from __future__ import annotations

import os
import threading
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
ARTIFACTS = Path(os.environ.get("DASHBOARD_ARTIFACTS", "/opt/cursor/artifacts"))

CHROME_SELECTORS = (
    "header.mast",
    "#kpis",
    "#board-filters",
    ".polarity-tabs",
    ".toolbar",
    ".filter-controls",
)

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - optional local dep
    sync_playwright = None


class _SiteHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        return


@unittest.skipUnless(sync_playwright is not None, "playwright is not installed")
class DashboardScrollTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (SITE / "index.html").exists():
            raise unittest.SkipTest("site/index.html missing")
        handler = partial(_SiteHandler, directory=str(SITE))
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _assert_scroll(self, width: int, height: int, label: str) -> None:
        page = self.browser.new_page(viewport={"width": width, "height": height})
        try:
            page.goto(f"http://127.0.0.1:{self.port}/index.html", wait_until="load")
            page.wait_for_selector("#kpis .kpi, #kpis .kpi-defs")
            page.evaluate("document.body.style.paddingBottom = '4000px'")

            positions = page.evaluate(
                """(sels) => sels.map((s) => {
                  const el = document.querySelector(s);
                  if (!el) return {selector: s, missing: true};
                  return {selector: s, position: getComputedStyle(el).position};
                })""",
                list(CHROME_SELECTORS),
            )
            for item in positions:
                self.assertFalse(item.get("missing"), item)
                self.assertNotIn(item["position"], ("sticky", "fixed"), item)

            stuck = page.evaluate(
                """() => [...document.querySelectorAll('*')]
                  .filter((el) => {
                    const pos = getComputedStyle(el).position;
                    return pos === 'fixed' || pos === 'sticky';
                  })
                  .map((el) => ({
                    id: el.id || '',
                    className: String(el.className || ''),
                    position: getComputedStyle(el).position,
                    tag: el.tagName.toLowerCase(),
                  }))"""
            )
            self.assertTrue(stuck, "expected #btn-top to be position:fixed")
            for el in stuck:
                self.assertEqual(el["position"], "fixed", el)
                self.assertEqual(el["id"], "btn-top", el)
                self.assertNotEqual(el["position"], "sticky", el)

            page.evaluate("window.scrollTo(0, 1500)")
            page.wait_for_function("() => window.scrollY >= 1500")

            vis = page.evaluate(
                """(sels) => {
                  const h = window.innerHeight;
                  const w = window.innerWidth;
                  return sels.map((s) => {
                    const el = document.querySelector(s);
                    const r = el.getBoundingClientRect();
                    const inView = r.bottom > 0 && r.top < h && r.right > 0 && r.left < w;
                    return {
                      selector: s,
                      inView,
                      top: r.top,
                      bottom: r.bottom,
                      scrollY: window.scrollY,
                    };
                  });
                }""",
                list(CHROME_SELECTORS),
            )
            for item in vis:
                self.assertFalse(
                    item["inView"],
                    f"{label}: {item['selector']} still in viewport after 1500px scroll: {item}",
                )

            ARTIFACTS.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(ARTIFACTS / f"scrolled-{label}.png"), full_page=False)
        finally:
            page.close()

    def test_desktop_chrome_leaves_viewport(self):
        self._assert_scroll(1440, 900, "desktop")

    def test_mobile_chrome_leaves_viewport(self):
        self._assert_scroll(390, 844, "mobile")


if __name__ == "__main__":
    unittest.main()
