import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.jma_local import JMA_LOCAL_URL, record_series_header
from farm_ontology.jma_urakawa_temperature import (
    FORECAST_DATA_URL,
    record_urakawa_temperatures,
)
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
FETCHED = (
    ROOT / "tests" / "fixtures" / "jma_015000_forecast.json"
).read_text(encoding="utf-8")
EXPECTED = (
    ("2026-11-17T09:00:00+09:00", "7"),
    ("2026-11-17T00:00:00+09:00", "7"),
    ("2026-11-18T00:00:00+09:00", "4"),
    ("2026-11-18T09:00:00+09:00", "9"),
)


class JmaUrakawaTemperatureTests(unittest.TestCase):
    def test_header_still_rejects_a_number(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaises(ValueError):
                record_series_header(
                    folder,
                    citation_url=JMA_LOCAL_URL,
                    value="7",
                )
            self.assertEqual(list(folder.iterdir()), [])

    def test_stores_the_printed_urakawa_temperatures(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jma-urakawa-temperature.json"
            record_urakawa_temperatures(path, FORECAST_DATA_URL, FETCHED)
            stored = json.loads(path.read_text(encoding="utf-8"))
        rows = stored["rows"]
        self.assertEqual(len(rows), 4)
        self.assertEqual(
            [(row["time"], row["value"]) for row in rows],
            list(EXPECTED),
        )
        for row in rows:
            self.assertEqual(row["area"], "浦河")
            self.assertEqual(row["series"], "temps")
            self.assertEqual(row["kind"], "forecast")
            self.assertEqual(row["label"], "forecast")
        self.assertEqual(stored["citation_url"], FORECAST_DATA_URL)
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertNotIn("permits_financial_use_test", stored)
        text = json.dumps(stored, ensure_ascii=False)
        for leftover in ("平取", "日高地方", "室蘭", "trade", "harvest"):
            self.assertNotIn(leftover, text)

    def test_trade_or_another_file_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jma-urakawa-temperature.json"
            with self.assertRaises(ValueError):
                record_urakawa_temperatures(
                    path,
                    "https://www.jma.go.jp/bosai/forecast/data/forecast/015020.json",
                    FETCHED,
                )
            for label in ("trade", "completed harvest", "平取", "日高地方", "室蘭", "7"):
                with self.assertRaises(ValueError):
                    record_urakawa_temperatures(
                        path,
                        FORECAST_DATA_URL,
                        FETCHED,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                record_urakawa_temperatures(
                    path,
                    FORECAST_DATA_URL,
                    FETCHED,
                    permits_financial_use_test=True,
                )
            with self.assertRaises(ValueError):
                record_urakawa_temperatures(
                    path,
                    FORECAST_DATA_URL,
                    FETCHED,
                    class_c_policy="open",
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_temperatures(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("jma_urakawa_temperature", text)
            self.assertNotIn("jma_local", text)


if __name__ == "__main__":
    unittest.main()
