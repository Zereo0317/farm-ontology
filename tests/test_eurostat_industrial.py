import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.eurostat_industrial import (
    EUROSTAT_INDUSTRIAL_URL,
    record_series_header,
)

ROOT = Path(__file__).resolve().parents[1]
URL = EUROSTAT_INDUSTRIAL_URL
NOT_OPENED = "the field was not opened"


class EurostatIndustrialTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Eurostat")
        self.assertEqual(header["product"], "Production in industry - monthly data")
        self.assertEqual(header["period"], NOT_OPENED)
        self.assertEqual(header["unit"], NOT_OPENED)
        self.assertEqual(header["administrative_area"], NOT_OPENED)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], NOT_OPENED)
        self.assertNotEqual(header["kind"], "index")
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
        for key in ("value", "price", "index_level", "growth", "trade", "figure", "copyright"):
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
            "index",
            "growth",
            "sts_inpr_m",
            "sts_esms",
            "licence",
            "license",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "eurostat_industrial.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn(
            "https://ec.europa.eu/eurostat/databrowser/product/page/sts_inpr_m did not print the product title, so it is not the citation.",
            flat,
        )
        self.assertIn(
            "https://ec.europa.eu/eurostat/cache/metadata/en/sts_esms.htm was not opened.",
            flat,
        )
        self.assertIn("https://ec.europa.eu/eurostat is not the citation.", flat)
        self.assertIn(
            "Do not relabel this header as an index, a yield, a forecast, or a completed harvest.",
            flat,
        )
        self.assertIn("Licence text was not opened.", flat)
        self.assertIn("The header is not marked public domain.", flat)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://ec.europa.eu/eurostat/databrowser/product/page/sts_inpr_m",
            "https://ec.europa.eu/eurostat/databrowser//product/page/sts_inpr_m",
            "https://ec.europa.eu/eurostat/cache/metadata/en/sts_esms.htm",
            "https://ec.europa.eu/eurostat",
            "https://example.com/eurostat.html",
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
            "index",
            "index value",
            "growth",
            "growth rate",
            "figure",
            "1.4",
            "2.5%",
            "Settlement",
            "YIELD",
            "Trade",
            "Forecast",
            "Observation",
            "Completed Harvest",
            "Public Domain",
            "Benchmark",
            "Index",
            "INDEX",
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
            {"kind": NOT_OPENED},
            {"kind": "index"},
            {"period": "2026"},
            {"unit": "index 2021=100"},
            {"administrative_area": "European Union"},
            {"value": 101.2},
            {"value": "growth rate"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_eurostat(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("eurostat_industrial", text)
            self.assertNotIn("getCategoryTree/icts/sts", text)
