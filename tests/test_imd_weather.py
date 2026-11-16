import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.imd_weather import IMD_WEATHER_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = IMD_WEATHER_URL
PERIOD = (
    "2026-11-16; Time of Issue: 20:35:00 hours IST; (Night); "
    "7 Days Rainfall Forecast; 16 November (Day 1) through "
    "22 November (Day 7)"
)
UNIT = "Legend Category %Stations"
AREA = "All India"
DOWNLOAD = (
    "https://mausam.imd.gov.in/backend/assets/aiwfb_pdf/"
    "b486c0d9e22dbb8d627d179337d58f38.pdf"
)


class ImdWeatherTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "India Meteorological Department")
        self.assertEqual(header["product"], "All India Weather Forecast Bulletin")
        self.assertEqual(header["period"], PERIOD)
        self.assertEqual(header["unit"], UNIT)
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
        for key in (
            "value",
            "price",
            "index_level",
            "growth",
            "trade",
            "figure",
            "copyright",
            "download_link",
            "rainfall",
        ):
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
            "copyright",
            "©",
            "millimetre",
            "Subdivision",
            "0830",
            "76-100",
            "51-75",
            "26-50",
            "1-25",
            "WS",
            "FWS",
            "SCT",
            "ISOL",
            "DRY",
            "Lodhi",
            "110003",
            "2434-4599",
            "1875",
            "advice",
            "redistribution",
            "Ministry of Earth Sciences",
            "Government of India",
            "SUMMARY AND FORECAST",
            "loss of profit",
            "disclaimer.php",
            "b486c0d9e22dbb8d627d179337d58f38",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "imd_weather.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn(
            "The printed download link is https://mausam.imd.gov.in/backend/assets/aiwfb_pdf/b486c0d9e22dbb8d627d179337d58f38.pdf.",
            flat,
        )
        self.assertIn(
            "It is not a rainfall file and it is not a second product.",
            flat,
        )
        self.assertIn(
            "ALL INDIA WEATHER SUMMARY AND FORECAST BULLETIN is the PDF line, not a second product.",
            flat,
        )
        self.assertIn(
            "Forecast and warning for any day is valid from 0830 hours IST of day till 0830 hours IST of next day.",
            flat,
        )
        self.assertIn("A forecast is not a completed harvest.", flat)
        self.assertIn(
            "The legend categories WS, FWS, SCT, ISOL, and DRY are labels, not millimetre amounts.",
            flat,
        )
        self.assertIn("No rainfall amount or subdivision row is stored.", flat)
        self.assertIn(
            "© Copyright 2026, Developed by IT Team, India Meteorological Department is a copyright line, not public domain.",
            flat,
        )
        self.assertIn(
            "The disclaimer says the site is not a substitute for independent professional advice.",
            flat,
        )
        self.assertIn("A separate redistribution grant was not printed.", flat)
        self.assertIn("https://mausam.imd.gov.in/ is not the citation.", flat)
        self.assertNotIn("loss of profit", flat)
        self.assertNotIn(DOWNLOAD, text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://mausam.imd.gov.in/",
            "https://mausam.imd.gov.in",
            "https://mausam.imd.gov.in/responsive/disclaimer.php",
            DOWNLOAD,
            "https://example.com/imd.html",
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
            "subdivision",
            "figure",
            "12.5",
            "76-100",
            "0",
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

    def test_replaced_fields_and_figures_write_nothing(self):
        attempts = (
            {"period": PERIOD},
            {"period": "2026-11-16"},
            {"period": "the field was not opened"},
            {"unit": UNIT},
            {"unit": "millimetre"},
            {"administrative_area": AREA},
            {"administrative_area": "the field was not opened"},
            {"administrative_area": "New Delhi"},
            {"administrative_area": "Subdivision"},
            {"value": 12.5},
            {"value": "76-100"},
            {"value": "rainfall"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_imd(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("imd_weather", text)
            self.assertNotIn("all_india_forcast_bulletin", text)
