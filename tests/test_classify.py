from __future__ import annotations

import unittest

from fitbit_scraper.classify import classify
from fitbit_scraper.models import detect_models


class ModelDetectionTests(unittest.TestCase):
    def test_charge_6(self):
        self.assertEqual(detect_models("My Fitbit Charge 6 battery died"), ["Charge 6"])

    def test_does_not_promote_family_when_numbered(self):
        self.assertEqual(detect_models("Fitbit Versa 4 GPS is broken"), ["Versa 4"])

    def test_ignores_make_sense(self):
        self.assertNotIn("Sense", detect_models("This Fitbit update does not make sense"))

    def test_ignores_vice_versa(self):
        self.assertNotIn("Versa", detect_models("I sync Fitbit and Apple Health, and vice versa"))

    def test_pixel_watch(self):
        self.assertEqual(detect_models("Pixel Watch 3 heart rate spikes"), ["Pixel Watch 3"])

    def test_fitbit_air(self):
        self.assertEqual(detect_models("The Fitbit Air screen cracked"), ["Fitbit Air"])


class ClassifyTests(unittest.TestCase):
    def test_battery_issue(self):
        info = classify("Charge 6 battery drain", "It dies after a few hours")
        self.assertTrue(info["keep"])
        self.assertEqual(info["primary_category"], "bateria")
        self.assertIn(info["severity"], {"alta", "media", "baja"})
        self.assertEqual(info["models"], ["Charge 6"])

    def test_drops_unrelated_news(self):
        info = classify(
            "Local football club wins again",
            "A great match in Buenos Aires",
            source_scoped=False,
        )
        self.assertFalse(info["keep"])

    def test_low_star_review(self):
        info = classify("Horrible app", "Crashes every time I open it", star_rating=1)
        self.assertTrue(info["keep"])
        self.assertEqual(info["sentiment"], "negativo")

    def test_bricked_is_high_severity(self):
        info = classify("Bricked Fitbit Sense 2", "Won't turn on after the firmware update")
        self.assertEqual(info["severity"], "alta")
        self.assertEqual(info["models"], ["Sense 2"])

    def test_screenless_launch_is_not_a_display_defect(self):
        info = classify(
            "Google lanza Fitbit Air: la pulsera inteligente sin pantalla",
            "Google apuesta por un wearable sin pantallas para competir con Whoop.",
            source_scoped=False,
        )
        self.assertFalse(info["keep"])

    def test_pixel_watch_is_not_a_screen_issue(self):
        info = classify(
            "Pixel Watch 3 hands-on review",
            "Google's latest Pixel Watch looks great on the wrist.",
            source_scoped=False,
        )
        self.assertFalse(info["keep"])
        self.assertNotEqual(info.get("primary_category"), "pantalla")


if __name__ == "__main__":
    unittest.main()
