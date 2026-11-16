import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.bps_manufacturing_index import (
    BPS_MANUFACTURING_INDEX_URL,
    record_series_header,
)

ROOT = Path(__file__).resolve().parents[1]
URL = BPS_MANUFACTURING_INDEX_URL
NOT_OPENED = "the field was not opened"


class BpsManufacturingIndexTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_an_index_value(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Badan Pusat Statistik")
        self.assertEqual(
            header["product"],
            "Indeks Produksi Bulanan Industri Besar dan Sedang Menurut KBLI 2 Digit "
            "[KBLI 2020] (2010=100)",
        )
        self.assertEqual(header["period"], NOT_OPENED)
        self.assertEqual(header["unit"], NOT_OPENED)
        self.assertEqual(header["administrative_area"], NOT_OPENED)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "index")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(
            header["copyright_notice"],
            "Hak Cipta © 2023 Badan Pusat Statistik",
        )
        self.assertNotIn("license", header)
        for field in ("period", "unit", "administrative_area"):
            self.assertNotIn("Bulanan", header[field])
            self.assertNotIn("bulanan", header[field])
            self.assertNotIn("2010=100", header[field])
        self.assertIn("Bulanan", header["product"])
        self.assertIn("(2010=100)", header["product"])
        for key in ("value", "price", "index_level", "index_value", "quantity"):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        self.assertEqual(text.count("2010=100"), 1)
        self.assertEqual(text.count("Bulanan"), 1)
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
            "province",
            "national",
            "nasional",
            "provinsi",
            "license",
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
            record_series_header(self.folder, citation_url="https://example.com/bps.html")
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
            "province",
            "national",
            "start month",
            "2010=100",
            "Bulanan",
            "quantity of goods",
            "trading right",
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

    def test_filled_fields_write_nothing(self):
        attempts = (
            {"period": "monthly"},
            {"unit": "2010=100"},
            {"administrative_area": "Indonesia"},
            {"period": NOT_OPENED},
            {"unit": NOT_OPENED},
            {"administrative_area": NOT_OPENED},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_bps_index(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("bps_manufacturing_index", text)
            self.assertNotIn("MjA3NyMy", text)
