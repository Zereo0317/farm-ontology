import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.data_gov_tw_58977 import DATA_GOV_TW_58977_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = DATA_GOV_TW_58977_URL


class DataGovTw58977Tests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "交通部中央氣象署")
        self.assertNotEqual(header["publisher"], "數位發展部")
        self.assertEqual(header["product"], "數值預報模式-區域預報模式(WRF)")
        self.assertEqual(header["period"], "第0小時至第84小時")
        self.assertEqual(header["kind"], "數值預報資料")
        self.assertNotEqual(header["kind"], header["product"])
        self.assertEqual(header["licence"], "政府資料開放授權條款-第1版")
        self.assertEqual(header["citation_url"], "https://data.gov.tw/dataset/58977")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(header["class_c_policy"], "closed")
        self.assertEqual(
            set(header),
            {
                "publisher",
                "product",
                "period",
                "citation_url",
                "kind",
                "licence",
                "permits_financial_use",
                "class_c_policy",
            },
        )
        for key in ("unit", "administrative_area", "value", "price", "temperature", "rainfall", "yield", "trade"):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "15公里",
            "3公里",
            "Grib2",
            "每6時",
            "2017-11-01",
            "2026-01-08",
            "生活安全及品質",
            "檔案資料",
            "yield",
            "price",
            "trade",
            "rainfall",
            "temperature",
            "completed harvest",
            "opendata.cwa.gov.tw",
            "rdec-key",
        ):
            self.assertNotIn(word, text, word)
        source = (ROOT / "farm_ontology" / "data_gov_tw_58977.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("The citation is the URL that was fetched.", flat)
        self.assertIn("https://data.gov.tw/ is not the citation.", flat)
        self.assertIn("https://data.gov.tw/dataset/58977/ is not the citation.", flat)
        self.assertIn("The publisher is 交通部中央氣象署.", flat)
        self.assertIn("數位發展部 is the platform operator, not the dataset publisher.", flat)
        self.assertIn("The product is 數值預報模式-區域預報模式(WRF).", flat)
        self.assertIn("The description prints 數值預報資料. That phrase is the kind.", flat)
        self.assertIn("The period is 第0小時至第84小時.", flat)
        self.assertIn("每6時 is the update frequency, not the period.", flat)
        self.assertIn("2017-11-01 is the shelf date, not the period.", flat)
        self.assertIn("2026-01-08 11:59 is the metadata update time, not the period.", flat)
        self.assertIn("15公里及3公里 is a resolution, not a unit.", flat)
        self.assertIn("Grib2格式 is a format, not a unit.", flat)
        self.assertIn("Unit was not printed.", flat)
        self.assertIn("生活安全及品質 is a service category, not an area.", flat)
        self.assertIn("Area was not printed.", flat)
        self.assertIn("The licence is 政府資料開放授權條款-第1版.", flat)
        self.assertIn("The resource links leave data.gov.tw and were not opened.", flat)
        self.assertIn("Do not store a rainfall amount.", flat)
        self.assertIn("Do not store a temperature.", flat)
        self.assertIn("Do not store a yield.", flat)
        self.assertIn("Do not store a price.", flat)
        self.assertIn("Do not store a trade.", flat)
        self.assertIn("A forecast is not a completed harvest.", flat)
        self.assertIn("permits_financial_use stays false.", flat)
        self.assertIn("Class C stays closed.", flat)
        self.assertNotIn("rdec-key", source)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://data.gov.tw/",
            "https://data.gov.tw/dataset/58977/",
            "https://data.gov.tw/licenses",
            "https://opendata.cwa.gov.tw/index",
            "https://opendata.cwa.gov.tw/dataset/all?page=1&searchValue=WRF",
            "https://example.com/dataset/58977",
        ):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "yield",
            "price",
            "trade",
            "rainfall",
            "rainfall amount",
            "temperature",
            "completed harvest",
            "Yield",
            "PRICE",
            "Trade",
            "15",
            "582",
            "5994",
            "2017-11-01",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_filled_fields_and_figures_write_nothing(self):
        attempts = (
            {"period": "2017-11-01"},
            {"unit": "Grib2"},
            {"unit": "15公里"},
            {"administrative_area": "生活安全及品質"},
            {"kind": "forecast"},
            {"licence": "CC-BY-NC-4.0"},
            {"value": 1},
            {"value": "rainfall"},
            {"value": "temperature"},
            {"permits_financial_use": True},
            {"class_c_policy": "open"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_data_gov_tw_58977(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("data_gov_tw_58977", text)
            self.assertNotIn("https://data.gov.tw/dataset/58977", text)


if __name__ == "__main__":
    unittest.main()
