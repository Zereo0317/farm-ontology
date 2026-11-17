import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.policy import CLASS_C_POLICY
from farm_ontology.usda_wasde import USDA_WASDE_URL, record_series_header
from farm_ontology.wasde_soybean_domestic import REPORT_URL, record_soybean_domestic_total

ROOT = Path(__file__).resolve().parents[1]
REPORT = (
    ROOT / "tests" / "fixtures" / "wasde1126-soybean-domestic.txt"
).read_text(encoding="utf-8")


class WasdeSoybeanDomesticTests(unittest.TestCase):
    def test_header_still_stores_no_quantity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            saved = record_series_header(folder, citation_url=USDA_WASDE_URL)
            text = (folder / saved["file"]).read_text(encoding="utf-8")
        self.assertNotIn("442.80", text)
        self.assertNotIn("827.51", text)
        self.assertNotIn("value", json.loads(text))

    def test_stores_the_november_world_domestic_total(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "wasde-soybean-domestic.json"
            record_soybean_domestic_total(path, REPORT)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["crop"], "soybean")
        self.assertEqual(stored["area"], "World")
        self.assertEqual(stored["period"], "2026/27")
        self.assertEqual(stored["month"], "Nov")
        self.assertEqual(stored["column"], "Domestic Total")
        self.assertEqual(stored["value"], "442.80")
        self.assertEqual(stored["unit"], "Million Metric Tons")
        self.assertEqual(stored["label"], "projection")
        self.assertEqual(stored["kind"], "projection")
        self.assertTrue(stored["not_a_completed_harvest"])
        self.assertTrue(stored["not_the_biratori_field"])
        self.assertTrue(stored["not_a_trade"])
        self.assertEqual(stored["citation_url"], REPORT_URL)
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertNotIn("permits_financial_use_test", stored)
        text = json.dumps(stored)
        for leftover in (
            "827.51",
            "442.18",
            "124.98",
            "442.50",
            "191.38",
            "386.24",
            "192.55",
            "123.50",
            "306.80",
            "Wheat",
        ):
            self.assertNotIn(leftover, text)

    def test_a_missing_cell_or_a_trade_label_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "wasde-soybean-domestic.json"
            with self.assertRaises(ValueError):
                record_soybean_domestic_total(path, "")
            with self.assertRaises(ValueError):
                record_soybean_domestic_total(path, REPORT.replace("Nov  124.98", "Dec  124.98"))
            with self.assertRaises(ValueError):
                record_soybean_domestic_total(path, "Wheat\nNov  827.51\n")
            for label in ("trade", "harvest", "Biratori", "wheat", "442.80"):
                with self.assertRaises(ValueError):
                    record_soybean_domestic_total(path, REPORT, label=label)
            with self.assertRaises(ValueError):
                record_soybean_domestic_total(path, REPORT, permits_financial_use=True)
            with self.assertRaises(ValueError):
                record_soybean_domestic_total(path, REPORT, permits_financial_use_test=True)
            with self.assertRaises(ValueError):
                record_soybean_domestic_total(path, REPORT, class_c_policy="open")
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_cell(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("wasde_soybean_domestic", text)
            self.assertNotIn("usda_wasde", text)
            self.assertNotIn("commodity-markets/wasde", text)
            self.assertNotIn("wasde1126", text)


if __name__ == "__main__":
    unittest.main()
