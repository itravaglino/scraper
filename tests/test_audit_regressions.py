"""Regression cases taken from the 1065-item scrape (false positives + true positives)."""

from __future__ import annotations

import unittest

from fitbit_scraper.classify import classify
from fitbit_scraper.pipeline import _community_scoped
from fitbit_scraper.relevance import is_fitbit_subject, is_noise_title


class FalsePositiveDrops(unittest.TestCase):
    def test_casio_hn(self):
        info = classify(
            "Casio F-B100W-1A",
            "A comment mentioned fitness trackers including Fitbit.",
            source_scoped=False,
            url="https://news.ycombinator.com/item?id=1",
        )
        self.assertFalse(info["keep"])

    def test_hamilton_dashboard(self):
        info = classify(
            "Show HN: Hamilton – a no-internet Android health dashboard, named after my dog",
            "Offline dashboard. Someone compared it to Fitbit.",
            source_scoped=False,
            url="https://play.google.com/store/apps/details?id=app.hamilton",
        )
        self.assertFalse(info["keep"])

    def test_macos_buggy(self):
        info = classify(
            "macOS 27 is so buggy",
            "Comments wander into wearables. Fitbit got mentioned.",
            source_scoped=False,
            url="https://news.ycombinator.com/item?id=2",
        )
        self.assertFalse(info["keep"])

    def test_luffu_spinout(self):
        info = classify(
            "JUST IN: Fitbit’s founders just launched a screenless health band for families. "
            "Luffu Link is built to help families keep track of aging parents",
            "Luffu Link, not a Fitbit product.",
            source_scoped=False,
        )
        self.assertFalse(info["keep"])
        self.assertEqual(info["reason"], "spinout_competidor")

    def test_smart_rings(self):
        info = classify(
            "Giving up on smart rings",
            "Oura and RingConn comparison. A Fitbit user comments.",
            source_scoped=False,
            url="https://news.ycombinator.com/item?id=3",
        )
        self.assertFalse(info["keep"])

    def test_pixel_watch_faces_only(self):
        info = classify(
            "Pixel Watch owners: 21-day test of two watch faces (free access if selected)",
            "Looking for Pixel Watch testers for watch faces. GPS is native.",
            source_scoped=True,
            url="https://www.reddit.com/r/fitbit/comments/abc/faces/",
        )
        self.assertFalse(info["keep"])
        self.assertEqual(info["reason"], "pixel_watch_only")

    def test_edge_unveil_dropped_even_if_forum_labeled(self):
        info = classify(
            "Google Fitbit Edge unveiled, reinventing the old pebble-style Fitbit",
            "Google announced the Fitbit Edge today.",
            source_scoped=True,
            url="https://www.wired.com/story/fitbit-edge/",
        )
        self.assertFalse(info["keep"])
        self.assertEqual(info["reason"], "lanzamiento")

    def test_shopping_roundup_women(self):
        info = classify(
            "Top 5 Best Fitbit For Women 2026 - Pixelfy.me",
            "Affiliate shopping list of Fitbit trackers.",
            source_scoped=False,
        )
        self.assertFalse(info["keep"])

    def test_youtube_pipe_dump(self):
        info = classify(
            "Delhi Internet Shutdown | Fitbit Edge | SBI UPI Scam Alert | OnePlus Ace 7 | 12 Oct 2026 - YouTube",
            "News dump thumbnail collage.",
            source_scoped=False,
        )
        self.assertFalse(info["keep"])
        self.assertIn(info["reason"], {"ruido_agregado", "otra_marca", "spinout_competidor"})

    def test_aliexpress_bands(self):
        info = classify(
            "Fitbit AIR Best Accuracy: 10$ AliExpress Bands Are AMAZING! - YouTube",
            "Cheap third-party straps.",
            source_scoped=False,
        )
        self.assertFalse(info["keep"])

    def test_whoops_and_ouras(self):
        info = classify(
            "Finally some Fitbit love in the 3rd party space - compare your sleep stats to your friends w/ Whoops and Ouras",
            "Third-party sleep social app.",
            source_scoped=True,
        )
        self.assertFalse(info["keep"])
        self.assertEqual(info["reason"], "whoop")

    def test_ultrahuman_dashboard(self):
        info = classify(
            "I missed Bevel on Android, so I built my own: one dashboard for everything in Health Connect (+ Ultrahuman)",
            "Indie Health Connect dashboard.",
            source_scoped=True,
        )
        self.assertFalse(info["keep"])

    def test_prime_day_deal(self):
        info = classify(
            "The Fitbit that fixed my broken sleep schedule is down to £59.99 in Amazon Prime Day sale - Tom's Guide",
            "Sale price on a tracker.",
            source_scoped=False,
        )
        self.assertFalse(info["keep"])

    def test_now_available_india_is_launch(self):
        info = classify(
            "Google Fitbit Air is now available in India!",
            "Retail launch announcement.",
            source_scoped=True,
            url="https://support.google.com/googlehealth/thread/1",
        )
        self.assertFalse(info["keep"])
        self.assertEqual(info["reason"], "lanzamiento")

    def test_google_help_wrapped_rss_is_scoped(self):
        self.assertTrue(
            _community_scoped(
                {
                    "source_kind": "support",
                    "source_label": "Soporte Google Health",
                    "title": "Severe Battery Drain Issue After Latest App Update - Google Help",
                    "url": "https://news.google.com/rss/articles/CBMiswFBVV95cUxP",
                }
            )
        )

    def test_community_url_not_wired(self):
        self.assertFalse(
            _community_scoped(
                {
                    "source_kind": "support",
                    "source_label": "community.fitbit.com",
                    "url": "https://www.wired.com/story/google-fitbit-edge/",
                }
            )
        )
        self.assertTrue(
            _community_scoped(
                {
                    "source_kind": "support",
                    "source_label": "Google Health Community",
                    "url": "https://support.google.com/googlehealth/thread/435214373",
                }
            )
        )


