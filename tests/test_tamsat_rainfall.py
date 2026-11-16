import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.tamsat_rainfall import TAMSAT_RAINFALL_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = TAMSAT_RAINFALL_URL
PERIOD = "1st January 1983 to present day"
UNIT = "mm"
AREA = (
    "African continent, including Madagascar "
    "(N: 38.025°, S: -35.9625°, W: -19.012°, E:51.975°)"
)


class TamsatRainfallTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "University of Reading")
        self.assertEqual(header["product"], "TAMSAT Rainfall")
        self.assertEqual(header["period"], PERIOD)
        self.assertEqual(header["unit"], UNIT)
        self.assertEqual(header["administrative_area"], AREA)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "rainfall estimate")
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
        for key in ("value", "price", "index_level", "growth", "trade", "figure", "copyright", "resolution"):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "settlement",
            "yield",
            "trade",
            "forecast",
            "completed harvest",
            "public domain",
            "benchmark",
            "index",
            "v3.1",
            "July",
            "2020",
            "2012",
            "0.0375",
            "4km",
            "daily",
            "pentadal",
            "dekadal",
            "monthly",
            "seasonal",
            "pentad",
            "rfe",
            "commercial",
            "CC BY",
            "creativecommons",
            "Copyright",
            "©",
            "true",
            "netCDF",
            "1974",
            "1894",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "tamsat_rainfall.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn(
            "v3.1 released 1st July 2020 is the printed version, not the period.",
            flat,
        )
        self.assertIn(
            "The time steps are daily, pentadal, dekadal, monthly, and seasonal.",
            flat,
        )
        self.assertIn("Latency is within 2 days after each pentad.", flat)
        self.assertIn(
            "Spatial resolution 0.0375° is the grid spacing, not the unit.",
            flat,
        )
        self.assertIn("The variables rfe and rfe_filled are names.", flat)
        self.assertIn("Do not store a rainfall amount.", flat)
        self.assertIn(
            "A rainfall estimate is not a completed harvest and it is not a weather forecast.",
            flat,
        )
        self.assertIn(
            "The page prints CC BY 4.0 and says the data are released for operational, research and commercial use.",
            flat,
        )
        self.assertIn(
            "That commercial sentence does not set permits_financial_use to true.",
            flat,
        )
        self.assertIn(
            "The deed page https://creativecommons.org/licenses/by/4.0/ was named by URL and was not opened as a second product.",
            flat,
        )
        self.assertIn(
            "© Copyright University of Reading is a copyright line, not public domain.",
            flat,
        )
        self.assertIn("https://ourresearch.reading.ac.uk/tamsat/ is not the citation.", flat)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://ourresearch.reading.ac.uk/tamsat/",
            "https://ourresearch.reading.ac.uk/tamsat",
            "https://ourresearch.reading.ac.uk/",
            "https://ourresearch.reading.ac.uk/tamsat/faq-rainfall/",
            "https://ourresearch.reading.ac.uk/tamsat/rainfall",
            "https://creativecommons.org/licenses/by/4.0/",
            "https://www.reading.ac.uk",
            "https://example.com/tamsat.html",
        ):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "settlement",
            "yield",
            "trade",
            "forecast",
            "completed harvest",
            "public domain",
            "benchmark",
            "index",
            "rainfall amount",
            "figure",
            "12.5",
            "0.0375",
            "v3.1",
            "4km",
            "Settlement",
            "YIELD",
            "Trade",
            "Forecast",
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
            {"period": "1st July 2020"},
            {"period": "1983-2012"},
            {"unit": UNIT},
            {"unit": "0.0375°"},
            {"unit": "hours"},
            {"administrative_area": AREA},
            {"administrative_area": "Madagascar"},
            {"administrative_area": "Middle East"},
            {"value": 12.5},
            {"value": "4km"},
            {"value": "0.0375"},
            {"permits_financial_use": True},
            {"permits_financial_use": "true"},
            {"permits_financial_use": False},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_tamsat(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("tamsat_rainfall", text)
            self.assertNotIn("tamsat/rainfall", text)
