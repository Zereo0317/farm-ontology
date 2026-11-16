import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.indonesia_bps import CITATION_URL, record_table_header

ROOT = Path(__file__).resolve().parents[1]
URL = CITATION_URL


class IndonesiaBpsTests(unittest.TestCase):
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
            "Badan Pusat Statistik (BPS-Statistics Indonesia)",
        )
        self.assertEqual(header["product"], "food crops")
        self.assertEqual(header["period"], "2020 through 2024")
        self.assertEqual(header["unit"], "annual")
        self.assertEqual(header["administrative_area"], "national")
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
        self.assertEqual(stored["administrative_area"], "national")
        self.assertNotIn("settlement", text)
        self.assertNotIn("yield", text)
        self.assertNotIn("trade", text)
        self.assertNotIn("price", text)
        self.assertNotIn("farm", text)
        for field in ("publisher", "product", "period", "unit", "administrative_area"):
            self.assertNotIn("production", header[field])
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

    def test_field_save_does_not_ingest_the_bps_table(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("indonesia_bps", text)
            self.assertNotIn("bps.go.id/en/statistics-table/2/MjM0NSMy", text)
