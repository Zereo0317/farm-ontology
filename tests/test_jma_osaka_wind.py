import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology import jma_osaka_wind
from farm_ontology.policy import CLASS_C_POLICY


class JmaOsakaWindTest(unittest.TestCase):
    def test_stores_printed_wind_with_the_bracket(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "osaka-wind.json"
            jma_osaka_wind.record_jma_osaka_wind(path, jma_osaka_wind.JMA_SYNOPDAY_URL)
            header = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            header,
            {
                "place": "大阪",
                "heading": "2026年11月17日\u300010時現在",
                "mark": "値]",
                "mark_meaning": "資料不足値 *2",
                "wind": [
                    {"group": "最大", "column": "風速", "value": "3.7]", "unit": "m/s"},
                    {"group": "最大", "column": "風向", "value": "北]"},
                    {"group": "最大", "column": "起時", "value": "08:33]"},
                ],
                "citation_url": jma_osaka_wind.JMA_SYNOPDAY_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(header["class_c_policy"], CLASS_C_POLICY)
        for cell in header["wind"]:
            self.assertTrue(str(cell["value"]).endswith("]"))
        text = json.dumps(header, ensure_ascii=False)
        self.assertNotIn("Biratori", text)
        self.assertNotIn("平取", text)
        self.assertNotIn("湿度", text)
        self.assertNotIn("5.8]", text)
        self.assertNotIn("08:43]", text)

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "osaka-wind.json"
            with self.assertRaises(ValueError):
                jma_osaka_wind.record_jma_osaka_wind(path, None)
            with self.assertRaises(ValueError):
                jma_osaka_wind.record_jma_osaka_wind(path, "   ")
            self.assertFalse(path.exists())

    def test_other_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "osaka-wind.json"
            for citation in (
                jma_osaka_wind.JMA_SYNOPDAY_URL + "/",
                "https://www.data.jma.go.jp/stats/data/mdrr/synopday/",
            ):
                with self.assertRaises(ValueError):
                    jma_osaka_wind.record_jma_osaka_wind(path, citation)
            self.assertFalse(path.exists())

    def test_rejected_labels_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "osaka-wind.json"
            for label in ("Biratori", "平取", "humidity", "complete observation", "yield", "trade"):
                with self.assertRaises(ValueError):
                    jma_osaka_wind.record_jma_osaka_wind(
                        path,
                        jma_osaka_wind.JMA_SYNOPDAY_URL,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                jma_osaka_wind.record_jma_osaka_wind(
                    path,
                    jma_osaka_wind.JMA_SYNOPDAY_URL,
                    wind_speed="3.7",
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_drop_the_mark(self) -> None:
        source = (
            Path(jma_osaka_wind.__file__).read_text(encoding="utf-8").replace("\n", " ")
        )
        self.assertIn("not a complete observation", source)
        self.assertIn("資料不足値", source)
        self.assertIn("not 平取 and not Biratori", source)
        self.assertIn("Humidity is not calculated", source)
        self.assertNotIn("field_save", source)


if __name__ == "__main__":
    unittest.main()
