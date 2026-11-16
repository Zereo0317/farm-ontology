import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.chirps_rainfall import CHIRPS_RAINFALL_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = CHIRPS_RAINFALL_URL
NOT_OPENED = "the field was not opened"
PERIOD = "1981 to near-present"


class ChirpsRainfallTests(unittest.TestCase):
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
            "Climate Hazards Center - UC Santa Barbara",
        )
        self.assertEqual(
            header["product"],
            "CHIRPS: Rainfall Estimates from Rain Gauge and Satellite Observations",
        )
        self.assertEqual(header["period"], PERIOD)
        self.assertEqual(header["unit"], NOT_OPENED)
        self.assertEqual(header["administrative_area"], NOT_OPENED)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Rainfall Estimates")
        self.assertNotEqual(header["kind"], "public domain")
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
            "price",
            "trade",
            "forecast",
            "completed harvest",
            "public domain",
            "benchmark",
            "index",
            "rainfall amount",
            "0.05",
            "50°",
            "December",
            "2026",
            "1999",
            "quasi-global",
            "35+",
            "CHIRPS2",
            "CHIRPS v3",
            "Pete Peterson",
            "93106",
            "United States",
            "All Rights Reserved",
            "Regents",
            "°",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "chirps_rainfall.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("https://www.chc.ucsb.edu/ is not the citation.", flat)
        self.assertIn("The CHIRPS v3 page was not opened.", flat)
        self.assertIn("December 2026 is not the data period.", flat)
        self.assertIn("0.05° is the satellite-imagery resolution, not a rainfall unit.", flat)
        self.assertIn(
            "Spanning 50°S-50°N (and all longitudes) is a latitude band, not the administrative area.",
            flat,
        )
        self.assertIn(
            "The public-domain waiver by Pete Peterson is a licence sentence, not the kind, and it does not set permits_financial_use to true.",
            flat,
        )
        self.assertIn("CHIRPS data is in the public domain as registered with Creative Commons.", flat)
        self.assertIn("Do not store a rainfall amount.", flat)
        self.assertIn("A rainfall estimate is not a completed harvest.", flat)
        self.assertNotIn("public domain", text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://www.chc.ucsb.edu/",
            "https://www.chc.ucsb.edu",
            "https://www.chc.ucsb.edu/data/chirps/",
            "http://www.chc.ucsb.edu/data/chirps",
            "https://example.com/chirps.html",
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
            "rainfall amount",
            "figure",
            "0.05",
            "12.5",
            "December 2026",
            "Settlement",
            "YIELD",
            "Price",
            "PRICE",
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
            {"period": "December 2026"},
            {"period": NOT_OPENED},
            {"unit": NOT_OPENED},
            {"unit": "0.05°"},
            {"unit": "mm"},
            {"administrative_area": NOT_OPENED},
            {"administrative_area": "50°S-50°N"},
            {"administrative_area": "the United States"},
            {"administrative_area": "Santa Barbara, CA 93106"},
            {"value": 12.5},
            {"value": "rainfall"},
            {"value": "price"},
            {"permits_financial_use": True},
            {"permits_financial_use": "true"},
            {"permits_financial_use": False},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_chirps(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("chirps_rainfall", text)
            self.assertNotIn("chc.ucsb.edu/data/chirps", text)
