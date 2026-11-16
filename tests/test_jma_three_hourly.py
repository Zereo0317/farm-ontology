import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.jma_three_hourly import JMA_THREE_HOURLY_URL, PERIOD, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = JMA_THREE_HOURLY_URL


class JmaThreeHourlyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Japan Meteorological Agency")
        self.assertEqual(header["product"], "Distribution/Three-hourly Forecasts")
        self.assertEqual(header["period"], PERIOD)
        self.assertIn("Valid for 06-09 JST, 17 November", header["period"])
        self.assertIn("Updated at 05 JST, 17 November 2026", header["period"])
        self.assertNotIn("unit", header)
        self.assertNotIn("administrative_area", header)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Distribution/Three-hourly Forecasts")
        self.assertEqual(header["kind"], header["product"])
        self.assertNotEqual(header["kind"], "forecast")
        self.assertNotEqual(header["kind"], "Forecasts")
        self.assertNotEqual(header["kind"], "Three-hourly Forecasts")
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
            "15",
            "21",
            "03",
            "5 km",
            "300 km",
            "300",
            "Geospatial",
            "Weather",
            "Daily",
            "Local Information",
            "Two-week",
            "Seasonal",
            "rainfall",
            "temperature",
            "yield",
            "price",
            "trade",
            "settlement",
            "completed harvest",
            "pattern=forecast",
            "map.html",
            "indexe",
            "kokusai",
            "unit",
            "administrative",
            "licence",
            "license",
            "2020",
            "km",
            "position",
        ):
            self.assertNotIn(word, text, word)
        source = (ROOT / "farm_ontology" / "jma_three_hourly.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("https://www.jma.go.jp/ is not the citation.", flat)
        self.assertIn("https://www.jma.go.jp/jma/indexe.html is not the citation.", flat)
        self.assertIn("https://www.jma.go.jp/jma/kokusai/multi.html is not the citation.", flat)
        self.assertIn(
            "https://www.jma.go.jp/bosai/#lang=en&pattern=forecast is not the citation.",
            flat,
        )
        self.assertIn(
            "https://www.jma.go.jp/bosai/map.html#contents=forecast&lang=en is not the citation.",
            flat,
        )
        self.assertIn("https://www.jma.go.jp/bosai/en_wdist is not the citation.", flat)
        self.assertIn("https://www.jma.go.jp/jma/en/copyright.html was not opened.", flat)
        self.assertIn(
            "The document title is Japan Meteorological Agency | Distribution/Three-hourly Forecasts.",
            flat,
        )
        self.assertIn(
            "Distribution/Three-hourly Forecasts is the document-title segment. It is the product and the kind.",
            flat,
        )
        self.assertIn("Forecasts is not the kind.", flat)
        self.assertIn("Three-hourly Forecasts is the contents control, not a second kind.", flat)
        self.assertIn("Weather is the map-title cell, not the product.", flat)
        self.assertIn("気象庁 is a printed name, not a second publisher.", flat)
        self.assertIn(
            "The stored period is Valid for 06-09 JST, 17 November; Updated at 05 JST, 17 November 2026.",
            flat,
        )
        self.assertIn("The slider hours 15, 21, and 03 are not the period.", flat)
        self.assertIn("5 km x 5 km is the grid size, not a unit.", flat)
        self.assertIn("300 km is the map scale, not a unit.", flat)
        self.assertIn("Unit is omitted.", flat)
        self.assertIn("Administrative area is omitted.", flat)
        self.assertIn("Japan inside the publisher name is not an administrative area.", flat)
        self.assertIn(
            "Geospatial Information Authority of Japan is an organization name, not the administrative area.",
            flat,
        )
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
            "https://www.jma.go.jp/jma/indexe.html",
            "https://www.jma.go.jp/jma/kokusai/multi.html",
            "https://www.jma.go.jp/bosai/#lang=en&pattern=forecast",
            "https://www.jma.go.jp/bosai/map.html#contents=forecast&lang=en",
            "https://www.jma.go.jp/bosai/en_wdist",
            "http://www.jma.go.jp/bosai/en_wdist/",
            "https://www.jma.go.jp/jma/en/copyright.html",
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
            "Forecasts",
            "Three-hourly Forecasts",
            "Weather",
            "5 km",
            "300 km",
            "15",
            "21",
            "03",
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
            {"period": PERIOD},
            {"period": "Valid for 06-09 JST, 17 November"},
            {"period": "Updated at 05 JST, 17 November 2026"},
            {"period": "15"},
            {"period": "5 km x 5 km"},
            {"period": "300 km"},
            {"unit": "5 km"},
            {"unit": "300 km"},
            {"unit": "temperature"},
            {"unit": "rainfall"},
            {"administrative_area": "Japan"},
            {"administrative_area": "Japan (list)"},
            {"administrative_area": "Geospatial Information Authority of Japan"},
            {"value": 12.5},
            {"value": "rainfall"},
            {"value": "temperature"},
            {"value": "300 km"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_jma_three_hourly(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("jma_three_hourly", text)
            self.assertNotIn("bosai/en_wdist", text)


if __name__ == "__main__":
    unittest.main()
