import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.fieldkit import DRY_NOTE, GRID_DEG, SOYBEAN_ID, build_observation

ROOT = Path(__file__).resolve().parents[1]
AT = datetime(2026, 11, 17, 0, 0, tzinfo=timezone.utc)


class FieldKitTests(unittest.TestCase):
    def test_dry_run_file_is_not_a_farm_and_keeps_the_grid(self):
        path = ROOT / "fixtures" / "field" / "dry-run-not-a-farm.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(document["dry_run"])
        self.assertFalse(document["labeled_as_farm"])
        self.assertEqual(document["latitude"], 0.0)
        self.assertEqual(document["longitude"], 0.0)
        self.assertIn("Not a farm", document["note"])
        self.assertEqual(document["crop"], "soybean")
        self.assertEqual(document["crop_ontology_id"], SOYBEAN_ID)
        self.assertEqual(document["gps_accuracy"], "unknown")
        self.assertIsNone(document["gps_accuracy_m"])
        self.assertEqual(document["weather"]["native_resolution_deg"], GRID_DEG)
        self.assertFalse(document["weather"]["shrunk_to_plant"])
        self.assertIsNone(document["weather"]["value"])
        self.assertIsNone(document["yield"])
        self.assertIsNone(document["futures_price"])
        self.assertEqual(document["class_c_policy"], "closed")
        self.assertFalse(document["permits_financial_use"])
        self.assertFalse(document["trade_signal"])

    def test_metres_are_stored_only_when_typed(self):
        unknown = build_observation(
            latitude=0.0, longitude=0.0, note=DRY_NOTE, at=AT, dry_run=True
        )
        self.assertEqual(unknown["gps_accuracy"], "unknown")
        stated = build_observation(
            latitude=1.0,
            longitude=2.0,
            note="row A",
            at=AT,
            dry_run=False,
            metres=4.0,
        )
        self.assertEqual(stated["gps_accuracy_m"], 4.0)
        self.assertEqual(stated["gps_accuracy"], "stated-metres")
        self.assertIsNone(stated["labeled_as_farm"])
        self.assertEqual(stated["weather"]["native_resolution_deg"], 0.05)
        self.assertNotEqual(stated["note"], unknown["note"])
