import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import usda_wasde_forecast
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]

REPORT = """
                              Million Metric Tons
================================================================================
                                          Total                 Total     Ending
Commodity                     Output     Supply   Trade 2/     Use 3/     Stocks
================================================================================

                                      World
Total Grains 4/
    2024/25                  2858.10    3653.95     500.19    2877.60     776.35
    2025/26 (Est.)           3022.84    3799.19     549.88    2971.36     827.82
    2026/27 (Proj.)
                      Oct    2944.32    3768.52     524.23    2980.67     787.84
                      Nov    2949.56    3777.38     524.28    2980.52     796.86
Wheat
    2024/25                   799.02    1068.90     210.86     808.47     260.42
    2025/26 (Est.)            844.03    1104.45     226.03     821.59     282.86
    2026/27 (Proj.)
                      Oct     822.39    1103.94     208.97     827.90     276.04
                      Nov     827.51    1110.36     208.66     829.55     280.82
Coarse Grains 5/
                                  United States
Wheat
    2026/27 (Proj.)
                      Nov      41.74      70.73      20.41      30.10      20.22
"""


class UsdaWasdeForecastTests(unittest.TestCase):
    def _record(self, path: Path, body: str = REPORT) -> None:
        usda_wasde_forecast.record_wasde_forecast(
            path,
            usda_wasde_forecast.REPORT_URL,
            body,
        )

    def test_stores_the_printed_world_wheat_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "world-wheat-output-forecast.json"
            self._record(path)
            stored = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            stored,
            {
                "series": "Wheat",
                "area": "World",
                "item": "Output",
                "period": "2026/27 (Proj.)",
                "month": "Nov",
                "value": 827.51,
                "unit": "Million Metric Tons",
                "kind": "published_forecast",
                "citation_url": usda_wasde_forecast.REPORT_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertEqual(stored["kind"], "published_forecast")
        self.assertNotEqual(stored["kind"], "completed harvest")
        self.assertIsInstance(stored["value"], float)
        self.assertEqual(json.dumps(stored["value"]), "827.51")
        text = json.dumps(stored)
        self.assertNotIn("208.66", text)
        self.assertNotIn("822.39", text)
        self.assertNotIn("41.74", text)
        self.assertNotIn("2949.56", text)
        self.assertNotIn("trade", text)
        self.assertNotIn("price", text)
        self.assertNotIn("harvest", text)

    def test_reading_the_stored_record_writes_no_trade_while_permits_financial_use_is_false(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "world-wheat-output-forecast.json"
            self._record(path)
            before = path.read_text(encoding="utf-8")
            names_before = sorted(item.name for item in folder.iterdir())
            stored = json.loads(before)
            after = path.read_text(encoding="utf-8")
            names_after = sorted(item.name for item in folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names_after, names_before)
        self.assertEqual(names_after, ["world-wheat-output-forecast.json"])
        self.assertFalse((folder / "trade.json").exists())
        self.assertEqual(stored["series"], "Wheat")
        self.assertEqual(stored["area"], "World")
        self.assertEqual(stored["item"], "Output")
        self.assertEqual(stored["period"], "2026/27 (Proj.)")
        self.assertEqual(stored["month"], "Nov")
        self.assertEqual(stored["value"], 827.51)
        self.assertEqual(stored["kind"], "published_forecast")
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], "closed")
        self.assertNotIn("trade", stored)
        self.assertNotIn("price", stored)
        self.assertNotIn("harvest", stored)
        self.assertNotIn("trade", after)
        self.assertNotIn("208.66", after)
        self.assertNotIn("price", after)
        self.assertNotIn("harvest", after)

    def test_missing_citation_or_failed_request_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "world-wheat-output-forecast.json"
            with self.assertRaises(ValueError):
                usda_wasde_forecast.record_wasde_forecast(
                    path,
                    usda_wasde_forecast.REPORT_URL,
                    REPORT,
                    request_failed=True,
                )
            with self.assertRaises(ValueError):
                usda_wasde_forecast.record_wasde_forecast(path, None, REPORT)
            with self.assertRaises(ValueError):
                usda_wasde_forecast.record_wasde_forecast(path, "   ", REPORT)
            with self.assertRaises(ValueError):
                usda_wasde_forecast.record_wasde_forecast(
                    path,
                    usda_wasde_forecast.REPORT_URL,
                    None,
                )
            with self.assertRaises(ValueError):
                usda_wasde_forecast.record_wasde_forecast(
                    path,
                    usda_wasde_forecast.REPORT_URL,
                    "   ",
                )
            self.assertFalse(path.exists())

    def test_other_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "world-wheat-output-forecast.json"
            for citation in (
                "https://www.usda.gov/oce/commodity-markets/wasde",
                "https://www.usda.gov/oce/commodity/wasde/wasde1126.pdf",
                "https://www.usda.gov/oce/commodity/wasde/wasde1026.txt",
            ):
                with self.assertRaises(ValueError):
                    usda_wasde_forecast.record_wasde_forecast(path, citation, REPORT)
            self.assertFalse(path.exists())

    def test_report_without_the_projection_writes_nothing(self) -> None:
        missing_nov = REPORT.replace(
            "                      Nov     827.51    1110.36     208.66     829.55     280.82\n",
            "",
            1,
        )
        self.assertNotIn("827.51", missing_nov)
        self.assertIn("41.74", missing_nov)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "world-wheat-output-forecast.json"
            with self.assertRaises(ValueError):
                self._record(path, missing_nov)
            self.assertFalse(path.exists())

    def test_price_trade_or_completed_harvest_label_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "world-wheat-output-forecast.json"
            for label in (
                "price",
                "trade",
                "completed harvest",
                "harvest",
                "Price",
                "TRADE",
            ):
                with self.assertRaises(ValueError):
                    usda_wasde_forecast.record_wasde_forecast(
                        path,
                        usda_wasde_forecast.REPORT_URL,
                        REPORT,
                        label=label,
                    )
            self.assertFalse(path.exists())

    def test_financial_use_or_open_class_c_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "world-wheat-output-forecast.json"
            with self.assertRaises(ValueError):
                usda_wasde_forecast.record_wasde_forecast(
                    path,
                    usda_wasde_forecast.REPORT_URL,
                    REPORT,
                    permits_financial_use=True,
                )
            with self.assertRaises(ValueError):
                usda_wasde_forecast.record_wasde_forecast(
                    path,
                    usda_wasde_forecast.REPORT_URL,
                    REPORT,
                    class_c_policy="open",
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_forecast(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("usda_wasde_forecast", text)
            self.assertNotIn("wasde1126", text)


if __name__ == "__main__":
    unittest.main()
