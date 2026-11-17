import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology import jma_tokyo_hourly_humidity
from farm_ontology.policy import CLASS_C_POLICY


class JmaTokyoHourlyHumidityTest(unittest.TestCase):
    def test_stores_printed_hour_6_humidity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tokyo-humidity.json"
            jma_tokyo_hourly_humidity.record_jma_tokyo_humidity(
                path,
                jma_tokyo_hourly_humidity.JMA_TOKYO_HOURLY_URL,
            )
            header = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            header,
            {
                "place": "東京（東京都)",
                "date": "2026年11月16日",
                "hour_column": "時",
                "hour": "6",
                "column": "湿度(％)",
                "percent": 88,
                "citation_url": jma_tokyo_hourly_humidity.JMA_TOKYO_HOURLY_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(header["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(header, ensure_ascii=False)
        self.assertNotIn("Biratori", text)
        self.assertNotIn("露点", text)
        self.assertNotIn("気温", text)

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tokyo-humidity.json"
            with self.assertRaises(ValueError):
                jma_tokyo_hourly_humidity.record_jma_tokyo_humidity(path, None)
            with self.assertRaises(ValueError):
                jma_tokyo_hourly_humidity.record_jma_tokyo_humidity(path, "   ")
            self.assertFalse(path.exists())

    def test_other_citation_writes_nothing(self) -> None:
        citation = jma_tokyo_hourly_humidity.JMA_TOKYO_HOURLY_URL
        swapped = citation.replace(
            "year=2026&month=11",
            "month=11&year=2026",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tokyo-humidity.json"
            for other in (
                citation + "p1",
                swapped,
                "https://www.data.jma.go.jp/stats/etrn/view/hourly_s1.php",
            ):
                with self.assertRaises(ValueError):
                    jma_tokyo_hourly_humidity.record_jma_tokyo_humidity(path, other)
            self.assertFalse(path.exists())

    def test_rejected_labels_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tokyo-humidity.json"
            for label in ("Biratori", "露点温度", "気温", "yield", "trade", "farm humidity"):
                with self.assertRaises(ValueError):
                    jma_tokyo_hourly_humidity.record_jma_tokyo_humidity(
                        path,
                        jma_tokyo_hourly_humidity.JMA_TOKYO_HOURLY_URL,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                jma_tokyo_hourly_humidity.record_jma_tokyo_humidity(
                    path,
                    jma_tokyo_hourly_humidity.JMA_TOKYO_HOURLY_URL,
                    humidity_percent="",
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_observation(self) -> None:
        source = (
            Path(jma_tokyo_hourly_humidity.__file__)
            .read_text(encoding="utf-8")
            .replace("\n", " ")
        )
        self.assertIn("Tokyo observation", source)
        self.assertIn("not a Biratori observation", source)
        self.assertIn("not a value calculated from 露点温度 or 気温", source)
        self.assertIn("not stored as humidity", source)
        self.assertNotIn("field_save", source)


if __name__ == "__main__":
    unittest.main()
