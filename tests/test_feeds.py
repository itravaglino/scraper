from __future__ import annotations

import unittest

from fitbit_scraper.feeds import parse_feed
from fitbit_scraper.textutil import strip_html


ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Apple Health sync</title>
    <id>t3_abc</id>
    <link href="https://www.reddit.com/r/fitbit/comments/abc/apple_health_sync/"/>
    <updated>2026-08-26T16:45:21+00:00</updated>
    <content type="html">&lt;p&gt;Since Google added Apple Health sync&lt;/p&gt;</content>
    <author><name>/u/tester</name></author>
  </entry>
</feed>
"""


class FeedTests(unittest.TestCase):
    def test_atom(self):
        items = parse_feed(ATOM)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Apple Health sync")
        self.assertIn("reddit.com", items[0]["url"])
        self.assertIn("Apple Health", items[0]["text"])
        self.assertTrue(items[0]["created_at"].startswith("2026-08-26"))
        self.assertIn("engagement", items[0])
        self.assertIsNone(items[0]["engagement"]["score"])

    def test_strip_html(self):
        self.assertEqual(strip_html("<div>Hola <b>Fitbit</b></div>"), "Hola Fitbit")


if __name__ == "__main__":
    unittest.main()
