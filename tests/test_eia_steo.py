import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.eia_steo import EIA_STEO_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = EIA_STEO_URL


class EiaSteoTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_price_or_quantity(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "U.S. Energy Information Administration")
        self.assertEqual(header["product"], "Short-Term Energy Outlook")
        self.assertEqual(
            header["period"],
            "monthly; the page opened was the 10 November 2026 release, which says "
            "the forecast was completed on 5 November 2026 and does not specifically "
            "account for market events after that day; the next release date printed "
            "on that page is 8 December 2026; a complete archive of past forecast "
            "vintages was not inventoried",
        )
        self.assertEqual(
            header["unit"],
            "a monthly outlook for energy supply, inventories, and prices, including "
            "petroleum; no price and no quantity is stored",
        )
        self.assertEqual(
            header["administrative_area"],
            "the outlook's published coverage; this record is not a stored world balance",
        )
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "forecast")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(
            header["copyright_statement"],
            "EIA states that U.S. government publications on its site are in the "
            "public domain and are not subject to copyright, and asks for a dated "
            "acknowledgment. Third-party items on the site can still be protected.",
        )
        for key in ("value", "price", "quantity", "score", "vintage", "observation"):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "settlement",
            "yield",
            "trade",
            "observation",
            "completed harvest",
            "benchmark",
            "completed supply",
        ):
            self.assertNotIn(word, text)
        self.assertIn("public domain", text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        with self.assertRaises(ValueError):
            record_series_header(self.folder, citation_url="https://example.com/steo.xlsx")
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "settlement",
            "yield",
            "trade",
            "observation",
            "completed harvest",
            "benchmark",
            "Settlement",
            "YIELD",
            "Observation",
            "Completed Harvest",
            "Benchmark",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_steo(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("eia_steo", text)
            self.assertNotIn("outlooks/steo", text)
