import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.noaa_oni import NOAA_ONI_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = NOAA_ONI_URL


class NoaaOniTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_an_anomaly(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "NOAA Climate Prediction Center")
        self.assertEqual(header["product"], "Oceanic Niño Index")
        self.assertEqual(
            header["period"],
            "seasonal; the ASCII file that was opened begins with DJF 1950; "
            "the episode page is titled 1950 to present; the page says the index "
            "is updated by the 5th of each month; the latest values can change for "
            "up to two months after the first real-time posting",
        )
        self.assertEqual(
            header["unit"],
            "a three-month running mean of ERSSTv5 sea-surface temperature anomalies "
            "in the Niño 3.4 region, in degrees Celsius; no anomaly value is stored",
        )
        self.assertEqual(
            header["administrative_area"],
            "the Niño 3.4 region; not a country and not a crop area",
        )
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "index")
        self.assertFalse(header["permits_financial_use"])
        for key in ("value", "anomaly", "roni", "celsius"):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "settlement",
            "yield",
            "trade",
            "oil balance",
            "manufacturing index",
            "observation",
            "forecast",
            "public domain",
            "completed harvest",
            "RONI",
            "official monitoring",
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
            record_series_header(self.folder, citation_url="https://example.com/oni.ascii")
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "settlement",
            "yield",
            "trade",
            "oil balance",
            "manufacturing index",
            "observation",
            "forecast",
            "public domain",
            "completed harvest",
            "Settlement",
            "YIELD",
            "Oil Balance",
            "Manufacturing Index",
            "Observation",
            "Forecast",
            "Public Domain",
            "Completed Harvest",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_oni(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("noaa_oni", text)
            self.assertNotIn("enso/oni/v5", text)
