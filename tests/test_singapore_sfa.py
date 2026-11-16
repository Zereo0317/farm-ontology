import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.singapore_sfa import CITATION_URL, record_sfa_header

ROOT = Path(__file__).resolve().parents[1]
URL = CITATION_URL


class SingaporeSfaTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_the_printed_header_without_a_figure(self):
        saved = record_sfa_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Singapore Food Agency")
        self.assertEqual(header["product"], "Singapore Food Statistics")
        self.assertEqual(header["period"], "2025 publication")
        self.assertEqual(
            header["unit"],
            "not printed as one unit; the publication lists local vegetables, "
            "beansprouts, mushrooms, eggs, and seafood",
        )
        self.assertEqual(header["administrative_area"], "Singapore")
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "observation")
        self.assertFalse(header["permits_financial_use"])
        for key in (
            "value",
            "price",
            "production",
            "yield",
            "import_share",
            "tonnes",
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
            "tonne",
        ):
            self.assertNotIn(word, text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_sfa_header(self.folder, citation_url=citation)
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
                record_sfa_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_sfa_publication(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("singapore_sfa", text)
            self.assertNotIn("sgfs-2025-publication_060526", text)
