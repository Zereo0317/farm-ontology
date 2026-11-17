import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.eia_psm import EIA_PSM_URL, read_stored_record, record_series_header
from farm_ontology.policy import class_c_policy

ROOT = Path(__file__).resolve().parents[1]
URL = EIA_PSM_URL


class EiaPsmTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_quantity(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "U.S. Energy Information Administration")
        self.assertEqual(header["product"], "Petroleum Supply Monthly")
        self.assertEqual(
            header["period"],
            "monthly; the page opened was the release with data for August 2026, "
            "release date 30 October 2026, next release 30 November 2026; the landing "
            "page does not state the first year of the continuous file; these monthly "
            "figures are preliminary, and final monthly data appear in Petroleum "
            "Supply Annual, Volume 2",
        )
        self.assertEqual(
            header["unit"],
            "monthly supply, disposition, and ending stocks of crude oil and petroleum "
            "products: production, imports, exports, refinery runs, stocks, and "
            "movements; no quantity is stored",
        )
        self.assertEqual(
            header["administrative_area"],
            "the United States and PAD districts; this record is not a world balance",
        )
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "report")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(
            header["copyright_statement"],
            "EIA states that U.S. government publications on its site are in the "
            "public domain and are not subject to copyright, and asks for a dated "
            "acknowledgment. Third-party items on the site can still be protected.",
        )
        for key in ("value", "quantity", "price", "forecast", "balance", "observation"):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "settlement",
            "yield",
            "trade",
            "forecast",
            "observation",
            "completed harvest",
            "benchmark",
            "completed supply",
        ):
            self.assertNotIn(word, text)
        self.assertIn("preliminary", text)
        self.assertIn("public domain", text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        with self.assertRaises(ValueError):
            record_series_header(self.folder, citation_url="https://example.com/psm.xls")
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "settlement",
            "yield",
            "trade",
            "forecast",
            "observation",
            "completed harvest",
            "benchmark",
            "Settlement",
            "YIELD",
            "Forecast",
            "Observation",
            "Completed Harvest",
            "Benchmark",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_reading_the_stored_record_writes_no_trade(self):
        saved = record_series_header(self.folder, citation_url=URL)
        path = self.folder / saved["file"]
        before = path.read_text(encoding="utf-8")
        names_before = sorted(item.name for item in self.folder.iterdir())
        header = read_stored_record(self.folder)
        after = path.read_text(encoding="utf-8")
        names_after = sorted(item.name for item in self.folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names_after, names_before)
        self.assertEqual(names_after, ["petroleum-supply-monthly.json"])
        self.assertIs(header["permits_financial_use"], False)
        self.assertEqual(class_c_policy(), "closed")
        self.assertNotIn("trade", header)
        self.assertNotIn("value", header)
        self.assertNotIn("quantity", header)
        self.assertNotIn("series", header)
        self.assertNotIn("trade", after)
        self.assertEqual(header["kind"], "report")
        self.assertNotEqual(header["kind"], "forecast")
        self.assertNotEqual(header["kind"], "trade")

    def test_field_save_does_not_ingest_the_psm(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("eia_psm", text)
            self.assertNotIn("petroleum/supply/monthly", text)
