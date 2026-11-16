import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.world_bank_pink_sheet import (
    WORLD_BANK_PINK_SHEET_URL,
    record_series_header,
)

ROOT = Path(__file__).resolve().parents[1]
URL = WORLD_BANK_PINK_SHEET_URL


class WorldBankPinkSheetTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_price_or_index_level(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "World Bank, Prospects Group")
        self.assertEqual(header["product"], "Pink Sheet")
        self.assertEqual(
            header["period"],
            "monthly file; the commodity-markets page says the next update after the "
            "3 November 2026 publication is 2 December 2026; the monthly workbook's "
            "own title line says nominal U.S. dollars, 1960 to present, and the period "
            "column runs 1960M01 through 2026M10 (802 months); the annual workbook, "
            "updated 2 September 2026, says annual prices from 1960 to present in "
            "nominal and real dollars; the monthly and annual workbooks were updated "
            "on different days",
        )
        self.assertEqual(
            header["unit"],
            "monthly nominal prices and nominal indexes, and annual nominal and real "
            "prices and indexes, for energy, agriculture, food, beverages, raw "
            "materials, fertilizers, and metals; the monthly price sheet has 71 series; "
            "indexes on the monthly file are 2010=100; monthly series are available "
            "only in nominal dollars; real means constant prices deflated by the "
            "Manufacturers Unit Value index; no price and no index level is stored",
        )
        self.assertEqual(
            header["administrative_area"],
            "the published commodity series, not a country balance; the Manufacturers "
            "Unit Value index is the U.S.-dollar unit-value index of manufactures "
            "exported from fifteen countries listed in the workbook: Brazil, Canada, "
            "China, Germany, France, India, Italy, Japan, Mexico, the Republic of "
            "Korea, South Africa, Spain, the United Kingdom, and the United States, "
            "plus one name spelled Pailand in the file",
        )
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "compilation")
        self.assertFalse(header["permits_financial_use"])
        self.assertIn("CC BY 4.0", header["copyright_statement"])
        self.assertIn("23 March 2018", header["copyright_statement"])
        self.assertIn("Pailand", header["administrative_area"])
        for key in ("value", "price", "index_level", "forecast", "observation"):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "settlement",
            "yield",
            "trade",
            "forecast",
            "observation",
            "completed harvest",
            "public domain",
            "benchmark",
        ):
            self.assertNotIn(word, text)
        self.assertIn("CC BY 4.0", text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        with self.assertRaises(ValueError):
            record_series_header(self.folder, citation_url="https://example.com/pink.xlsx")
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "settlement",
            "yield",
            "trade",
            "forecast",
            "observation",
            "completed harvest",
            "public domain",
            "benchmark",
            "Settlement",
            "YIELD",
            "Forecast",
            "Observation",
            "Completed Harvest",
            "Public Domain",
            "Benchmark",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_pink_sheet(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("world_bank_pink_sheet", text)
            self.assertNotIn("research/commodity-markets", text)
