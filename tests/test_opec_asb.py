import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.opec_asb import OPEC_ASB_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = OPEC_ASB_URL
NOT_OPENED = "the field was not opened"


class OpecAsbTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "OPEC Secretariat")
        self.assertEqual(header["product"], "OPEC Annual Statistical Bulletin (ASB)")
        self.assertEqual(header["period"], "2026")
        self.assertEqual(header["unit"], NOT_OPENED)
        self.assertEqual(header["administrative_area"], NOT_OPENED)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Disclaimer")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(
            set(header),
            {
                "publisher",
                "product",
                "period",
                "unit",
                "administrative_area",
                "citation_url",
                "kind",
                "permits_financial_use",
            },
        )
        for key in (
            "value",
            "price",
            "balance",
            "production",
            "figure",
            "benchmark",
            "copyright",
        ):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "settlement",
            "yield",
            "trade",
            "forecast",
            "observation",
            "completed harvest",
            "public domain",
            "benchmark",
            "price",
            "balance",
            "production",
            "educational",
            "non-commercial",
            "permission",
            "foreword",
            "ASB_Disclaimer",
            "Whilst reasonable efforts",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "opec_asb.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn(
            "https://asb.opec.org/ASB_Disclaimer.html loaded a foreword and is not the citation.",
            flat,
        )
        self.assertIn(
            "The bulletin is not a benchmark or input data to a benchmark.",
            flat,
        )
        self.assertIn(
            "Full reproduction needs the OPEC Secretariat's written permission.",
            flat,
        )
        self.assertIn(
            "The educational and non-commercial sentence is not a grant to store a balance, price, or production figure.",
            flat,
        )
        self.assertIn("The bulletin is not marked public domain.", flat)
        self.assertNotIn("Whilst reasonable efforts have been made", source)
        self.assertNotIn("exclusive economic right", source)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://asb.opec.org/ASB_Disclaimer.html",
            "https://asb.opec.org/",
            "https://example.com/asb.pdf",
        ):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "settlement",
            "yield",
            "trade",
            "forecast",
            "observation",
            "completed harvest",
            "public domain",
            "benchmark",
            "price",
            "balance",
            "production",
            "production figure",
            "figure",
            "2025",
            "4",
            "5",
            "Settlement",
            "YIELD",
            "Trade",
            "Forecast",
            "Observation",
            "Completed Harvest",
            "Public Domain",
            "Benchmark",
            "Price",
            "Production",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_filled_fields_and_figures_write_nothing(self):
        attempts = (
            {"unit": NOT_OPENED},
            {"administrative_area": NOT_OPENED},
            {"unit": "mb/d"},
            {"administrative_area": "Member Countries"},
            {"period": "2026"},
            {"period": "2025"},
            {"value": 12.4},
            {"value": "production"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_opec(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("opec_asb", text)
            self.assertNotIn("asb-2026.pdf", text)
