import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.gsci_methodology import GSCI_METHODOLOGY_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = GSCI_METHODOLOGY_URL
NOT_OPENED = "the field was not opened"


class GsciMethodologyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "S&P Dow Jones Indices")
        self.assertEqual(header["product"], "S&P GSCI Methodology")
        self.assertEqual(header["period"], NOT_OPENED)
        self.assertEqual(header["unit"], NOT_OPENED)
        self.assertEqual(header["administrative_area"], NOT_OPENED)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Index Methodology")
        self.assertFalse(header["permits_financial_use"])
        self.assertNotEqual(header["period"], "August 2026")
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
            "August 2026",
            "2026",
            "permission",
            "licence",
            "license",
            "All rights reserved",
            "methodology/article/sp-gsci-methodology",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "gsci_methodology.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn(
            "August 2026 is the methodology edition line, not a data period.",
            flat,
        )
        self.assertIn("https://www.spglobal.com/spdji/en/ is not the citation.", flat)
        self.assertIn(
            "https://www.spglobal.com/spdji/en/methodology/article/sp-gsci-methodology/ is not the citation.",
            flat,
        )
        self.assertIn(
            "Redistribution or reproduction needs the prior written permission of S&P Dow Jones Indices LLC.",
            flat,
        )
        self.assertIn(
            "A licence is required to display, create derivative works of, or distribute anything that uses S&P Dow Jones Indices and/or index data.",
            flat,
        )
        self.assertIn("The methodology is not marked public domain.", flat)
        self.assertNotIn("No content contained in these materials", source)
        self.assertNotIn("All rights reserved", source)
        self.assertNotIn("does not constitute an offer of services", source)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://www.spglobal.com/spdji/en/",
            "https://www.spglobal.com/spdji/en/methodology/article/sp-gsci-methodology/",
            "https://example.com/gsci.pdf",
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
            "August 2026",
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
            {"period": "August 2026"},
            {"unit": "index points"},
            {"administrative_area": "global"},
            {"value": 550.2},
            {"value": "index level"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_gsci(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("gsci_methodology", text)
            self.assertNotIn("methodology-sp-gsci.pdf", text)
