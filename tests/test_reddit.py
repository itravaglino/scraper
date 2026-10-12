from __future__ import annotations

import unittest
from unittest.mock import patch

from fitbit_scraper.config import REDDIT_PAUSE_SEC, REQUEST_RETRIES
from fitbit_scraper.feedlist import reddit_after_token, reddit_feeds, reddit_listing_url
from fitbit_scraper.httputil import parse_retry_after
from fitbit_scraper.sources import public_source_error, scrape_reddit


class RedditPolitenessTests(unittest.TestCase):
    def test_expanded_reddit_feeds(self):
        feeds = reddit_feeds()
        ids = [f["id"] for f in feeds]
        self.assertGreaterEqual(len(feeds), 12)
        self.assertIn("reddit_fitbit_new", ids)
        self.assertIn("reddit_fitbit_top_week", ids)
        self.assertIn("reddit_fitbit_top_month", ids)
        self.assertIn("reddit_googlehealthfitbit", ids)
        self.assertIn("reddit_googlehealthapp", ids)
        self.assertIn("reddit_fitbitair", ids)
        self.assertIn("reddit_q_sync", ids)
        self.assertIn("reddit_q_battery", ids)
        self.assertIn("reddit_q_migration", ids)
        self.assertIn("reddit_global_search", ids)
        self.assertNotIn("reddit_fitness", ids)
        new = next(f for f in feeds if f["id"] == "reddit_fitbit_new")
        self.assertGreaterEqual(new.get("pages") or 1, 2)
        self.assertIn("limit=", new["url"])
        pixel = next(f for f in feeds if f["id"] == "reddit_googlepixelwatch")
        self.assertFalse(pixel["scoped"])

    def test_listing_url_paginates(self):
        first = reddit_listing_url("fitbit", "new")
        self.assertIn("/r/fitbit/new/.rss", first)
        self.assertIn("limit=100", first)
        page2 = reddit_listing_url("fitbit", "new", after="t3_abc")
        self.assertIn("after=t3_abc", page2)
        top = reddit_listing_url("fitbit", "top", t="week")
        self.assertIn("t=week", top)

    def test_after_token(self):
        self.assertEqual(reddit_after_token({"id": "t3_abc123"}), "t3_abc123")
        self.assertEqual(
            reddit_after_token({"url": "https://www.reddit.com/r/fitbit/comments/xyz99/hello/"}),
            "t3_xyz99",
        )

    def test_reddit_pause_is_long(self):
        self.assertGreaterEqual(REDDIT_PAUSE_SEC, 8)
        self.assertGreaterEqual(REQUEST_RETRIES, 3)

    def test_retry_after_seconds(self):
        self.assertEqual(parse_retry_after("12"), 12.0)
        self.assertIsNone(parse_retry_after(None))
        self.assertIsNone(parse_retry_after("nope"))

    def test_public_429_has_no_runtimeerror(self):
        state, msg = public_source_error(RuntimeError("HTTP 429 Too Many Requests"))
        self.assertEqual(state, "skip")
        self.assertEqual(msg, "Límite de peticiones (HTTP 429)")
        self.assertNotIn("RuntimeError", msg)

    def test_reddit_retries_instead_of_skipping_later_jobs(self):
        limited = {
            "ok": False,
            "state": "skip",
            "error": "Límite de peticiones (HTTP 429)",
            "fetched": 0,
            "kept": 0,
            "reports": [],
        }
        calls = []

        def fake_run(source_id, label, fn, kind="web"):
            calls.append(source_id)
            return {**limited, "id": source_id, "label": label, "kind": kind}

        with patch("fitbit_scraper.sources._run_source", side_effect=fake_run):
            results = scrape_reddit()
        self.assertGreaterEqual(len(results), 12)
        self.assertEqual(len(calls), len(results))
        self.assertTrue(all("Omitida" not in (r.get("error") or "") for r in results))
        self.assertIn("reddit_global_search", calls)


if __name__ == "__main__":
    unittest.main()
