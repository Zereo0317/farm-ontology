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

    def test_stores_the_printed_header_without_a_figure(self):
        saved = record_afcd_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(
            header["publisher"],
            "Agriculture, Fisheries and Conservation Department, "
            "and the Census and Statistics Department",
        )
        self.assertEqual(
            header["product"],
            "local agricultural production and fresh-food consumption",
        )
        self.assertEqual(
            header["period"],
            "2025; the wholesale consumption table includes 2023–2025",
        )
        self.assertEqual(
            header["unit"],
            "not printed as one unit; the opened pages name vegetables, flowers, "
            "fruit, pigs, poultry, fish, eggs, and cattle",
        )
        self.assertEqual(
            header["administrative_area"],
            "Hong Kong, the territory and named wholesale markets",
        )
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "estimate")
        self.assertFalse(header["permits_financial_use"])
        for key in (
            "value",
            "price",
            "production",
            "yield",
            "throughput",
            "farmed_area",
            "soybean",
        ):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "settlement",
            "yield",
            "trade",
            "soybean",
            "completed harvest",
            "throughput",
        ):
            self.assertNotIn(word, text)
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
        self.assertFalse(record["permits_financial_use"])
        self.assertNotIn("trade", record)
        self.assertNotIn("trade", text)
        self.assertNotIn("value", record)
        self.assertNotIn("series", record)
        self.assertNotEqual(record["administrative_area"].strip().lower(), "farm")
        self.assertEqual(CLASS_C_POLICY, "closed")

    def test_field_save_does_not_ingest_the_afcd_estimate(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("hong_kong_afcd", text)
            self.assertNotIn("agr_hk.html", text)