class TruePositiveKeeps(unittest.TestCase):
    def test_killed_charge_5(self):
        info = classify(
            "Recent app update has killed my Charge 5",
            "Since Google Health the Charge 5 dies overnight.",
            source_scoped=True,
            url="https://support.google.com/googlehealth/thread/1",
        )
        self.assertTrue(info["keep"])
        self.assertEqual(info["polarity"], "mala")
        self.assertEqual(info["models"], ["Charge 5"])

    def test_charge_6_no_longer_syncing(self):
        info = classify(
            "Charge 6 no longer syncing and now not pairing",
            "Charge 6 will not pair after the app update.",
            source_scoped=True,
            url="https://support.google.com/googlehealth/thread/2",
        )
        self.assertTrue(info["keep"])
        self.assertEqual(info["polarity"], "mala")

    def test_sense_battery_no_longer_accepts(self):
        info = classify(
            "Fitbit Sense battery no longer accepts recharge",
            "The Sense sits on the charger at 0%.",
            source_scoped=True,
            url="https://support.google.com/googlehealth/thread/3",
        )
        self.assertTrue(info["keep"])
        self.assertEqual(info["polarity"], "mala")

    def test_inspire_solid_green(self):
        info = classify(
            "Inspire 3 Solid Green Screen - Google Help",
            "Screen is stuck green after the update.",
            source_scoped=True,
        )
        self.assertTrue(info["keep"])
        self.assertEqual(info["polarity"], "mala")

    def test_air_isnt_autotracking(self):
        info = classify(
            "Fitbit air isn't autotracking workouts. - Google Help",
            "Walks are not detected.",
            source_scoped=True,
        )
        self.assertTrue(info["keep"])
        self.assertEqual(info["polarity"], "mala")

    def test_unicode_wont_connect(self):
        info = classify(
            "Fitbit Charge 6 won’t connect after Google Health",
            "Pairing fails every time.",
            source_scoped=False,
        )
        self.assertTrue(info["keep"])
        self.assertEqual(info["polarity"], "mala")

    def test_complaints_megathread_kept(self):
        info = classify(
            "Weekly Google Health / Fitbit App Feedback & Complaints Megathread",
            "Post app bugs here.",
            source_scoped=True,
            url="https://www.reddit.com/r/fitbit/comments/mega/",
        )
        self.assertTrue(info["keep"])
        self.assertEqual(info["polarity"], "mala")

    def test_verge_workaround(self):
        info = classify(
            "Google has closed the retired Fitbit app workaround. | The Verge",
            "Sideloaded old Fitbit app builds no longer bypass Google Health.",
            source_scoped=False,
            url="https://www.theverge.com/tech/1009476/google-has-closed-the-retired-fitbit-app-workaround",
        )
        self.assertTrue(info["keep"])
        self.assertEqual(info["polarity"], "mala")

    def test_generic_fitbit_title_dropped_not_revisar(self):
        info = classify(
            "Fitbit air on iPhone",
            "Just got one.",
            source_scoped=True,
            url="https://www.reddit.com/r/fitbit/comments/airiphone/",
        )
        self.assertFalse(info["keep"])
        self.assertEqual(info["reason"], "sin_senal")

    def test_undercounts_is_mala_not_revisar(self):
        info = classify(
            "The Air undercounts and I have evidence.",
            "Steps are short vs phone.",
            source_scoped=True,
        )
        self.assertTrue(info["keep"])
        self.assertEqual(info["polarity"], "mala")

    def test_frayed_strap_is_mala(self):
        info = classify(
            "Fitbit Air strap fabric frayed out. It's been only 3 months. Is it normal?",
            "The band is coming apart.",
            source_scoped=True,
        )
        self.assertTrue(info["keep"])
        self.assertEqual(info["polarity"], "mala")

    def test_noise_whoop_regex_plural(self):
        noisy, why = is_noise_title("Fitbit vs Whoops sleep comparison")
        self.assertTrue(noisy)
        self.assertEqual(why, "whoop")

    def test_truncated_google_help_is_mala(self):
        info = classify(
            "since the new update 5.07 the app no longer ...",
            "since the new update 5.07 the app no longer syncs. Google Help",
            source_scoped=True,
            url="https://news.google.com/rss/articles/abc",
        )
        self.assertTrue(info["keep"])
        self.assertEqual(info["polarity"], "mala")

    def test_body_complaint_under_generic_title_is_mala(self):
        info = classify(
            "Fitbit air on iPhone",
            "I bought my Fitbit air yesterday. For some reason it is not tracking my heart rate "
            "and did not track my sleep last night. Is it faulty?",
            source_scoped=True,
            url="https://www.reddit.com/r/fitbit/comments/airiphone/",
        )
        self.assertTrue(info["keep"])
        self.assertEqual(info["polarity"], "mala")

    def test_pixel_plus_air_kept(self):
        ok, reason = is_fitbit_subject(
            "Pixel Watch + Fitbit Air: Notifications and Health Guardian?",
            "Can I use both?",
            "https://www.reddit.com/r/fitbit/comments/pw/",
            source_scoped=True,
        )
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
