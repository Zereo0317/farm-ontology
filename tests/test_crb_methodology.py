import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.crb_methodology import CRB_METHODOLOGY_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = CRB_METHODOLOGY_URL
NOT_OPENED = "the field was not opened"


class CrbMethodologyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "FTSE International Limited")
        self.assertEqual(header["product"], "FTSE/CoreCommodity CRB\u00ae Index Methodology")
        self.assertEqual(header["period"], NOT_OPENED)
        self.assertEqual(header["unit"], NOT_OPENED)
        self.assertEqual(header["administrative_area"], NOT_OPENED)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Methodology")
        self.assertFalse(header["permits_financial_use"])
        self.assertNotEqual(header["period"], "May 2026")
        self.assertNotEqual(header["period"], "08 May 2026")
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
            "May 2026",
            "08 May 2026",
            "2026",
            "v1.2",
            "permission",
            "licence",
            "license",
            "investment",
            "All rights reserved",
            "commodity-indices",
            "796803",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "crb_methodology.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn(
            "May 2026 and Effective Date 08 May 2026 are document dates, not a data period.",
            flat,
        )
        self.assertIn("https://www.lseg.com/ is not the citation.", flat)
        self.assertIn(
            "https://www.lseg.com/en/ftse-russell/indices/commodity-indices is not the citation.",
            flat,
        )
        self.assertIn(
            "No part may be reproduced without the prior written permission of the applicable member of LSEG.",
            flat,
        )
        self.assertIn(
            "Use and distribution of LSEG data requires a licence from LSEG and/or its licensors.",
            flat,
        )
        self.assertIn(
            "The document says it is not investment advice and that indices cannot be invested in directly.",
            flat,
        )
        self.assertIn(
            "Document Classification: Public is the cover label and is not public domain.",
            flat,
        )
        self.assertIn("The methodology is not marked public domain.", flat)
        self.assertNotIn("All rights reserved", source)
        self.assertNotIn("photocopying, recording or otherwise", source)
        self.assertNotIn("796803", source)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://www.lseg.com/",
            "https://www.lseg.com/en/ftse-russell",
            "https://www.lseg.com/en/ftse-russell/indices/commodity-indices",
            "https://example.com/crb.pdf",
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
            "May 2026",
            "08 May 2026",
            "v1.2",
            "2026",
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
            {"period": "May 2026"},
            {"period": "08 May 2026"},
            {"unit": "USD"},
            {"administrative_area": "United Kingdom"},
            {"value": 220.4},
            {"value": "index level"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_crb(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("crb_methodology", text)
            self.assertNotIn("ftse-corecommodity-crb-index-methodology.pdf", text)
