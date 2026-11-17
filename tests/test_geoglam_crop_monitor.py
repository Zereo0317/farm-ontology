import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.geoglam_crop_monitor import (
    CITATION_URL,
    record_crop_monitor_header,
    record_printed_class,
)
from farm_ontology.policy import CLASS_C_POLICY

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

    def test_reading_the_stored_record_writes_no_trade(self):
        saved = record_printed_class(self.folder, citation_url=URL)
        path = self.folder / saved["file"]
        before = path.read_text(encoding="utf-8")
        names_before = sorted(item.name for item in self.folder.iterdir())
        record = json.loads(before)
        after = path.read_text(encoding="utf-8")
        names_after = sorted(item.name for item in self.folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names_after, names_before)
        self.assertEqual(names_after, ["china-rice-condition.json"])
        self.assertEqual(record["crop"], "rice")
        self.assertEqual(record["place"], "China")
        self.assertEqual(record["month"], "October 28th, 2026")
        self.assertEqual(record["condition_class"], "favourable")
        self.assertEqual(record["citation_url"], URL)
        self.assertFalse(record["permits_financial_use"])
        self.assertEqual(record["class_c_policy"], "closed")
        self.assertEqual(record["class_c_policy"], CLASS_C_POLICY)
        self.assertNotIn("trade", record)
        self.assertNotIn("yield", record)
        self.assertNotIn("tonne", record)
        for word in ("trade", "yield", "tonne", "percent", "%"):
            self.assertNotIn(word, after)

    def test_class_without_the_citation_or_as_a_trade_writes_nothing(self):
        for citation in (
            None,
            "",
            "   ",
            "https://www.cropmonitor.org/s/AMIS_CropMonitor_202611-d7hb.pdf",
        ):
            with self.assertRaises(ValueError):
                record_printed_class(self.folder, citation_url=citation)
        for label in ("yield", "tonne", "tonnes", "trade", "YIELD", "Trade"):
            with self.assertRaises(ValueError):
                record_printed_class(self.folder, citation_url=URL, label=label)
        with self.assertRaises(ValueError):
            record_printed_class(self.folder, citation_url=URL, condition_class="poor")
        with self.assertRaises(ValueError):
            record_printed_class(self.folder, citation_url=URL, permits_financial_use=True)
        with self.assertRaises(ValueError):
            record_printed_class(self.folder, citation_url=URL, class_c_policy="open")
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_crop_monitor(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("geoglam_crop_monitor", text)
            self.assertNotIn("crop-monitor-for-amis", text)
