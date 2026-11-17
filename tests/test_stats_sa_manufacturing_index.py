import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.policy import CLASS_C_POLICY
from farm_ontology.stats_sa_manufacturing import (
    COPYRIGHT_NOTICE,
    STATS_SA_MANUFACTURING_URL,
)
from farm_ontology.stats_sa_manufacturing_index import record_printed_index

ROOT = Path(__file__).resolve().parents[1]
URL = STATS_SA_MANUFACTURING_URL


class StatsSaManufacturingIndexTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_reading_the_stored_record_writes_no_trade(self):
        saved = record_printed_index(self.folder, citation_url=URL)
        path = self.folder / saved["file"]
        before = path.read_text(encoding="utf-8")
        names_before = sorted(item.name for item in self.folder.iterdir())
        record = json.loads(before)
        after = path.read_text(encoding="utf-8")
        names_after = sorted(item.name for item in self.folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names_after, names_before)
        self.assertEqual(names_after, ["manufacturing-production-index.json"])
        self.assertEqual(record["series"], "Index of the volume of manufacturing production")
        self.assertEqual(record["period"], "September 2026")
        self.assertEqual(record["unit"], "Base: 2019=100")
        self.assertEqual(record["value"], "95,1")
        self.assertEqual(record["citation_url"], URL)
        self.assertEqual(record["copyright_notice"], COPYRIGHT_NOTICE)
        self.assertIn("acknowledge Stats SA", record["copyright_notice"])
        self.assertFalse(record["permits_financial_use"])
        self.assertEqual(record["class_c_policy"], "closed")
        self.assertEqual(record["class_c_policy"], CLASS_C_POLICY)
        self.assertNotIn("trade", record)
        self.assertNotIn("settlement", record)
        for word in (
            "trade",
            "settlement",
            "quantity of goods",
            "310 284",
            "89,5",
            "98,5",
            "3,5",
            "October",
        ):
            self.assertNotIn(word, after)
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("stats_sa_manufacturing_index", text)

    def test_missing_citation_or_a_trade_writes_nothing(self):
        for citation in (
            None,
            "",
            "   ",
            "https://www.statssa.gov.za/publications/P30412/P30412October2026.pdf",
        ):
            with self.assertRaises(ValueError):
                record_printed_index(self.folder, citation_url=citation)
        for label in ("trade", "settlement", "quantity of goods", "TRADE"):
            with self.assertRaises(ValueError):
                record_printed_index(self.folder, citation_url=URL, label=label)
        with self.assertRaises(ValueError):
            record_printed_index(self.folder, citation_url=URL, value="3,5")
        with self.assertRaises(ValueError):
            record_printed_index(self.folder, citation_url=URL, permits_financial_use=True)
        with self.assertRaises(ValueError):
            record_printed_index(self.folder, citation_url=URL, class_c_policy="open")
        self.assertEqual(list(self.folder.iterdir()), [])
