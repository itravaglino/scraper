from __future__ import annotations

import unittest

from fitbit_scraper.cluster import cluster_reports


def _rep(i, title, text, cat="bateria", model="Charge 6"):
    return {
        "id": f"r{i}",
        "title": title,
        "text": text,
        "url": f"https://example.test/{i}",
        "source": "test",
        "source_label": "Test",
        "primary_category": cat,
        "categories": [cat],
        "models": [model],
        "severity": "media",
        "sentiment": "negativo",
        "created_at": "2026-08-26T08:00:00-03:00",
        "star_rating": None,
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

    def test_recurring_uses_stable_id(self):
        reports = [_rep(1, "Band broke", "The Charge 6 band clasp broke", cat="correa")]
        first, index = cluster_reports(reports, {"clusters": {}})
        cid = first[0]["id"]
        index["clusters"][cid]["first_seen"] = "2026-08-01"
        second, _ = cluster_reports(reports, index)
        self.assertTrue(second[0]["recurring"])
        self.assertEqual(second[0]["id"], cid)


if __name__ == "__main__":
    unittest.main()
