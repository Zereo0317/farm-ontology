import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.hko_weather import HKO_WEATHER_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = HKO_WEATHER_URL
NOT_OPENED = "the field was not opened"
PERIOD = (
    "Forecast hours 03 to 72 hour in 3-hour interval "
    "(surface Weather forecast from 06 hour); "
    "Update frequency Updated four times daily based on analysis at "
    "00, 06, 12, and 18 UTC (08, 14, 20, and 02 HKT).; "
    "Update time table Updated at 03 HKT, 09 HKT, 15 HKT, 21 HKT everyday."
)
AREA = "8-46.5 N, 85-148 E"


class HkoWeatherTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Hong Kong Observatory(HKO)")
        self.assertEqual(header["product"], "HKO Non-Hydrostatic Model")
        self.assertEqual(header["period"], PERIOD)
        self.assertEqual(header["unit"], NOT_OPENED)
        self.assertEqual(header["administrative_area"], AREA)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "forecast")
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
        for key in ("value", "price", "index_level", "growth", "trade", "figure", "copyright", "resolution"):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "settlement",
            "yield",
            "trade",
            "observation",
            "completed harvest",
            "public domain",
            "benchmark",
            "index",
            "10 km",
            "rainfall",
            "Product information",
            "Weather Forecast",
            "Numerical Weather Prediction",
            "Chart area",
            "licence",
            "license",
            "copyright",
            "script",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "hko_weather.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("The page heading is Product information.", flat)
        self.assertIn(
            "Product information｜Hong Kong Observatory(HKO)｜Weather Forecast.",
            flat,
        )
        self.assertIn("The document title ends with Weather Forecast.", flat)
        self.assertIn("The model row is HKO Non-Hydrostatic Model.", flat)
        self.assertIn("A forecast is not a completed harvest.", flat)
        self.assertIn(
            "Model resolution 10 km is a printed resolution label. It is not the unit and it is not a rainfall amount.",
            flat,
        )
        self.assertIn("The product-types table cells are labels.", flat)
        self.assertIn("Header and footer scripts were not opened.", flat)
        self.assertIn("Licence text was not printed.", flat)
        self.assertIn("The header is not marked public domain.", flat)
        self.assertIn("https://www.hko.gov.hk/ is not the citation.", flat)
        self.assertNotIn("10 km", text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://www.hko.gov.hk/",
            "https://www.hko.gov.hk",
            "https://www.hko.gov.hk/en/",
            "https://www.hko.gov.hk/en/nhm/prodinfo.htm/",
            "https://example.com/hko.html",
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
            "10 km",
            "figure",
            "10",
            "46.5",
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

    def test_filled_unit_and_replaced_fields_write_nothing(self):
        attempts = (
            {"unit": NOT_OPENED},
            {"unit": "10 km"},
            {"unit": "mm"},
            {"period": PERIOD},
            {"period": "03 to 72 hour"},
            {"administrative_area": AREA},
            {"administrative_area": "Chart area"},
            {"administrative_area": "Hong Kong"},
            {"value": 10},
            {"value": "10 km"},
            {"value": "rainfall"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_hko(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("hko_weather", text)
            self.assertNotIn("prodinfo.htm", text)
