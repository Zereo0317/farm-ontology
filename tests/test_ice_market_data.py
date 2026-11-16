import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.ice_market_data import ICE_MARKET_DATA_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = ICE_MARKET_DATA_URL
NOT_OPENED = "the field was not opened"


class IceMarketDataTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "ICE Futures Europe")
        self.assertEqual(header["product"], "Market Data Policy")
        self.assertEqual(header["period"], NOT_OPENED)
        self.assertEqual(header["unit"], NOT_OPENED)
        self.assertEqual(header["administrative_area"], NOT_OPENED)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Market Data Policy")
        self.assertFalse(header["permits_financial_use"])
        self.assertNotEqual(header["period"], "January 2026")
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
        for key in (
            "value",
            "price",
            "quote",
            "settlement",
            "trade",
            "figure",
            "copyright",
            "copyright_notice",
            "brent",
        ):
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
            "price",
            "quote",
            "Brent",
            "January 2026",
            "Version 4",
            "2025",
            "redistribut",
            "free of charge",
            "Intercontinental",
            "public domain",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "ice_market_data.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn(
            "Version 4 January 2026 is the policy version date, not a data period.",
            flat,
        )
        self.assertIn("names Brent under ICE Futures Europe (Commodities).", flat)
        self.assertIn(
            "This material may not be reproduced or redistributed in whole or in part without the express, prior written consent of Intercontinental Exchange, Inc.",
            flat,
        )
        self.assertIn(
            "© Copyright Intercontinental Exchange, Inc. 2025. All Rights Reserved.",
            flat,
        )
        self.assertIn("The policy is not marked public domain.", flat)
        self.assertIn(
            "These are available free of charge on ICE's website, see links below.",
            flat,
        )
        self.assertIn("That free end-of-day sentence is not a redistribution grant.", flat)
        self.assertIn("A quote page was not opened.", flat)
        self.assertIn("No settlement file was downloaded.", flat)
        self.assertIn("https://www.ice.com/ is not the citation.", flat)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://www.ice.com/",
            "https://www.ice.com/index",
            "https://example.com/ice.pdf",
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
            "price",
            "quote",
            "brent",
            "redistribution grant",
            "figure",
            "January 2026",
            "Version 4",
            "2025",
            "Settlement",
            "YIELD",
            "Trade",
            "Forecast",
            "Observation",
            "Completed Harvest",
            "Public Domain",
            "Benchmark",
            "Price",
            "Quote",
            "Brent",
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
            {"period": "January 2026"},
            {"unit": "USD"},
            {"administrative_area": "Europe"},
            {"value": 80.25},
            {"value": "Brent"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_ice(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("ice_market_data", text)
            self.assertNotIn("ICE_Futures_Europe_Market_Data_Policy", text)
