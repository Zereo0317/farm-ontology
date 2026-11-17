import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.policy import CLASS_C_POLICY
from farm_ontology.soybean_observation_check import (
    ADJUSTMENT_COEFFICIENT,
    check_with_observations,
)

ROOT = Path(__file__).resolve().parents[1]
NDVI = 0.6067
TEMPERATURE_2M = 273.0963548024495
SOIL_WATER = 0.385250727335612
PRECIPITATION = 0.00030462741841574825
OBSERVATIONS = (
    {"ndvi": NDVI},
    {"temperature_2m": TEMPERATURE_2M},
    {"soil_water": SOIL_WATER},
    {"precipitation": PRECIPITATION},
    {
        "ndvi": NDVI,
        "temperature_2m": TEMPERATURE_2M,
        "soil_water": SOIL_WATER,
        "precipitation": PRECIPITATION,
    },
)


class SoybeanObservationCheckTests(unittest.TestCase):
    def test_observations_do_not_change_the_2024_product(self) -> None:
        self.assertEqual(ADJUSTMENT_COEFFICIENT, 0)
        plain = check_with_observations(2024)
        self.assertEqual(plain["product"], 132_444)
        self.assertEqual(plain["label"], "check")
        self.assertTrue(plain["not_a_completed_harvest_for_the_biratori_field"])
        self.assertTrue(plain["not_a_trade"])
        self.assertFalse(plain["permits_financial_use"])
        self.assertEqual(plain["class_c_policy"], CLASS_C_POLICY)
        self.assertNotIn("permits_financial_use_test", plain)
        for observation in OBSERVATIONS:
            stored = check_with_observations(2024, **observation)
            self.assertEqual(stored["product"], 132_444)
            self.assertEqual(stored["product_unit"], "t")
            self.assertEqual(stored["adjustment_coefficient"], 0)
            self.assertEqual(stored["label"], "check")

    def test_observations_create_no_tonnes_for_2025_or_2026(self) -> None:
        for year in (2025, 2026):
            for observation in OBSERVATIONS:
                stored = check_with_observations(year, **observation)
                self.assertFalse(stored["planted_area_stored"])
                self.assertNotIn("product", stored)
                self.assertNotIn("product_unit", stored)
                text = json.dumps(stored)
                for invented in ("132444", "132,444", "46,800", "46800", "132,400"):
                    self.assertNotIn(invented, text)

    def test_a_trade_switch_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "soybean-observation-check.json"
            with self.assertRaises(ValueError):
                check_with_observations(2024, path, ndvi=NDVI, permits_financial_use=True)
            with self.assertRaises(ValueError):
                check_with_observations(2024, path, permits_financial_use_test=True)
            with self.assertRaises(ValueError):
                check_with_observations(2026, path, precipitation=PRECIPITATION, class_c_policy="open")
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_check(self) -> None:
        text = (ROOT / "farm_ontology" / "soybean_observation_check.py").read_text(encoding="utf-8")
        self.assertIn("ADJUSTMENT_COEFFICIENT = 0", text)
        self.assertNotIn("fit", text.lower())
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            source = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("soybean_observation_check", source)


if __name__ == "__main__":
    unittest.main()
