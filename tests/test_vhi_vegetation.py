import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.vhi_vegetation import VHI_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = VHI_URL
NOT_OPENED = "the field was not opened"
PERIOD = "1981 to the present"


class VhiVegetationTests(unittest.TestCase):
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
            "NOAA Center for Satellite Applications and Research",
        )
        self.assertEqual(
            header["product"],
            "STAR - Global Vegetation Health Products: Introduction",
        )
        self.assertEqual(header["period"], PERIOD)
        self.assertEqual(header["unit"], NOT_OPENED)
        self.assertEqual(header["administrative_area"], NOT_OPENED)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Vegetation Health Indices (VHI)")
        self.assertNotEqual(header["kind"], "index value")
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
            "index value",
            "figure",
            "2012",
            "1982",
            "1994",
            "1995",
            "2019",
            "2026",
            "July",
            "September",
            "February",
            "4 km",
            "7-day",
            "1km",
            "16km",
            "km",
            "VIIRS",
            "AVHRR",
            "Drought",
            "United States",
            "placeholder",
            "experimental",
            "operational",
            "official",
            "NESDIS",
            "Commerce",
            "Oceanic",
            "Atmospheric",
            "Province",
            "Country",
            "4,000",
            "disclaimer",
            "JavaScript",
            "licence",
            "license",
            "grant",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "vhi_vegetation.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("https://www.star.nesdis.noaa.gov/ is not the citation.", flat)
        self.assertIn(
            "https://www.star.nesdis.noaa.gov/smcd/emb/vci/VH/ is not the citation.",
            flat,
        )
        self.assertIn(
            "2012 is the VIIRS start, not a replacement for 1981 to the present.",
            flat,
        )
        self.assertIn(
            "September 1994 through February 1995 is a gap, not the period.",
            flat,
        )
        self.assertIn("4 km and 7-day are resolution, not the unit.", flat)
        self.assertIn(
            "Data and images displayed on STAR sites are provided for experimental use only and are not official operational NOAA products.",
            flat,
        )
        self.assertIn("That notice is not a grant.", flat)
        self.assertIn(
            "The United States map alt is a placeholder, not the area.",
            flat,
        )
        self.assertIn("The header is not marked public domain.", flat)
        self.assertIn("Do not store an index value.", flat)
        self.assertIn("A vegetation index is not a completed harvest.", flat)
        self.assertIn("index.php", text)
        self.assertNotIn("index value", text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://www.star.nesdis.noaa.gov/",
            "https://www.star.nesdis.noaa.gov",
            "https://www.star.nesdis.noaa.gov/smcd/emb/vci/VH/",
            "https://www.star.nesdis.noaa.gov/smcd/emb/vci/VH/index.html",
            "http://www.star.nesdis.noaa.gov/smcd/emb/vci/VH/index.php",
            "https://star.nesdis.noaa.gov/smcd/emb/vci/VH/index.php",
            "https://www.star.nesdis.noaa.gov/smcd/emb/vci/VH/index.php/",
            "https://example.com/vhi.html",
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
            "index value",
            "vegetation index",
            "experimental use",
            "figure",
            "2012",
            "4 km",
            "1994",
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
            "Index Value",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_replaced_fields_and_figures_write_nothing(self):
        attempts = (
            {"period": PERIOD},
            {"period": "2012"},
            {"period": "from 2012 to present"},
            {"period": "since 1982"},
            {"period": "since 2012"},
            {"period": "September 1994 through February 1995"},
            {"period": "30 July 2019"},
            {"period": NOT_OPENED},
            {"unit": NOT_OPENED},
            {"unit": "4 km"},
            {"unit": "7-day"},
            {"unit": "1km"},
            {"unit": "% Drought Area"},
            {"administrative_area": NOT_OPENED},
            {"administrative_area": "Global"},
            {"administrative_area": "United States"},
            {"administrative_area": "Country"},
            {"administrative_area": "Province"},
            {"value": 4},
            {"value": "index value"},
            {"value": "price"},
            {"permits_financial_use": True},
            {"permits_financial_use": "true"},
            {"permits_financial_use": False},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_vhi(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("vhi_vegetation", text)
            self.assertNotIn("star.nesdis.noaa.gov/smcd/emb/vci/VH", text)
