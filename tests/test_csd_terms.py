import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology.csd_industrial import CSD_INDUSTRIAL_URL, record_series_header
from farm_ontology.csd_terms import TERMS_LINK, record_terms_link
from farm_ontology.policy import CLASS_C_POLICY


class CsdTermsTests(unittest.TestCase):
    def test_stores_that_the_subject_page_prints_no_terms_link(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "csd-terms.json"
            record_terms_link(path, CSD_INDUSTRIAL_URL)
            stored = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            stored,
            {
                "citation_url": CSD_INDUSTRIAL_URL,
                "terms_link": "the subject page prints no terms link",
                "permits_financial_use": False,
            },
        )
        self.assertEqual(stored["terms_link"], TERMS_LINK)
        self.assertIs(stored["permits_financial_use"], False)
        self.assertEqual(CLASS_C_POLICY, "closed")
        text = json.dumps(stored, ensure_ascii=False)
        self.assertNotIn("2015", text)
        self.assertNotIn("100", text)
        self.assertNotIn("610", text)
        self.assertNotIn("copyright", text)
        self.assertNotIn("trade", stored)
        self.assertNotIn("value", stored)
        self.assertNotIn("quantity", stored)

    def test_reading_the_stored_record_writes_no_trade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "csd-terms.json"
            record_terms_link(path, CSD_INDUSTRIAL_URL)
            before = path.read_text(encoding="utf-8")
            names_before = sorted(item.name for item in folder.iterdir())
            record = json.loads(before)
            after = path.read_text(encoding="utf-8")
            names_after = sorted(item.name for item in folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names_after, names_before)
        self.assertEqual(names_after, ["csd-terms.json"])
        self.assertEqual(record["terms_link"], "the subject page prints no terms link")
        self.assertIs(record["permits_financial_use"], False)
        self.assertNotIn("trade", record)
        self.assertFalse((folder / "trade.json").exists())

    def test_header_still_rejects_the_parenthetical_figure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaises(ValueError):
                record_series_header(
                    folder,
                    citation_url=CSD_INDUSTRIAL_URL,
                    value="(Year 2015=100)",
                )
            self.assertEqual(list(folder.iterdir()), [])

    def test_a_figure_or_another_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "csd-terms.json"
            with self.assertRaises(ValueError):
                record_terms_link(path, CSD_INDUSTRIAL_URL, value=100)
            with self.assertRaises(ValueError):
                record_terms_link(path, CSD_INDUSTRIAL_URL, label="trade")
            with self.assertRaises(ValueError):
                record_terms_link(path, CSD_INDUSTRIAL_URL, label="quantity of goods")
            with self.assertRaises(ValueError):
                record_terms_link(path, "https://www.censtatd.gov.hk/en/web_table.html?id=610-65001")
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
