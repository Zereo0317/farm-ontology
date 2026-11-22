"""Boundary-walk tests: pins in, governed polygon record out."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology.page_io import dispatch


class BoundaryWalkTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.old = __import__("os").environ.get("FARM_RECORD_DIR")
        __import__("os").environ["FARM_RECORD_DIR"] = self._tmp.name

    def tearDown(self):
        __import__("os").environ.pop("FARM_RECORD_DIR", None)
        if self.old:
            __import__("os").environ["FARM_RECORD_DIR"] = self.old
        self._tmp.cleanup()

    def _full(self, accuracy=3.5):
        return {
            "op": "boundary_walk",
            "parcel_name": "toyomi-1",
            "corners": [
                {"corner": "NW", "lat": 42.7020, "lon": 142.4070, "accuracy_m": accuracy},
                {"corner": "NE", "lat": 42.7020, "lon": 142.4074, "accuracy_m": accuracy},
                {"corner": "SE", "lat": 42.7016, "lon": 142.4074, "accuracy_m": accuracy},
                {"corner": "SW", "lat": 42.7016, "lon": 142.4070, "accuracy_m": accuracy},
            ],
            "centre": {"lat": 42.7018, "lon": 142.4072, "accuracy_m": accuracy},
        }

    def test_walk_persists_with_honest_accuracy(self):
        saved = dispatch(self._full())
        walk = saved["walk"]
        self.assertEqual(walk["record_type"], "boundary-walk")
        self.assertEqual(walk["corner_count"], 4)
        self.assertTrue(walk["points"][0]["gps_accuracy_m"] > 0)
        self.assertEqual(walk["tenure"], "unknown")
        self.assertFalse(walk["permits_financial_use"])
        # file actually written
        path = Path(self._tmp.name) / "boundary" / saved["file"]
        self.assertTrue(path.exists())
        body = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(body["parcel_name"], "toyomi-1")

    def test_three_walks_same_second_preserve_every_record(self):
        from datetime import datetime, timezone
        from unittest.mock import patch
        instant = datetime(2026, 11, 22, 12, tzinfo=timezone.utc)
        with patch("farm_ontology.record._now", return_value=instant):
            saved = [dispatch(self._full()) for _ in range(3)]
        self.assertEqual(len({item["file"] for item in saved}), 3)
        self.assertEqual(len(dispatch({"op": "list_walks"})["walks"]), 3)

    def test_four_metred_corners_yield_a_shoelace_estimate(self):
        saved = dispatch(self._full())
        walk = saved["walk"]
        self.assertIsNotNone(walk["area_estimate_ha"])
        # 44.4 m (lat) × ~32.7 m (lon at 42.7°N) ≈ 0.1455 ha — the shoelace
        # uses the latitude-corrected metre-per-degree, not naive squares.
        self.assertAlmostEqual(walk["area_estimate_ha"], 0.1455, places=2)
        self.assertIn("worst pin accuracy", walk["accuracy_note"])

    def test_missing_accuracy_stays_unknown_never_averaged(self):
        req = self._full()
        for c in req["corners"]:
            c.pop("accuracy_m")
        saved = dispatch(req)
        walk = saved["walk"]
        self.assertIsNone(walk["area_estimate_ha"])  # no fairy maths
        self.assertTrue(all(p["gps_accuracy"] == "unknown" for p in walk["points"]))

    def test_duplicates_and_bad_corners_are_refused(self):
        req = self._full()
        req["corners"][1]["corner"] = "NW"
        with self.assertRaises(ValueError):
            dispatch(req)
        req2 = self._full()
        req2["corners"][2]["corner"] = "XX"
        with self.assertRaises(ValueError):
            dispatch(req2)
        req3 = self._full()
        req3["corners"] = req3["corners"][:2]
        with self.assertRaises(ValueError):
            dispatch(req3)

    def test_list_walks_returns_the_walk(self):
        dispatch(self._full())
        listed = dispatch({"op": "list_walks"})
        self.assertEqual(listed["walks"][0]["parcel_name"], "toyomi-1")

    def test_dry_run_leaves_no_file(self):
        req = self._full()
        req["dry_run"] = True
        saved = dispatch(req)
        path = Path(self._tmp.name) / "boundary" / saved["file"]
        self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
