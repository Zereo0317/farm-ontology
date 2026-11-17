import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.policy import CLASS_C_POLICY
from farm_ontology.soybean_harvest_totals import FILE_URL, record_harvest_totals
from farm_ontology.soybean_table import CITATION_URL, record_table_header

ROOT = Path(__file__).resolve().parents[1]
FILE_TEXT = (
    ROOT / "tests" / "fixtures" / "soybean-harvest-totals.txt"
).read_text(encoding="utf-8")


class SoybeanHarvestTotalTests(unittest.TestCase):
    def test_header_still_stores_no_figure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaises(ValueError):
                record_table_header(folder, citation_url=CITATION_URL, label="yield")
            self.assertEqual(list(folder.iterdir()), [])

    def test_stores_the_two_printed_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "soybean-harvest-totals.json"
            record_harvest_totals(path, FILE_TEXT)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["crop"], "大豆")
        self.assertEqual(stored["period"], "令和６年産")
        self.assertEqual(stored["series"], "収穫量")
        self.assertEqual(stored["unit"], "t")
        self.assertEqual(stored["citation_url"], FILE_URL)
        self.assertEqual(
            [row["area"] for row in stored["rows"]],
            ["全国", "北海道"],
        )
        self.assertEqual(stored["rows"][0]["value"], "252,400")
        self.assertEqual(stored["rows"][1]["value"], "132,400")
        self.assertEqual(
            stored["rows"][1]["printed_under"],
            ["全国農業地域", "都道府県"],
        )
        for row in stored["rows"]:
            self.assertEqual(row["label"], "national or prefecture total")
            self.assertTrue(row["not_the_biratori_field"])
            self.assertEqual(row["not_a_yield_for"], "PC24+PVC")
            self.assertTrue(row["not_a_trade"])
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertNotIn("permits_financial_use_test", stored)
        text = json.dumps(stored, ensure_ascii=False)
        for leftover in ("青森", "都府県", "7,730", "120,000", "7730"):
            self.assertNotIn(leftover, text)
        self.assertEqual(text.count("132,400"), 1)

    def test_a_missing_row_or_a_trade_label_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "soybean-harvest-totals.json"
            with self.assertRaises(ValueError):
                record_harvest_totals(path, "")
            with self.assertRaises(ValueError):
                record_harvest_totals(path, FILE_TEXT.replace("都道府県\t北海道\t132,400", ""))
            with self.assertRaises(ValueError):
                record_harvest_totals(
                    path,
                    FILE_TEXT.replace("都道府県\t北海道\t132,400", "都道府県\t北海道\t1"),
                )
            for label in ("yield", "trade", "Biratori", "PC24+PVC", "252,400"):
                with self.assertRaises(ValueError):
                    record_harvest_totals(path, FILE_TEXT, label=label)
            with self.assertRaises(ValueError):
                record_harvest_totals(path, FILE_TEXT, permits_financial_use=True)
            with self.assertRaises(ValueError):
                record_harvest_totals(path, FILE_TEXT, permits_financial_use_test=True)
            with self.assertRaises(ValueError):
                record_harvest_totals(path, FILE_TEXT, class_c_policy="open")
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_totals(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("soybean_harvest_totals", text)
            self.assertNotIn("soybean_table", text)
            self.assertNotIn("000040286486", text)


if __name__ == "__main__":
    unittest.main()
