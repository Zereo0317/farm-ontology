import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.bls_cpi_food_energy import (
    BLS_CPI_FOOD_ENERGY_URL,
    record_series_header,
)

ROOT = Path(__file__).resolve().parents[1]
URL = BLS_CPI_FOOD_ENERGY_URL


class BlsCpiFoodEnergyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_an_index_level(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "U.S. Bureau of Labor Statistics")
        self.assertEqual(header["product"], "Consumer Price Index, food and energy")
        self.assertEqual(
            header["period"],
            "monthly program; the start month of the current food and energy item "
            "codes was not read from cu.series; the CPI handbook says BLS began "
            "publishing city indexes in 1919, began regular publication of the U.S. "
            "city average in 1921, and estimated that national index back to 1913; "
            "it also says the 1913-21 national extension used food prices only; that "
            "is program history, not a claim that today's food and energy series "
            "codes are continuous from 1913",
        )
        self.assertEqual(
            header["unit"],
            "CPI for all urban consumers, including all items, food, and energy; the "
            "publication-level appendix lists item code SA0 for all items and SA0E "
            "for energy, both published for the U.S. city average; food is a "
            "published major group; these are consumer prices, not commodity export "
            "prices; no index level is stored",
        )
        self.assertEqual(
            header["administrative_area"],
            "U.S. city average; not a farm price and not an export price",
        )
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "index")
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
        self.assertIn(
            "not a claim that today's food and energy series codes are continuous from 1913",
            header["period"],
        )
        for key in ("value", "price", "index_level", "forecast", "observation"):
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
            record_series_header(self.folder, citation_url="https://example.com/cpi.xlsx")
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

    def test_field_save_does_not_ingest_the_cpi(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("bls_cpi_food_energy", text)
            self.assertNotIn("bls.gov/cpi", text)
