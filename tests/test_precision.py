from __future__ import annotations

import unittest

from fitbit_scraper.classify import classify
from fitbit_scraper.models import detect_models


def _not_mala_alta(info: dict) -> None:
    if info.get("keep") and info.get("polarity") == "mala":
        raise AssertionError(f"should not stay in the problem queue: {info}")
    if info.get("severity") == "alta":
        raise AssertionError(f"should never be gravedad alta: {info}")


class GoldFalsePositiveTests(unittest.TestCase):
    """Real misfires from this project. First four must not be mala-alta Fitbit defects."""

    def test_slept_great_reddit_footer(self):
        info = classify(
            "I slept great",
            "I slept great last night. submitted by u/test. "
            "Use this thread if you have a problem with the app or a product recall question.",
            source_scoped=True,
            url="https://www.reddit.com/r/fitbit/comments/abc/slept/",
        )
        _not_mala_alta(info)
        self.assertNotEqual(info.get("severity"), "alta")
        self.assertNotEqual((info.get("polarity"), info.get("severity")), ("mala", "alta"))

    def test_oneplus_watch_wallet(self):
        info = classify(
            '[Fix] Google Wallet "Identity Verification Error" when adding a card to Wear OS / OnePlus Watch (In-App Loop)',
            "brand new OnePlus Watch 3 (running Wear OS)",
            source_scoped=False,
            url="https://www.reddit.com/r/WearOS/comments/abc/wallet/",
        )
        self.assertFalse(info["keep"])
        _not_mala_alta(info)

    def test_framework_laptop(self):
        info = classify(
            "Fixing a bricked Framework laptop",
            "Some people mentioned Fitbit in the comments of this HN thread.",
            source_scoped=False,
            url="https://news.ycombinator.com/item?id=1",
        )
        self.assertFalse(info["keep"])
        _not_mala_alta(info)

    def test_chromecast_history(self):
        info = classify(
            "Moments in Chromecast's history",
            "A commenter said they also had a Fitbit.",
            source_scoped=False,
            url="https://news.ycombinator.com/item?id=2",
        )
        self.assertFalse(info["keep"])
        _not_mala_alta(info)

    def test_galaxy_watch_whatsapp(self):
        info = classify(
            "Bug WhatsApp : Les messages vocaux envoyés depuis ma Galaxy Watch Ultra 2 sont illisibles",
            "Galaxy Watch Ultra 2 Wear OS iPhone",
            source_scoped=False,
        )
        self.assertFalse(info["keep"])
        _not_mala_alta(info)

    def test_huawei_fitbit_agptek_roundup(self):
        info = classify(
            "Huawei vs Fitbit vs Agptek: best fitness bands 2026 roundup",
            "We compared Huawei Band, Fitbit Charge 6 and Agptek watches. Shockingly close.",
            source_scoped=False,
        )
        self.assertFalse(info["keep"])
        _not_mala_alta(info)

    def test_whoop_vs_fitbit_air_review(self):
        info = classify(
            "After 30 days wearing the $100 Fitbit Air alongside my Whoop MG, I have the final verdict. "
            "Shockingly, Whoop overreports deep sleep",
            "I broke this down into four categories: design, sleep, fitness, and health.",
            source_scoped=False,
        )
        _not_mala_alta(info)
        self.assertNotEqual(info.get("severity"), "alta")
        if info.get("keep"):
            self.assertNotEqual(info.get("polarity"), "mala")

    def test_battery_replacement_tutorial_not_alta(self):
        info = classify(
            "Fitbit Charge 5 Battery Replacement Tutorial! Is your Fitbit Charge 5 draining fast or completely dead?",
            "This step-by-step guide walks you through safely opening the device.",
            source_scoped=False,
        )
        self.assertNotEqual(info.get("severity"), "alta")
        if info.get("keep"):
            self.assertNotEqual(info.get("polarity"), "mala")

    def test_real_charge6_drain_still_mala(self):
        info = classify("Charge 6 battery drain", "It dies after a few hours")
        self.assertTrue(info["keep"])
        self.assertEqual(info["polarity"], "mala")
        self.assertGreaterEqual(info["confidence"], 0.5)
        self.assertIsNotNone(info["severity"])
        self.assertNotEqual(info["severity"], "alta")

    def test_bricked_title_can_be_alta(self):
        info = classify("Bricked Fitbit Sense 2", "Won't turn on after the firmware update")
        self.assertEqual(info["polarity"], "mala")
        self.assertEqual(info["severity"], "alta")
        self.assertGreaterEqual(info["confidence"], 0.75)


class ModelPrecisionTests(unittest.TestCase):
    def test_bare_air_is_not_fitbit_air(self):
        self.assertNotIn(
            "Fitbit Air",
            detect_models("I need some fresh air while wearing my Fitbit Charge 6"),
        )

    def test_bare_sense_is_not_sense(self):
        self.assertNotIn("Sense", detect_models("This Fitbit update does not make sense"))
        self.assertEqual(detect_models("Fitbit Sense 2 died"), ["Sense 2"])

    def test_fitbit_air_still_detected(self):
        self.assertEqual(detect_models("The Fitbit Air screen cracked"), ["Fitbit Air"])


if __name__ == "__main__":
    unittest.main()
