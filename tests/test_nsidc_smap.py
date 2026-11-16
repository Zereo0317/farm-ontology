import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.nsidc_smap import NSIDC_SMAP_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = NSIDC_SMAP_URL
NOT_OPENED = "the field was not opened"
PERIOD = "April 2015"


class NsidcSmapTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "National Snow and Ice Data Center")
        self.assertEqual(header["product"], "Soil Moisture Active Passive Data (SMAP)")
        self.assertEqual(header["period"], PERIOD)
        self.assertEqual(header["unit"], NOT_OPENED)
        self.assertEqual(header["administrative_area"], "Global")
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Soil Moisture Active Passive Data")
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
            "July",
            "every two to three days",
            "days",
            "everywhere",
            "Earth",
            "Geographic",
            "radar",
            "Level-1",
            "CIRES",
            "Colorado",
            "DAAC",
            "NASA",
            "©",
            "2026",
            "frozen",
            "Advancing",
            "Policies",
            "JavaScript",
            "18:21:31",
            "licence",
            "license",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "nsidc_smap.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("https://nsidc.org/ is not the citation.", flat)
        self.assertIn("https://nsidc.org/data/smap/ is not the citation.", flat)
        self.assertIn("April 2015 is when the mission began operating.", flat)
        self.assertIn("July 2015 is the radar failure, not the period end.", flat)
        self.assertIn("every two to three days is a cadence, not the period.", flat)
        self.assertIn(
            "© 2026, National Snow and Ice Data Center - Advancing knowledge of Earth's frozen regions is a copyright line, not a licence grant.",
            flat,
        )
        self.assertIn("The header is not marked public domain.", flat)
        self.assertIn("Do not store a soil-moisture value.", flat)
        self.assertIn("A soil-moisture product is not a completed harvest.", flat)
        self.assertNotIn("July 2015", text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://nsidc.org/",
            "https://nsidc.org",
            "https://nsidc.org/data/smap/",
            "http://nsidc.org/data/smap",
            "https://smap.jpl.nasa.gov/",
            "https://example.com/nsidc.html",
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
            "July 2015",
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
            {"period": PERIOD},
            {"period": "July 2015"},
            {"period": "every two to three days"},
            {"period": NOT_OPENED},
            {"unit": NOT_OPENED},
            {"unit": "m3/m3"},
            {"administrative_area": "Global"},
            {"administrative_area": NOT_OPENED},
            {"administrative_area": "everywhere on Earth"},
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

    def test_field_save_does_not_ingest_nsidc(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("nsidc_smap", text)
            self.assertNotIn("nsidc.org/data/smap", text)
