import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.ecmwf_open_data import ECMWF_OPEN_DATA_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = ECMWF_OPEN_DATA_URL
NOT_OPENED = "the field was not opened"


class EcmwfOpenDataTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "ECMWF")
        self.assertEqual(header["product"], "Open data")
        self.assertEqual(header["period"], NOT_OPENED)
        self.assertEqual(header["unit"], NOT_OPENED)
        self.assertEqual(header["administrative_area"], NOT_OPENED)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Open data")
        self.assertNotEqual(header["kind"], "forecast value")
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
            "completed harvest",
            "public domain",
            "benchmark",
            "index",
            "forecast value",
            "figure",
            "October",
            "2026",
            "0.1",
            "0.25",
            "degrees",
            "°",
            "doi",
            "10.21957",
            "CC-BY",
            "4.0",
            "commercially",
            "attribution",
            "redistributed",
            "licence",
            "license",
            "Terms",
            "Charges",
            "Agreement",
            "European",
            "Weather",
            "Catalogue",
            "ensemble",
            "seasonal",
            "resolution",
            "GRIB",
            "global",
            "Open-Meteo",
            "open-meteo",
            "9.0",
            "JavaScript",
            "parameters",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "ecmwf_open_data.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("https://www.ecmwf.int/ is not the citation.", flat)
        self.assertIn(
            "https://www.ecmwf.int/en/forecasts/datasets is not the citation.",
            flat,
        )
        self.assertIn("https://doi.org/10.21957/open-data is not the citation.", flat)
        self.assertIn(
            "https://api.open-meteo.com/v1/forecast is not the citation.",
            flat,
        )
        self.assertIn("The Open-Meteo adapter is not this header.", flat)
        self.assertIn("20 October 2026 is a change date, not the period.", flat)
        self.assertIn(
            "0.1° and 0.25 degrees are grid resolution, not the unit.",
            flat,
        )
        self.assertIn(
            "This means that the data may be redistributed and used commercially, subject to appropriate attribution. That sentence is not a right to trade.",
            flat,
        )
        self.assertIn("The Service Charges page was not opened.", flat)
        self.assertIn("The DOI page was not opened.", flat)
        self.assertIn("The header is not marked public domain.", flat)
        self.assertIn("Do not store a forecast value.", flat)
        self.assertIn("A forecast is not a completed harvest.", flat)
        self.assertIn("open-data", text)
        self.assertNotIn("forecast value", text)
        self.assertNotIn("open-meteo", text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://www.ecmwf.int/",
            "https://www.ecmwf.int",
            "https://www.ecmwf.int/en/forecasts/datasets",
            "https://www.ecmwf.int/en/forecasts/datasets/open-data/",
            "http://www.ecmwf.int/en/forecasts/datasets/open-data",
            "https://ecmwf.int/en/forecasts/datasets/open-data",
            "https://doi.org/10.21957/open-data",
            "https://api.open-meteo.com/v1/forecast",
            "https://example.com/ecmwf.html",
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
            "forecast value",
            "cc-by-4.0",
            "commercially",
            "figure",
            "0.1",
            "0.25",
            "2026",
            "4.0",
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
            "Forecast",
            "Forecast Value",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_replaced_fields_and_figures_write_nothing(self):
        attempts = (
            {"period": NOT_OPENED},
            {"period": "20 October 2026"},
            {"period": "Open data"},
            {"unit": NOT_OPENED},
            {"unit": "0.1°"},
            {"unit": "0.25 degrees"},
            {"unit": "GRIB2"},
            {"administrative_area": NOT_OPENED},
            {"administrative_area": "global"},
            {"administrative_area": "Global"},
            {"value": 0.1},
            {"value": "forecast value"},
            {"value": "price"},
            {"permits_financial_use": True},
            {"permits_financial_use": "true"},
            {"permits_financial_use": False},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_ecmwf(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("ecmwf_open_data", text)
            self.assertNotIn("ecmwf.int/en/forecasts/datasets/open-data", text)
