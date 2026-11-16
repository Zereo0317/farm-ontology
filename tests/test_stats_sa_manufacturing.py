import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.stats_sa_manufacturing import (
    STATS_SA_MANUFACTURING_URL,
    record_series_header,
)

ROOT = Path(__file__).resolve().parents[1]
URL = STATS_SA_MANUFACTURING_URL


class StatsSaManufacturingTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_an_index_or_sales_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Statistics South Africa (Stats SA)")
        self.assertEqual(header["product"], "Manufacturing: Production and sales")
        self.assertEqual(header["period"], "September 2026")
        self.assertEqual(header["unit"], "(Base: 2019=100) and (R million)")
        self.assertEqual(header["administrative_area"], "South Africa")
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "report")
        self.assertFalse(header["permits_financial_use"])
        self.assertIn("Stats SA has copyright on this publication.", header["copyright_notice"])
        self.assertIn("utilise", header["copyright_notice"])
        self.assertNotIn("financial", header["copyright_notice"])
        for key in (
            "value",
            "price",
            "index_level",
            "index_value",
            "amount",
            "sales",
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
            "licence",
            "license",
            "13:00",
            "0001",
            "X44",
            "P3041.2",
            "404",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "stats_sa_manufacturing.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("P3041.2", source)
        self.assertIn("(Preliminary)", source)
        self.assertIn("embargoed until 10 November 2026", source)
        self.assertIn("13:00", source)
        self.assertIn("Private Bag X44, Pretoria, 0001", source)
        self.assertIn("404", source)
        self.assertIn("bulk history file was not opened", source)
        self.assertIn("separate licence name was not printed", source)
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
                citation_url="https://www.statssa.gov.za/publications/P30412/P30412October2026.pdf",
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
            "quantity of goods",
            "trading right",
            "100",
            "2019=100",
            "13:00",
            "0001",
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

    def test_stored_numbers_write_nothing(self):
        attempts = (
            {"value": 100},
            {"value": "2019=100"},
            {"period": "13:00"},
            {"unit": "1234"},
            {"administrative_area": "0001"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_stats_sa(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("stats_sa_manufacturing", text)
            self.assertNotIn("P30412September2026", text)
