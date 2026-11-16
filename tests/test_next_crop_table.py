import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.next_crop_table import CITATION_URL, record_crop_table_header

ROOT = Path(__file__).resolve().parents[1]
URL = CITATION_URL


class NextCropTableTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_the_printed_header_without_a_figure(self):
        saved = record_crop_table_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Companhia Nacional de Abastecimento")
        self.assertEqual(header["product"], "Safra de grãos")
        self.assertEqual(
            header["period"],
            "monthly during the crop year; bulletins numbered from October 2013",
        )
        self.assertEqual(header["unit"], "not printed on the opened series page")
        self.assertEqual(header["administrative_area"], "Brazil, national and state")
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "estimate")
        self.assertFalse(header["permits_financial_use"])
        for key in ("value", "price", "area", "production", "yield", "trade"):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in ("settlement", "yield", "trade", "observation", "completed harvest"):
            self.assertNotIn(word, text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_crop_table_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "settlement",
            "yield",
            "trade",
            "observation",
            "completed harvest",
            "Settlement",
            "YIELD",
            "Observation",
            "Completed Harvest",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_crop_table_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_crop_table(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("next_crop_table", text)
            self.assertNotIn("safra-de-graos", text)
