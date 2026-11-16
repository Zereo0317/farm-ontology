import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.modis_vegetation import MODIS_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = MODIS_URL
NOT_OPENED = "the field was not opened"
PERIOD = "2000-02-18 to Present"


class ModisVegetationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Earth Science Data Systems, NASA")
        self.assertEqual(
            header["product"],
            "MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid V061",
        )
        self.assertEqual(header["period"], PERIOD)
        self.assertEqual(header["unit"], "NDVI")
        self.assertEqual(header["administrative_area"], "Global")
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Vegetation Indices")
        self.assertNotEqual(header["kind"], "pixel value")
        self.assertNotEqual(header["unit"], "EVI")
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
            "pixel value",
            "pixel",
            "figure",
            "EVI",
            "Julian",
            "Rank",
            "N/A",
            "Meters",
            "meters",
            "2021",
            "2026",
            "16 Day",
            "days",
            "openly",
            "restriction",
            "shared",
            "EOSDIS",
            "Guidance",
            "usgs",
            "DAAC",
            "Goddard",
            "GSFC",
            "Center",
            "Home",
            "HDF",
            "180",
            "Published",
            "Updated",
            "JavaScript",
            "licence",
            "license",
            "scale",
            "fill",
            "6.1",
            "Level",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "modis_vegetation.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("https://www.earthdata.nasa.gov/ is not the citation.", flat)
        self.assertIn(
            "https://lpdaac.usgs.gov/products/mod13q1v061/ is not the citation.",
            flat,
        )
        self.assertIn("16 Day is temporal resolution, not a second period.", flat)
        self.assertIn("2021-02-16 is a catalogue date, not the period.", flat)
        self.assertIn("250 Meters is resolution, not the unit.", flat)
        self.assertIn(
            "EVI is a layer name, not a pixel value, and it does not replace NDVI.",
            flat,
        )
        self.assertIn(
            "This dataset is openly shared, without restriction, in accordance with the EOSDIS Data Use and Citation Guidance.",
            flat,
        )
        self.assertIn("That sentence is not a right to trade.", flat)
        self.assertIn("The EOSDIS guidance page was not opened.", flat)
        self.assertIn("The header is not marked public domain.", flat)
        self.assertIn("Do not store a pixel value.", flat)
        self.assertIn("A vegetation index is not a completed harvest.", flat)
        self.assertIn("NDVI", text)
        self.assertNotIn("EVI", text)
        self.assertNotIn("2021-02-16", text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://www.earthdata.nasa.gov/",
            "https://www.earthdata.nasa.gov",
            "https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod13q1-061/",
            "http://www.earthdata.nasa.gov/data/catalog/lpcloud-mod13q1-061",
            "https://earthdata.nasa.gov/data/catalog/lpcloud-mod13q1-061",
            "https://lpdaac.usgs.gov/products/mod13q1v061/",
            "https://lpdaac.usgs.gov/products/mod13q1v061",
            "https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod13q1-060",
            "https://example.com/modis.html",
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
            "pixel value",
            "index value",
            "evi",
            "EVI",
            "without restriction",
            "openly shared",
            "figure",
            "250",
            "2021-02-16",
            "0.8",
            "90",
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
            "Pixel Value",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_replaced_fields_and_figures_write_nothing(self):
        attempts = (
            {"period": PERIOD},
            {"period": "16 Day"},
            {"period": "every 16 days"},
            {"period": "2021-02-16"},
            {"period": "Present"},
            {"period": NOT_OPENED},
            {"unit": "NDVI"},
            {"unit": "EVI"},
            {"unit": "Julian day"},
            {"unit": "Rank"},
            {"unit": "N/A"},
            {"unit": "250 Meters"},
            {"unit": NOT_OPENED},
            {"administrative_area": "Global"},
            {"administrative_area": "GLOBAL"},
            {"administrative_area": NOT_OPENED},
            {"administrative_area": "Earth"},
            {"value": 0.8},
            {"value": "pixel value"},
            {"value": "price"},
            {"value": "EVI"},
            {"permits_financial_use": True},
            {"permits_financial_use": "true"},
            {"permits_financial_use": False},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_modis(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("modis_vegetation", text)
            self.assertNotIn("lpcloud-mod13q1", text)
