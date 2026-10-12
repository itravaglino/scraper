from __future__ import annotations

import unittest
from datetime import datetime, timezone, timedelta

from fitbit_scraper.classify import classify
from fitbit_scraper.config import ITUNES_COUNTRIES, ITUNES_REVIEW_PAGES, PLAY_COUNTRIES
from fitbit_scraper.feedlist import direct_rss_feeds, news_feeds, x_feeds
from fitbit_scraper.htmlparse import parse_google_health_threads, parse_play_reviews
from fitbit_scraper.sources import _report


def _recent() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()


class MigrationAndPolarityTests(unittest.TestCase):
    def test_verge_workaround_is_mala(self):
        info = classify(
            "Google has closed the retired Fitbit app workaround. | The Verge",
            "Users who sideloaded outdated builds of the Fitbit app to avoid being forced to switch to Google Health.",
            source_scoped=False,
            url="https://www.theverge.com/tech/1009476/google-has-closed-the-retired-fitbit-app-workaround",
        )
        self.assertTrue(info["keep"])
        self.assertEqual(info["polarity"], "mala")

    def test_android_authority_holdouts(self):
        info = classify(
            "Fitbit holdouts are finally being pushed to Google Health",
            "Older Fitbit app versions are now running into a mandatory update screen.",
            source_scoped=False,
            url="https://www.androidauthority.com/fitbit-old-app-forced-google-health-update-3721759/",
        )
        self.assertTrue(info["keep"])
        self.assertEqual(info["polarity"], "mala")

    def test_techradar_hate_headline(self):
        info = classify(
            "‘I hate the new Google Health app’: Fitbit fans bemoan the ‘end of an era’ as last holdouts are forced to switch",
            "Fitbit users are being forced to switch to the Google Health app.",
            source_scoped=False,
        )
        self.assertTrue(info["keep"])
        self.assertEqual(info["polarity"], "mala")

    def test_negative_phrasing_beats_praise(self):
        info = classify(
            "Fitbit Charge 6 is a headache and won't sync",
            "I love the design. Amazing GPS. Excellent build. Best tracker otherwise.",
            source_scoped=False,
        )
        self.assertTrue(info["keep"])
        self.assertEqual(info["polarity"], "mala")
        self.assertEqual(info["models"], ["Charge 6"])

    def test_model_from_title_not_body(self):
        info = classify(
            "Inspire 3 battery drain after Google Health",
            "I used to own a Sense 2 and a Versa 3. The Charge 6 was fine.",
            source_scoped=False,
        )
        self.assertEqual(info["models"], ["Inspire 3"])

    def test_support_battery_thread(self):
        info = classify(
            "My Charge 5 tracker battery is draining within hours",
            "Ever since the Google Health app migration the Charge 5 dies overnight.",
            source_scoped=True,
            url="https://support.google.com/googlehealth/thread/435214373",
        )
        self.assertTrue(info["keep"])
        self.assertEqual(info["polarity"], "mala")
        self.assertEqual(info["models"], ["Charge 5"])

    def test_outage_headline(self):
        info = classify(
            "Fitbit outage: watches won't sync since this morning",
            "Downdetector shows a spike.",
            source_scoped=False,
        )
        self.assertTrue(info["keep"])
        self.assertEqual(info["polarity"], "mala")

    def test_repair_ad_shorts_dropped(self):
        info = classify(
            "Fitbit Charge 5 screen replacement #shorts",
            "We repair Fitbits cheap. Send it in.",
            source_scoped=False,
        )
        self.assertFalse(info["keep"])

    def test_report_keeps_recent_migration(self):
        rec = _report(
            source="news",
            source_label="The Verge RSS",
            url="https://www.theverge.com/tech/1009476/google-has-closed-the-retired-fitbit-app-workaround",
            title="Google has closed the retired Fitbit app workaround",
            text="Sideloaded old Fitbit app builds no longer bypass Google Health.",
            created_at=_recent(),
            source_scoped=False,
            source_kind="news",
        )
        self.assertIsNotNone(rec)
        self.assertEqual(rec["polarity"], "mala")


class FeedExpansionTests(unittest.TestCase):
    def test_direct_rss_and_x(self):
        rss = direct_rss_feeds()
        ids = [f["id"] for f in rss]
        self.assertIn("rss_verge", ids)
        self.assertIn("rss_androidauthority", ids)
        self.assertIn("rss_techradar", ids)
        self.assertIn("rss_gadgetsandwearables", ids)
        self.assertTrue(all(f.get("require_subject") for f in rss))
        x = x_feeds()
        self.assertTrue(any("x.com" in f["url"] or "nitter" in f["url"] or "twitter.com" in f["url"] for f in x))

    def test_news_has_model_and_support_queries(self):
        news = news_feeds()
        ids = [f["id"] for f in news]
        self.assertIn("gnews_support_googlehealth", ids)
        self.assertIn("gnews_migration", ids)
        self.assertIn("gnews_outage", ids)
        self.assertTrue(any(i.startswith("gnews_model_charge_6") for i in ids))
        self.assertTrue(any(i.startswith("gnews_gh_") for i in ids))

    def test_store_coverage(self):
        self.assertGreaterEqual(len(ITUNES_COUNTRIES), 12)
        self.assertGreaterEqual(ITUNES_REVIEW_PAGES, 3)
        self.assertGreaterEqual(len(PLAY_COUNTRIES), 10)


class HtmlParseTests(unittest.TestCase):
    def test_play_reviews(self):
        html = """
        <div data-review-id="abc-1"> Jane more_vert
        <span aria-label="Rated 1 stars out of five stars" role="img"></span>
        <span class="bp9Aid">October 9, 2026</span></header>
        <div class="h3YV2d">Charge 6 won&#39;t sync after Google Health. Battery drain overnight.</div>
        <div data-review-id="abc-1" data-original-thumbs-up-count="7"></div>
        """
        items = parse_play_reviews(html)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["star_rating"], 1)
        self.assertIn("2026-10-09", items[0]["created_at"] or "")
        self.assertIn("won't sync", items[0]["text"])
        self.assertEqual(items[0]["id"], "abc-1")

    def test_google_health_threads(self):
        html = r'''["/googlehealth/thread/435214373?hl=en","My Charge 5 tracker battery is draining within ...","thanks for sharing battery drain",62,"435214373",null,null,null,null,"en",null,"Google Health",null,null,25,null,null,null,null,null,"28:abc","tok",6,null,null,[2,12,70,null,"1779215465730"'''
        items = parse_google_health_threads(html)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], "435214373")
        self.assertIn("Charge 5", items[0]["title"])
        self.assertIn("googlehealth/thread/435214373", items[0]["url"])
        self.assertIsNotNone(items[0]["created_at"])
        self.assertTrue(items[0]["created_at"].startswith("2026-"))

    def test_google_health_rejects_14_digit_future_stamp(self):
        html = r'''["/googlehealth/thread/9?hl=en","Charge 6 battery drain","body",62,"9",null,null,null,null,"en",null,"Google Health",null,null,25,null,null,null,null,null,"28:abc","tok",6,null,null,[2,12,70,null,"17792154657300"'''
        items = parse_google_health_threads(html)
        self.assertEqual(len(items), 1)
        stamp = items[0]["created_at"]
        self.assertTrue(stamp is None or stamp.startswith("202"))


if __name__ == "__main__":
    unittest.main()
