import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.jma_local import JMA_LOCAL_URL, record_series_header
from farm_ontology.jma_office_forecast import (
    FORECAST_DATA_URL,
    record_office_forecast,
)
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
MANY = json.dumps(
    {
        "timeDefines": [
            "2026-11-17T12:00:00+09:00",
            "2026-11-17T18:00:00+09:00",
        ],
        "areas": [
            {
                "area": {"name": "日高地方", "code": "015020"},
                "pops": ["0", "20"],
            }
        ],
    },
    ensure_ascii=False,
)
ONE = json.dumps(
    {
        "timeDefines": ["2026-11-18T00:00:00+09:00"],
        "areas": [
            {
                "area": {"name": "胆振・日高地方", "code": "015000"},
                "pops": ["10"],
            }
        ],
    },
    ensure_ascii=False,
)


class JmaOfficeForecastTests(unittest.TestCase):
    def test_header_still_rejects_a_figure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaises(ValueError):
                record_series_header(
                    folder,
                    citation_url=JMA_LOCAL_URL,
                    value="10",
                )
            self.assertEqual(list(folder.iterdir()), [])

    def test_opened_forecast_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jma-office-forecast.json"
            with self.assertRaises(ValueError) as caught:
                record_office_forecast(path, FORECAST_DATA_URL, MANY)
            self.assertIn("no single forecast value", str(caught.exception))
            self.assertFalse(path.exists())

    def test_one_printed_forecast_keeps_area_period_and_url(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jma-office-forecast.json"
            record_office_forecast(path, FORECAST_DATA_URL, ONE)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["value"], "10")
        self.assertEqual(stored["area"], "胆振・日高地方")
        self.assertEqual(stored["period"], "2026-11-18T00:00:00+09:00")
        self.assertEqual(stored["citation_url"], FORECAST_DATA_URL)
        self.assertEqual(stored["kind"], "forecast")
        self.assertEqual(stored["label"], "forecast")
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertNotIn("permits_financial_use_test", stored)
        text = json.dumps(stored)
        for leftover in ("trade", "harvest", "rainfall"):
            self.assertNotIn(leftover, text)

    def test_another_code_or_a_test_switch_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jma-office-forecast.json"
            with self.assertRaises(ValueError):
                record_office_forecast(
                    path,
                    "https://www.jma.go.jp/bosai/forecast/data/forecast/015020.json",
                    ONE,
                )
            for label in ("trade", "completed harvest", "rainfall amount"):
                with self.assertRaises(ValueError):
                    record_office_forecast(
                        path,
                        FORECAST_DATA_URL,
                        ONE,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                record_office_forecast(
                    path,
                    FORECAST_DATA_URL,
                    ONE,
                    permits_financial_use_test=True,
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_forecast(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("jma_office_forecast", text)
            self.assertNotIn("jma_local", text)
            self.assertNotIn("015000", text)


if __name__ == "__main__":
    unittest.main()
