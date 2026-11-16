import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.mss_weather import MSS_WEATHER_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = MSS_WEATHER_URL
PERIOD = "the next 24 hours; Data from Mar 2016 to Nov 2026; Updated every 6 hours"
UNIT = "Degrees Celsius; Percentage; Kilometeres per hour"
AREA = "Singapore"


class MssWeatherTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(
            header["publisher"],
            "National Environment Agency, Meteorological Service Singapore (MSS)",
        )
        self.assertEqual(header["product"], "24-hour Weather Forecast")
        self.assertEqual(header["period"], PERIOD)
        self.assertEqual(header["unit"], UNIT)
        self.assertIn("Kilometeres", header["unit"])
        self.assertNotIn("Kilometres", header["unit"])
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
        for key in ("value", "price", "index_level", "growth", "trade", "figure", "copyright", "map"):
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
            "Kilometres",
            "Fair",
            "Rain",
            "Showers",
            "rainfall",
            "west",
            "east",
            "central",
            "north",
            "south",
            "Ang Mo Kio",
            "map",
            "SINGV",
            "©",
            "Open Government Products",
            "Open Data Licence",
            "commercial",
            "licence",
            "license",
            "open-data-licence",
            "(API)",
            "perior",
            "1.0.11",
            "feedback@data.gov.sg",
            "true",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "mss_weather.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("Keep the printed spelling Kilometeres.", flat)
        self.assertIn(
            "Free forever for personal or commercial use, under the Open Data Licence.",
            flat,
        )
        self.assertIn("https://data.gov.sg/open-data-licence was not opened.", flat)
        self.assertIn(
            "Commercial reuse of the dataset is not a right to trade, and it does not set permits_financial_use to true.",
            flat,
        )
        self.assertIn("A forecast is not a completed harvest.", flat)
        self.assertIn(
            "The words Fair, Rain, Showers, and the other forecast labels are labels.",
            flat,
        )
        self.assertIn("Do not store a rainfall amount.", flat)
        self.assertIn(
            "west, east, central, north, and south are printed region names.",
            flat,
        )
        self.assertIn("Ang Mo Kio is an example area name.", flat)
        self.assertIn("Do not store them as a rainfall map.", flat)
        self.assertIn(
            "© 2026 Open Government Products is a copyright line, not public domain.",
            flat,
        )
        self.assertIn("https://data.gov.sg/ is not the citation.", flat)
        self.assertNotIn("SINGV", flat)
        self.assertNotIn("SINGV", text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://data.gov.sg/",
            "https://data.gov.sg",
            "https://data.gov.sg/open-data-licence",
            URL + "/",
            "https://example.com/mss.html",
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
            "Fair",
            "Rain",
            "Showers",
            "rainfall amount",
            "west",
            "east",
            "central",
            "north",
            "south",
            "Ang Mo Kio",
            "figure",
            "24",
            "6",
            "1.4",
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
            {"period": "the next 24 hours"},
            {"unit": UNIT},
            {"unit": "Kilometres per hour"},
            {"unit": "mm"},
            {"administrative_area": AREA},
            {"administrative_area": "west"},
            {"administrative_area": "Ang Mo Kio"},
            {"value": 24},
            {"value": "rainfall"},
            {"permits_financial_use": True},
            {"permits_financial_use": "true"},
            {"permits_financial_use": False},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_mss(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("mss_weather", text)
            self.assertNotIn("d_ce2eb1e307bda31993c533285834ef2b", text)
