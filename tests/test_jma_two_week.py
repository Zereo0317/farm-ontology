import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.jma_two_week import JMA_TWO_WEEK_URL, PERIOD, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = JMA_TWO_WEEK_URL


class JmaTwoWeekTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Japan Meteorological Agency")
        self.assertEqual(header["product"], "Two-week Temperature Forecast")
        self.assertEqual(header["period"], PERIOD)
        self.assertIn(
            "The Two-week Temperature Forecast is issued at 14:30 JST every day.",
            header["period"],
        )
        self.assertIn(
            "five-day average temperatures from eight days ahead",
            header["period"],
        )
        self.assertNotIn("unit", header)
        self.assertNotIn("administrative_area", header)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Two-week Temperature Forecast")
        self.assertEqual(header["kind"], header["product"])
        self.assertNotEqual(header["kind"], "forecast")
        self.assertNotEqual(header["kind"], "Forecast")
        self.assertNotEqual(header["kind"], "Two-week Forecast")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(
            set(header),
            {
                "publisher",
                "product",
                "period",
                "citation_url",
                "kind",
                "permits_financial_use",
            },
        )
        for key in (
            "value",
            "price",
            "temperature",
            "rainfall",
            "trade",
            "figure",
            "unit",
            "administrative_area",
        ):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "気象庁",
            "防災",
            "Two-week Forecast",
            "Forecasts",
            "Local Information",
            "Three-hourly",
            "Daily",
            "Seasonal",
            "prefecture",
            "probability",
            "%",
            "copyright.html",
            "pattern=forecast",
            "en_wdist",
            "map.html",
            "rainfall",
            "yield",
            "price",
            "trade",
            "settlement",
            "completed harvest",
            "unit",
            "administrative",
            "licence",
            "license",
            "indexe",
            "kokusai",
            "position",
            "km",
        ):
            self.assertNotIn(word, text, word)
        source = (ROOT / "farm_ontology" / "jma_two_week.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("https://www.jma.go.jp/ is not the citation.", flat)
        self.assertIn("https://www.data.jma.go.jp/ is not the citation.", flat)
        self.assertIn(
            "https://www.data.jma.go.jp/cpd/twoweek/en is not the citation.",
            flat,
        )
        self.assertIn("https://www.jma.go.jp/jma/indexe.html is not the citation.", flat)
        self.assertIn("https://www.jma.go.jp/jma/kokusai/multi.html is not the citation.", flat)
        self.assertIn(
            "https://www.jma.go.jp/bosai/#lang=en&pattern=forecast is not the citation.",
            flat,
        )
        self.assertIn("https://www.jma.go.jp/bosai/en_wdist/ is not the citation.", flat)
        self.assertIn("https://www.jma.go.jp/jma/en/copyright.html was not opened.", flat)
        self.assertIn(
            "The page does not print a separate citation URL. The citation is the data-url the menu printed.",
            flat,
        )
        self.assertIn(
            "The document title is Japan Meteorological Agency | Two-week Temperature Forecast.",
            flat,
        )
        self.assertIn(
            "Two-week Temperature Forecast is the document-title segment. It is the product and the kind.",
            flat,
        )
        self.assertIn("Forecast is not the kind.", flat)
        self.assertIn("Two-week Forecast is the breadcrumb, not a second kind.", flat)
        self.assertIn(
            "The word Temperature in the title is the product name. A temperature number is not stored.",
            flat,
        )
        self.assertIn("気象庁 is a printed name, not a second publisher.", flat)
        self.assertIn(
            "The stored period is The Two-week Temperature Forecast is issued at 14:30 JST every day.; five-day average temperatures from eight days ahead.",
            flat,
        )
        self.assertIn("Unit is omitted.", flat)
        self.assertIn("Administrative area is omitted.", flat)
        self.assertIn(
            "The prefecture menu and the map region labels are not an administrative area.",
            flat,
        )
        self.assertIn("Probability percentages are not stored.", flat)
        self.assertIn("Hidden list-view blocks were not stored.", flat)
        self.assertIn("Do not store a rainfall amount.", flat)
        self.assertIn("Do not store a temperature number.", flat)
        self.assertIn("A forecast is not a completed harvest.", flat)
        self.assertIn("An index is not a quantity of goods.", flat)
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
            "https://www.data.jma.go.jp/",
            "https://www.data.jma.go.jp/cpd/twoweek/en",
            "https://www.jma.go.jp/jma/indexe.html",
            "https://www.jma.go.jp/jma/kokusai/multi.html",
            "https://www.jma.go.jp/bosai/#lang=en&pattern=forecast",
            "https://www.jma.go.jp/bosai/en_wdist/",
            "http://www.data.jma.go.jp/cpd/twoweek/en/",
            "https://www.jma.go.jp/jma/en/copyright.html",
            "//www.jma.go.jp/jma/en/copyright.html",
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
            "Forecast",
            "Two-week Forecast",
            "30%",
            "14:30",
            "8",
            "Settlement",
            "YIELD",
            "Price",
            "PRICE",
            "Trade",
            "Completed Harvest",
            "FORECAST",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_filled_fields_and_figures_write_nothing(self):
        attempts = (
            {"period": PERIOD},
            {"period": "The Two-week Temperature Forecast is issued at 14:30 JST every day."},
            {"period": "five-day average temperatures from eight days ahead"},
            {"period": "14:30"},
            {"unit": "temperature"},
            {"unit": "°C"},
            {"administrative_area": "Japan"},
            {"administrative_area": "Hokkaido"},
            {"value": 12.5},
            {"value": "temperature"},
            {"value": "30%"},
            {"value": "rainfall"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_jma_two_week(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("jma_two_week", text)
            self.assertNotIn("cpd/twoweek/en", text)


if __name__ == "__main__":
    unittest.main()
