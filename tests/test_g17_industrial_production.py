import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.g17_industrial_production import (
    G17_INDUSTRIAL_PRODUCTION_URL,
    record_series_header,
)

ROOT = Path(__file__).resolve().parents[1]
URL = G17_INDUSTRIAL_PRODUCTION_URL


class G17IndustrialProductionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_an_index_level(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Board of Governors of the Federal Reserve System")
        self.assertEqual(header["product_version"], "G.17 Industrial Production and Capacity Utilization")
        self.assertEqual(header["series"], "Industrial production")
        self.assertEqual(header["period"], "Monthly, release dated 16 October 2026, covering September")
        self.assertEqual(header["unit"], "index")
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "observation")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(header["class_c_policy"], "closed")
        self.assertNotIn("value", header)
        self.assertNotIn("price", header)
        self.assertNotIn("level", header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        self.assertNotIn("settlement", text)
        self.assertNotIn("yield", text)
        self.assertNotIn("trade", text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, ""):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_settlement_yield_or_trade_label_writes_nothing(self):
        for label in ("settlement", "yield", "trade", "Settlement", "YIELD"):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        with self.assertRaises(ValueError):
            record_series_header(self.folder, citation_url="https://example.invalid/g17")
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_g17_series(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("g17_industrial_production", text)
            self.assertNotIn("federalreserve.gov/releases/g17", text)


if __name__ == "__main__":
    unittest.main()
