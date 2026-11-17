import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology import jma_tokyo_humidity_1116
from farm_ontology.policy import CLASS_C_POLICY

LIVE_BODY = """
<h3>東京（東京都)　2026年11月16日　（１時間ごとの値）</h3>
<table>
<tr><th>時</th><th>気圧(hPa)</th><th>降水量(mm)</th><th>気温(℃)</th><th>露点温度(℃)</th><th>蒸気圧(hPa)</th><th>湿度(％)</th></tr>
<tr><td>6</td><td>1007.6</td><td>1010.5</td><td>--</td><td>12.5</td><td>10.6</td><td>12.8</td><td>88</td><td>1.9</td><td>北西</td></tr>
<tr><td>24</td><td>1019.4</td><td>1022.3</td><td>--</td><td>14.3</td><td>5.4</td><td>9.0</td><td>55</td><td>1.1</td><td>北北西</td></tr>
</table>
"""


class JmaTokyoHumidity1116Test(unittest.TestCase):
    def test_stores_the_last_printed_percent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tokyo-humidity.json"
            jma_tokyo_humidity_1116.record_jma_tokyo_humidity_1116(
                path,
                jma_tokyo_humidity_1116.TOKYO_HOURLY_URL,
                LIVE_BODY,
            )
            stored = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            stored,
            {
                "place": "東京（東京都)",
                "date": "2026年11月16日",
                "hour": 24,
                "relative_humidity_percent": 55,
                "unit": "％",
                "citation_url": jma_tokyo_humidity_1116.TOKYO_HOURLY_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(stored, ensure_ascii=False)
        self.assertNotIn("88", text)
        self.assertNotIn("大阪", text)
        self.assertNotIn("12.5", text)
        self.assertNotIn("10.6", text)

    def test_failed_request_or_empty_body_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tokyo-humidity.json"
            with self.assertRaises(ValueError):
                jma_tokyo_humidity_1116.record_jma_tokyo_humidity_1116(
                    path,
                    jma_tokyo_humidity_1116.TOKYO_HOURLY_URL,
                    LIVE_BODY,
                    request_failed=True,
                )
            with self.assertRaises(ValueError):
                jma_tokyo_humidity_1116.record_jma_tokyo_humidity_1116(
                    path,
                    jma_tokyo_humidity_1116.TOKYO_HOURLY_URL,
                    None,
                )
            self.assertFalse(path.exists())

    def test_missing_percent_writes_nothing(self) -> None:
        missing = LIVE_BODY.replace("<td>88</td>", "<td></td>", 1).replace("<td>55</td>", "<td></td>", 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tokyo-humidity.json"
            with self.assertRaises(ValueError):
                jma_tokyo_humidity_1116.record_jma_tokyo_humidity_1116(
                    path,
                    jma_tokyo_humidity_1116.TOKYO_HOURLY_URL,
                    missing,
                )
            self.assertFalse(path.exists())
        source = Path(jma_tokyo_humidity_1116.__file__).read_text(encoding="utf-8")
        self.assertIn("not calculated from temperature and dewpoint", source)

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tokyo-humidity.json"
            with self.assertRaises(ValueError):
                jma_tokyo_humidity_1116.record_jma_tokyo_humidity_1116(path, None, LIVE_BODY)
            with self.assertRaises(ValueError):
                jma_tokyo_humidity_1116.record_jma_tokyo_humidity_1116(
                    path,
                    jma_tokyo_humidity_1116.TOKYO_HOURLY_URL.replace("day=16", "day=17"),
                    LIVE_BODY,
                )
            self.assertFalse(path.exists())

    def test_second_station_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tokyo-humidity.json"
            for label in ("大阪", "平取"):
                with self.assertRaises(ValueError):
                    jma_tokyo_humidity_1116.record_jma_tokyo_humidity_1116(
                        path,
                        jma_tokyo_humidity_1116.TOKYO_HOURLY_URL,
                        LIVE_BODY,
                        label=label,
                    )
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
