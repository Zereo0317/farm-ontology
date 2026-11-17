import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology.nbs_industrial import (
    NBS_INDUSTRIAL_URL,
    REPRODUCTION_SENTENCE,
    record_series_header,
)
from farm_ontology.nbs_industrial_growth import (
    PRINTED_TITLE,
    VALUE,
    record_title_growth_rate,
)
from farm_ontology.policy import CLASS_C_POLICY


class NbsIndustrialGrowthTests(unittest.TestCase):
    def test_stores_the_title_growth_rate_with_the_attribution_sentence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nbs-industrial-growth.json"
            record_title_growth_rate(path, NBS_INDUSTRIAL_URL)
            stored = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(stored["title"], "2026年10月份规模以上工业增加值增长4.8%")
        self.assertEqual(stored["title"], PRINTED_TITLE)
        self.assertEqual(stored["value"], 4.8)
        self.assertEqual(stored["value"], VALUE)
        self.assertIsInstance(stored["value"], float)
        self.assertEqual(stored["unit"], "%")
        self.assertEqual(stored["kind"], "growth rate")
        self.assertEqual(stored["statement"], "This is a growth rate, not a quantity of goods.")
        self.assertEqual(stored["publisher"], "国家统计局")
        self.assertEqual(stored["reproduction_sentence"], REPRODUCTION_SENTENCE)
        self.assertIn("国家统计局", stored["reproduction_sentence"])
        self.assertIn("www.stats.gov.cn", stored["reproduction_sentence"])
        self.assertEqual(stored["citation_url"], NBS_INDUSTRIAL_URL)
        self.assertIs(stored["permits_financial_use"], False)
        self.assertEqual(CLASS_C_POLICY, "closed")
        text = json.dumps(stored, ensure_ascii=False)
        self.assertNotIn("2000", text)
        self.assertNotIn("10:00", text)
        self.assertNotIn("11/16", text)
        self.assertNotIn("trade", stored)
        self.assertNotIn("quantity", stored)

    def test_reading_the_stored_record_writes_no_trade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "nbs-industrial-growth.json"
            record_title_growth_rate(path, NBS_INDUSTRIAL_URL)
            before = path.read_text(encoding="utf-8")
            names_before = sorted(item.name for item in folder.iterdir())
            record = json.loads(before)
            after = path.read_text(encoding="utf-8")
            names_after = sorted(item.name for item in folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names_after, names_before)
        self.assertEqual(names_after, ["nbs-industrial-growth.json"])
        self.assertEqual(record["value"], 4.8)
        self.assertEqual(record["kind"], "growth rate")
        self.assertIn("not a quantity of goods", record["statement"])
        self.assertIs(record["permits_financial_use"], False)
        self.assertNotIn("trade", record)
        self.assertFalse((folder / "trade.json").exists())

    def test_header_function_still_rejects_a_growth_rate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaises(ValueError):
                record_series_header(folder, citation_url=NBS_INDUSTRIAL_URL, value=4.8)
            self.assertEqual(list(folder.iterdir()), [])

    def test_other_numbers_and_a_trade_label_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nbs-industrial-growth.json"
            with self.assertRaises(ValueError):
                record_title_growth_rate(path, NBS_INDUSTRIAL_URL, value=2000)
            with self.assertRaises(ValueError):
                record_title_growth_rate(path, NBS_INDUSTRIAL_URL, label="trade")
            with self.assertRaises(ValueError):
                record_title_growth_rate(
                    path,
                    NBS_INDUSTRIAL_URL,
                    label="quantity of goods",
                )
            with self.assertRaises(ValueError):
                record_title_growth_rate(path, None)
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
