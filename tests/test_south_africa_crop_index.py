import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.south_africa_crop_index import CITATION_URL, record_crop_index_header

ROOT = Path(__file__).resolve().parents[1]
URL = CITATION_URL
HEADER_KEYS = {
    "publisher",
    "product",
    "period",
    "unit",
    "administrative_area",
    "citation_url",
    "kind",
    "permits_financial_use",
}


class SouthAfricaCropIndexTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_the_printed_header_without_a_provincial_estimate(self):
        saved = record_crop_index_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Grain SA")
        self.assertEqual(header["product"], "crop estimates index")
        self.assertEqual(
            header["period"],
            "the index shows a 1 November 2026 release among others; "
            "the start of the archive was not read",
        )
        self.assertEqual(
            header["unit"],
            "not a stored figure; the index lists soybean, maize, sunflower, "
            "sorghum, wheat, dry beans, and groundnuts",
        )
        self.assertEqual(
            header["administrative_area"],
            "province, for South Africa, as named on the index",
        )
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "redistribution")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(set(header), HEADER_KEYS)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "settlement",
            "yield",
            "trade",
            "observation",
            "completed harvest",
            "Crop Estimates Committee",
            "DALRRD",
            "SAGIS",
            "official statistical office",
        ):
            self.assertNotIn(word, text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_crop_index_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "settlement",
            "yield",
            "trade",
            "official statistical office",
            "observation",
            "completed harvest",
            "Settlement",
            "YIELD",
            "Official Statistical Office",
            "Observation",
            "Completed Harvest",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_crop_index_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_index(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("south_africa_crop_index", text)
            self.assertNotIn("grainsa.co.za", text)
