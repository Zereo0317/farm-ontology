import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.inmet_weather import INMET_WEATHER_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = INMET_WEATHER_URL
NOT_OPENED = "the field was not opened"


class InmetWeatherTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "INMET")
        self.assertEqual(header["product"], "Previsão")
        self.assertEqual(header["period"], NOT_OPENED)
        self.assertEqual(header["unit"], NOT_OPENED)
        self.assertEqual(header["administrative_area"], NOT_OPENED)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Previsão")
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
            "trade",
            "forecast",
            "observation",
            "completed harvest",
            "public domain",
            "benchmark",
            "index",
            "rainfall",
            "JavaScript",
            "Last-Modified",
            "10 Mar 2026",
            "18:10:53",
            "Instituto Nacional de Meteorologia",
            "Capitais",
            "portal.inmet.gov.br",
            "http://previsao.inmet.gov.br/",
            "71e1b5f9",
            "72b31329",
            "chunk.js",
            "licence",
            "license",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "inmet_weather.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("https://portal.inmet.gov.br/ is not the citation.", flat)
        self.assertIn(
            "Instituto Nacional de Meteorologia - INMET is the homepage title, not the citation.",
            flat,
        )
        self.assertIn("The forecast page title is INMET :: Previsão.", flat)
        self.assertIn("You need to enable JavaScript to run this app.", flat)
        self.assertIn(
            "The bundles /static/js/2.71e1b5f9.chunk.js and /static/js/main.72b31329.chunk.js were not unpacked.",
            flat,
        )
        self.assertIn("Period, unit, area, and licence were not printed.", flat)
        self.assertIn(
            "Last-Modified: Tue, 10 Mar 2026 18:10:53 GMT is a file timestamp, not a forecast period.",
            flat,
        )
        self.assertIn("Do not store a rainfall amount.", flat)
        self.assertIn("A forecast is not a completed harvest.", flat)
        self.assertIn("The header is not marked public domain.", flat)
        self.assertIn("http://previsao.inmet.gov.br/ is not the citation.", flat)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://portal.inmet.gov.br/",
            "https://portal.inmet.gov.br",
            "http://previsao.inmet.gov.br/",
            "https://previsao.inmet.gov.br",
            "https://example.com/inmet.html",
        ):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "settlement",
            "yield",
            "trade",
            "observation",
            "completed harvest",
            "public domain",
            "benchmark",
            "index",
            "rainfall amount",
            "figure",
            "12.5",
            "18:10:53",
            "Settlement",
            "YIELD",
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
            {"period": "Tue, 10 Mar 2026 18:10:53 GMT"},
            {"unit": "mm"},
            {"administrative_area": "Capitais"},
            {"administrative_area": "Brasil"},
            {"value": 12.5},
            {"value": "rainfall"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_inmet(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("inmet_weather", text)
            self.assertNotIn("previsao.inmet.gov.br", text)
