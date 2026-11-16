import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.edb_manufacturing import EDB_MANUFACTURING_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = EDB_MANUFACTURING_URL
SINGSTAT_URL = (
    "https://www.singstat.gov.sg/find-data/explore-data-themes/industry/"
    "manufacturing/latest-news-data"
)


class EdbManufacturingTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_an_index_value(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(
            header["publisher"],
            "Singapore Economic Development Board (EDB)",
        )
        self.assertEqual(
            header["product"],
            "Monthly manufacturing performance (September 2026)",
        )
        self.assertEqual(header["period"], "September 2026")
        self.assertEqual(header["unit"], "the field was not opened")
        self.assertEqual(header["administrative_area"], "Singapore")
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "report")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(
            header["copyright_notice"],
            "© 2026 Singapore Economic Development Board",
        )
        self.assertEqual(header["dateline"], "26 Oct 2026")
        self.assertEqual(header["last_updated"], "16 Nov 2026")
        for key in (
            "value",
            "price",
            "index_level",
            "index_value",
            "quantity",
            "licence",
            "license",
        ):
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
            "trading right",
            "quantity of goods",
            "singstat.gov.sg",
            "179101",
            "Singapore EDB",
            "licence",
            "license",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "edb_manufacturing.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(SINGSTAT_URL, source.replace("\n", ""))
        self.assertIn("monthly index of industrial production", source)
        self.assertIn("Singapore EDB", source)
        self.assertIn("Singapore 179101", source)
        self.assertIn("Terms of use page was not opened", source)
        self.assertIn("spreadsheet downloads", source)
        self.assertIn("bulk history file was not opened", source)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://www.singstat.gov.sg/find-data/explore-data-themes/industry/manufacturing/latest-news-data",
            "https://example.com/edb.html",
        ):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
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
            "quantity of goods",
            "trading right",
            "index value",
            "100",
            "2019=100",
            "26 Oct 2026",
            "Settlement",
            "YIELD",
            "Trade",
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

    def test_filled_unit_writes_nothing(self):
        attempts = (
            {"unit": "the field was not opened"},
            {"unit": "2019=100"},
            {"unit": "index"},
            {"value": 100},
            {"value": "50.0"},
            {"period": "100"},
            {"administrative_area": "179101"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_edb(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("edb_manufacturing", text)
            self.assertNotIn("monthly-manufacturing-performance", text)
