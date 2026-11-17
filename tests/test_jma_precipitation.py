import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.jma_precipitation import (
    JMA_PRECIPITATION_URL,
    PERIOD,
    UNIT,
    record_series_header,
)

ROOT = Path(__file__).resolve().parents[1]
URL = JMA_PRECIPITATION_URL


class JmaPrecipitationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Japan Meteorological Agency")
        self.assertEqual(header["product"], "Precipitation Analysis/Forecasts")
        self.assertNotEqual(header["product"], "Localized Torrential Rain Forecast Map")
        self.assertNotEqual(
            header["product"],
            "Analysis and Forecasts of Precipitation",
        )
        self.assertEqual(header["period"], PERIOD)
        self.assertIn("1-hour. precipitation", header["period"])
        self.assertIn("09:00 JST, 17 November 2026", header["period"])
        self.assertIn("updated every 10 minutes", header["period"])
        self.assertIn("up to 6 hours ahead", header["period"])
        self.assertIn("from 7 to 15 hours ahead", header["period"])
        self.assertIn("updated every hour", header["period"])
        self.assertEqual(header["unit"], UNIT)
        self.assertEqual(header["unit"], "mm/h")
        self.assertNotIn("administrative_area", header)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Analysis; Forecasts")
        self.assertNotEqual(header["kind"], header["product"])
        self.assertNotEqual(header["kind"], "Forecast")
        self.assertNotEqual(header["kind"], "Forecasts")
        self.assertNotEqual(header["kind"], "Analysis")
        self.assertNotEqual(header["kind"], "Localized Torrential Rain Forecast Map")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(
            set(header),
            {
                "publisher",
                "product",
                "period",
                "unit",
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
            "administrative_area",
        ):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "Localized Torrential Rain Forecast Map",
            "Analysis and Forecasts of Precipitation",
            "elements:sjfcstmap",
            "elements:rasrf",
            "35.173808",
            "134.011230",
            "colordepth",
            "zoom:",
            "Local Information",
            "Disaster Mitigation",
            "Geospatial",
            "GSI Tiles",
            "rainfall",
            "temperature",
            "yield",
            "price",
            "trade",
            "settlement",
            "completed harvest",
            "administrative",
            "position",
            "2020",
            "km",
            "licence",
            "license",
            "index",
            "subtitle",
        ):
            self.assertNotIn(word, text, word)
        source = (ROOT / "farm_ontology" / "jma_precipitation.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("https://www.jma.go.jp/ is not the citation.", flat)
        self.assertIn("https://www.jma.go.jp/bosai/ is not the citation.", flat)
        self.assertIn("https://www.jma.go.jp/bosai/en_kaikotan is not the citation.", flat)
        self.assertIn("en_kaikotan/ is not the citation.", flat)
        self.assertIn(
            "https://www.jma.go.jp/bosai/#lang=en&pattern=forecast is not the citation.",
            flat,
        )
        self.assertIn(
            "https://www.jma.go.jp/bosai/en_kaikotan/#zoom:5/lat:35.173808/lon:134.011230/colordepth:normal/elements:rasrf&slmcs is not the citation.",
            flat,
        )
        self.assertIn(
            "https://www.jma.go.jp/bosai/en_kaikotan/#elements:sjfcstmap is not the citation.",
            flat,
        )
        self.assertIn("The citation is the printed canonical link.", flat)
        self.assertIn("The map-view hash is omitted.", flat)
        self.assertIn(
            "The document title is Japan Meteorological Agency | Analysis and Forecasts of Precipitation.",
            flat,
        )
        self.assertIn(
            "Precipitation Analysis/Forecasts is the product. Analysis; Forecasts is the kind.",
            flat,
        )
        self.assertIn(
            "Analysis and Forecasts of Precipitation is the document-title segment, not the product.",
            flat,
        )
        self.assertIn("Localized Torrential Rain Forecast Map is not the product.", flat)
        self.assertIn("Local Information is the menu document title, not the product.", flat)
        self.assertIn(
            "Information on Disaster Mitigation is the group heading, not a stored field.",
            flat,
        )
        self.assertIn(
            "The stored period is 1-hour. precipitation; 09:00 JST, 17 November 2026; 09:00; 21:00; 00:00; 03:00; 06:00; 09:00; 11:50; 15:00; 18:00; 21:00; updated every 10 minutes; up to 6 hours ahead; from 7 to 15 hours ahead; updated every hour.",
            flat,
        )
        self.assertIn("The stored unit is mm/h.", flat)
        self.assertIn("A unit is not a rainfall amount.", flat)
        self.assertIn("Legend scale amounts are not stored.", flat)
        self.assertIn("Administrative area is omitted.", flat)
        self.assertIn("The map subtitle is omitted.", flat)
        self.assertIn("Do not store a rainfall amount.", flat)
        self.assertIn("Do not store a temperature.", flat)
        self.assertIn("A forecast is not a completed harvest.", flat)
        self.assertIn("An analysis is not a quantity of goods.", flat)
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
            "https://www.jma.go.jp/bosai/",
            "https://www.jma.go.jp/bosai/en_kaikotan",
            "en_kaikotan/",
            "https://www.jma.go.jp/bosai/#lang=en&pattern=forecast",
            "https://www.jma.go.jp/bosai/en_kaikotan/#zoom:5/lat:35.173808/lon:134.011230/colordepth:normal/elements:rasrf&slmcs",
            "https://www.jma.go.jp/bosai/en_kaikotan/#elements:sjfcstmap",
            "http://www.jma.go.jp/bosai/en_kaikotan/",
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
            "position",
            "Localized Torrential Rain Forecast Map",
            "Analysis and Forecasts of Precipitation",
            "mm",
            "10",
            "35.173808",
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
            {"period": "1-hour. precipitation"},
            {"period": "09:00 JST, 17 November 2026"},
            {"unit": UNIT},
            {"unit": "mm"},
            {"administrative_area": "Japan"},
            {"administrative_area": "Hokkaido"},
            {"value": 12.5},
            {"value": "rainfall"},
            {"value": "mm/h"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_jma_precipitation(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("jma_precipitation", text)
            self.assertNotIn("Precipitation Analysis/Forecasts", text)
            self.assertNotIn("en_kaikotan", text)


if __name__ == "__main__":
    unittest.main()
