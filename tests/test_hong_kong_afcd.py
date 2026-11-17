import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.hong_kong_afcd import (
    CITATION_URL,
    read_stored_record,
    record_afcd_header,
)
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
URL = CITATION_URL


class HongKongAfcdTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_only_the_vegetable_land_figure(self):
        saved = record_afcd_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["series"], "land used for vegetable")
        self.assertEqual(header["period"], "the end of 2025")
        self.assertEqual(header["value"], "342 ha")
        self.assertEqual(header["unit"], "ha")
        self.assertEqual(
            header["publisher"],
            "Agriculture, Fisheries and Conservation Department, "
            "and the Census and Statistics Department",
        )
        self.assertEqual(
            header["administrative_area"],
            "Hong Kong, the territory and named wholesale markets",
        )
        self.assertNotEqual(header["administrative_area"].strip().lower(), "farm")
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "estimate")
        self.assertFalse(header["permits_financial_use"])
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for absent in (
            "116",
            "250",
            "4 ha",
            "flower",
            "field crop",
            "orchard",
            "861",
            "354",
            "198",
            "309",
            "42 tonnes",
            "11,500",
            "167",
            "settlement",
            "yield",
            "trade",
            "soybean",
            "completed harvest",
            "throughput",
        ):
            self.assertNotIn(absent, text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_afcd_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "settlement",
            "yield",
            "trade",
            "soybean crop",
            "completed harvest",
            "Settlement",
            "YIELD",
            "Soybean Crop",
            "Completed Harvest",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_afcd_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_reading_the_stored_record_writes_no_trade(self):
        saved = record_afcd_header(self.folder, citation_url=URL)
        path = self.folder / saved["file"]
        names_before = sorted(item.name for item in self.folder.iterdir())
        record = read_stored_record(path)
        names_after = sorted(item.name for item in self.folder.iterdir())
        text = path.read_text(encoding="utf-8")
        self.assertEqual(names_after, names_before)
        self.assertEqual(names_after, ["local-agricultural-production.json"])
        self.assertEqual(record["series"], "land used for vegetable")
        self.assertEqual(record["period"], "the end of 2025")
        self.assertEqual(record["value"], "342 ha")
        self.assertFalse(record["permits_financial_use"])
        self.assertNotIn("trade", record)
        self.assertNotIn("trade", text)
        self.assertNotIn("116", text)
        self.assertNotIn("250", text)
        self.assertNotIn("yield", text)
        self.assertNotEqual(record["administrative_area"].strip().lower(), "farm")
        self.assertEqual(CLASS_C_POLICY, "closed")

    def test_field_save_does_not_ingest_the_afcd_estimate(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("hong_kong_afcd", text)
            self.assertNotIn("agr_hk.html", text)
