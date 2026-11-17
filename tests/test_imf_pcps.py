import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.imf_pcps import IMF_PCPS_URL, record_series_header
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
URL = IMF_PCPS_URL


class ImfPcpsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_price_or_index_level(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "International Monetary Fund")
        self.assertEqual(header["product"], "Primary Commodity Price System")
        self.assertEqual(
            header["period"],
            "the FAQ, last updated 21 November 2025, says tables are annual, "
            "quarterly, monthly, and weekly; monthly figures are updated in the "
            "first full week of the month; the FAQ says some prices start in 1980 "
            "and index coverage starts in 1992; the technical note says the "
            "all-commodity index starts in January 1992",
        )
        self.assertEqual(
            header["unit"],
            "benchmark prices and indexes for energy, agriculture, fertilizers, and "
            "metals, as the IMF names them; the all-commodity index is monthly, "
            "quarterly, and annual, weighted by 2014-2016 world import shares, and "
            "is 2016=100; group indexes include food, agricultural raw materials, "
            "industrial inputs (agricultural raw materials and metals), and fuel; "
            "the petroleum index is the simple average of Dated Brent, West Texas "
            "Intermediate, and Dubai Fateh; no price and no index level is stored",
        )
        self.assertEqual(
            header["administrative_area"],
            "the published commodity indexes; the FAQ also describes a commodity "
            "terms-of-trade database for 182 economies from 1962, and that database "
            "is not stored here",
        )
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "compilation")
        self.assertFalse(header["permits_financial_use"])
        self.assertIn("11 October 2024", header["copyright_statement"])
        self.assertIn("only partly rendered", header["copyright_statement"])
        self.assertIn("benchmark prices", header["unit"])
        self.assertIn("terms-of-trade", header["administrative_area"])
        for key in (
            "value",
            "price",
            "index_level",
            "forecast",
            "observation",
            "benchmark",
            "trade",
        ):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "settlement",
            "yield",
            "forecast",
            "observation",
            "completed harvest",
            "public domain",
        ):
            self.assertNotIn(word, text)
        self.assertIn("only partly rendered", text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        with self.assertRaises(ValueError):
            record_series_header(self.folder, citation_url="https://example.com/pcps.xlsx")
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

    def test_field_save_does_not_ingest_the_pcps(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("imf_pcps", text)
            self.assertNotIn("np/res/commod", text)

    def test_reading_the_stored_record_writes_no_trade(self):
        saved = record_series_header(self.folder, citation_url=URL)
        path = self.folder / saved["file"]
        before = path.read_text(encoding="utf-8")
        names_before = sorted(item.name for item in self.folder.iterdir())
        record = json.loads(before)
        after = path.read_text(encoding="utf-8")
        names_after = sorted(item.name for item in self.folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names_after, names_before)
        self.assertEqual(names_after, ["pcps.json"])
        self.assertIs(record["permits_financial_use"], False)
        self.assertEqual(CLASS_C_POLICY, "closed")
        self.assertNotIn("trade", record)
        self.assertNotIn("value", record)
        self.assertNotIn("price", record)
        self.assertNotIn("index_level", record)
        self.assertFalse((self.folder / "trade.json").exists())
