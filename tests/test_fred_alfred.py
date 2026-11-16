import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.fred_alfred import FRED_ALFRED_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = FRED_ALFRED_URL


class FredAlfredTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_value(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(
            header["publisher"],
            "Federal Reserve Bank of St. Louis, reprinting other publishers",
        )
        self.assertEqual(header["product"], "FRED and ALFRED")
        self.assertEqual(
            header["period"],
            "follows the source series; ALFRED's help page says many sources do not "
            "keep their own previously published estimates, and that some vintages "
            "are then checked against third-party data services; coverage is "
            "whatever vintages ALFRED holds, not every series",
        )
        self.assertEqual(
            header["unit"],
            "not a new measurement; FRED redistributes many of the government series "
            "already recorded; ALFRED stores vintage versions so a reader can see a "
            "series as it was published on a past date; no value is stored",
        )
        self.assertEqual(
            header["administrative_area"],
            "the reprinted series; this record is not a new geographic measurement",
        )
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["citation_url"], "https://fred.stlouisfed.org/legal/terms")
        self.assertEqual(header["kind"], "reprint")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(
            set(header),
            {
                "publisher",
                "product",
                "period",
                "unit",
                "administrative_area",
                "citation_url",
                "kind",
                "permits_financial_use",
            },
        )
        self.assertIn("not a new measurement", header["unit"])
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
        self.assertNotIn("https://alfred.stlouisfed.org/help", text)
        self.assertNotIn("docs/api/terms_of_use.html", text)
        source = (ROOT / "farm_ontology" / "fred_alfred.py").read_text(encoding="utf-8")
        self.assertIn("https://alfred.stlouisfed.org/help", source)
        self.assertIn("https://fred.stlouisfed.org/docs/api/terms_of_use.html", source)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        with self.assertRaises(ValueError):
            record_series_header(
                self.folder,
                citation_url="https://alfred.stlouisfed.org/help",
            )
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
            "new measurement",
            "Settlement",
            "YIELD",
            "Trade",
            "Forecast",
            "Observation",
            "Completed Harvest",
            "Public Domain",
            "Benchmark",
            "New Measurement",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_fred(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("fred_alfred", text)
            self.assertNotIn("fred.stlouisfed.org", text)
