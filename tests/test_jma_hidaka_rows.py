import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.jma_hidaka_rows import FORECAST_DATA_URL, record_hidaka_rows
from farm_ontology.jma_local import JMA_LOCAL_URL, record_series_header
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
FETCHED = (
    ROOT / "tests" / "fixtures" / "jma_015000_forecast.json"
).read_text(encoding="utf-8")
BIRATORI = json.dumps(
    {
        "timeDefines": ["2026-11-17T11:00:00+09:00"],
        "areas": [
            {
                "area": {"name": "平取", "code": "000000"},
                "weathers": ["晴れ"],
            },
            {
                "area": {"name": "日高地方", "code": "015020"},
                "weathers": ["くもり"],
            },
        ],
    },
    ensure_ascii=False,
)


class JmaHidakaRowsTests(unittest.TestCase):
    def test_header_still_rejects_a_number(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaises(ValueError):
                record_series_header(
                    folder,
                    citation_url=JMA_LOCAL_URL,
                    value="100",
                )
            self.assertEqual(list(folder.iterdir()), [])

    def test_hidaka_portion_rows_are_stored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jma-hidaka-rows.json"
            record_hidaka_rows(path, FORECAST_DATA_URL, FETCHED)
            stored = json.loads(path.read_text(encoding="utf-8"))
        rows = stored["rows"]
        self.assertEqual(len(rows), 18)
        first = rows[0]
        self.assertEqual(first["area"], "日高地方")
        self.assertEqual(first["time"], "2026-11-17T11:00:00+09:00")
        self.assertEqual(first["series"], "weatherCodes")
        self.assertEqual(first["value"], "100")
        self.assertEqual(first["kind"], "forecast")
        self.assertEqual(first["label"], "forecast")
        self.assertEqual(stored["citation_url"], FORECAST_DATA_URL)
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertNotIn("permits_financial_use_test", stored)
        areas = {row["area"] for row in rows}
        self.assertEqual(areas, {"日高地方"})
        for leftover in ("平取", "胆振地方", "室蘭", "浦河", "胆振・日高地方"):
            self.assertNotIn(leftover, json.dumps(stored, ensure_ascii=False))
        for row in rows:
            self.assertEqual(row["label"], "forecast")
            self.assertNotIn("trade", row["label"])
            self.assertNotIn("harvest", row["label"])

    def test_biratori_rows_replace_the_hidaka_portion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jma-hidaka-rows.json"
            record_hidaka_rows(path, FORECAST_DATA_URL, BIRATORI)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(stored["rows"]), 1)
        self.assertEqual(stored["rows"][0]["area"], "平取")
        self.assertEqual(stored["rows"][0]["value"], "晴れ")
        self.assertNotIn("日高地方", json.dumps(stored, ensure_ascii=False))

    def test_trade_or_another_file_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jma-hidaka-rows.json"
            with self.assertRaises(ValueError):
                record_hidaka_rows(
                    path,
                    "https://www.jma.go.jp/bosai/forecast/data/forecast/015020.json",
                    FETCHED,
                )
            for label in ("trade", "completed harvest", "100"):
                with self.assertRaises(ValueError):
                    record_hidaka_rows(
                        path,
                        FORECAST_DATA_URL,
                        FETCHED,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                record_hidaka_rows(
                    path,
                    FORECAST_DATA_URL,
                    FETCHED,
                    permits_financial_use_test=True,
                )
            with self.assertRaises(ValueError):
                record_hidaka_rows(
                    path,
                    FORECAST_DATA_URL,
                    FETCHED,
                    class_c_policy="open",
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_rows(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("jma_hidaka_rows", text)
            self.assertNotIn("jma_local", text)


if __name__ == "__main__":
    unittest.main()
