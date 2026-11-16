import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.gfs_forecast import GFS_FORECAST_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = GFS_FORECAST_URL
NOT_OPENED = "the field was not opened"
PERIOD = "up to 16 days"


class GfsForecastTests(unittest.TestCase):
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
            "National Oceanic and Atmospheric Administration",
        )
        self.assertEqual(header["product"], "Global Forecast System")
        self.assertEqual(header["period"], PERIOD)
        self.assertEqual(header["unit"], NOT_OPENED)
        self.assertEqual(header["administrative_area"], NOT_OPENED)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Global Forecast System")
        self.assertNotEqual(header["kind"], "forecast value")
        self.assertNotEqual(header["kind"], "GFS")
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
            "120",
            "13",
            "km",
            "127",
            "2019",
            "2021",
            "June",
            "March",
            "hourly",
            "hours",
            "four",
            "Four",
            "ncei",
            "404",
            "Commerce",
            "Department",
            "Bootstrap",
            "Otto",
            "Thornton",
            "Jacob",
            "Disclaimer",
            "disclaimer",
            "NCEP",
            "GFS",
            "Home",
            "JavaScript",
            "licence",
            "license",
            "products",
            "climate",
            "layers",
            "vertical",
            "cornerstone",
            "wave",
            "5-16",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "gfs_forecast.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("https://www.emc.ncep.noaa.gov/ is not the citation.", flat)
        self.assertIn(
            "https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast-system is not the citation.",
            flat,
        )
        self.assertIn("The NCEI URL returned HTTP 404.", flat)
        self.assertIn("Four times a day is a run cadence, not the period.", flat)
        self.assertIn(
            "Hourly for the first 120 hours, then 3 hourly, is output frequency, not the period.",
            flat,
        )
        self.assertIn("12 June 2019 is an implementation date, not the period.", flat)
        self.assertIn("22 March 2021 is an implementation date, not the period.", flat)
        self.assertIn("13 km is resolution, not the unit.", flat)
        self.assertIn("The Bootstrap author line is not the publisher.", flat)
        self.assertIn("The disclaimer page was not opened.", flat)
        self.assertIn("The header is not marked public domain.", flat)
        self.assertIn("Do not store a forecast value.", flat)
        self.assertIn("A forecast is not a completed harvest.", flat)
        self.assertIn("gfs.php", text)
        self.assertNotIn("forecast value", text)
        self.assertNotIn("ncei.noaa.gov", text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://www.emc.ncep.noaa.gov/",
            "https://www.emc.ncep.noaa.gov",
            "https://www.emc.ncep.noaa.gov/emc/pages/numerical_forecast_systems/",
            "https://www.emc.ncep.noaa.gov/emc/pages/numerical_forecast_systems/gfs.php/",
            "http://www.emc.ncep.noaa.gov/emc/pages/numerical_forecast_systems/gfs.php",
            "https://emc.ncep.noaa.gov/emc/pages/numerical_forecast_systems/gfs.php",
            "https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast-system",
            "https://www.ncei.noaa.gov/",
            "https://www.ecmwf.int/en/forecasts/datasets/open-data",
            "https://example.com/gfs.html",
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
            "disclaimer",
            "figure",
            "13",
            "120",
            "2019",
            "2021",
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
            "Disclaimer",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_replaced_fields_and_figures_write_nothing(self):
        attempts = (
            {"period": PERIOD},
            {"period": "four times a day"},
            {"period": "Four times a day"},
            {"period": "hourly forecast output for the first 120 hours, then 3 hourly for days 5-16"},
            {"period": "June 12, 2019"},
            {"period": "March 22, 2021"},
            {"period": "12 June 2019"},
            {"period": NOT_OPENED},
            {"unit": NOT_OPENED},
            {"unit": "13 km"},
            {"unit": "~13 km"},
            {"unit": "127 vertical layers"},
            {"administrative_area": NOT_OPENED},
            {"administrative_area": "global"},
            {"administrative_area": "Global"},
            {"value": 13},
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

    def test_field_save_does_not_ingest_gfs(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("gfs_forecast", text)
            self.assertNotIn("numerical_forecast_systems/gfs.php", text)
