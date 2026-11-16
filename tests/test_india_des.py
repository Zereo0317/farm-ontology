import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.india_des import CITATION_URL, record_table_header

ROOT = Path(__file__).resolve().parents[1]
URL = CITATION_URL


class IndiaDesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_printed_header_without_a_figure(self):
        saved = record_table_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(
            header["publisher"],
            "Directorate of Economics and Statistics, "
            "Department of Agriculture and Farmers Welfare",
        )
        self.assertEqual(header["product"], "advance and final estimates")
        self.assertEqual(header["period"], "agricultural year July–June")
        self.assertEqual(header["unit"], "area")
        self.assertEqual(header["administrative_area"], "state")
        self.assertNotEqual(header["administrative_area"], "farm")
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "observation")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(header["class_c_policy"], "closed")
        for absent in (
            "value",
            "price",
            "production",
            "yield",
            "trade",
            "settlement",
        ):
            self.assertNotIn(absent, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        stored = json.loads(text)
        self.assertEqual(stored["administrative_area"], "state")
        self.assertNotIn("settlement", text)
        self.assertNotIn("yield", text)
        self.assertNotIn("trade", text)
        self.assertNotIn("price", text)
        self.assertNotIn("production", text)
        self.assertNotIn("farm", text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_table_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_settlement_yield_or_trade_label_writes_nothing(self):
        for label in ("settlement", "yield", "trade", "Settlement", "YIELD", " Trade "):
            with self.assertRaises(ValueError):
                record_table_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_des_table(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("india_des", text)
            self.assertNotIn("desagri.gov.in/statistics-type/advance-estimates", text)
