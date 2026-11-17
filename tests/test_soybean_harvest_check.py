import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.policy import CLASS_C_POLICY
from farm_ontology.soybean_harvest_check import (
    HARVEST_T,
    PLANTED_AREA_HA,
    YIELD_KG_PER_10A,
    check_printed_hokkaido_harvest,
)

ROOT = Path(__file__).resolve().parents[1]


class SoybeanHarvestCheckTests(unittest.TestCase):
    def test_2024_product_and_rounding_difference(self) -> None:
        stored = check_printed_hokkaido_harvest(2024)
        product = PLANTED_AREA_HA * YIELD_KG_PER_10A // 100
        self.assertEqual(product, 132_444)
        self.assertEqual(stored["planted_area"], "46,800")
        self.assertEqual(stored["planted_area_unit"], "ha")
        self.assertEqual(stored["yield_rate"], "283")
        self.assertEqual(stored["yield_rate_unit"], "kg per 10 ares")
        self.assertEqual(stored["harvest"], "132,400")
        self.assertEqual(stored["harvest_unit"], "t")
        self.assertEqual(stored["product"], product)
        self.assertEqual(stored["product"], 132_444)
        self.assertEqual(stored["difference"], product - HARVEST_T)
        self.assertEqual(stored["difference"], 44)
        self.assertEqual(stored["difference_is"], "rounding")
        self.assertTrue(stored["not_a_new_official_harvest"])
        self.assertEqual(stored["label"], "check of printed figures")
        self.assertEqual(stored["period"], "令和６年産")
        self.assertEqual(stored["area"], "北海道")
        self.assertTrue(stored["not_a_completed_harvest_for_the_biratori_field"])
        self.assertTrue(stored["not_a_trade"])
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertNotIn("permits_financial_use_test", stored)

    def test_2025_and_2026_return_no_tonnes(self) -> None:
        for year in (2025, 2026):
            stored = check_printed_hokkaido_harvest(year)
            self.assertFalse(stored["planted_area_stored"])
            self.assertEqual(stored["year"], year)
            for key in (
                "planted_area",
                "yield_rate",
                "harvest",
                "product",
                "difference",
                "product_unit",
                "harvest_unit",
            ):
                self.assertNotIn(key, stored)
            text = json.dumps(stored)
            for invented in (
                "46,800",
                "46800",
                "283",
                "132,400",
                "132400",
                "132,444",
                "132444",
                "44",
            ):
                self.assertNotIn(invented, text)

    def test_a_trade_switch_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "soybean-harvest-check.json"
            with self.assertRaises(ValueError):
                check_printed_hokkaido_harvest(2024, path, permits_financial_use=True)
            with self.assertRaises(ValueError):
                check_printed_hokkaido_harvest(2024, path, permits_financial_use_test=True)
            with self.assertRaises(ValueError):
                check_printed_hokkaido_harvest(2025, path, class_c_policy="open")
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_check(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("soybean_harvest_check", text)


if __name__ == "__main__":
    unittest.main()
