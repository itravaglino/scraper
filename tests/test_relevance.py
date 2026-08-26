from __future__ import annotations

import unittest

from fitbit_scraper.classify import classify
from fitbit_scraper.relevance import is_fitbit_subject


class OffTopicTests(unittest.TestCase):
    def test_oneplus_watch_wallet_error(self):
        info = classify(
            '[Fix] Google Wallet "Identity Verification Error" when adding a card to Wear OS / OnePlus Watch (In-App Loop)',
            "brand new OnePlus Watch 3 (running Wear OS)",
            source_scoped=False,
            url="https://www.reddit.com/r/WearOS/comments/abc/wallet/",
        )
        self.assertFalse(info["keep"])
        self.assertEqual(info["reason"], "otra_marca")

    def test_framework_laptop(self):
        info = classify(
            "Fixing a bricked Framework laptop",
            "Some people mentioned Fitbit in the comments of this HN thread.",
            source_scoped=False,
            url="https://news.ycombinator.com/item?id=1",
        )
        self.assertFalse(info["keep"])

    def test_chromecast_history(self):
        info = classify(
            "Moments in Chromecast's history",
            "A commenter said they also had a Fitbit.",
            source_scoped=False,
            url="https://news.ycombinator.com/item?id=2",
        )
        self.assertFalse(info["keep"])

    def test_eyeref_wearos(self):
        info = classify(
            "Looking for Wear OS testers for EyeRef, an ophthalmology reference app",
            "Hi everyone, I recently built EyeRef for Wear OS users",
            source_scoped=False,
            url="https://www.reddit.com/r/WearOS/comments/eyeref/",
        )
        self.assertFalse(info["keep"])

    def test_galaxy_watch_whatsapp(self):
        info = classify(
            'Bug WhatsApp : Les messages vocaux envoyés depuis ma Galaxy Watch Ultra 2 sont illisibles',
            "Galaxy Watch Ultra 2 Wear OS iPhone",
            source_scoped=False,
        )
        self.assertFalse(info["keep"])

    def test_generic_wearos_app(self):
        info = classify(
            "Watchletic - The most connected workout app for Wear OS.",
            "A Wear OS app. Someone compared it to Fitbit.",
            source_scoped=False,
        )
        self.assertFalse(info["keep"])

    def test_shopping_roundup(self):
        ok, reason = is_fitbit_subject(
            "Best smartwatches 2026: Apple Watch vs Garmin vs Fitbit vs Samsung",
            "",
            "",
            source_scoped=False,
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "comparativa_genérica")

    def test_fitbit_vs_galaxy_is_on_topic(self):
        info = classify(
            "Fitbit Air (99€) vs Galaxy Watch 7 (80€): ¿Vale la pena pagar más?",
            "Comparo la Fitbit Air contra Galaxy Watch 7. La Fitbit no sincroniza bien.",
            source_scoped=False,
        )
        self.assertTrue(info["keep"])

    def test_charge6_issue_still_kept(self):
        info = classify("Charge 6 battery drain", "It dies after a few hours")
        self.assertTrue(info["keep"])
        self.assertEqual(info["polarity"], "mala")

    def test_pixel_watch_kept(self):
        info = classify(
            "Pixel Watch 3 heart rate spikes",
            "Fitbit tracking on Pixel Watch is broken",
            source_scoped=False,
        )
        self.assertTrue(info["keep"])


if __name__ == "__main__":
    unittest.main()
