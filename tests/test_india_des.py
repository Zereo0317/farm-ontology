import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.header_schema import read_stored_header
from farm_ontology.india_des import CITATION_URL, record_table_header

ROOT = Path(__file__).resolve().parents[1]
URL = CITATION_URL


class IndiaDesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_the_rice_total_cell(self):
        saved = record_table_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["series"], "rice total")
        self.assertEqual(header["product"], "rice total")
        self.assertEqual(header["period"], "2025-26 third advance estimates")
        self.assertEqual(header["value"], "1540.24")
        self.assertEqual(header["unit"], "Production in Lakh Tonnes")
        self.assertEqual(header["administrative_area"], "not printed on the page")
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "observation")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(header["class_c_policy"], "closed")
        for absent in ("price", "yield", "trade", "settlement", "kharif", "rabi", "summer"):
            self.assertNotIn(absent, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        stored = json.loads(text)
        self.assertEqual(stored["value"], "1540.24")
        self.assertEqual(stored["administrative_area"], "not printed on the page")
        for absent in (
            "yield",
            "trade",
            "price",
            "kharif",
            "rabi",
            "summer",
            "1247.58",
            "181.07",
            "111.59",
            "India",
            "all India",
            "state",
            "farm",
            "1206.57",
            "wheat",
        ):
            self.assertNotIn(absent, text)
        self.assertEqual(
            sorted(item.name for item in self.folder.iterdir()),
            ["india-des-estimates.json", "india-des-wheat.json"],
        )

    def test_stores_the_wheat_rabi_cell(self):
        saved = record_table_header(self.folder, citation_url=URL)
        wheat = saved["wheat"]
        self.assertEqual(wheat["series"], "wheat")
        self.assertEqual(wheat["product"], "wheat")
        self.assertEqual(wheat["season"], "Rabi")
        self.assertEqual(wheat["period"], "2025-26 third advance estimates")
        self.assertEqual(wheat["value"], "1206.57")
        self.assertEqual(wheat["unit"], "Production in Lakh Tonnes")
        self.assertEqual(wheat["administrative_area"], "not printed on the page")
        self.assertEqual(wheat["citation_url"], URL)
        self.assertFalse(wheat["permits_financial_use"])
        self.assertEqual(wheat["class_c_policy"], "closed")
        self.assertNotIn("total", wheat)
        self.assertEqual(saved["header"]["value"], "1540.24")
        self.assertEqual(saved["header"]["series"], "rice total")
        text = (self.folder / saved["wheat_file"]).read_text(encoding="utf-8")
        for absent in (
            "total",
            "yield",
            "trade",
            "India",
            "all India",
            "state",
            "1540.24",
            "kharif",
            "summer",
        ):
            self.assertNotIn(absent, text)
        self.assertIn("Rabi", text)
        self.assertIn("1206.57", text)

    def test_reading_the_stored_record_writes_no_trade(self):
        saved = record_table_header(self.folder, citation_url=URL)
        path = self.folder / saved["file"]
        before = path.read_text(encoding="utf-8")
        record = json.loads(before)
        names_before = sorted(item.name for item in self.folder.iterdir())
        read = read_stored_header(record)
        self.assertEqual(record["value"], "1540.24")
        self.assertEqual(record["unit"], "Production in Lakh Tonnes")
        self.assertEqual(record["administrative_area"], "not printed on the page")
        self.assertIs(record["permits_financial_use"], False)
        self.assertIs(read["permits_financial_use"], False)
        self.assertEqual(record["class_c_policy"], "closed")
        self.assertNotIn("trade", read)
        self.assertNotIn("yield", read)
        self.assertNotIn("trade", before)
        self.assertNotIn("yield", before)
        self.assertEqual(path.read_text(encoding="utf-8"), before)
        self.assertEqual(
            sorted(item.name for item in self.folder.iterdir()),
            names_before,
        )
        wheat_path = self.folder / saved["wheat_file"]
        wheat_before = wheat_path.read_text(encoding="utf-8")
        wheat = json.loads(wheat_before)
        wheat_read = read_stored_header(wheat)
        self.assertEqual(wheat["value"], "1206.57")
        self.assertEqual(wheat["season"], "Rabi")
        self.assertNotIn("total", wheat)
        self.assertIs(wheat["permits_financial_use"], False)
        self.assertIs(wheat_read["permits_financial_use"], False)
        self.assertNotIn("trade", wheat_read)
        self.assertNotIn("yield", wheat_read)
        self.assertNotIn("trade", wheat_before)
        self.assertEqual(wheat_path.read_text(encoding="utf-8"), wheat_before)
        self.assertEqual(
            names_before,
            ["india-des-estimates.json", "india-des-wheat.json"],
        )

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_table_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_settlement_yield_or_trade_label_writes_nothing(self):
        for label in (
            "settlement",
            "yield",
            "trade",
            "kharif",
            "rabi",
            "summer",
            "india",
            "all india",
            "state",
            "Settlement",
            "YIELD",
            " Trade ",
        ):
            with self.assertRaises(ValueError):
                record_table_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_des_table(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("india_des", text)
            self.assertNotIn("desagri.gov.in/statistics-type/advance-estimates", text)
            self.assertNotIn("Time-Series-3rd-AE-2025-26-English.pdf", text)
