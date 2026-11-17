import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology import printed_intervals
from farm_ontology.policy import CLASS_C_POLICY


def _citations() -> dict:
    return {row["source"]: row["citation_url"] for row in printed_intervals.INTERVALS}


class PrintedIntervalsTest(unittest.TestCase):
    def test_stores_the_printed_intervals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "intervals.json"
            printed_intervals.record_printed_intervals(path, _citations())
            statement = json.loads(path.read_text(encoding="utf-8"))

        by_source = {row["source"]: row for row in statement["intervals"]}
        self.assertEqual(by_source["BPA balancing file"]["interval"], "5-minute readings")
        self.assertEqual(
            by_source["USGS instantaneous streamflow"]["interval"],
            "15-minute record, hourly transmission",
        )
        self.assertEqual(
            by_source["JMA national daily table"]["interval"],
            "updated about 40 minutes past each hour",
        )
        self.assertEqual(by_source["JMA national daily table"]["printed"], "更新時刻は、毎時40分頃です。")
        self.assertEqual(by_source["SMAP temporal resolution"]["interval"], "1 day")
        self.assertEqual(by_source["USDA NASS Crop Progress"]["interval"], "weekly")
        self.assertEqual(by_source["Sentinel-2 revisit"]["interval"], "5 days at the Equator")
        self.assertEqual(by_source["World Bank Pink Sheet"]["interval"], "monthly")
        self.assertEqual(by_source["Conab soy series"]["interval"], "crop year")
        self.assertEqual(
            by_source["Conab soy series"]["note"],
            "The 2026/27 column is a forecast, not completed output.",
        )
        self.assertEqual(
            by_source["EIA Weekly Petroleum Status Report"]["interval"],
            "weekly",
        )
        self.assertFalse(statement["permits_financial_use"])
        self.assertEqual(statement["class_c_policy"], CLASS_C_POLICY)
        self.assertNotIn("price", statement)
        for row in statement["intervals"]:
            self.assertNotIn("price", row)
            self.assertNotIn("trade", row)

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "intervals.json"
            with self.assertRaises(ValueError):
                printed_intervals.record_printed_intervals(path, None)
            with self.assertRaises(ValueError):
                printed_intervals.record_printed_intervals(path, {})
            partial = _citations()
            partial.pop("World Bank Pink Sheet")
            with self.assertRaises(ValueError):
                printed_intervals.record_printed_intervals(path, partial)
            self.assertFalse(path.exists())

    def test_other_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "intervals.json"
            swapped = _citations()
            swapped["World Bank Pink Sheet"] = swapped["World Bank Pink Sheet"] + "/"
            with self.assertRaises(ValueError):
                printed_intervals.record_printed_intervals(path, swapped)
            self.assertFalse(path.exists())

    def test_slow_series_are_not_a_fast_feed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "intervals.json"
            for source in (
                "World Bank Pink Sheet",
                "Conab soy series",
                "USDA NASS Crop Progress",
                "EIA Weekly Petroleum Status Report",
            ):
                for feed in ("5-minute", "hourly", "5-minute readings"):
                    with self.assertRaises(ValueError):
                        printed_intervals.record_printed_intervals(
                            path,
                            _citations(),
                            source=source,
                            feed=feed,
                        )
            self.assertFalse(path.exists())

    def test_trade_is_refused_while_financial_use_is_false(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "intervals.json"
            for source in _citations():
                with self.assertRaises(ValueError):
                    printed_intervals.record_printed_intervals(
                        path,
                        _citations(),
                        source=source,
                        label="trade",
                        permits_financial_use=False,
                    )
            with self.assertRaises(ValueError):
                printed_intervals.record_printed_intervals(
                    path,
                    _citations(),
                    price="not stored",
                    permits_financial_use=False,
                )
            self.assertFalse(path.exists())
            source = Path(printed_intervals.__file__).read_text(encoding="utf-8")
            self.assertNotIn("10.7900", source)
            self.assertNotIn("181616.6", source)
            self.assertNotIn("field_save", source)


if __name__ == "__main__":
    unittest.main()
