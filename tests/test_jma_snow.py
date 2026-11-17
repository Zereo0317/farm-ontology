import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.jma_snow import JMA_SNOW_URL, PERIOD, UNIT, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = JMA_SNOW_URL


class JmaSnowTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Japan Meteorological Agency")
        self.assertEqual(header["product"], "Snow Analysis/Forecasts")
        self.assertNotEqual(header["product"], "Analysis and Forecasts of Snow")
        self.assertNotEqual(header["product"], "Snow depth")
        self.assertEqual(header["period"], PERIOD)
        self.assertIn("08 JST, 17 November 2026", header["period"])
        self.assertIn("08 JST", header["period"])
        self.assertIn("periods of 3, 6, 12, 24, 48 and 72 hours", header["period"])
        self.assertEqual(header["unit"], UNIT)
        self.assertEqual(header["unit"], "cm; 300 km")
        self.assertNotIn("administrative_area", header)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Analysis; Forecasts")
        self.assertNotEqual(header["kind"], header["product"])
        self.assertNotEqual(header["kind"], "Forecast")
        self.assertNotEqual(header["kind"], "Forecasts")
        self.assertNotEqual(header["kind"], "Analysis")
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
            "snowfall",
            "rainfall",
            "trade",
            "figure",
            "administrative_area",
        ):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "Analysis and Forecasts of Snow",
            "Snow depth",
            "area_type",
            "area_code",
            "010000",
            "Local Information",
            "Disaster Mitigation",
            "Geospatial",
            "GSI Tiles",
            "snowfall",
            "rainfall",
            "temperature",
            "yield",
            "price",
            "trade",
            "settlement",
            "completed harvest",
            "administrative",
            "position",
            "2019",
            "en_kaikotan",
            "licence",
            "license",
            "index",
        ):
            self.assertNotIn(word, text, word)
        source = (ROOT / "farm_ontology" / "jma_snow.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("https://www.jma.go.jp/ is not the citation.", flat)
        self.assertIn("https://www.jma.go.jp/bosai/ is not the citation.", flat)
        self.assertIn("https://www.jma.go.jp/bosai/en_snow is not the citation.", flat)
        self.assertIn("en_snow/ is not the citation.", flat)
        self.assertIn(
            "https://www.jma.go.jp/bosai/#lang=en&pattern=forecast is not the citation.",
            flat,
        )
        self.assertIn(
            "https://www.jma.go.jp/bosai/en_snow/#area_type=japan&area_code=010000 is not the citation.",
            flat,
        )
        self.assertIn("https://www.jma.go.jp/bosai/en_kaikotan/ is not the citation.", flat)
        self.assertIn("The citation is the printed canonical link.", flat)
        self.assertIn("The map-view hash is omitted.", flat)
        self.assertIn(
            "The document title is Japan Meteorological Agency | Analysis and Forecasts of Snow.",
            flat,
        )
        self.assertIn(
            "Snow Analysis/Forecasts is the product. Analysis; Forecasts is the kind.",
            flat,
        )
        self.assertIn(
            "Analysis and Forecasts of Snow is the document-title segment, not the product.",
            flat,
        )
        self.assertIn("Snow depth is the map title line, not a stored field.", flat)
        self.assertIn("Local Information is the menu document title, not the product.", flat)
        self.assertIn(
            "Information on Disaster Mitigation is the group heading, not a stored field.",
            flat,
        )
        self.assertIn(
            "The stored period is 08 JST, 17 November 2026; 08 JST; 09; 12; 15; 18; 21; 00; 03; 06; 09; 12; periods of 3, 6, 12, 24, 48 and 72 hours.",
            flat,
        )
        self.assertIn("The stored unit is cm; 300 km.", flat)
        self.assertIn("A unit is not a snowfall amount.", flat)
        self.assertIn("Legend scale amounts are not stored.", flat)
        self.assertIn("Administrative area is omitted.", flat)
        self.assertIn("area_type=japan and area_code=010000 are not an administrative area.", flat)
        self.assertIn("Do not store a snowfall amount.", flat)
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
            "https://www.jma.go.jp/bosai/en_snow",
            "en_snow/",
            "https://www.jma.go.jp/bosai/#lang=en&pattern=forecast",
            "https://www.jma.go.jp/bosai/en_snow/#area_type=japan&area_code=010000",
            "https://www.jma.go.jp/bosai/en_kaikotan/",
            "http://www.jma.go.jp/bosai/en_snow/",
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
            "snowfall amount",
            "rainfall amount",
            "temperature",
            "position",
            "Snow depth",
            "Analysis and Forecasts of Snow",
            "cm",
            "72",
            "010000",
            "300 km",
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
            {"period": "08 JST, 17 November 2026"},
            {"period": "periods of 3, 6, 12, 24, 48 and 72 hours"},
            {"unit": UNIT},
            {"unit": "cm"},
            {"unit": "300 km"},
            {"administrative_area": "Japan"},
            {"administrative_area": "010000"},
            {"value": 12.5},
            {"value": "snowfall"},
            {"value": "cm"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_jma_snow(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("jma_snow", text)
            self.assertNotIn("Snow Analysis/Forecasts", text)
            self.assertNotIn("en_snow", text)


if __name__ == "__main__":
    unittest.main()
