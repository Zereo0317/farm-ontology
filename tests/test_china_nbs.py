import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.china_nbs import CITATION_URL, record_nbs_header

ROOT = Path(__file__).resolve().parents[1]
URL = CITATION_URL


class ChinaNbsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_the_printed_header_without_a_number(self):
        saved = record_nbs_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "National Bureau of Statistics of China")
        self.assertEqual(header["product"], "Output of major farm products")
        self.assertEqual(
            header["period"],
            "annual; a start year was not stated in the opened reply",
        )
        self.assertEqual(header["unit"], "not printed in the opened reply")
        self.assertEqual(
            header["administrative_area"],
            "national query; provincial yearbooks also publish sown area and output",
        )
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "observation")
        self.assertFalse(header["permits_financial_use"])
        for key in ("value", "price", "production", "yield", "number", "output"):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in ("settlement", "yield", "trade", "completed harvest"):
            self.assertNotIn(word, text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_nbs_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "settlement",
            "yield",
            "trade",
            "completed harvest",
            "Settlement",
            "YIELD",
            "Completed Harvest",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_nbs_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_nbs_query(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("china_nbs", text)
            self.assertNotIn("t20240524_1953659", text)
