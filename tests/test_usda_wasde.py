import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.usda_wasde import USDA_WASDE_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = USDA_WASDE_URL


class UsdaWasdeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_quantity(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(
            header["publisher"],
            "World Agricultural Outlook Board, U.S. Department of Agriculture",
        )
        self.assertEqual(
            header["product"],
            "World Agricultural Supply and Demand Estimates",
        )
        self.assertEqual(
            header["period"],
            "monthly, released at 12:00 p.m. Eastern; the page lists the 2026 and "
            "2027 dates; the November 2026 report was linked from the page; "
            "the first archived edition was not established",
        )
        self.assertEqual(
            header["unit"],
            "annual supply-and-use forecasts for U.S. and world wheat, rice, coarse "
            "grains, oilseeds, and cotton, plus U.S. sugar, meat, poultry, eggs, and "
            "milk, and Mexico's sugar balance; no quantity is stored",
        )
        self.assertEqual(
            header["administrative_area"],
            "the published U.S. and world tables; not a farm",
        )
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "forecast")
        self.assertFalse(header["permits_financial_use"])
        for key in ("value", "quantity", "score", "balance", "observation"):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "settlement",
            "yield",
            "trade",
            "observation",
            "completed harvest",
            "public domain",
            "benchmark",
        ):
            self.assertNotIn(word, text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        with self.assertRaises(ValueError):
            record_series_header(self.folder, citation_url="https://example.com/wasde.pdf")
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "settlement",
            "yield",
            "trade",
            "observation",
            "completed harvest",
            "public domain",
            "benchmark",
            "Settlement",
            "YIELD",
            "Observation",
            "Completed Harvest",
            "Public Domain",
            "Benchmark",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_wasde(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("usda_wasde", text)
            self.assertNotIn("commodity-markets/wasde", text)
