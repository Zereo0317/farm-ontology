import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.argus_terms import ARGUS_TERMS_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = ARGUS_TERMS_URL
NOT_OPENED = "the field was not opened"


class ArgusTermsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Argus Media Limited")
        self.assertEqual(header["product"], "Argus Media Website Terms of Use")
        self.assertEqual(header["period"], NOT_OPENED)
        self.assertEqual(header["unit"], NOT_OPENED)
        self.assertEqual(header["administrative_area"], NOT_OPENED)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Terms of Use")
        self.assertFalse(header["permits_financial_use"])
        self.assertNotEqual(header["period"], "14 May 2024")
        self.assertNotIn("London", header["administrative_area"])
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
            "14 May 2024",
            "2024",
            "2026",
            "advice",
            "consent",
            "intellectual",
            "London",
            "graph",
            "All rights reserved",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "argus_terms.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn(
            "14 May 2024 is the terms update date, not a data period.",
            flat,
        )
        self.assertIn("https://www.argusmedia.com/ is not the citation.", flat)
        self.assertIn("https://www.argusmedia.com/en is not the citation.", flat)
        self.assertIn("The Copyright Policy named on the page was not opened.", flat)
        self.assertIn("No intellectual property is transferred.", flat)
        self.assertIn(
            "The content does not constitute advice or recommendations.",
            flat,
        )
        self.assertIn(
            "No part, including single prices, graphs, or news, may be copied or reproduced without the prior written consent of the publisher.",
            flat,
        )
        self.assertIn(
            "© 2026 Argus Media group. All rights reserved. is a copyright line, not public domain.",
            flat,
        )
        self.assertIn("The terms are not marked public domain.", flat)
        self.assertNotIn("01642534", source)
        self.assertNotIn("WC1X 8NL", source)
        self.assertNotIn("282921096", source)
        self.assertNotIn("Theobald", source)
        self.assertNotIn("spider", source)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://www.argusmedia.com/",
            "https://www.argusmedia.com/en",
            "https://example.com/argus.html",
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
            "single prices",
            "figure",
            "14 May 2024",
            "2024",
            "2026",
            "01642534",
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
            {"period": "14 May 2024"},
            {"unit": "USD"},
            {"administrative_area": "London"},
            {"administrative_area": "England and Wales"},
            {"value": 84.0},
            {"value": "single prices"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_argus(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("argus_terms", text)
            self.assertNotIn("argusmedia.com/en/policies/terms-of-use", text)
