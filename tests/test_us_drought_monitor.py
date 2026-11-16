import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.us_drought_monitor import US_DROUGHT_MONITOR_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = US_DROUGHT_MONITOR_URL


class UsDroughtMonitorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_percent_or_index_value(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(
            header["publisher"],
            "National Drought Mitigation Center at the University of Nebraska-Lincoln, "
            "with USDA, NOAA, and NASA",
        )
        self.assertEqual(header["product"], "U.S. Drought Monitor")
        self.assertEqual(
            header["period"],
            "weekly; the map page says the data cutoff is Tuesday at 7:00 a.m. Eastern "
            "and the map is released Thursday at 8:30 a.m. Eastern; the map that was "
            "opened was released 12 November 2026 for data valid 10 November 2026; "
            "Drought.gov says the Drought Monitor files in its historical tool run "
            "from 2000 to the present",
        )
        self.assertEqual(
            header["unit"],
            "an expert classification of drought intensity; percent of area and a "
            "drought-severity index are named on the page; no percent and no index "
            "value is stored",
        )
        self.assertEqual(
            header["administrative_area"],
            "the United States, Puerto Rico, the Pacific islands, and the Virgin Islands",
        )
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "classification")
        self.assertFalse(header["permits_financial_use"])
        for key in ("value", "percent", "index_value", "palmer", "spi"):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "settlement",
            "yield",
            "trade",
            "observation",
            "forecast",
            "public domain",
            "completed harvest",
            "Palmer",
            "1895",
            "Standardized Precipitation",
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
            record_series_header(self.folder, citation_url="https://example.com/drought.zip")
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "settlement",
            "yield",
            "trade",
            "observation",
            "forecast",
            "public domain",
            "completed harvest",
            "Settlement",
            "YIELD",
            "Observation",
            "Forecast",
            "Public Domain",
            "Completed Harvest",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_drought_monitor(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("us_drought_monitor", text)
            self.assertNotIn("droughtmonitor.unl.edu", text)
