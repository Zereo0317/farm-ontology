import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import jma_forecast_reading
from farm_ontology.jma_daily import JMA_DAILY_URL
from farm_ontology.jma_daily import record_series_header as record_daily_header
from farm_ontology.jma_local import JMA_LOCAL_URL, record_series_header
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
FETCHED = (
    "<title>気象庁｜統合地図ページ</title>"
    "<p>申し訳ございません。ページの読み込みに失敗しました。</p>"
    "<p>N o w &nbsp; L o a d i n g . . .</p>"
    '<script>{"天気予報":"Daily Forecasts","東京":"Tokyo","札幌":"Sapporo"}</script>'
)
ONE = "Sample Reach forecast is 3."
TWO = "Sample Reach forecast is 3. Other Reach forecast is 4."


class JmaForecastReadingTests(unittest.TestCase):
    def test_headers_still_reject_a_figure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaises(ValueError):
                record_series_header(folder, citation_url=JMA_LOCAL_URL, value="3")
            with self.assertRaises(ValueError):
                record_daily_header(folder, citation_url=JMA_DAILY_URL, value="3")
            self.assertEqual(list(folder.iterdir()), [])

    def test_fetched_pages_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jma-forecast-reading.json"
            for body in (FETCHED, ""):
                with self.assertRaises(ValueError):
                    jma_forecast_reading.record_forecast_reading(
                        path,
                        JMA_LOCAL_URL,
                        body,
                        source_url=JMA_DAILY_URL,
                    )
            self.assertFalse(path.exists())

    def test_one_printed_value_is_stored_as_a_forecast(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jma-forecast-reading.json"
            jma_forecast_reading.record_forecast_reading(
                path,
                JMA_LOCAL_URL,
                ONE,
                source_url=JMA_DAILY_URL,
            )
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["value"], "3")
        self.assertEqual(stored["administrative_area"], "Sample Reach")
        self.assertEqual(stored["kind"], "forecast")
        self.assertEqual(stored["citation_url"], JMA_LOCAL_URL)
        self.assertEqual(stored["forecast_page"], JMA_DAILY_URL)
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertNotIn("permits_financial_use_test", stored)
        text = json.dumps(stored)
        for leftover in ("Hokkaido", "Sapporo", "Tokyo", "rainfall", "trade", "harvest"):
            self.assertNotIn(leftover, text)

    def test_two_values_or_another_page_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jma-forecast-reading.json"
            with self.assertRaises(ValueError):
                jma_forecast_reading.record_forecast_reading(
                    path,
                    JMA_LOCAL_URL,
                    TWO,
                    source_url=JMA_DAILY_URL,
                )
            with self.assertRaises(ValueError):
                jma_forecast_reading.record_forecast_reading(
                    path,
                    JMA_DAILY_URL,
                    ONE,
                    source_url=JMA_DAILY_URL,
                )
            self.assertFalse(path.exists())

    def test_trade_or_open_class_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jma-forecast-reading.json"
            for label in ("trade", "completed harvest", "temperature", "12.5"):
                with self.assertRaises(ValueError):
                    jma_forecast_reading.record_forecast_reading(
                        path,
                        JMA_LOCAL_URL,
                        ONE,
                        source_url=JMA_DAILY_URL,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                jma_forecast_reading.record_forecast_reading(
                    path,
                    JMA_LOCAL_URL,
                    ONE,
                    source_url=JMA_DAILY_URL,
                    permits_financial_use=True,
                )
            with self.assertRaises(ValueError):
                jma_forecast_reading.record_forecast_reading(
                    path,
                    JMA_LOCAL_URL,
                    ONE,
                    source_url=JMA_DAILY_URL,
                    class_c_policy="open",
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_reading(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("jma_forecast_reading", text)
            self.assertNotIn("jma_daily", text)
            self.assertNotIn("jma_local", text)


if __name__ == "__main__":
    unittest.main()
