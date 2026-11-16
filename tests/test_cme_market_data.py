import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.cme_market_data import CME_MARKET_DATA_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = CME_MARKET_DATA_URL


class CmeMarketDataTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_settlement_or_trade(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "CME Group")
        self.assertEqual(header["product"], "listed contracts and historical market data")
        self.assertEqual(
            header["period"],
            "trading-day settlements, plus delayed and real-time feeds under license; "
            "an official production page stating the first stored day was not opened; "
            "a CME client wiki in a space named EPICSANDBOX says DataMine end-of-day "
            "and time-and-sales history runs from 1 January 1982 or from contract "
            "inception if later; because that page is a sandbox wiki, the 1982 date "
            "is not treated as confirmed",
        )
        self.assertEqual(
            header["unit"],
            "the exchange publishes settlement and trade information for the contracts "
            "used to compare these markets, including NYMEX crude oil and CBOT grain "
            "and oilseed futures; this pass did not open a contract specification or "
            "copy a settlement; no settlement and no trade is stored",
        )
        self.assertEqual(
            header["administrative_area"],
            "the listed contracts named on the licensing pages; not a stored position",
        )
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "catalog")
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
        self.assertIn("not treated as confirmed", header["period"])
        self.assertIn("no settlement and no trade is stored", header["unit"])
        for key in (
            "value",
            "price",
            "settlement",
            "trade",
            "index_level",
            "forecast",
            "observation",
            "confirmed",
            "start_date",
        ):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "yield",
            "forecast",
            "observation",
            "completed harvest",
            "public domain",
            "benchmark",
            "price",
            "trading right",
        ):
            self.assertNotIn(word, text)
        self.assertNotIn("1982 date is confirmed", text)
        self.assertNotIn("january-2025-non-display-policy-faq.pdf", text)
        self.assertNotIn("market-data-policy-education-center.html", text)
        source = (ROOT / "farm_ontology" / "cme_market_data.py").read_text(encoding="utf-8")
        self.assertIn(
            "https://www.cmegroup.com/market-data/license-data/files/january-2025-non-display-policy-faq.pdf",
            source,
        )
        self.assertIn(
            "https://www.cmegroup.com/market-data/license-data/market-data-policy-education-center.html",
            source,
        )
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://www.cmegroup.com/market-data/license-data/files/january-2025-non-display-policy-faq.pdf",
            "https://www.cmegroup.com/market-data/license-data/market-data-policy-education-center.html",
            "https://example.com/cme.xlsx",
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
            "1982",
            "1982 confirmed",
            "confirmed 1982",
            "1 January 1982",
            "Settlement",
            "YIELD",
            "Trade",
            "Forecast",
            "Observation",
            "Completed Harvest",
            "Public Domain",
            "Benchmark",
            "1982 Confirmed",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_cme(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("cme_market_data", text)
            self.assertNotIn("historical-information-distribution", text)
