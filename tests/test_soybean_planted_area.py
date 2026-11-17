import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.policy import CLASS_C_POLICY
from farm_ontology.soybean_planted_area import FILE_URL, record_planted_area
from farm_ontology.soybean_table import CITATION_URL, record_table_header

ROOT = Path(__file__).resolve().parents[1]
FILE_TEXT = (ROOT / "tests" / "fixtures" / "soybean-planted-area.txt").read_text(encoding="utf-8")


class SoybeanPlantedAreaTests(unittest.TestCase):
    def test_header_still_stores_no_figure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaises(ValueError):
                record_table_header(folder, citation_url=CITATION_URL, label="yield")
            self.assertEqual(list(folder.iterdir()), [])

    def test_stores_the_two_printed_areas(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "soybean-planted-area.json"
            record_planted_area(path, FILE_TEXT)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["crop"], "大豆")
        self.assertEqual(stored["period"], "令和６年産")
        self.assertEqual(stored["series"], "作付面積")
        self.assertEqual(stored["citation_url"], FILE_URL)
        self.assertEqual([row["area"] for row in stored["rows"]], ["全国", "北海道"])
        self.assertEqual(stored["rows"][0]["value"], "153,900")
        self.assertEqual(stored["rows"][0]["unit"], "ha")
        self.assertEqual(stored["rows"][1]["value"], "46,800")
        self.assertEqual(stored["rows"][1]["unit"], "ha")
        self.assertEqual(stored["rows"][1]["printed_under"], ["全国農業地域", "都道府県"])
        for row in stored["rows"]:
            self.assertEqual(row["label"], "national or prefecture area")
            self.assertTrue(row["not_the_biratori_field"])
            self.assertTrue(row["not_a_trade"])
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertNotIn("permits_financial_use_test", stored)
        text = json.dumps(stored, ensure_ascii=False)
        for leftover in (
            "青森",
            "都府県",
            "107,000",
            "5,640",
            "164",
            "283",
            "252,400",
            "132,400",
            "収穫量",
            "10ａ当たり収量",
        ):
            self.assertNotIn(leftover, text)
        self.assertEqual(text.count("46,800"), 1)

    def test_a_missing_cell_is_omitted_and_a_trade_label_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "soybean-planted-area.json"
            national_only = "\n".join(
                line
                for line in FILE_TEXT.splitlines()
                if "北海道" not in line and "都府県" not in line and "青森" not in line
            )
            record_planted_area(path, national_only)
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual([row["area"] for row in stored["rows"]], ["全国"])
            path.unlink()
            with self.assertRaises(ValueError):
                record_planted_area(path, "")
            with self.assertRaises(ValueError):
                record_planted_area(
                    path,
                    FILE_TEXT.replace("都道府県\t北海道\t46,800\tha", "都道府県\t北海道\t1\tha"),
                )
            for label in ("yield", "trade", "Biratori", "PC24+PVC", "153,900"):
                with self.assertRaises(ValueError):
                    record_planted_area(path, FILE_TEXT, label=label)
            with self.assertRaises(ValueError):
                record_planted_area(path, FILE_TEXT, permits_financial_use=True)
            with self.assertRaises(ValueError):
                record_planted_area(path, FILE_TEXT, permits_financial_use_test=True)
            with self.assertRaises(ValueError):
                record_planted_area(path, FILE_TEXT, class_c_policy="open")
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_areas(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("soybean_planted_area", text)
            self.assertNotIn("soybean_table", text)
            self.assertNotIn("000040286486", text)


if __name__ == "__main__":
    unittest.main()
