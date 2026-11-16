import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.era5_land import ERA5_LAND_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = ERA5_LAND_URL
NOT_OPENED = "the field was not opened"
PERIOD = "January 1950 to present"


class Era5LandTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Copernicus C3S")
        self.assertEqual(header["product"], "ERA5-Land hourly data from 1950 to present")
        self.assertEqual(header["period"], PERIOD)
        self.assertEqual(header["unit"], NOT_OPENED)
        self.assertEqual(header["administrative_area"], "Global")
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Reanalysis")
        self.assertNotEqual(header["kind"], "copied value")
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
            "price",
            "trade",
            "forecast",
            "completed harvest",
            "public domain",
            "benchmark",
            "index",
            "copied value",
            "0.1",
            "9 km",
            "°",
            "2019",
            "2026",
            "CC-BY",
            "licence",
            "license",
            "ECMWF",
            "Europe",
            "Earth",
            "GRIB",
            "centimetres",
            "decades",
            "Past",
            "Horizontal",
            "Spatial",
            "Publication",
            "Terms",
            "JavaScript",
            "Hourly",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "era5_land.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("https://cds.climate.copernicus.eu/ is not the citation.", flat)
        self.assertIn(
            "https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land is not the citation.",
            flat,
        )
        self.assertIn("0.1° and 9 km are resolution, not the unit.", flat)
        self.assertIn(
            "Hourly is the temporal resolution already named in the product, not a second period.",
            flat,
        )
        self.assertIn("2019-07-12 is the publication date, not the period.", flat)
        self.assertIn(
            "The CC-BY licence button was printed, and the licence text behind it was not opened, so it is not a grant.",
            flat,
        )
        self.assertIn("The header is not marked public domain.", flat)
        self.assertIn("Do not store a copied value.", flat)
        self.assertIn("A reanalysis is not a completed harvest.", flat)
        self.assertNotIn("2019-07-12", text)
        self.assertNotIn("tab=download", text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://cds.climate.copernicus.eu/",
            "https://cds.climate.copernicus.eu",
            "https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land",
            "https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land/",
            "http://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=overview",
            "https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=download",
            "https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=overview/",
            "https://example.com/era5.html",
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
            "forecast",
            "completed harvest",
            "public domain",
            "benchmark",
            "index",
            "copied value",
            "cc-by",
            "cc-by licence",
            "figure",
            "0.1",
            "9 km",
            "2019-07-12",
            "Settlement",
            "YIELD",
            "Price",
            "PRICE",
            "Trade",
            "Completed Harvest",
            "Public Domain",
            "Benchmark",
            "Index",
            "INDEX",
            "Copied Value",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_replaced_fields_and_figures_write_nothing(self):
        attempts = (
            {"period": PERIOD},
            {"period": "hourly"},
            {"period": "Hourly"},
            {"period": "2019-07-12"},
            {"period": "2026-11-16"},
            {"period": "Past"},
            {"period": "from 1950 to present"},
            {"period": NOT_OPENED},
            {"unit": NOT_OPENED},
            {"unit": "0.1°"},
            {"unit": "9 km"},
            {"unit": "GRIB"},
            {"unit": "centimetres"},
            {"administrative_area": "Global"},
            {"administrative_area": NOT_OPENED},
            {"administrative_area": "Earth"},
            {"administrative_area": "Europe"},
            {"value": 0.1},
            {"value": "copied value"},
            {"value": "price"},
            {"permits_financial_use": True},
            {"permits_financial_use": "true"},
            {"permits_financial_use": False},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_era5(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("era5_land", text)
            self.assertNotIn("reanalysis-era5-land", text)
