import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.aws_cwa_opendata import AWS_CWA_OPENDATA_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = AWS_CWA_OPENDATA_URL


class AwsCwaOpendataTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Central Weather Administration")
        self.assertNotEqual(header["publisher"], "Registry of Open Data on AWS")
        self.assertEqual(header["product"], "Central Weather Administration OpenData")
        self.assertNotEqual(header["product"], header["publisher"])
        self.assertEqual(header["licence"], "http://data.gov.tw/license")
        self.assertEqual(header["citation_url"], "https://registry.opendata.aws/cwa_opendata/")
        self.assertNotEqual(
            header["citation_url"],
            "https://registry.opendata.aws/cwa_opendata",
        )
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(header["class_c_policy"], "closed")
        self.assertEqual(
            set(header),
            {
                "publisher",
                "product",
                "citation_url",
                "licence",
                "permits_financial_use",
                "class_c_policy",
            },
        )
        for key in (
            "period",
            "unit",
            "administrative_area",
            "kind",
            "value",
            "price",
            "temperature",
            "rainfall",
            "yield",
            "trade",
        ):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "WRF",
            "58977",
            "數值預報",
            "交通部中央氣象署",
            "第0小時至第84小時",
            "政府資料開放授權條款",
            "arn:aws",
            "cwaopendata",
            "ap-northeast-1",
            "yield",
            "price",
            "trade",
            "rainfall",
            "temperature",
            "forecast",
            "DATE",
        ):
            self.assertNotIn(word, text, word)
        source = (ROOT / "farm_ontology" / "aws_cwa_opendata.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("The citation is the URL that was fetched.", flat)
        self.assertIn("https://registry.opendata.aws/cwa_opendata is not the citation.", flat)
        self.assertIn("http://data.gov.tw/license is not the citation.", flat)
        self.assertIn("https://data.gov.tw/dataset/58977 is not the citation.", flat)
        self.assertIn("The publisher is Central Weather Administration.", flat)
        self.assertIn("The product is Central Weather Administration OpenData.", flat)
        self.assertIn("Kind was not printed.", flat)
        self.assertIn("Period was not printed.", flat)
        self.assertIn("Unit was not printed.", flat)
        self.assertIn("Area was not printed.", flat)
        self.assertIn("The licence is http://data.gov.tw/license.", flat)
        self.assertIn("The licence page was not opened.", flat)
        self.assertIn("This page is not the data.gov.tw WRF header.", flat)
        self.assertIn("Do not store a rainfall amount.", flat)
        self.assertIn("Do not store a temperature.", flat)
        self.assertIn("Do not store a yield.", flat)
        self.assertIn("Do not store a price.", flat)
        self.assertIn("Do not store a trade.", flat)
        self.assertIn("A forecast is not a completed harvest.", flat)
        self.assertIn("permits_financial_use stays false.", flat)
        self.assertIn("Class C stays closed.", flat)
        self.assertNotIn("數值預報模式-區域預報模式(WRF)", source)
        self.assertNotIn("第0小時至第84小時", source)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://registry.opendata.aws/cwa_opendata",
            "https://registry.opendata.aws/",
            "http://data.gov.tw/license",
            "https://data.gov.tw/dataset/58977",
            "https://www.cwa.gov.tw/",
            "https://github.com/awslabs/open-data-registry/blob/main/datasets/cwa_opendata.yaml",
            "https://example.com/cwa_opendata/",
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
            "forecast",
            "Yield",
            "PRICE",
            "Trade",
            "DATE",
            "2026-01-08",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_filled_fields_and_figures_write_nothing(self):
        attempts = (
            {"period": "Data is updated as soon as newer one is available."},
            {"unit": "chart"},
            {"administrative_area": "ap-northeast-1"},
            {"kind": "數值預報資料"},
            {"kind": "weather"},
            {"kind": "forecast"},
            {"licence": "政府資料開放授權條款-第1版"},
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

    def test_field_save_does_not_ingest_aws_cwa_opendata(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("aws_cwa_opendata", text)
            self.assertNotIn("https://registry.opendata.aws/cwa_opendata/", text)


if __name__ == "__main__":
    unittest.main()
