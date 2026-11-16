import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.pink_sheet import PINK_SHEET_MONTHLY_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = PINK_SHEET_MONTHLY_URL


class PinkSheetTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_fetch_stores_one_series_header_without_a_price(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "World Bank")
        self.assertEqual(header["product_version"], "CMO Historical Data Monthly")
        self.assertEqual(header["series"], "Crude oil, average")
        self.assertEqual(header["period"], "1960 to present")
        self.assertEqual(header["unit"], "($/bbl)")
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "observation")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(header["class_c_policy"], "closed")
        self.assertNotIn("value", header)
        self.assertNotIn("price", header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        self.assertNotIn("settlement", text)
        self.assertNotIn("yield", text)
        self.assertNotIn("trade", text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        with patch("farm_ontology.pink_sheet.urllib.request.urlopen", side_effect=AssertionError("fetched")):
            for citation in (None, ""):
                with self.assertRaises(ValueError):
                    record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_settlement_yield_or_trade_label_writes_nothing(self):
        with patch("farm_ontology.pink_sheet.urllib.request.urlopen", side_effect=AssertionError("fetched")):
            for label in ("settlement", "yield", "trade", "Settlement", "YIELD"):
                with self.assertRaises(ValueError):
                    record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_pink_sheet(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("pink_sheet", text)
            self.assertNotIn("CMO-Historical", text)
