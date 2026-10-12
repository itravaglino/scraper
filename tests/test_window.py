from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from fitbit_scraper.feedlist import hn_search_url, news_feeds, reddit_feeds, social_feeds
from fitbit_scraper.sources import _report, _run_source
from fitbit_scraper.window import (
    filter_reports_in_window,
    google_date_ops,
    iso_in_window,
    reddit_t_param,
    scrape_window_days,
)


def _recent_iso(days_ago: int = 2) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


class WindowTests(unittest.TestCase):
    def test_default_window_covers_trimestre(self):
        self.assertEqual(scrape_window_days(), 90)

    def test_env_override(self):
        with patch.dict(os.environ, {"SCRAPE_WINDOW_DAYS": "30"}):
            self.assertEqual(scrape_window_days(), 30)
            self.assertEqual(reddit_t_param(), "month")
            self.assertIn("when:30d", google_date_ops())
            self.assertIn("after:", google_date_ops())

    def test_old_recall_out_of_window(self):
        self.assertFalse(iso_in_window("2020-03-02T12:00:00+00:00"))
        self.assertFalse(iso_in_window("2018-11-01T00:00:00Z"))

    def test_recent_in_window(self):
        self.assertTrue(iso_in_window(_recent_iso(1)))
        self.assertTrue(iso_in_window(_recent_iso(20)))

    def test_undated_rejected(self):
        self.assertFalse(iso_in_window(None))
        self.assertFalse(iso_in_window(""))
        self.assertFalse(iso_in_window("not-a-date"))

    def test_report_drops_old_and_undated(self):
        kwargs = dict(
            source="news",
            source_label="Noticias",
            url="https://example.test/ionic-recall",
            title="Fitbit Ionic recalled due to overheating risk",
            text="Fitbit is recalling the Ionic watch after overheating reports.",
            source_scoped=False,
            source_kind="news",
        )
        self.assertIsNone(_report(**kwargs, created_at="2020-03-02T00:00:00+00:00"))
        self.assertIsNone(_report(**kwargs, created_at=None))
        kept = _report(**kwargs, created_at=_recent_iso(3))
        self.assertIsNotNone(kept)
        self.assertTrue(iso_in_window(kept["created_at"]))

    def test_filter_reports_in_window(self):
        rows = [
            {"id": "old", "created_at": "2021-01-01T00:00:00+00:00", "title": "old"},
            {"id": "new", "created_at": _recent_iso(5), "title": "new"},
            {"id": "blank", "created_at": None, "title": "blank"},
        ]
        kept = filter_reports_in_window(rows)
        self.assertEqual([r["id"] for r in kept], ["new"])

    def test_parse_iso_drops_far_future(self):
        from fitbit_scraper.window import parse_iso

        self.assertIsNone(parse_iso("2535-06-03T00:00:00+00:00"))
        self.assertIsNone(parse_iso("1999-01-01T00:00:00Z"))

    def test_filter_salvages_far_future_help_stamp(self):
        rows = [{"id": "help", "created_at": "2535-06-03T00:00:00+00:00", "title": "Charge 5"}]
        kept = filter_reports_in_window(rows)
        self.assertEqual(len(kept), 1)
        self.assertTrue(kept[0]["created_at"].startswith("202"))

    def test_feed_urls_are_date_bounded(self):
        news = news_feeds()
        self.assertGreaterEqual(len(news), 30)
        gnews = [f for f in news if "news.google.com" in f["url"]]
        bing = [f for f in news if "bing.com" in f["url"]]
        self.assertGreaterEqual(len(gnews), 20)
        self.assertGreaterEqual(len(bing), 2)
        for feed in gnews:
            self.assertTrue("when:" in feed["url"] or "when%3A" in feed["url"], feed["url"])
        site_feeds = [f for f in gnews if "site:" in f["url"] or "site%3A" in f["url"]]
        self.assertTrue(site_feeds)
        for feed in site_feeds:
            self.assertFalse("after:" in feed["url"] or "after%3A" in feed["url"], feed["url"])
        for feed in bing:
            self.assertNotIn("when:", feed["url"])
            self.assertNotIn("after:", feed["url"])
            compact = feed["url"].lower().replace("%3d", "=")
            self.assertIn("format=rss", compact)
        self.assertTrue(any("googlehealth" in f["url"] for f in news))
        social = social_feeds()
        self.assertGreaterEqual(len(social), 10)
        self.assertTrue(any("youtube.com" in f["url"] for f in social))
        self.assertTrue(any("tiktok.com" in f["url"] for f in social))
        self.assertTrue(any("instagram.com" in f["url"] for f in social))
        for feed in social:
            self.assertTrue("when:" in feed["url"] or "when%3A" in feed["url"], feed["url"])
        reddit = reddit_feeds()
        self.assertGreaterEqual(len(reddit), 12)
        self.assertTrue(any("r/fitbit" in (f.get("url") or "") for f in reddit))
        self.assertTrue(any("search.rss" in (f.get("url") or "") for f in reddit))
        for feed in reddit:
            self.assertIn(".rss", feed["url"])
        hn = hn_search_url("fitbit")
        self.assertIn("numericFilters=", hn)
        self.assertTrue("created_at_i>" in hn or "created_at_i%3E" in hn)

    def test_429_skips_source(self):
        def boom():
            raise RuntimeError("HTTP 429 Too Many Requests")

        status = _run_source("gnews_en", "Noticias", boom, kind="news")
        self.assertFalse(status["ok"])
        self.assertEqual(status["state"], "skip")
        self.assertEqual(status["error"], "Límite de peticiones (HTTP 429)")
        self.assertNotIn("RuntimeError", status["error"])
        self.assertEqual(status["reports"], [])


class WorkflowReliabilityTests(unittest.TestCase):
    def test_dispatch_rebases_and_still_deploys(self):
        yml = Path(".github/workflows/daily.yml").read_text(encoding="utf-8")
        self.assertIn("git rebase", yml)
        self.assertIn("git fetch origin main", yml)
        self.assertIn("workflow_dispatch", yml)
        self.assertIn("SCRAPE_WINDOW_DAYS", yml)
        self.assertIn("fetch-depth: 0", yml)
        self.assertIn("upload-pages-artifact", yml)
        self.assertIn("Could not push after retries", yml)
        self.assertIn("exit 0", yml)


if __name__ == "__main__":
    unittest.main()
