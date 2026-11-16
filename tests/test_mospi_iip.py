import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.mospi_iip import MOSPI_IIP_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = MOSPI_IIP_URL


class MospiIipTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_an_index_number(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(
            header["publisher"],
            "Ministry of Statistics and Programme Implementation",
        )
        self.assertEqual(header["product"], "Index of Industrial Production")
        self.assertEqual(header["period"], "September 2026")
        self.assertEqual(header["unit"], "the field was not opened")
        self.assertEqual(header["administrative_area"], "all India")
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "index")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(
            header["copyright_notice"],
            "© 2025 Ministry of Statistics & Programme Implementation",
        )
        self.assertEqual(
            header["source_line"],
            "Index of Industrial Production data is available on the e-Sankhyiki "
            "portal developed by the Ministry of Statistics and Programme Implementation.",
        )
        self.assertEqual(
            header["release_title"],
            "Press Release on Quick Estimates of all India Index of Industrial "
            "Production (IIP) base year 2022-23 for September 2026",
        )
        self.assertEqual(
            header["product_note"],
            "The Index of Industrial Production is a quantitative index.",
        )
        self.assertIn("2022-23", header["release_title"])
        self.assertNotIn("2022", header["unit"])
        self.assertNotIn("reference_period", header)
        for key in (
            "value",
            "price",
            "index_level",
            "index_value",
            "index_number",
            "quantity",
            "forecast",
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
            "reference_period",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "mospi_iip.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("reference_period 2026", flat)
        self.assertIn("Period stays September 2026", flat)
        self.assertIn("not copied into unit", flat)
        self.assertIn("not a quantity of goods", flat)
        self.assertIn("bulk history file was not opened", flat)
        self.assertIn("not a trading right", flat)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        with self.assertRaises(ValueError):
            record_series_header(self.folder, citation_url="https://example.com/iip.html")
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
            "index number",
            "2022-23",
            "145.2",
            "2026",
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

    def test_filled_unit_and_index_numbers_write_nothing(self):
        attempts = (
            {"unit": "the field was not opened"},
            {"unit": "2022-23"},
            {"unit": "base year 2022-23"},
            {"value": 145.2},
            {"value": "100"},
            {"period": "2026"},
            {"period": "2022-23"},
            {"administrative_area": "Maharashtra"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_mospi(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("mospi_iip", text)
            self.assertNotIn("54-index-of-industrial-production", text)
