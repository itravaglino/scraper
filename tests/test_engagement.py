from __future__ import annotations

import unittest

from fitbit_scraper.engagement import format_engagement, parse_engagement_text, pack_engagement


class EngagementTests(unittest.TestCase):
    def test_unknown_is_none_not_zero(self):
        self.assertIsNone(format_engagement({"score": None, "comments": None, "views": None}))
        packed = pack_engagement()
        self.assertIsNone(packed["label"])
        self.assertIsNone(packed["score"])

    def test_does_not_invent_from_empty_text(self):
        parsed = parse_engagement_text("My Fitbit Charge 6 will not sync at all")
        self.assertIsNone(parsed["score"])
        self.assertIsNone(parsed["comments"])
        self.assertIsNone(parsed["views"])

    def test_parses_hn_style_and_views(self):
        parsed = parse_engagement_text("42 points 12 comments 1.2k views")
        self.assertEqual(parsed["score"], 42)
        self.assertEqual(parsed["comments"], 12)
        self.assertEqual(parsed["views"], 1200)
        self.assertIn("42 pts", format_engagement(parsed))

    def test_zero_points_is_known(self):
        label = format_engagement({"score": 0, "comments": None, "views": None})
        self.assertEqual(label, "0 pts")


if __name__ == "__main__":
    unittest.main()
