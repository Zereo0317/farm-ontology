import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology import jma_shinwa_humidity
from farm_ontology.policy import CLASS_C_POLICY


class JmaShinwaHumidityTest(unittest.TestCase):
    def _record(self, path: Path) -> None:
        jma_shinwa_humidity.record_jma_shinwa_humidity(
            path,
            jma_shinwa_humidity.SHINWA_URL,
            station_list_citation_url=jma_shinwa_humidity.STATION_LIST_URL,
            station_page_citation_url=jma_shinwa_humidity.STATION_PAGE_URL,
        )

    def test_stores_printed_shinwa_cells_and_no_hiratori_percent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shinwa-humidity.json"
            self._record(path)
            header = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(header["place"], "新和")
        self.assertEqual(header["heading"], "新和（日高地方)")
        self.assertEqual(header["date"], "2026年11月16日")
        self.assertEqual(header["hour"], "1")
        self.assertEqual(
            header["cells"],
            [
                {"column": "湿度(％)", "value": 91},
                {"column": "気温(℃)", "value": 3.8},
                {"column": "露点温度(℃)", "value": 2.5},
            ],
        )
        self.assertEqual(header["citation_url"], jma_shinwa_humidity.SHINWA_URL)
        self.assertEqual(
            header["hiratori_station_list"],
            {
                "station": "平取",
                "block": "1594",
                "humidity_flag": "0",
                "observation_end": "2004年10月11日まで観測",
                "citation_url": jma_shinwa_humidity.STATION_LIST_URL,
            },
        )
        self.assertEqual(
            header["hiratori_station_page"],
            {
                "station": "平取",
                "hourly_humidity_table": False,
                "citation_url": jma_shinwa_humidity.STATION_PAGE_URL,
            },
        )
        self.assertNotIn("percent", header["hiratori_station_list"])
        self.assertNotIn("percent", header["hiratori_station_page"])
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(header["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(header, ensure_ascii=False)
        self.assertNotIn("Biratori", text)
        self.assertNotIn("ビラトリ", text)

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shinwa-humidity.json"
            with self.assertRaises(ValueError):
                jma_shinwa_humidity.record_jma_shinwa_humidity(path, None)
            with self.assertRaises(ValueError):
                jma_shinwa_humidity.record_jma_shinwa_humidity(
                    path,
                    jma_shinwa_humidity.SHINWA_URL,
                    station_list_citation_url=None,
                    station_page_citation_url=jma_shinwa_humidity.STATION_PAGE_URL,
                )
            with self.assertRaises(ValueError):
                jma_shinwa_humidity.record_jma_shinwa_humidity(
                    path,
                    jma_shinwa_humidity.SHINWA_URL,
                    station_list_citation_url="   ",
                    station_page_citation_url=jma_shinwa_humidity.STATION_PAGE_URL,
                )
            self.assertFalse(path.exists())

    def test_other_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shinwa-humidity.json"
            with self.assertRaises(ValueError):
                jma_shinwa_humidity.record_jma_shinwa_humidity(
                    path,
                    jma_shinwa_humidity.STATION_PAGE_URL,
                    station_list_citation_url=jma_shinwa_humidity.STATION_LIST_URL,
                    station_page_citation_url=jma_shinwa_humidity.STATION_PAGE_URL,
                )
            with self.assertRaises(ValueError):
                jma_shinwa_humidity.record_jma_shinwa_humidity(
                    path,
                    jma_shinwa_humidity.SHINWA_URL + "p1",
                    station_list_citation_url=jma_shinwa_humidity.STATION_LIST_URL,
                    station_page_citation_url=jma_shinwa_humidity.STATION_PAGE_URL,
                )
            self.assertFalse(path.exists())

    def test_rejected_labels_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shinwa-humidity.json"
            for label in ("Biratori", "平取", "farm reading", "yield", "trade"):
                with self.assertRaises(ValueError):
                    jma_shinwa_humidity.record_jma_shinwa_humidity(
                        path,
                        jma_shinwa_humidity.SHINWA_URL,
                        station_list_citation_url=jma_shinwa_humidity.STATION_LIST_URL,
                        station_page_citation_url=jma_shinwa_humidity.STATION_PAGE_URL,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                jma_shinwa_humidity.record_jma_shinwa_humidity(
                    path,
                    jma_shinwa_humidity.SHINWA_URL,
                    station_list_citation_url=jma_shinwa_humidity.STATION_LIST_URL,
                    station_page_citation_url=jma_shinwa_humidity.STATION_PAGE_URL,
                    humidity_percent=91,
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_a_calculated_reading(self) -> None:
        source = (
            Path(jma_shinwa_humidity.__file__)
            .read_text(encoding="utf-8")
            .replace("\n", " ")
        )
        self.assertIn("place label is 新和", source)
        self.assertIn("not a Biratori farm reading", source)
        self.assertIn("not calculated from them", source)
        self.assertIn("no hourly humidity table", source)
        self.assertIn("no humidity percent", source)
        self.assertNotIn("field_save", source)


if __name__ == "__main__":
    unittest.main()
