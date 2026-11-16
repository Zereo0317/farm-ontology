import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.bcom_methodology import BCOM_METHODOLOGY_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = BCOM_METHODOLOGY_URL
NOT_OPENED = "the field was not opened"


class BcomMethodologyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], 'Bloomberg Index Services Limited ("BISL")')
        self.assertEqual(header["product"], "Bloomberg Commodity Index")
        self.assertEqual(header["period"], NOT_OPENED)
        self.assertEqual(header["unit"], NOT_OPENED)
        self.assertEqual(header["administrative_area"], NOT_OPENED)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Index Methodology")
        self.assertFalse(header["permits_financial_use"])
        self.assertNotEqual(header["period"], "October 2026")
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
            "weight",
            "index_level",
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
            "weight",
            "index level",
            "October 2026",
            "London",
            "EC4N",
            "Queen Victoria",
            "advice",
            "consent",
            "redistribut",
            "CONFIDENTIAL",
            "All rights reserved",
            "merchantability",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "bcom_methodology.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn(
            "October 2026 is a change date in the document, not a data period.",
            flat,
        )
        self.assertIn("The London postal address is not an administrative area.", flat)
        self.assertIn("https://www.bloomberg.com/ is not the citation.", flat)
        self.assertIn(
            "https://www.bloomberg.com/professional/products/indices/ is not the citation.",
            flat,
        )
        self.assertIn(
            "The document and its contents may not be forwarded or redistributed without the prior consent of Bloomberg.",
            flat,
        )
        self.assertIn(
            "The document is factual information rather than financial product advice.",
            flat,
        )
        self.assertIn("It is not possible to invest directly in an index.", flat)
        self.assertIn("A licensing contact was printed and is not a grant.", flat)
        self.assertIn("The viewer title CONFIDENTIAL is not body text.", flat)
        self.assertIn("The methodology is not marked public domain.", flat)
        self.assertNotIn("All rights reserved", source)
        self.assertNotIn("merchantability", source)
        self.assertNotIn("212 617 5020", source)
        self.assertNotIn("EC4N 4TQ", source)
        self.assertNotIn("recommendations as to whether or not", source)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://www.bloomberg.com/",
            "https://www.bloomberg.com/professional/products/indices/",
            "https://www.bloomberg.com/professional/products/indices/documentation/",
            "https://example.com/bcom.pdf",
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
            "weight",
            "index level",
            "figure",
            "London",
            "United Kingdom",
            "October 2026",
            "OCT-2026",
            "EC4N 4TQ",
            "Settlement",
            "YIELD",
            "Trade",
            "Forecast",
            "Observation",
            "Completed Harvest",
            "Public Domain",
            "Benchmark",
            "Price",
            "Weight",
            "Index Level",
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
            {"period": "October 2026"},
            {"unit": "index points"},
            {"administrative_area": "London"},
            {"administrative_area": "United Kingdom"},
            {"value": 104.2},
            {"value": "index level"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_bcom(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("bcom_methodology", text)
            self.assertNotIn("BCOM-Methodology-OCT-2026.pdf", text)
