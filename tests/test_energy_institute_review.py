import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.energy_institute_review import (
    ENERGY_INSTITUTE_REVIEW_URL,
    record_series_header,
)

ROOT = Path(__file__).resolve().parents[1]
URL = ENERGY_INSTITUTE_REVIEW_URL


class EnergyInstituteReviewTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_quantity_or_price(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(
            header["publisher"],
            "Energy Institute, with Ember as co-author of the current edition. "
            "Previously published by bp. The Institute has been custodian since 2023.",
        )
        self.assertEqual(header["product"], "Statistical Review of World Energy")
        self.assertEqual(
            header["period"],
            "annual, covering the prior year; the Institute's site says the review "
            "has been published since 1952; the tables on display cover 2015-2025; "
            "the site says downloadable Excel goes back to 1965 for many sectors; "
            "the PDF opened is the 74th edition; the Excel workbook was not opened, "
            "so 1965 is the site's claim, not a span counted in the workbook",
        )
        self.assertEqual(
            header["unit"],
            "annual production, consumption, trade, refining, and prices for oil, "
            "oil products, gas, coal, nuclear, hydro, and renewables, plus total "
            "energy and carbon dioxide emissions; the edition page says more than "
            "50 countries and 12 regions; no quantity and no price is stored",
        )
        self.assertEqual(
            header["administrative_area"],
            "the review's published country and region tables; the PDF's reserves "
            "note says proved-reserve figures are a compilation, not a single SEC "
            "definition, and that countries use different methods",
        )
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "compilation")
        self.assertFalse(header["permits_financial_use"])
        for key in ("value", "quantity", "price", "forecast", "observation", "settlement"):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "settlement",
            "yield",
            "forecast",
            "observation",
            "completed harvest",
            "public domain",
            "benchmark",
            "Creative Commons",
            "CC BY",
        ):
            self.assertNotIn(word, text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        with self.assertRaises(ValueError):
            record_series_header(self.folder, citation_url="https://example.com/review.xlsx")
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

    def test_field_save_does_not_ingest_the_review(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("energy_institute_review", text)
            self.assertNotIn("energyinst.org/statistical-review", text)
