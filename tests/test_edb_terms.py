import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology.edb_manufacturing import EDB_MANUFACTURING_URL, record_series_header
from farm_ontology.edb_terms import (
    REPRODUCTION_SENTENCE,
    TERMS_URL,
    record_terms_sentence,
)
from farm_ontology.policy import CLASS_C_POLICY


class EdbTermsTests(unittest.TestCase):
    def test_stores_the_reproduction_sentence_and_the_personal_download_exception(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "edb-terms.json"
            record_terms_sentence(path, EDB_MANUFACTURING_URL)
            stored = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(stored["citation_url"], EDB_MANUFACTURING_URL)
        self.assertEqual(stored["terms_url"], "https://www.edb.gov.sg/en/terms")
        self.assertEqual(stored["terms_url"], TERMS_URL)
        self.assertEqual(stored["reproduction_sentence"], REPRODUCTION_SENTENCE)
        self.assertIn("without the prior written permission of EDB", stored["reproduction_sentence"])
        self.assertIn(
            "download one copy of the material on a single computer for your own personal domestic use only",
            stored["reproduction_sentence"],
        )
        self.assertEqual(
            stored["statement"],
            "An index is not a quantity of goods and not a trade.",
        )
        self.assertIs(stored["permits_financial_use"], False)
        self.assertEqual(CLASS_C_POLICY, "closed")
        self.assertNotIn("value", stored)
        self.assertNotIn("index_value", stored)
        text = json.dumps(stored)
        self.assertNotIn("2019=100", text)
        self.assertNotIn(".xls", text)
        self.assertNotIn(".xlsx", text)

    def test_reading_the_stored_record_writes_no_trade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "edb-terms.json"
            record_terms_sentence(path, EDB_MANUFACTURING_URL)
            before = path.read_text(encoding="utf-8")
            names_before = sorted(item.name for item in folder.iterdir())
            record = json.loads(before)
            after = path.read_text(encoding="utf-8")
            names_after = sorted(item.name for item in folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names_after, names_before)
        self.assertEqual(names_after, ["edb-terms.json"])
        self.assertIn("prior written permission of EDB", record["reproduction_sentence"])
        self.assertIs(record["permits_financial_use"], False)
        self.assertNotIn("trade", record)
        self.assertFalse((folder / "trade.json").exists())

    def test_header_function_still_rejects_an_index_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaises(ValueError):
                record_series_header(folder, citation_url=EDB_MANUFACTURING_URL, value=100)
            self.assertEqual(list(folder.iterdir()), [])

    def test_an_index_value_or_another_page_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "edb-terms.json"
            with self.assertRaises(ValueError):
                record_terms_sentence(path, EDB_MANUFACTURING_URL, value=100)
            with self.assertRaises(ValueError):
                record_terms_sentence(path, EDB_MANUFACTURING_URL, label="trade")
            with self.assertRaises(ValueError):
                record_terms_sentence(path, EDB_MANUFACTURING_URL, label="index value")
            with self.assertRaises(ValueError):
                record_terms_sentence(path, TERMS_URL)
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
