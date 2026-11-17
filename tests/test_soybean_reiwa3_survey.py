import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.policy import CLASS_C_POLICY
from farm_ontology.soybean_reiwa3_survey import (
    CITATION_URL,
    FILE_URL,
    record_hokkaido_survey,
)

ROOT = Path(__file__).resolve().parents[1]
FILE_TEXT = (ROOT / "tests" / "fixtures" / "soybean-reiwa3-hokkaido.txt").read_text(encoding="utf-8")


class SoybeanReiwa3SurveyTests(unittest.TestCase):
    def test_stores_each_printed_hokkaido_cell_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "soybean-reiwa3-hokkaido.json"
            record_hokkaido_survey(path, FILE_TEXT)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["crop"], "大豆")
        self.assertEqual(stored["period"], "令和３年産")
        self.assertEqual(stored["crop_year"], 2021)
        self.assertEqual(stored["area"], "北海道")
        self.assertEqual(stored["file_name"], "f002-03-021.xls")
        self.assertEqual(stored["citation_url"], CITATION_URL)
        self.assertEqual(stored["file_url"], FILE_URL)
        self.assertEqual(
            [(row["series"], row["value"], row["unit"]) for row in stored["rows"]],
            [
                ("作付面積", "42,000", "ha"),
                ("10ａ当たり収量", "251", "kg"),
                ("収穫量", "105,400", "ｔ"),
            ],
        )
        for row in stored["rows"]:
            self.assertEqual(row["printed_under"], ["全国農業地域", "都道府県"])
            self.assertEqual(row["label"], "prefecture survey total")
            self.assertTrue(row["not_the_biratori_field"])
            self.assertTrue(row["not_a_trade"])
            self.assertEqual(row["area"], "北海道")
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertNotIn("permits_financial_use_test", stored)
        text = json.dumps(stored, ensure_ascii=False)
        for leftover in (
            "青森",
            "146,200",
            "246,500",
            "5,070",
            "8,210",
            "3,100",
            "12,400",
            "235",
        ):
            self.assertNotIn(leftover, text)
        self.assertEqual(text.count("42,000"), 1)
        self.assertEqual(text.count("105,400"), 1)
        self.assertEqual(text.count("251"), 1)

    def test_a_missing_cell_is_omitted(self) -> None:
        blanked = FILE_TEXT.replace("105,400", "")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "soybean-reiwa3-hokkaido.json"
            record_hokkaido_survey(path, blanked)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            [row["series"] for row in stored["rows"]],
            ["作付面積", "10ａ当たり収量"],
        )
        self.assertNotIn("105,400", json.dumps(stored, ensure_ascii=False))

    def test_a_disagreement_or_a_trade_switch_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "soybean-reiwa3-hokkaido.json"
            changed = FILE_TEXT.replace(
                "(都道府県)\n北海道\t42,000",
                "(都道府県)\n北海道\t42,001",
                1,
            )
            with self.assertRaises(ValueError):
                record_hokkaido_survey(path, changed)
            with self.assertRaises(ValueError):
                record_hokkaido_survey(path, "")
            with self.assertRaises(ValueError):
                record_hokkaido_survey(path, FILE_TEXT, label="trade")
            with self.assertRaises(ValueError):
                record_hokkaido_survey(path, FILE_TEXT, permits_financial_use=True)
            with self.assertRaises(ValueError):
                record_hokkaido_survey(path, FILE_TEXT, permits_financial_use_test=True)
            with self.assertRaises(ValueError):
                record_hokkaido_survey(path, FILE_TEXT, class_c_policy="open")
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_survey(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            source = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("soybean_reiwa3_survey", source)


if __name__ == "__main__":
    unittest.main()
