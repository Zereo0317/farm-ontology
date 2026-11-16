import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.census_m3 import CENSUS_M3_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = CENSUS_M3_URL


class CensusM3Tests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_dollar_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "U.S. Census Bureau")
        self.assertEqual(
            header["product"],
            "Manufacturers' Shipments, Inventories, and Orders",
        )
        self.assertEqual(
            header["period"],
            "monthly; the dataset list showed M3-mf.zip last updated 3 November 2026; "
            "the public time-series view of total manufacturing shipments displays "
            "years beginning in 1992; every current-month estimate is preliminary "
            "and is superseded later",
        )
        self.assertEqual(
            header["unit"],
            "monthly value of shipments, inventories, new orders, and unfilled orders; "
            "no dollar figure is stored",
        )
        self.assertEqual(header["administrative_area"], "United States manufacturing")
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "survey")
        self.assertFalse(header["permits_financial_use"])
        for key in ("value", "dollars", "dollar_figure", "price", "orders"):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "settlement",
            "yield",
            "trade",
            "forecast",
            "public domain",
            "observation",
            "completed harvest",
        ):
            self.assertNotIn(word, text)
        self.assertIn("preliminary", text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        with self.assertRaises(ValueError):
            record_series_header(self.folder, citation_url="https://example.com/M3-mf.zip")
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "settlement",
            "yield",
            "trade",
            "forecast",
            "public domain",
            "observation",
            "completed harvest",
            "futures settlement",
            "Settlement",
            "YIELD",
            "Forecast",
            "Public Domain",
            "Observation",
            "Completed Harvest",
            "Futures Settlement",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_m3_survey(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("census_m3", text)
            self.assertNotIn("manufacturing/m3", text)
