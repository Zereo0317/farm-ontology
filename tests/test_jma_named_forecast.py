import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.jma_local import JMA_LOCAL_URL, record_series_header
from farm_ontology.jma_named_forecast import record_named_forecast
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
FETCHED = (
    '"015000":"Iburi Hidaka Region"'
    '<a href="https://www.jma.go.jp/bosai/map.html">Nationwide information</a>'
)
ONE_LINK = '<a href="https://www.jma.go.jp/bosai/forecast/hidaka.html">日高</a>'
ONE_PAGE = "日高 forecast is 7 for 18 November 2026"
TWO_PAGE = (
    "日高 forecast is 7 for 18 November 2026. "
    "日高 forecast is 9 for 19 November 2026"
)
FOLLOWED = "https://www.jma.go.jp/bosai/forecast/hidaka.html"


class JmaNamedForecastTests(unittest.TestCase):
    def test_header_still_rejects_a_figure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaises(ValueError):
                record_series_header(
                    folder,
                    citation_url=JMA_LOCAL_URL,
                    value="7",
                )
            self.assertEqual(list(folder.iterdir()), [])

    def test_fetched_page_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jma-named-forecast.json"
            with self.assertRaises(ValueError) as caught:
                record_named_forecast(path, JMA_LOCAL_URL, FETCHED)
            self.assertIn("no link naming", str(caught.exception))
            self.assertFalse(path.exists())

    def test_one_printed_forecast_keeps_area_period_and_url(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jma-named-forecast.json"
            record_named_forecast(
                path,
                JMA_LOCAL_URL,
                ONE_LINK,
                followed_url=FOLLOWED,
                followed_body=ONE_PAGE,
            )
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["value"], "7")
        self.assertEqual(stored["area"], "日高")
        self.assertEqual(stored["period"], "18 November 2026")
        self.assertEqual(stored["citation_url"], FOLLOWED)
        self.assertEqual(stored["kind"], "forecast")
        self.assertEqual(stored["label"], "forecast")
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertNotIn("permits_financial_use_test", stored)
        text = json.dumps(stored)
        for leftover in ("015000", "trade", "harvest", "latitude", "longitude"):
            self.assertNotIn(leftover, text)

    def test_two_values_or_an_area_code_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jma-named-forecast.json"
            with self.assertRaises(ValueError):
                record_named_forecast(
                    path,
                    JMA_LOCAL_URL,
                    ONE_LINK,
                    followed_url=FOLLOWED,
                    followed_body=TWO_PAGE,
                )
            with self.assertRaises(ValueError):
                record_named_forecast(
                    path,
                    JMA_LOCAL_URL,
                    FETCHED,
                    followed_url="https://www.jma.go.jp/bosai/forecast.html#code=015000",
                    followed_body="015000 forecast is 7 for 18 November 2026",
                )
            self.assertFalse(path.exists())

    def test_trade_or_test_switch_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jma-named-forecast.json"
            for label in ("trade", "completed harvest", "temperature", "015000"):
                with self.assertRaises(ValueError):
                    record_named_forecast(
                        path,
                        JMA_LOCAL_URL,
                        ONE_LINK,
                        followed_url=FOLLOWED,
                        followed_body=ONE_PAGE,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                record_named_forecast(
                    path,
                    JMA_LOCAL_URL,
                    ONE_LINK,
                    followed_url=FOLLOWED,
                    followed_body=ONE_PAGE,
                    permits_financial_use_test=True,
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_forecast(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("jma_named_forecast", text)
            self.assertNotIn("jma_local", text)
            self.assertNotIn("bosai/#lang=en&pattern=forecast", text)


if __name__ == "__main__":
    unittest.main()
