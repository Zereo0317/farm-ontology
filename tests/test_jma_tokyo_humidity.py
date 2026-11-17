import tempfile
import unittest
from pathlib import Path

from farm_ontology import jma_tokyo_humidity

LIVE_BODY = """
<div>2026年11月17日のページを表示しましたが、<br />閲覧可能な日は、昨日2026年11月16日までです。<br />閲覧可能な日まで戻るか、「メニューに戻る」ボタンをクリックして下さい。</div>
"""

NO_PERCENT = """
<table>
<tr><td>時</td><td>気温</td><td>露点温度</td><td>湿度</td></tr>
<tr><td>1</td><td></td><td></td><td></td></tr>
</table>
"""


class JmaTokyoHumidityTest(unittest.TestCase):
    def test_live_page_has_no_humidity_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tokyo-humidity.json"
            with self.assertRaises(ValueError):
                jma_tokyo_humidity.record_jma_tokyo_humidity(
                    path,
                    jma_tokyo_humidity.TOKYO_HOURLY_URL,
                    LIVE_BODY,
                )
            self.assertFalse(path.exists())

    def test_failed_request_or_empty_body_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tokyo-humidity.json"
            with self.assertRaises(ValueError):
                jma_tokyo_humidity.record_jma_tokyo_humidity(
                    path,
                    jma_tokyo_humidity.TOKYO_HOURLY_URL,
                    LIVE_BODY,
                    request_failed=True,
                )
            with self.assertRaises(ValueError):
                jma_tokyo_humidity.record_jma_tokyo_humidity(
                    path,
                    jma_tokyo_humidity.TOKYO_HOURLY_URL,
                    None,
                )
            self.assertFalse(path.exists())

    def test_temperature_and_dewpoint_without_a_percent_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tokyo-humidity.json"
            with self.assertRaises(ValueError):
                jma_tokyo_humidity.record_jma_tokyo_humidity(
                    path,
                    jma_tokyo_humidity.TOKYO_HOURLY_URL,
                    NO_PERCENT,
                )
            self.assertFalse(path.exists())
        source = Path(jma_tokyo_humidity.__file__).read_text(encoding="utf-8")
        self.assertIn("not calculated from temperature and dewpoint", source)

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tokyo-humidity.json"
            with self.assertRaises(ValueError):
                jma_tokyo_humidity.record_jma_tokyo_humidity(path, None, LIVE_BODY)
            with self.assertRaises(ValueError):
                jma_tokyo_humidity.record_jma_tokyo_humidity(
                    path,
                    jma_tokyo_humidity.TOKYO_HOURLY_URL + "1",
                    LIVE_BODY,
                )
            self.assertFalse(path.exists())

    def test_second_station_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tokyo-humidity.json"
            for label in ("大阪", "平取"):
                with self.assertRaises(ValueError):
                    jma_tokyo_humidity.record_jma_tokyo_humidity(
                        path,
                        jma_tokyo_humidity.TOKYO_HOURLY_URL,
                        LIVE_BODY,
                        label=label,
                    )
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
