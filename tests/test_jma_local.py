import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.jma_local import JMA_LOCAL_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = JMA_LOCAL_URL


class JmaLocalTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Japan Meteorological Agency")
        self.assertEqual(header["product"], "Local Information")
        self.assertNotIn("period", header)
        self.assertNotIn("unit", header)
        self.assertEqual(header["administrative_area"], "Nationwide information")
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Local Information")
        self.assertEqual(header["kind"], header["product"])
        self.assertNotEqual(header["kind"], "forecast")
        self.assertNotEqual(header["product"], "Daily Forecasts")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(
            set(header),
            {
                "publisher",
                "product",
                "administrative_area",
                "citation_url",
                "kind",
                "permits_financial_use",
            },
        )
        for key in ("value", "price", "temperature", "rainfall", "trade", "figure", "copyright"):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "気象庁",
            "Daily",
            "Three-hourly",
            "Two-week",
            "Seasonal",
            "Temperature",
            "Precipitation",
            "Hokkaido",
            "Tokyo",
            "Okinawa",
            "settlement",
            "yield",
            "price",
            "trade",
            "completed harvest",
            "rainfall",
            "temperature",
            "indexe",
            "kokusai",
            "Choose Your Town",
            "GPS",
            "prefecture",
            "the field was not opened",
            "period",
            "unit",
            "licence",
            "license",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "jma_local.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("https://www.jma.go.jp/ is not the citation.", flat)
        self.assertIn("https://www.jma.go.jp/jma/indexe.html is not the citation.", flat)
        self.assertIn("https://www.jma.go.jp/jma/kokusai/multi.html is not the citation.", flat)
        self.assertIn("The page did not print a separate canonical URL.", flat)
        self.assertIn(
            "The document title is Japan Meteorological Agency | Local Information.",
            flat,
        )
        self.assertIn(
            "Local Information is the document-title segment. It is not one of the forecast menu titles.",
            flat,
        )
        self.assertIn("気象庁 is a printed name, not a second publisher.", flat)
        self.assertIn("Weather is the group name, not the product.", flat)
        self.assertIn("Daily Forecasts was not opened.", flat)
        self.assertIn("Three-hourly Forecasts was not opened.", flat)
        self.assertIn("Two-week Temperature Forecast was not opened.", flat)
        self.assertIn("Seasonal Forecasts was not opened.", flat)
        self.assertIn("Daily, Three-hourly, Two-week, and Seasonal are not a period.", flat)
        self.assertIn("Period is omitted.", flat)
        self.assertIn("Unit is omitted.", flat)
        self.assertIn("The stored administrative area is Nationwide information.", flat)
        self.assertIn("Choose Your Town is not the administrative area.", flat)
        self.assertIn(
            "Hokkaido, Tokyo, and Okinawa are prefecture names. They are not the administrative area.",
            flat,
        )
        self.assertIn("Do not store a rainfall amount.", flat)
        self.assertIn("Do not store a temperature.", flat)
        self.assertIn("A forecast is not a completed harvest.", flat)
        self.assertIn("The header is not marked public domain.", flat)
        self.assertIn("permits_financial_use stays false.", flat)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://www.jma.go.jp/",
            "https://www.jma.go.jp/jma/indexe.html",
            "https://www.jma.go.jp/jma/kokusai/multi.html",
            "https://www.jma.go.jp/bosai/",
            "https://www.jma.go.jp/bosai/#lang=en",
            "https://www.jma.go.jp/bosai/#pattern=forecast",
            "http://www.jma.go.jp/bosai/#lang=en&pattern=forecast",
            "https://example.com/jma.html",
        ):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "settlement",
            "yield",
            "price",
            "trade",
            "completed harvest",
            "rainfall amount",
            "temperature",
            "Daily",
            "Three-hourly",
            "Two-week",
            "Seasonal",
            "12.5",
            "Settlement",
            "YIELD",
            "Price",
            "PRICE",
            "Trade",
            "Completed Harvest",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_filled_fields_and_figures_write_nothing(self):
        attempts = (
            {"period": "Daily"},
            {"period": "Three-hourly"},
            {"period": "Two-week"},
            {"period": "Seasonal"},
            {"period": "the field was not opened"},
            {"unit": "the field was not opened"},
            {"unit": "temperature"},
            {"unit": "rainfall"},
            {"administrative_area": "Nationwide information"},
            {"administrative_area": "Hokkaido"},
            {"administrative_area": "Tokyo"},
            {"administrative_area": "Choose Your Town"},
            {"value": 12.5},
            {"value": "rainfall"},
            {"value": "temperature"},
            {"value": "price"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_jma_local(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("jma_local", text)
            self.assertNotIn("bosai/#lang=en&pattern=forecast", text)


if __name__ == "__main__":
    unittest.main()
