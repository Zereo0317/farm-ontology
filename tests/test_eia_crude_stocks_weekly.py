import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology import eia_crude_stocks_weekly
from farm_ontology.policy import CLASS_C_POLICY

LIVE_BODY = """
<title>Weekly U.S. Ending Stocks excluding SPR of Crude Oil  (Thousand Barrels)</title>
<p>Release Date: 11/12/2026</p>
<p>Next Release Date: 11/18/2026</p>
<table>
<tr><td>Year-Month</td><td>Week 1</td><td></td><td>Week 2</td></tr>
<tr><td>End Date</td><td>Value</td><td>End Date</td><td>Value</td></tr>
<tr><td>2026-Oct</td><td>10/30</td><td>409,760</td></tr>
<tr><td>2026-Nov</td><td>11/06</td><td>414,417</td><td></td><td></td></tr>
</table>
"""


class EiaCrudeStocksWeeklyTest(unittest.TestCase):
    def test_stores_the_latest_printed_week(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "crude-stocks.json"
            eia_crude_stocks_weekly.record_eia_crude_stocks_weekly(
                path,
                eia_crude_stocks_weekly.EIA_STOCKS_URL,
                LIVE_BODY,
            )
            stored = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            stored,
            {
                "series": "Weekly U.S. Ending Stocks excluding SPR of Crude Oil (Thousand Barrels)",
                "year_month": "2026-Nov",
                "week": "11/06",
                "value": "414,417",
                "unit": "Thousand Barrels",
                "kind": "stock level",
                "citation_url": eia_crude_stocks_weekly.EIA_STOCKS_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(stored)
        self.assertNotIn("409,760", text)
        self.assertNotIn("10/30", text)
        self.assertNotIn("11/12", text)
        self.assertNotIn("11/18", text)
        self.assertNotIn("5-minute", text)
        self.assertNotIn("hourly", text)

    def test_week_ending_6_november_2026_is_a_stock_level_not_a_price(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "crude-stocks.json"
            eia_crude_stocks_weekly.record_eia_crude_stocks_weekly(
                path,
                eia_crude_stocks_weekly.EIA_STOCKS_URL,
                LIVE_BODY,
            )
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(stored["year_month"], "2026-Nov")
            self.assertEqual(stored["week"], "11/06")
            self.assertEqual(stored["value"], "414,417")
            self.assertEqual(stored["unit"], "Thousand Barrels")
            self.assertEqual(stored["kind"], "stock level")
            self.assertNotIn("price", stored)
            self.assertNotIn("trade", stored)
            self.assertFalse(stored["permits_financial_use"])
            self.assertFalse((folder / "trade.json").exists())
            for label in ("price", "trade"):
                rejected = folder / "rejected.json"
                with self.assertRaises(ValueError):
                    eia_crude_stocks_weekly.record_eia_crude_stocks_weekly(
                        rejected,
                        eia_crude_stocks_weekly.EIA_STOCKS_URL,
                        LIVE_BODY,
                        label=label,
                    )
                self.assertFalse(rejected.exists())

    def test_failed_request_or_empty_body_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "crude-stocks.json"
            with self.assertRaises(ValueError):
                eia_crude_stocks_weekly.record_eia_crude_stocks_weekly(
                    path,
                    eia_crude_stocks_weekly.EIA_STOCKS_URL,
                    LIVE_BODY,
                    request_failed=True,
                )
            with self.assertRaises(ValueError):
                eia_crude_stocks_weekly.record_eia_crude_stocks_weekly(
                    path,
                    eia_crude_stocks_weekly.EIA_STOCKS_URL,
                    None,
                )
            self.assertFalse(path.exists())

    def test_missing_value_writes_nothing(self) -> None:
        missing = LIVE_BODY.replace("<td>414,417</td>", "<td></td>", 1).replace(
            "<td>409,760</td>", "<td></td>", 1
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "crude-stocks.json"
            with self.assertRaises(ValueError):
                eia_crude_stocks_weekly.record_eia_crude_stocks_weekly(
                    path,
                    eia_crude_stocks_weekly.EIA_STOCKS_URL,
                    missing,
                )
            self.assertFalse(path.exists())

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "crude-stocks.json"
            with self.assertRaises(ValueError):
                eia_crude_stocks_weekly.record_eia_crude_stocks_weekly(path, None, LIVE_BODY)
            with self.assertRaises(ValueError):
                eia_crude_stocks_weekly.record_eia_crude_stocks_weekly(
                    path,
                    eia_crude_stocks_weekly.EIA_STOCKS_URL + "&x=1",
                    LIVE_BODY,
                )
            self.assertFalse(path.exists())

    def test_fast_feed_label_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "crude-stocks.json"
            for label in ("5-minute", "hourly"):
                with self.assertRaises(ValueError):
                    eia_crude_stocks_weekly.record_eia_crude_stocks_weekly(
                        path,
                        eia_crude_stocks_weekly.EIA_STOCKS_URL,
                        LIVE_BODY,
                        label=label,
                    )
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
