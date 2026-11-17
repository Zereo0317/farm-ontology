import json
import re
import tempfile
import unittest
import urllib.request
from pathlib import Path

from farm_ontology import jma_niwa_hour_humidity
from farm_ontology.policy import CLASS_C_POLICY


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AssertionError("the refetch does not follow another page")


def _hour_one_humidity(page: str) -> str:
    row = re.search(
        r'<tr class="mtx" style="text-align:right;">(.*?)</tr>',
        page,
        re.S,
    )
    cells = [
        re.sub(r"<[^>]+>", "", cell)
        for cell in re.findall(r"<td[^>]*>(.*?)</td>", row.group(1), re.S)
    ]
    if cells[0] != "1":
        raise AssertionError("the first printed hour is not 1")
    return cells[5]


class JmaNiwaHourHumidityTest(unittest.TestCase):
    def _record(self, path: Path) -> None:
        jma_niwa_hour_humidity.record_jma_niwa_hour_humidity(
            path,
            jma_niwa_hour_humidity.NIWA_URL,
        )

    def test_stores_the_printed_hour_and_percent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "niwa-humidity.json"
            self._record(path)
            header = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            header,
            {
                "place": "新和",
                "heading": "新和（日高地方)\u30002026年11月16日（１時間ごとの値）",
                "date": "2026年11月16日",
                "hour_column": "時",
                "hour": "1",
                "humidity_column": "湿度(％)",
                "humidity_percent": 91,
                "citation_url": jma_niwa_hour_humidity.NIWA_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(header["class_c_policy"], CLASS_C_POLICY)
        self.assertIsInstance(header["humidity_percent"], int)
        self.assertEqual(list(header).count("place"), 1)
        text = json.dumps(header, ensure_ascii=False)
        self.assertNotIn("平取", text)
        self.assertNotIn("Biratori", text)
        self.assertNotIn("3.8", text)
        self.assertNotIn("2.5", text)

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "niwa-humidity.json"
            with self.assertRaises(ValueError):
                jma_niwa_hour_humidity.record_jma_niwa_hour_humidity(path, None)
            with self.assertRaises(ValueError):
                jma_niwa_hour_humidity.record_jma_niwa_hour_humidity(path, "   ")
            self.assertFalse(path.exists())

    def test_other_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "niwa-humidity.json"
            with self.assertRaises(ValueError):
                jma_niwa_hour_humidity.record_jma_niwa_hour_humidity(
                    path,
                    jma_niwa_hour_humidity.NIWA_URL.replace("day=16", "day=17"),
                )
            self.assertFalse(path.exists())

    def test_rejected_labels_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "niwa-humidity.json"
            for label in ("平取", "Biratori", "calculated", "yield"):
                with self.assertRaises(ValueError):
                    jma_niwa_hour_humidity.record_jma_niwa_hour_humidity(
                        path,
                        jma_niwa_hour_humidity.NIWA_URL,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                jma_niwa_hour_humidity.record_jma_niwa_hour_humidity(
                    path,
                    jma_niwa_hour_humidity.NIWA_URL,
                    station="平取",
                )
            with self.assertRaises(ValueError):
                jma_niwa_hour_humidity.record_jma_niwa_hour_humidity(
                    path,
                    jma_niwa_hour_humidity.NIWA_URL,
                    humidity_percent=91,
                )
            with self.assertRaises(ValueError):
                jma_niwa_hour_humidity.record_jma_niwa_hour_humidity(
                    path,
                    jma_niwa_hour_humidity.NIWA_URL,
                    permits_financial_use=True,
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_calculate_humidity(self) -> None:
        source = (
            Path(jma_niwa_hour_humidity.__file__)
            .read_text(encoding="utf-8")
            .replace("\n", " ")
        )
        self.assertIn("station of this citation is 新和", source)
        self.assertIn("second station is not added", source)
        self.assertIn("Humidity is not calculated", source)
        self.assertIn("does not print 平取", source)
        self.assertIn("湿度(％)", source)
        self.assertNotIn("field_save", source)

    def test_live_refetch_prints_hour_1_and_91_percent(self) -> None:
        request = urllib.request.Request(
            jma_niwa_hour_humidity.NIWA_URL,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        opener = urllib.request.build_opener(_NoRedirect)
        with opener.open(request, timeout=60) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.geturl(), jma_niwa_hour_humidity.NIWA_URL)
            page = response.read().decode("utf-8")
        self.assertIn(jma_niwa_hour_humidity.HEADING, page)
        self.assertIn("新和", page)
        self.assertNotIn("平取", page)
        self.assertIn("湿度", page)
        self.assertEqual(_hour_one_humidity(page), "91")
        self.assertEqual(jma_niwa_hour_humidity.HOUR, "1")
        self.assertEqual(jma_niwa_hour_humidity.HUMIDITY_PERCENT, 91)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "niwa-humidity.json"
            self._record(path)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["hour"], "1")
        self.assertEqual(stored["humidity_percent"], 91)
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], "closed")


if __name__ == "__main__":
    unittest.main()
