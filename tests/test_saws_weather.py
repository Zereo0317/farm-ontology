import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.saws_weather import SAWS_WEATHER_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = SAWS_WEATHER_URL
NOT_OPENED = "the field was not opened"


class SawsWeatherTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "South African Weather Service (SAWS)")
        self.assertEqual(header["product"], "Official Weather Forecasts")
        self.assertEqual(header["period"], NOT_OPENED)
        self.assertEqual(header["unit"], NOT_OPENED)
        self.assertEqual(header["administrative_area"], NOT_OPENED)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Official Weather Forecasts")
        self.assertNotEqual(header["kind"], "forecast")
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
            "observation",
            "completed harvest",
            "public domain",
            "benchmark",
            "index",
            "rainfall",
            "warnings",
            "Last-Modified",
            "05 Nov 2026",
            "11:22:38",
            "16 Nov 2026",
            "18:12:38",
            "Dmkf9C-7",
            "DvFxhP_Q",
            "TAMSAT",
            "licence",
            "license",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "saws_weather.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn(
            "South African Weather Service (SAWS) | Official Weather Forecasts.",
            flat,
        )
        self.assertIn("The body was an empty page shell.", flat)
        self.assertIn(
            "The bundles /assets/index-Dmkf9C-7.js and /assets/index-DvFxhP_Q.css were not unpacked.",
            flat,
        )
        self.assertIn("Period, unit, area, and licence were not printed.", flat)
        self.assertIn(
            "Last-Modified: Thu, 05 Nov 2026 11:22:38 GMT is a file timestamp, not a forecast period.",
            flat,
        )
        self.assertIn("Do not store a rainfall amount.", flat)
        self.assertIn("A forecast is not a completed harvest.", flat)
        self.assertIn("The header is not marked public domain.", flat)
        self.assertNotIn("index", text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://www.weathersa.co.za",
            "http://www.weathersa.co.za/",
            "https://weathersa.co.za/",
            "https://www.weathersa.co.za/index.html",
            "https://example.com/saws.html",
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
            "observation",
            "completed harvest",
            "public domain",
            "benchmark",
            "index",
            "rainfall amount",
            "figure",
            "12.5",
            "11:22:38",
            "Settlement",
            "YIELD",
            "Price",
            "PRICE",
            "Trade",
            "Observation",
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

    def test_filled_fields_and_figures_write_nothing(self):
        attempts = (
            {"period": NOT_OPENED},
            {"unit": NOT_OPENED},
            {"administrative_area": NOT_OPENED},
            {"period": "Thu, 05 Nov 2026 11:22:38 GMT"},
            {"unit": "mm"},
            {"administrative_area": "South Africa"},
            {"administrative_area": "South African"},
            {"value": 12.5},
            {"value": "rainfall"},
            {"value": "price"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_saws(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("saws_weather", text)
            self.assertNotIn("weathersa.co.za", text)
