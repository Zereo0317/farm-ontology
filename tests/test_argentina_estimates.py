import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.argentina_estimates import CITATION_URL, record_estimates_header

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


class ArgentinaEstimatesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_the_printed_header_without_a_figure(self):
        saved = record_estimates_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Dirección de Estimaciones Agrícolas")
        self.assertEqual(header["product"], "Estimaciones agrícolas")
        self.assertEqual(
            header["period"],
            "catalog coverage starts 1969-01-01 and is updated twice a year; "
            "the catalog end date is also 1969-01-01 and is not the last campaign",
        )
        self.assertEqual(
            header["unit"],
            "not a stored figure; the catalog names sown area, harvested area, "
            "production in tonnes, and yield in kg/ha",
        )
        self.assertEqual(
            header["administrative_area"],
            "province and partido or department",
        )
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "estimate")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(set(header), HEADER_KEYS)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in ("settlement", "trade", "observation", "completed harvest"):
            self.assertNotIn(word, text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_estimates_header(self.folder, citation_url=citation)
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
                record_estimates_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_estimates(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("argentina_estimates", text)
            self.assertNotIn("estimaciones-agricolas", text)
