import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.fao_food_price_index import FAO_FOOD_PRICE_INDEX_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = FAO_FOOD_PRICE_INDEX_URL


class FaoFoodPriceIndexTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_an_index_level(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(
            header["publisher"],
            "Food and Agriculture Organization of the United Nations",
        )
        self.assertEqual(header["product"], "Food Price Index")
        self.assertEqual(
            header["period"],
            "monthly; the page opened was the 6 November 2026 release; "
            "the official monthly nominal index runs from 1990; "
            "the 1961 annual file is a spliced extension and is not the same "
            "object as the post-1990 price index",
        )
        self.assertEqual(
            header["unit"],
            "an index; five group indexes are cereals, vegetable oils, dairy, meat, "
            "and sugar, weighted by average export shares for 2014-2016; "
            "no index level is stored",
        )
        self.assertEqual(
            header["administrative_area"],
            "an international export-price basket; not a country, not a retail price, "
            "and not a farm",
        )
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "index")
        self.assertFalse(header["permits_financial_use"])
        for key in ("value", "level", "index_level", "price", "vintage"):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "settlement",
            "yield",
            "trade",
            "observation",
            "public domain",
            "completed harvest",
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
            record_series_header(
                self.folder,
                citation_url="https://example.com/fao-food-price-index.xlsx",
            )
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "settlement",
            "yield",
            "trade",
            "retail price",
            "futures settlement",
            "observation",
            "public domain",
            "completed harvest",
            "Settlement",
            "YIELD",
            "Retail Price",
            "Futures Settlement",
            "Observation",
            "Public Domain",
            "Completed Harvest",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_food_price_index(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("fao_food_price_index", text)
            self.assertNotIn("foodpricesindex", text)
