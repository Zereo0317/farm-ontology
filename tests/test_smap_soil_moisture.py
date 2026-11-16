import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.smap_soil_moisture import (
    SMAP_SOIL_MOISTURE_URL,
    record_series_header,
)

ROOT = Path(__file__).resolve().parents[1]
URL = SMAP_SOIL_MOISTURE_URL
NOT_OPENED = "the field was not opened"


class SmapSoilMoistureTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "NASA")
        self.assertEqual(header["product"], "SMAP | Soil Moisture Active Passive")
        self.assertEqual(header["period"], NOT_OPENED)
        self.assertEqual(header["unit"], NOT_OPENED)
        self.assertEqual(header["administrative_area"], NOT_OPENED)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Soil Moisture Active Passive")
        self.assertNotEqual(header["kind"], "soil-moisture value")
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
            "soil-moisture value",
            "January 31, 2015",
            "2015",
            "2014-06-02",
            "17:12:34",
            "2026",
            "404",
            "/data/",
            "Jet Propulsion",
            "California Institute",
            "Privacy",
            "freeze",
            "nsidc",
            "NSIDC",
            "licence",
            "license",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "smap_soil_moisture.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn(
            "https://smap.jpl.nasa.gov/data/ returned HTTP 404 and was not a product title.",
            flat,
        )
        self.assertIn("January 31, 2015 is a launch countdown, not the period.", flat)
        self.assertIn("Licence was not opened.", flat)
        self.assertIn("The header is not marked public domain.", flat)
        self.assertIn("NSIDC was not opened.", flat)
        self.assertIn("Do not store a soil-moisture value.", flat)
        self.assertIn("A soil-moisture product is not a completed harvest.", flat)
        self.assertNotIn("2015", text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://smap.jpl.nasa.gov",
            "http://smap.jpl.nasa.gov/",
            "https://smap.jpl.nasa.gov/data/",
            "https://smap.jpl.nasa.gov/data",
            "https://www.nasa.gov/",
            "https://www.jpl.nasa.gov/",
            "https://nsidc.org/",
            "https://example.com/smap.html",
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
            "soil-moisture value",
            "figure",
            "0.25",
            "January 31, 2015",
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
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_replaced_fields_and_figures_write_nothing(self):
        attempts = (
            {"period": NOT_OPENED},
            {"period": "January 31, 2015"},
            {"period": "2014-06-02 17:12:34 -0700"},
            {"unit": NOT_OPENED},
            {"unit": "m3/m3"},
            {"administrative_area": NOT_OPENED},
            {"administrative_area": "California"},
            {"administrative_area": "Earth"},
            {"value": 0.25},
            {"value": "soil-moisture value"},
            {"value": "price"},
            {"permits_financial_use": True},
            {"permits_financial_use": "true"},
            {"permits_financial_use": False},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_smap(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("smap_soil_moisture", text)
            self.assertNotIn("smap.jpl.nasa.gov", text)
