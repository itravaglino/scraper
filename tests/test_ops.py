from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPS = ROOT / "web" / "assets" / "ops.js"


def _ops(expr: str):
    script = (
        "const fs=require('fs');"
        f"eval(fs.readFileSync({json.dumps(str(OPS))},'utf8'));"
        f"console.log(JSON.stringify({expr}));"
    )
    r = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


class FilterUrlTests(unittest.TestCase):
    def test_defaults(self):
        st = _ops("FitbitOps.parseState('')")
        self.assertEqual(st["polarity"], "mala")
        self.assertEqual(st["range"], 30)
        self.assertEqual(st["sev"], "")

    def test_roundtrip(self):
        qs = _ops(
            "FitbitOps.serializeState({polarity:'buena',range:7,sev:'alta',model:'Charge 6',q:'batería'})"
        )
        self.assertIn("p=buena", qs)
        self.assertIn("t=7", qs)
        self.assertIn("s=alta", qs)
        parsed = _ops(f"FitbitOps.parseState({json.dumps('?' + qs)})")
        self.assertEqual(parsed["polarity"], "buena")
        self.assertEqual(parsed["range"], 7)
        self.assertEqual(parsed["sev"], "alta")
        self.assertEqual(parsed["model"], "Charge 6")
        self.assertEqual(parsed["q"], "batería")

    def test_csv_columns(self):
        cols = _ops("FitbitOps.CSV_COLUMNS")
        self.assertEqual(
            cols,
            [
                "id",
                "polarity",
                "severity",
                "models",
                "category",
                "published_at",
                "source",
                "title",
                "url",
                "count",
                "language",
                "impact",
            ],
        )
        csv = _ops(
            "FitbitOps.clustersToCsv([{id:'c1',polarity:'mala',severity:'alta',models:['Charge 6'],"
            "category_label:'Batería',last_report_at:'2026-08-26T12:00:00+00:00',sources:['Reddit'],"
            "title:'Battery drain',reports:[{url:'https://example.test/1'}],count:2,"
            "language_labels:['Inglés'],engagement_label:'12 pts'}])"
        )
        header = csv.split("\n")[0]
        self.assertEqual(header, ",".join(cols))
        self.assertIn("Battery drain", csv)
        self.assertIn("alta", csv)

    def test_in_range_drops_old(self):
        now = 1780000000000  # fixed
        self.assertTrue(
            _ops(f"FitbitOps.inRange(new Date({now - 86400000}).toISOString(), 30, {now})")
        )
        self.assertFalse(
            _ops("FitbitOps.inRange('2020-03-02T00:00:00Z', 30, Date.parse('2026-08-26T00:00:00Z'))")
        )


if __name__ == "__main__":
    unittest.main()
