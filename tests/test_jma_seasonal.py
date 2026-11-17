import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.jma_seasonal import JMA_SEASONAL_URL, PERIOD, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = JMA_SEASONAL_URL


class JmaSeasonalTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Japan Meteorological Agency")
        self.assertEqual(header["product"], "Seasonal Forecasts")
        self.assertEqual(header["period"], PERIOD)
        self.assertIn("Issued at 14:30 JST, 12 Nov. 2026", header["period"])
        self.assertIn("11/14-12/13", header["period"])
        self.assertIn("up to six months ahead", header["period"])
        self.assertNotIn("unit", header)
        self.assertNotIn("administrative_area", header)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Seasonal Forecasts")
        self.assertEqual(header["kind"], header["product"])
        self.assertNotEqual(header["kind"], "forecast")
        self.assertNotEqual(header["kind"], "Forecasts")
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
            "統合地図",
            "Local Information",
            "Average temperature",
            "temperature",
            "elem=temperature",
            "pattern=P1M",
            "34.5",
            "137",
            "11/14-11/20",
            "11/21-11/27",
            "11/28-12/11",
            "Nov.-Jan.",
            "Winter",
            "below-",
            "near-",
            "above-normal",
            "probability",
            "copyright.html",
            "contents=forecast",
            "pattern=forecast",
            "en_wdist",
            "twoweek",
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
            "index",
            "position",
            "km",
            "Daily",
            "Three-hourly",
            "Two-week",
        ):
            self.assertNotIn(word, text, word)
        source = (ROOT / "farm_ontology" / "jma_seasonal.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("https://www.jma.go.jp/ is not the citation.", flat)
        self.assertIn("https://www.jma.go.jp/bosai/map.html is not the citation.", flat)
        self.assertIn(
            "https://www.jma.go.jp/bosai/map.html#contents=forecast&lang=en is not the citation.",
            flat,
        )
        self.assertIn(
            "https://www.jma.go.jp/bosai/map.html#5/34.5/137/&elem=temperature&pattern=P1M&term=0&contents=season&lang=en is not the citation.",
            flat,
        )
        self.assertIn(
            "https://www.jma.go.jp/bosai/#lang=en&pattern=forecast is not the citation.",
            flat,
        )
        self.assertIn("https://www.jma.go.jp/jma/en/copyright.html was not opened.", flat)
        self.assertIn(
            "The page does not print a separate citation URL. The citation is the data-url the menu printed.",
            flat,
        )
        self.assertIn(
            "The document title is Japan Meteorological Agency｜Seasonal Forecasts.",
            flat,
        )
        self.assertIn(
            "Seasonal Forecasts is the document-title segment. It is the product and the kind.",
            flat,
        )
        self.assertIn("Forecasts is not the kind.", flat)
        self.assertIn("気象庁 is a printed name, not a second publisher.", flat)
        self.assertIn(
            "The stored period is Issued at 14:30 JST, 12 Nov. 2026; 11/14-12/13; up to six months ahead.",
            flat,
        )
        self.assertIn(
            "11/14-11/20, 11/21-11/27, 11/28-12/11, Nov.-Jan., Nov., Dec., Jan., and Winter (Dec.-Feb.) are other term labels. They are not the period.",
            flat,
        )
        self.assertIn("Average temperature is not stored.", flat)
        self.assertIn("The probability legend is not stored.", flat)
        self.assertIn("Unit is omitted.", flat)
        self.assertIn("Administrative area is omitted.", flat)
        self.assertIn("The list of places is not an administrative area.", flat)
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
            "https://www.jma.go.jp/bosai/map.html",
            "https://www.jma.go.jp/bosai/map.html#contents=forecast&lang=en",
            "https://www.jma.go.jp/bosai/map.html#5/34.5/137/&elem=temperature&pattern=P1M&term=0&contents=season&lang=en",
            "https://www.jma.go.jp/bosai/#lang=en&pattern=forecast",
            "https://www.jma.go.jp/bosai/en_wdist/",
            "https://www.data.jma.go.jp/cpd/twoweek/en/",
            "https://www.jma.go.jp/jma/indexe.html",
            "https://www.jma.go.jp/jma/kokusai/multi.html",
            "https://www.jma.go.jp/jma/en/copyright.html",
            "http://www.jma.go.jp/bosai/map.html#contents=season&lang=en",
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
            "Average temperature",
            "Winter (Dec.-Feb.)",
            "Nov.-Jan.",
            "11/14-11/20",
            "30%",
            "14:30",
            "Settlement",
            "YIELD",
            "Price",
            "PRICE",
            "Trade",
            "Completed Harvest",
            "FORECASTS",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_filled_fields_and_figures_write_nothing(self):
        attempts = (
            {"period": PERIOD},
            {"period": "Issued at 14:30 JST, 12 Nov. 2026"},
            {"period": "11/14-12/13"},
            {"period": "11/14-11/20"},
            {"period": "Winter (Dec.-Feb.)"},
            {"period": "up to six months ahead"},
            {"unit": "temperature"},
            {"unit": "°C"},
            {"administrative_area": "Japan"},
            {"administrative_area": "Japan (list)"},
            {"value": 12.5},
            {"value": "temperature"},
            {"value": "30%"},
            {"value": "rainfall"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_jma_seasonal(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("jma_seasonal", text)
            self.assertNotIn("contents=season", text)


if __name__ == "__main__":
    unittest.main()
