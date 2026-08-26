from __future__ import annotations

import unittest

from fitbit_scraper.config import REDDIT_PAUSE_SEC
from fitbit_scraper.feedlist import reddit_feeds
from fitbit_scraper.httputil import parse_retry_after
from fitbit_scraper.sources import public_source_error, scrape_reddit
from unittest.mock import patch


class RedditPolitenessTests(unittest.TestCase):
    def test_few_reddit_feeds(self):
        feeds = reddit_feeds()
        self.assertLessEqual(len(feeds), 4)
        ids = [f["id"] for f in feeds]
        self.assertIn("reddit_fitbit", ids)
        self.assertIn("reddit_global_search", ids)
        self.assertNotIn("reddit_global_pt", ids)
        self.assertNotIn("reddit_fitness", ids)

    def test_reddit_pause_is_long(self):
        self.assertGreaterEqual(REDDIT_PAUSE_SEC, 8)

    def test_retry_after_seconds(self):
        self.assertEqual(parse_retry_after("12"), 12.0)
        self.assertIsNone(parse_retry_after(None))
        self.assertIsNone(parse_retry_after("nope"))

    def test_public_429_has_no_runtimeerror(self):
        state, msg = public_source_error(RuntimeError("HTTP 429 Too Many Requests"))
        self.assertEqual(state, "skip")
        self.assertEqual(msg, "Límite de peticiones (HTTP 429)")
        self.assertNotIn("RuntimeError", msg)

    def test_reddit_stops_after_two_limits(self):
        limited = {
            "ok": False,
            "state": "skip",
            "error": "Límite de peticiones (HTTP 429)",
            "fetched": 0,
            "kept": 0,
            "reports": [],
        }

        def fake_run(source_id, label, fn, kind="web"):
            return {**limited, "id": source_id, "label": label, "kind": kind}

        with patch("fitbit_scraper.sources._run_source", side_effect=fake_run):
            results = scrape_reddit()
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["error"], "Límite de peticiones (HTTP 429)")
        self.assertEqual(results[1]["error"], "Límite de peticiones (HTTP 429)")
        self.assertIn("Omitida", results[2]["error"])


if __name__ == "__main__":
    unittest.main()
