import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.published_forecast import PSD_CITATION_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = PSD_CITATION_URL


class PublishedForecastTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_forecast_header_without_a_number(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(
            header["publisher"],
            "United States Department of Agriculture, Foreign Agricultural Service",
        )
        self.assertEqual(header["product_version"], "Production, Supply and Distribution (PSD)")
        self.assertEqual(header["series"], "open marketing year")
        self.assertEqual(header["period"], "Current and coming marketing years")
        self.assertEqual(header["unit"], "Country")
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "forecast")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(header["class_c_policy"], "closed")
        self.assertNotIn("value", header)
        self.assertNotIn("price", header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        self.assertNotIn("harvest", text)
        self.assertNotIn("settlement", text)
        self.assertNotIn("yield", text)
        self.assertNotIn("trade", text)
        self.assertNotRegex(text, r"\d")
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_harvest_yield_settlement_or_trade_label_writes_nothing(self):
        for label in ("harvest", "yield", "settlement", "trade", "Harvest", "YIELD"):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_forecast(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("published_forecast", text)
            self.assertNotIn("psdonline", text)
