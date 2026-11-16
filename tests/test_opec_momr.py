import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.opec_momr import OPEC_MOMR_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = OPEC_MOMR_URL


class OpecMomrTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_quantity(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(
            header["publisher"],
            "Organization of the Petroleum Exporting Countries",
        )
        self.assertEqual(header["product"], "Monthly Oil Market Report")
        self.assertEqual(
            header["period"],
            "monthly; the November 2026 issue was the current file when the "
            "publications reader was opened; the public HTML page lists issues back "
            "through 2025 in the portion retrieved; a machine-readable history of "
            "every edition since the report began was not found",
        )
        self.assertEqual(
            header["unit"],
            "narrative and tables on world oil demand, non-OPEC supply, OPEC "
            "production, the balance, stocks, and rigs; no quantity is stored",
        )
        self.assertEqual(
            header["administrative_area"],
            "the report's published world and country tables; "
            "this record is not a stored world balance",
        )
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "report")
        self.assertFalse(header["permits_financial_use"])
        for key in ("value", "quantity", "outlook", "benchmark", "balance"):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "settlement",
            "benchmark",
            "yield",
            "trade",
            "observation",
            "forecast",
            "public domain",
            "completed harvest",
            "completed supply",
            "outlook",
        ):
            self.assertNotIn(word, text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        with self.assertRaises(ValueError):
            record_series_header(self.folder, citation_url="https://example.com/momr.pdf")
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "settlement",
            "benchmark",
            "yield",
            "trade",
            "observation",
            "forecast",
            "public domain",
            "completed harvest",
            "Settlement",
            "Benchmark",
            "YIELD",
            "Observation",
            "Forecast",
            "Public Domain",
            "Completed Harvest",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_momr(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("opec_momr", text)
            self.assertNotIn("monthly-oil-market-report.html", text)
