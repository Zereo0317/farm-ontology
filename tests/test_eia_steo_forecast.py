import json
import re
import tempfile
import unittest
import urllib.request
from pathlib import Path

from farm_ontology import eia_steo_forecast
from farm_ontology.policy import CLASS_C_POLICY


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AssertionError("the refetch does not follow another page")


def _first_forecast_cell(page: str) -> str:
    table = re.search(r'class="notables"(.*?)</table>', page, re.S)
    years = re.findall(r'class="thyear">([^<]+)</th>', table.group(1))
    row = re.search(
        r"OPEC total liquid fuels production </strong></span>"
        r'<span class="units">\(million barrels per day\)</span></td>\s*'
        r"<td>([^<]+)</td>",
        table.group(1),
    )
    if years[0] != "2026":
        raise AssertionError("the first printed year column is not 2026")
    return row.group(1).strip()


class EiaSteoForecastTest(unittest.TestCase):
    def _record(self, path: Path) -> None:
        eia_steo_forecast.record_eia_steo_forecast(path, eia_steo_forecast.STEO_URL)

    def test_stores_the_printed_2026_production_forecast(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "steo-forecast.json"
            self._record(path)
            header = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            header,
            {
                "series": "OPEC total liquid fuels production",
                "period": "2026",
                "value": "24.5",
                "unit": "million barrels per day",
                "kind": "published forecast",
                "citation_url": "https://www.eia.gov/outlooks/steo/",
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(header["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(header)
        self.assertNotIn("trade", text)
        self.assertNotIn("observation", text)
        self.assertNotIn("settlement", text)
        self.assertNotIn("completed supply", text)
        self.assertNotIn("28.4", text)
        self.assertNotIn("23.9", text)

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "steo-forecast.json"
            with self.assertRaises(ValueError):
                eia_steo_forecast.record_eia_steo_forecast(path, None)
            with self.assertRaises(ValueError):
                eia_steo_forecast.record_eia_steo_forecast(path, "   ")
            self.assertFalse(path.exists())

    def test_other_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "steo-forecast.json"
            with self.assertRaises(ValueError):
                eia_steo_forecast.record_eia_steo_forecast(
                    path,
                    "https://www.eia.gov/outlooks/steo/pdf/compare.pdf",
                )
            self.assertFalse(path.exists())

    def test_forbidden_labels_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "steo-forecast.json"
            for label in ("settlement", "observation", "completed supply", "trade", "TRADE"):
                with self.assertRaises(ValueError):
                    eia_steo_forecast.record_eia_steo_forecast(
                        path,
                        eia_steo_forecast.STEO_URL,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                eia_steo_forecast.record_eia_steo_forecast(
                    path,
                    eia_steo_forecast.STEO_URL,
                    value="28.4",
                )
            with self.assertRaises(ValueError):
                eia_steo_forecast.record_eia_steo_forecast(
                    path,
                    eia_steo_forecast.STEO_URL,
                    permits_financial_use=True,
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_call_the_forecast_a_settlement(self) -> None:
        source = (
            Path(eia_steo_forecast.__file__).read_text(encoding="utf-8").replace("\n", " ")
        )
        self.assertIn("OPEC total liquid fuels production", source)
        self.assertIn("24.5", source)
        self.assertIn("published forecast", source)
        self.assertIn("not completed supply, an observation, or a settlement", source)
        self.assertNotIn("field_save", source)

    def test_live_refetch_prints_the_2026_production_forecast(self) -> None:
        request = urllib.request.Request(
            eia_steo_forecast.STEO_URL,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        opener = urllib.request.build_opener(_NoRedirect)
        with opener.open(request, timeout=60) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.geturl(), eia_steo_forecast.STEO_URL)
            page = response.read().decode("utf-8")
        self.assertIn("Notable Forecast Changes", page)
        self.assertEqual(_first_forecast_cell(page), "24.5")
        self.assertEqual(eia_steo_forecast.SERIES, "OPEC total liquid fuels production")
        self.assertEqual(eia_steo_forecast.PERIOD, "2026")
        self.assertEqual(eia_steo_forecast.VALUE, "24.5")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "steo-forecast.json"
            self._record(path)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["kind"], "published forecast")
        self.assertEqual(stored["value"], "24.5")
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], "closed")

    def test_reading_the_record_writes_no_trade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "steo-forecast.json"
            self._record(path)
            before = path.read_text(encoding="utf-8")
            names_before = sorted(item.name for item in folder.iterdir())
            header = json.loads(before)
            after = path.read_text(encoding="utf-8")
            names_after = sorted(item.name for item in folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names_after, names_before)
        self.assertEqual(names_after, ["steo-forecast.json"])
        self.assertEqual(header["series"], "OPEC total liquid fuels production")
        self.assertEqual(header["period"], "2026")
        self.assertEqual(header["value"], "24.5")
        self.assertEqual(header["kind"], "published forecast")
        self.assertFalse(header["permits_financial_use"])
        self.assertNotIn("trade", header)
        self.assertNotIn("observation", header)
        self.assertNotIn("settlement", header)
        self.assertNotIn("trade", after)
        self.assertNotIn("observation", after)
        self.assertNotIn("settlement", after)


if __name__ == "__main__":
    unittest.main()
