import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.iea_oil import IEA_OIL_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = IEA_OIL_URL
NOT_OPENED = "the field was not opened"


class IeaOilTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], 'International Energy Agency ("IEA")')
        self.assertEqual(header["product"], "Terms of Use for Non-CC Material")
        self.assertEqual(header["period"], NOT_OPENED)
        self.assertEqual(header["unit"], NOT_OPENED)
        self.assertEqual(header["administrative_area"], NOT_OPENED)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Terms")
        self.assertFalse(header["permits_financial_use"])
        self.assertNotEqual(header["period"], "November 2026")
        self.assertNotIn("Oil Market Report", header["product"])
        self.assertNotIn("MODS", header["product"])
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
            "supply",
            "demand",
            "stock",
            "balance",
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
            "supply",
            "demand",
            "stock",
            "price",
            "refinery",
            "world oil balance",
            "November 2026",
            "Oil Market Report",
            "MODS",
            "OMR",
            "CC BY",
            "three months",
            "financial services",
            "financial decisions",
            "OECD",
            "Purchase licence",
            "Data product",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "iea_oil.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("https://www.iea.org/ is not the citation.", flat)
        self.assertIn(
            "Oil Market Report - November 2026 is a report title on another page, not a period.",
            flat,
        )
        self.assertIn(
            "Oil Market Report (OMR) and Monthly Oil Data Service (MODS) Full Service are purchase-licence product names.",
            flat,
        )
        self.assertIn(
            "No supply, demand, stock, price, refinery figure, or world oil balance is stored.",
            flat,
        )
        self.assertIn("The current Oil Market Report is not CC BY 4.0.", flat)
        self.assertIn(
            "reports are made publicly available three months after their release.",
            flat,
        )
        self.assertIn("That sentence is not a grant to store the current balance.", flat)
        self.assertIn(
            "are not used for the purposes of (i) providing financial services or advice or (ii) informing investment, corporate or financial decisions.",
            flat,
        )
        self.assertIn("sharing the file in full is not permitted.", flat)
        self.assertIn("The terms are not marked public domain.", flat)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://www.iea.org/",
            "https://www.iea.org/terms",
            "https://www.iea.org/data-and-statistics/data-product/oil-market-report-omr",
            "https://www.iea.org/data-and-statistics/data-product/monthly-oil-data-service-mods-full-service",
            "https://www.iea.org/reports/oil-market-report-november-2026",
            "https://example.com/iea.html",
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
            "supply",
            "demand",
            "stock",
            "price",
            "refinery",
            "world oil balance",
            "figure",
            "November 2026",
            "CC BY 4.0",
            "4.0",
            "Settlement",
            "YIELD",
            "Trade",
            "Forecast",
            "Observation",
            "Completed Harvest",
            "Public Domain",
            "Benchmark",
            "Price",
            "Supply",
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
            {"period": "November 2026"},
            {"unit": "mb/d"},
            {"administrative_area": "world"},
            {"value": 1.2},
            {"value": "world oil balance"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_iea(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("iea_oil", text)
            self.assertNotIn("terms-of-use-for-non-cc-material", text)
