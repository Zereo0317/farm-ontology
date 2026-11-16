import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.csd_industrial import CSD_INDUSTRIAL_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = CSD_INDUSTRIAL_URL
NOT_OPENED = "the field was not opened"


class CsdIndustrialTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Census and Statistics Department")
        self.assertEqual(
            header["product"],
            "Index of Industrial Production for Manufacturing and Waste Management Sectors",
        )
        self.assertEqual(header["period"], NOT_OPENED)
        self.assertEqual(header["unit"], NOT_OPENED)
        self.assertEqual(header["administrative_area"], NOT_OPENED)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "index")
        self.assertFalse(header["permits_financial_use"])
        self.assertNotIn("(", header["product"])
        self.assertNotIn("Energy Supply", header["product"])
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
        for key in ("value", "price", "index_level", "index_value", "figure", "copyright"):
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
            "trading right",
            "quantity of goods",
            "610-65001",
            "Energy Supply",
            "Web Table",
            "copyright",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "csd_industrial.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("Manufacturing, Energy Supply and Waste Management", flat)
        self.assertIn("https://www.censtatd.gov.hk/en/", flat)
        self.assertIn("parenthetical figure on the product line was not copied", flat)
        self.assertIn("Web Table", flat)
        self.assertIn("610-65001 was not printed as a title", flat)
        self.assertIn("copyright sentence were not opened", flat)
        self.assertIn("bulk history file was not opened", flat)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://www.censtatd.gov.hk/en/",
            "https://example.com/csd.html",
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
            "observation",
            "completed harvest",
            "public domain",
            "benchmark",
            "quantity of goods",
            "trading right",
            "figure",
            "610-65001",
            "3.2",
            "(5.1)",
            "Settlement",
            "YIELD",
            "Trade",
            "Forecast",
            "Observation",
            "Completed Harvest",
            "Public Domain",
            "Benchmark",
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
            {"period": "September 2026"},
            {"unit": "2022-23"},
            {"administrative_area": "Hong Kong"},
            {"value": 101.4},
            {"value": "610-65001"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_csd(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("csd_industrial", text)
            self.assertNotIn("scode310", text)
