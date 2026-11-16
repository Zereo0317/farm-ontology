import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.platts_terms import PLATTS_TERMS_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = PLATTS_TERMS_URL
NOT_OPENED = "the field was not opened"
METHODOLOGY_PDF = (
    "https://www.spglobal.com/content/dam/spglobal/ci/en/documents/platts/en/"
    "our-methodology/methodology-specifications/"
    "Platts-Assessments-Methodology-Guide.pdf"
)


class PlattsTermsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "S&P Global Commodity Insights")
        self.assertEqual(header["product"], "Trial Subscription Terms and Conditions")
        self.assertEqual(header["period"], NOT_OPENED)
        self.assertEqual(header["unit"], NOT_OPENED)
        self.assertEqual(header["administrative_area"], NOT_OPENED)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Terms")
        self.assertFalse(header["permits_financial_use"])
        self.assertNotEqual(header["period"], "May 2024")
        self.assertNotIn("Methodology", header["product"])
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
            "assessment",
            "spread",
            "trade",
            "figure",
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
            "assessment",
            "spread",
            "May 2024",
            "investment",
            "advice",
            "licence",
            "license",
            "Platts-Assessments-Methodology-Guide.pdf",
            "royalty-free",
            "master subscription agreement",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "platts_terms.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn(
            "May 2024 is that guide's update line, not a period, and that guide prints no licence sentence.",
            flat,
        )
        self.assertIn(METHODOLOGY_PDF, flat)
        self.assertIn("The grant is only an internal evaluation licence.", flat)
        self.assertIn("The information is not financial or investment advice.", flat)
        self.assertIn(
            "No user should rely on a price assessment in an investment decision.",
            flat,
        )
        self.assertIn(
            "Publishing, reproducing, or distributing the information needs an additional licence.",
            flat,
        )
        self.assertIn("The master subscription agreement was not opened.", flat)
        self.assertIn("The terms are not marked public domain.", flat)
        self.assertNotIn("non-exclusive, non-transferable, royalty-free", source)
        self.assertNotIn("INTENDED ONLY FOR PROFESSIONALS", source)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            METHODOLOGY_PDF,
            "https://www.spglobal.com/",
            "https://www.spglobal.com/energy/en/pricing-benchmarks/our-methodology/assessment-methodologies",
            "https://example.com/platts.html",
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
            "assessment",
            "spread",
            "price assessment",
            "figure",
            "May 2024",
            "2024",
            "Settlement",
            "YIELD",
            "Trade",
            "Forecast",
            "Observation",
            "Completed Harvest",
            "Public Domain",
            "Benchmark",
            "Price",
            "Assessment",
            "Spread",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_filled_fields_and_figures_write_nothing(self):
        attempts = (
            {"period": NOT_OPENED},
            {"unit": NOT_OPENED},
            {"administrative_area": NOT_OPENED},
            {"period": "May 2024"},
            {"unit": "USD"},
            {"administrative_area": "global"},
            {"value": 82.5},
            {"value": "assessment"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_platts(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("platts_terms", text)
            self.assertNotIn("platts-trial-subscription-terms-and-conditions", text)
