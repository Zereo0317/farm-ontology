import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.jma_marine import (
    ADMINISTRATIVE_AREA,
    JMA_MARINE_URL,
    PERIOD,
    record_series_header,
)

ROOT = Path(__file__).resolve().parents[1]
URL = JMA_MARINE_URL


class JmaMarineTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Japan Meteorological Agency")
        self.assertEqual(header["product"], "Distribution Marine Forecasts")
        self.assertEqual(header["period"], PERIOD)
        self.assertIn("Valid for 09 JST, 17 November", header["period"])
        self.assertIn("Initial time : 03 JST, 17 November", header["period"])
        self.assertIn("09 JST, 17", header["period"])
        self.assertIn("15 JST, 17", header["period"])
        self.assertIn("21 JST, 17", header["period"])
        self.assertIn("03 JST, 18", header["period"])
        self.assertNotIn("unit", header)
        self.assertEqual(header["administrative_area"], ADMINISTRATIVE_AREA)
        self.assertTrue(header["administrative_area"].startswith("SEA EAST OF SAKHALIN"))
        self.assertTrue(header["administrative_area"].endswith("SEA SOUTH OF OKINAWA"))
        self.assertIn("SEA OFF ABASHIRI", header["administrative_area"])
        self.assertIn("SETONAIKAI", header["administrative_area"])
        self.assertEqual(header["administrative_area"].count("; "), 36)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["citation_url"], "https://www.jma.go.jp/bosai/en_umimesh/")
        self.assertEqual(header["kind"], "Forecasts; Wind")
        self.assertNotEqual(header["kind"], header["product"])
        self.assertNotEqual(header["kind"], "Forecasts")
        self.assertNotEqual(header["kind"], "Wind")
        self.assertNotEqual(header["kind"], "Forecast")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(
            set(header),
            {
                "publisher",
                "product",
                "period",
                "administrative_area",
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
            "wave",
            "trade",
            "figure",
            "unit",
        ):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "海上分布予報",
            "wave",
            "height",
            "speed",
            "rainfall",
            "temperature",
            "yield",
            "price",
            "trade",
            "settlement",
            "completed harvest",
            "unit",
            "position",
            "2019",
            "Geospatial",
            "GSI Tiles",
            "km",
            "m/s",
            "licence",
            "license",
            "index",
        ):
            self.assertNotIn(word, text, word)
        source = (ROOT / "farm_ontology" / "jma_marine.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("https://www.jma.go.jp/ is not the citation.", flat)
        self.assertIn("https://www.jma.go.jp/bosai/ is not the citation.", flat)
        self.assertIn("https://www.jma.go.jp/bosai/en_umimesh is not the citation.", flat)
        self.assertIn("en_umimesh/ is not the citation.", flat)
        self.assertIn(
            "https://www.jma.go.jp/bosai/#lang=en&pattern=forecast is not the citation.",
            flat,
        )
        self.assertIn("The citation is the printed canonical link.", flat)
        self.assertIn("The map-view hash is omitted because it contains a position.", flat)
        self.assertIn(
            "The document title is Japan Meteorological Agency | Distribution Marine Forecasts.",
            flat,
        )
        self.assertIn(
            "Distribution Marine Forecasts is the product. Forecasts; Wind is the kind.",
            flat,
        )
        self.assertIn("Forecasts is not the kind. Wind is not the kind.", flat)
        self.assertIn("海上分布予報 is the icon title, not the product.", flat)
        self.assertIn(
            "The stored period is Valid for 09 JST, 17 November; Initial time : 03 JST, 17 November; 09 JST, 17; 15 JST, 17; 21 JST, 17; 03 JST, 18.",
            flat,
        )
        self.assertIn("Unit is omitted.", flat)
        self.assertIn(
            "The stored administrative area is the printed sea-area labels from SEA EAST OF SAKHALIN through SEA SOUTH OF OKINAWA.",
            flat,
        )
        self.assertIn("Do not store a wave height.", flat)
        self.assertIn("Do not store a wind speed.", flat)
        self.assertIn("Do not store a rainfall amount.", flat)
        self.assertIn("Do not store a temperature.", flat)
        self.assertIn("A forecast is not a completed harvest.", flat)
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
            "https://www.jma.go.jp/bosai/en_umimesh",
            "en_umimesh/",
            "https://www.jma.go.jp/bosai/#lang=en&pattern=forecast",
            "https://www.jma.go.jp/bosai/en_snow/",
            "https://www.jma.go.jp/bosai/en_kaikotan/",
            "http://www.jma.go.jp/bosai/en_umimesh/",
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
            "wave height",
            "wind speed",
            "rainfall amount",
            "temperature",
            "position",
            "海上分布予報",
            "09",
            "3 m",
            "10 m/s",
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
            {"period": "Valid for 09 JST, 17 November"},
            {"unit": "m"},
            {"unit": "m/s"},
            {"administrative_area": ADMINISTRATIVE_AREA},
            {"administrative_area": "SEA EAST OF SAKHALIN"},
            {"value": 2.5},
            {"value": "wave height"},
            {"value": "wind speed"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_jma_marine(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("jma_marine", text)
            self.assertNotIn("Distribution Marine Forecasts", text)
            self.assertNotIn("en_umimesh", text)


if __name__ == "__main__":
    unittest.main()
