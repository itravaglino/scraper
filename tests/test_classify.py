from __future__ import annotations

import unittest

from fitbit_scraper.classify import classify, detect_language
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
        self.assertEqual(info["polarity"], "mala")
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
        self.assertEqual(info["polarity"], "mala")

    def test_bricked_is_high_severity(self):
        info = classify("Bricked Fitbit Sense 2", "Won't turn on after the firmware update")
        self.assertEqual(info["polarity"], "mala")
        self.assertEqual(info["severity"], "alta")
        self.assertEqual(info["models"], ["Sense 2"])

    def test_screenless_launch_is_not_a_display_defect(self):
        info = classify(
            "Google lanza Fitbit Air: la pulsera inteligente sin pantalla",
            "Google apuesta por un wearable sin pantallas para competir con Whoop.",
            source_scoped=False,
        )
        self.assertFalse(info["keep"])

    def test_pixel_watch_praise_is_buena_not_severity(self):
        info = classify(
            "Pixel Watch 3 hands-on review",
            "Google's latest Pixel Watch looks great on the wrist. I love the GPS.",
            source_scoped=False,
        )
        self.assertTrue(info["keep"])
        self.assertEqual(info["polarity"], "buena")
        self.assertIsNone(info["severity"])
        self.assertIn("positivo", info["badges"])
        self.assertNotEqual(info.get("primary_category"), "pantalla")

    def test_fix_headline_is_buena_not_gravedad_media(self):
        info = classify(
            "Google has fixed Fitbit Charge 6 battery drain",
            "A firmware update resolved the issue. Users say it now works.",
            source_scoped=False,
        )
        self.assertTrue(info["keep"])
        self.assertEqual(info["polarity"], "buena")
        self.assertIsNone(info["severity"])
        self.assertNotIn("gravedad media", " ".join(info["badges"]))

    def test_mixed_review_goes_to_revisar_not_media(self):
        info = classify(
            "Fitbit Charge 6 review: pros and cons",
            "Some users love the GPS, some users hate the battery. Mixed review.",
            source_scoped=False,
        )
        self.assertEqual(info["polarity"], "revisar")
        self.assertIsNone(info["severity"])

    def test_spanish_falla_is_mala(self):
        info = classify(
            "Fitbit Versa 4 no sincroniza",
            "La aplicación no funciona y la batería se agota a las pocas horas.",
            source_scoped=False,
        )
        self.assertTrue(info["keep"])
        self.assertEqual(info["polarity"], "mala")
        self.assertIsNotNone(info["severity"])
        self.assertEqual(info["language"], "es")

    def test_portuguese_praise_is_buena(self):
        info = classify(
            "Amei meu Fitbit Charge 6",
            "Funciona bem demais, bateria ótima, recomendo.",
            source_scoped=False,
            lang_hint="pt",
        )
        self.assertTrue(info["keep"])
        self.assertEqual(info["polarity"], "buena")
        self.assertIsNone(info["severity"])
        self.assertEqual(info["language"], "pt")

    def test_french_defect_is_mala(self):
        info = classify(
            "Fitbit Charge 6 ne fonctionne pas",
            "La batterie est à plat et la synchronisation plante tout le temps.",
            source_scoped=False,
            lang_hint="fr",
        )
        self.assertTrue(info["keep"])
        self.assertEqual(info["polarity"], "mala")
        self.assertIsNotNone(info["severity"])
        self.assertEqual(info["language"], "fr")

    def test_german_defekt_is_mala(self):
        info = classify(
            "Fitbit Sense 2 Defekt",
            "Die Uhr ist kaputt und funktioniert nicht nach dem Update.",
            source_scoped=False,
            lang_hint="de",
        )
        self.assertTrue(info["keep"])
        self.assertEqual(info["polarity"], "mala")
        self.assertEqual(info["language"], "de")

    def test_italian_praise_not_media(self):
        info = classify(
            "Adoro il GPS del Fitbit Charge 6",
            "Funziona benissimo, ottimo orologio, buona notizia per chi corre.",
            source_scoped=False,
            lang_hint="it",
        )
        self.assertEqual(info["polarity"], "buena")
        self.assertIsNone(info["severity"])

    def test_gps_review_is_not_gravedad_media(self):
        info = classify(
            "Fitbit Charge 4 Review! - It has GPS! But Is it any good for runners?",
            "Unboxing and first look at the GPS band.",
            source_scoped=False,
        )
        self.assertNotEqual(info["polarity"], "mala")
        self.assertIsNone(info["severity"])

    def test_english_screenless_launch_not_a_defect(self):
        info = classify(
            "Google is officially rebooting its wearable strategy with Fitbit Air, a lightweight, screenless fitness tracker",
            "The screen-free band competes with Whoop.",
            source_scoped=False,
        )
        self.assertFalse(info["keep"])
        self.assertNotEqual(info.get("severity"), "media")
        info = classify(
            "Fitbit Charge 6 故障",
            "同期の不具合でバッテリーがすぐ切れる",
            source_scoped=False,
            lang_hint="ja",
        )
        self.assertEqual(info["polarity"], "mala")
        self.assertEqual(info["language"], "ja")
        self.assertIsNotNone(info["severity"])


class LanguageDetectTests(unittest.TestCase):
    def test_spanish(self):
        self.assertEqual(
            detect_language("La batería no funciona y la sincronización falla"),
            "es",
        )

    def test_hint_fallback(self):
        self.assertEqual(detect_language("Fitbit Charge 6", hint="pt"), "pt")

    def test_cjk(self):
        self.assertEqual(detect_language("フィットビット 故障 バッテリー"), "ja")


if __name__ == "__main__":
    unittest.main()
