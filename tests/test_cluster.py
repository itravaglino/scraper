from __future__ import annotations

import unittest

from fitbit_scraper.cluster import cluster_reports


def _rep(i, title, text, cat="bateria", model="Charge 6", polarity="mala", severity="media", lang="en"):
    return {
        "id": f"r{i}",
        "title": title,
        "text": text,
        "url": f"https://example.test/{i}",
        "source": "test",
        "source_label": "Test",
        "source_kind": "reddit",
        "primary_category": cat,
        "categories": [cat],
        "models": [model],
        "severity": severity if polarity == "mala" else None,
        "sentiment": "negativo" if polarity == "mala" else "positivo",
        "polarity": polarity,
        "language": lang,
        "language_label": "Inglés" if lang == "en" else lang,
        "created_at": "2026-08-26T08:00:00-03:00",
        "confidence": 0.8,
    }


class ClusterTests(unittest.TestCase):
    def test_similar_battery_reports_merge(self):
        reports = [
            _rep(1, "Battery drain", "Charge 6 battery dies after a few hours of use"),
            _rep(2, "Battery dies", "My Charge 6 battery dies after a few hours now"),
            _rep(3, "GPS drift", "GPS track jumps all over the city during a run", cat="gps"),
        ]
        clusters, _ = cluster_reports(reports, {"clusters": {}})
        self.assertGreaterEqual(len(clusters), 2)
        battery = [c for c in clusters if c["category"] == "bateria"][0]
        self.assertGreaterEqual(battery["count"], 2)
        self.assertFalse(battery["recurring"])
        self.assertEqual(battery["polarity"], "mala")

    def test_recurring_uses_stable_id(self):
        reports = [_rep(1, "Band broke", "The Charge 6 band clasp broke", cat="correa")]
        first, index = cluster_reports(reports, {"clusters": {}})
        cid = first[0]["id"]
        index["clusters"][cid]["first_seen"] = "2026-08-01"
        second, _ = cluster_reports(reports, index)
        self.assertTrue(second[0]["recurring"])
        self.assertEqual(second[0]["id"], cid)

    def test_does_not_mix_buena_into_mala_case(self):
        reports = [
            _rep(1, "Battery drain", "Charge 6 dies in two hours", polarity="mala"),
            _rep(
                2,
                "Google fixed Charge 6 battery",
                "Update now works great",
                polarity="buena",
                severity=None,
            ),
        ]
        clusters, _ = cluster_reports(reports, {"clusters": {}})
        self.assertEqual(len(clusters), 2)
        polarities = {c["polarity"] for c in clusters}
        self.assertEqual(polarities, {"mala", "buena"})
        buena = [c for c in clusters if c["polarity"] == "buena"][0]
        self.assertIsNone(buena["severity"])
        mala = [c for c in clusters if c["polarity"] == "mala"][0]
        self.assertEqual(mala["severity"], "media")

    def test_gps_praise_not_in_gps_bug_cluster(self):
        reports = [
            _rep(1, "GPS drift", "GPS lost during run", cat="gps", polarity="mala"),
            _rep(2, "Love the GPS", "GPS is great", cat="gps", polarity="buena", severity=None),
        ]
        clusters, _ = cluster_reports(reports, {"clusters": {}})
        self.assertEqual(len(clusters), 2)

    def test_unrelated_sin_modelo_do_not_dumpster(self):
        reports = [
            _rep(
                1,
                "Whoop comparison final verdict",
                "I wore both",
                cat="calidad",
                model="Sin modelo",
                polarity="mala",
                severity="baja",
            ),
            _rep(
                2,
                "Warranty replacement took months",
                "hardware quality",
                cat="calidad",
                model="Sin modelo",
                polarity="mala",
                severity="alta",
            ),
        ]
        reports[0]["confidence"] = 0.4
        reports[1]["confidence"] = 0.82
        clusters, _ = cluster_reports(reports, {"clusters": {}})
        self.assertEqual(len(clusters), 2)

    def test_severity_is_majority_not_max(self):
        reports = [
            _rep(1, "Charge 6 battery drain overnight", "dies at night", severity="media"),
            _rep(2, "Charge 6 battery drain continues", "still dying", severity="media"),
            _rep(3, "Charge 6 battery drain recall rumor", "someone said recall", severity="alta"),
        ]
        reports[0]["confidence"] = 0.8
        reports[1]["confidence"] = 0.8
        reports[2]["confidence"] = 0.3
        clusters, _ = cluster_reports(reports, {"clusters": {}})
        battery = [c for c in clusters if c["category"] == "bateria"][0]
        self.assertEqual(battery["severity"], "media")
        self.assertGreaterEqual(battery["count"], 2)


if __name__ == "__main__":
    unittest.main()
