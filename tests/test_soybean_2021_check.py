import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.policy import CLASS_C_POLICY
from farm_ontology.soybean_2021_check import (
    HARVEST_T,
    PLANTED_AREA_HA,
    YIELD_KG_PER_10A,
    check_2021_hokkaido_survey,
)

ROOT = Path(__file__).resolve().parents[1]


class Soybean2021CheckTests(unittest.TestCase):
    def test_2021_product_and_rounding_difference(self) -> None:
        stored = check_2021_hokkaido_survey(2021)
        product = PLANTED_AREA_HA * YIELD_KG_PER_10A * 10 // 1000
        self.assertEqual(product, 105_420)
        self.assertEqual(stored["period"], "令和３年産")
        self.assertEqual(stored["area"], "北海道")
        self.assertEqual(stored["planted_area"], "42,000")
        self.assertEqual(stored["planted_area_unit"], "ha")
        self.assertEqual(stored["yield_rate"], "251")
        self.assertEqual(stored["yield_rate_unit"], "kg per 10 ares")
        self.assertEqual(stored["harvest"], "105,400")
        self.assertEqual(stored["harvest_unit"], "t")
        self.assertEqual(stored["product"], product)
        self.assertEqual(stored["product_unit"], "t")
        self.assertEqual(stored["difference"], product - HARVEST_T)
        self.assertEqual(stored["difference"], 20)
        self.assertEqual(stored["difference_is"], "rounding")
        self.assertTrue(stored["not_a_new_official_harvest"])
        self.assertEqual(stored["label"], "prefecture survey check")
        self.assertTrue(stored["not_a_completed_harvest_for_the_biratori_field"])
        self.assertTrue(stored["not_a_forecast"])
        self.assertTrue(stored["not_a_trade"])
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertNotIn("permits_financial_use_test", stored)
        text = json.dumps(stored, ensure_ascii=False)
        self.assertEqual(text.count("42,000"), 1)
        self.assertEqual(text.count("105,400"), 1)
        self.assertEqual(text.count("251"), 1)

    def test_2025_and_2026_return_no_tonnes(self) -> None:
        for year in (2025, 2026):
            stored = check_2021_hokkaido_survey(year)
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
                "42,000",
                "42000",
                "251",
                "105,400",
                "105400",
                "105,420",
                "105420",
            ):
                self.assertNotIn(invented, text)

    def test_a_trade_switch_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "soybean-2021-check.json"
            with self.assertRaises(ValueError):
                check_2021_hokkaido_survey(2021, path, permits_financial_use=True)
            with self.assertRaises(ValueError):
                check_2021_hokkaido_survey(2021, path, permits_financial_use_test=True)
            with self.assertRaises(ValueError):
                check_2021_hokkaido_survey(2026, path, class_c_policy="open")
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_check(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            source = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("soybean_2021_check", source)


if __name__ == "__main__":
    unittest.main()
