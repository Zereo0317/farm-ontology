import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.eia_weekly import EIA_WEEKLY_CRUDE_STOCKS_URL, record_series_header
from farm_ontology.testing import online_gate

ROOT = Path(__file__).resolve().parents[1]
URL = EIA_WEEKLY_CRUDE_STOCKS_URL


class EiaWeeklyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    @online_gate()
    def test_fetch_stores_one_series_header_without_a_stock_level(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "U.S. Energy Information Administration")
        self.assertEqual(header["product_version"], "Weekly Petroleum Status Report")
        self.assertEqual(header["series"], "Weekly U.S. Ending Stocks excluding SPR of Crude Oil")
        self.assertEqual(header["period"], "Weekly")
        self.assertEqual(header["unit"], "Thousand Barrels")
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "observation")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(header["class_c_policy"], "closed")
        self.assertNotIn("value", header)
        self.assertNotIn("price", header)
        self.assertNotIn("balance", header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        self.assertNotIn("settlement", text)
        self.assertNotIn("yield", text)
        self.assertNotIn("trade", text)
        self.assertNotRegex(text, r"\d{3},\d{3}")
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        with patch("farm_ontology.eia_weekly.urllib.request.urlopen", side_effect=AssertionError("fetched")):
            for citation in (None, ""):
                with self.assertRaises(ValueError):
                    record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_settlement_yield_or_trade_label_writes_nothing(self):
        with patch("farm_ontology.eia_weekly.urllib.request.urlopen", side_effect=AssertionError("fetched")):
            for label in ("settlement", "yield", "trade", "Settlement", "YIELD"):
                with self.assertRaises(ValueError):
                    record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_weekly_series(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("eia_weekly", text)
            self.assertNotIn("WCESTUS1", text)
