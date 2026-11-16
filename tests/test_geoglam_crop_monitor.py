import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.geoglam_crop_monitor import CITATION_URL, record_crop_monitor_header

ROOT = Path(__file__).resolve().parents[1]
URL = CITATION_URL


class GeoglamCropMonitorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_the_printed_header_without_a_figure(self):
        saved = record_crop_monitor_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "GEOGLAM Crop Monitor")
        self.assertEqual(header["product"], "Crop Monitor for AMIS condition classes")
        self.assertEqual(
            header["period"],
            "eleven reports a year, first Thursday of the month, "
            "every month except January",
        )
        self.assertEqual(
            header["unit"],
            "condition class; the opened rules name exceptional, favourable, "
            "watch, poor, out-of-season, and no data",
        )
        self.assertEqual(
            header["administrative_area"],
            "main growing areas, national and subnational units",
        )
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "assessment")
        self.assertFalse(header["permits_financial_use"])
        for key in ("value", "class", "percent", "tonne", "yield", "place"):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "settlement",
            "yield",
            "trade",
            "tonne",
            "observation",
            "completed harvest",
            "percent",
            "%",
        ):
            self.assertNotIn(word, text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_crop_monitor_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "settlement",
            "yield",
            "trade",
            "tonne",
            "observation",
            "completed harvest",
            "Settlement",
            "YIELD",
            "Tonne",
            "Observation",
            "Completed Harvest",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_crop_monitor_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_crop_monitor(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("geoglam_crop_monitor", text)
            self.assertNotIn("crop-monitor-for-amis", text)
