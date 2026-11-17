import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology import jma_osaka_wind_current
from farm_ontology.policy import CLASS_C_POLICY

LIVE_BODY = """
<div>毎日の全国データ一覧表（日別値詳細版:2026年11月17日　10時現在）</div>
<table>
<tr><td>要素</td><td>風速</td></tr>
<tr><td>単位</td><td>m/s</td></tr>
<tr><td>値]</td><td>資料不足値 *2</td></tr>
<tr>
<td>大阪</td><td></td><td></td><td>1021.9]</td><td>04:25]</td><td></td>
<td>13.3]</td><td>09:00]</td><td>9.9]</td><td>06:27]</td><td></td><td></td>
<td>71]</td><td>09:00]</td><td></td>
<td>3.7]</td><td>北]</td><td>08:33]</td>
<td>5.8]</td><td>北]</td><td>08:43]</td>
</tr>
</table>
"""


class JmaOsakaWindCurrentTest(unittest.TestCase):
    def test_stores_the_printed_osaka_wind(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "osaka-wind.json"
            jma_osaka_wind_current.record_jma_osaka_wind_current(
                path,
                jma_osaka_wind_current.JMA_SYNOPDAY_URL,
                LIVE_BODY,
            )
            stored = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            stored,
            {
                "place": "大阪",
                "heading": "2026年11月17日\u300010時現在",
                "group": "最大",
                "speed": "3.7]",
                "unit": "m/s",
                "direction": "北]",
                "time": "08:33]",
                "mark": "値]",
                "mark_meaning": "資料不足値 *2",
                "citation_url": jma_osaka_wind_current.JMA_SYNOPDAY_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(stored, ensure_ascii=False)
        self.assertNotIn("5.8", text)
        self.assertNotIn("08:43", text)
        self.assertNotIn("平取", text)

    def test_failed_request_or_empty_body_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "osaka-wind.json"
            with self.assertRaises(ValueError):
                jma_osaka_wind_current.record_jma_osaka_wind_current(
                    path,
                    jma_osaka_wind_current.JMA_SYNOPDAY_URL,
                    LIVE_BODY,
                    request_failed=True,
                )
            with self.assertRaises(ValueError):
                jma_osaka_wind_current.record_jma_osaka_wind_current(
                    path,
                    jma_osaka_wind_current.JMA_SYNOPDAY_URL,
                    None,
                )
            self.assertFalse(path.exists())

    def test_missing_direction_or_time_writes_nothing(self) -> None:
        missing = LIVE_BODY.replace("<td>北]</td><td>08:33]</td>", "<td></td><td></td>", 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "osaka-wind.json"
            with self.assertRaises(ValueError):
                jma_osaka_wind_current.record_jma_osaka_wind_current(
                    path,
                    jma_osaka_wind_current.JMA_SYNOPDAY_URL,
                    missing,
                )
            self.assertFalse(path.exists())

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "osaka-wind.json"
            with self.assertRaises(ValueError):
                jma_osaka_wind_current.record_jma_osaka_wind_current(path, None, LIVE_BODY)
            with self.assertRaises(ValueError):
                jma_osaka_wind_current.record_jma_osaka_wind_current(
                    path,
                    jma_osaka_wind_current.JMA_SYNOPDAY_URL + "/",
                    LIVE_BODY,
                )
            self.assertFalse(path.exists())

    def test_rejected_labels_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "osaka-wind.json"
            for label in ("平取", "trade", "yield"):
                with self.assertRaises(ValueError):
                    jma_osaka_wind_current.record_jma_osaka_wind_current(
                        path,
                        jma_osaka_wind_current.JMA_SYNOPDAY_URL,
                        LIVE_BODY,
                        label=label,
                    )
            self.assertFalse(path.exists())
            source = Path(jma_osaka_wind_current.__file__).read_text(encoding="utf-8")
            self.assertNotIn("5.8]", source)


if __name__ == "__main__":
    unittest.main()
