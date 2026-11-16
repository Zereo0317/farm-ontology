import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.cma_weather import CMA_WEATHER_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = CMA_WEATHER_URL
NOT_OPENED = "the field was not opened"
PERIOD = (
    "数据起始时间 2017年1月19日; 数据终止时间 目前; "
    "制作时间 实时; 更新频率 1小时，1天"
)
AREA = "亚洲区域（0-65°N，60-160°E）"


class CmaWeatherTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "国家气象信息中心(中国气象局气象数据中心)")
        self.assertEqual(
            header["product"],
            "中国气象局陆面数据同化系统（CLDAS-V2.0）实时产品数据集",
        )
        self.assertEqual(header["period"], PERIOD)
        self.assertEqual(header["unit"], NOT_OPENED)
        self.assertEqual(header["administrative_area"], AREA)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "融合分析产品")
        self.assertNotEqual(header["kind"], "forecast")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(
            set(header),
            {
                "publisher",
                "product",
                "period",
                "unit",
                "administrative_area",
                "citation_url",
                "kind",
                "permits_financial_use",
            },
        )
        for key in ("value", "price", "index_level", "growth", "trade", "figure", "copyright"):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "settlement",
            "yield",
            "trade",
            "forecast",
            "observation",
            "completed harvest",
            "public domain",
            "benchmark",
            "index",
            "Copyright",
            "copyright",
            "2005",
            "等经纬度",
            "滞后",
            "普通注册用户访问",
            "共享级别",
            "中关村",
            "100081",
            "datacenter@cma.gov.cn",
            "中国区域陆面产品",
            "0P0625",
            "1.2.156.416",
            "precipitation",
            "licence",
            "license",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "cma_weather.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("The page calls the product a 等经纬度网格融合分析产品.", flat)
        self.assertIn("实时产品实时更新发布,滞后1小时.", flat)
        self.assertIn("An analysis is not a completed harvest.", flat)
        self.assertIn("Do not relabel it as a forecast, a yield, or a trade.", flat)
        self.assertIn("Unit was not opened.", flat)
        self.assertIn(
            "The quality paragraph prints precipitation error figures. Those figures are not copied and no unit is taken from them.",
            flat,
        )
        self.assertIn("中国区域陆面产品 is a breadcrumb, not the administrative area.", flat)
        self.assertIn(
            "地址：北京海淀区中关村南大街46号 邮编：100081 is the centre's address, not the product area.",
            flat,
        )
        self.assertIn("Sharing level 普通注册用户访问 is not a redistribution grant.", flat)
        self.assertIn(
            "Copyright 2005-2017 国家气象信息中心(中国气象局气象数据中心) is a copyright line, not public domain.",
            flat,
        )
        self.assertIn("https://data.cma.cn/ is not the citation.", flat)
        self.assertNotIn("0P0625", flat)
        self.assertNotIn("1.2.156.416", flat)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://data.cma.cn/",
            "https://data.cma.cn",
            "https://data.cma.cn/data/detail/dataCode/NAFP_CLDAS2.0_RT.html/",
            "https://example.com/cma.html",
        ):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "settlement",
            "yield",
            "trade",
            "forecast",
            "observation",
            "completed harvest",
            "public domain",
            "benchmark",
            "index",
            "figure",
            "1.4",
            "2.5%",
            "100081",
            "Settlement",
            "YIELD",
            "Trade",
            "Forecast",
            "Observation",
            "Completed Harvest",
            "Public Domain",
            "Benchmark",
            "Index",
            "INDEX",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_filled_unit_and_replaced_fields_write_nothing(self):
        attempts = (
            {"unit": NOT_OPENED},
            {"unit": "mm"},
            {"unit": "precipitation"},
            {"period": PERIOD},
            {"period": "2017年1月19日"},
            {"period": "实时产品实时更新发布,滞后1小时"},
            {"administrative_area": AREA},
            {"administrative_area": "北京"},
            {"administrative_area": "中国区域"},
            {"value": 1.2},
            {"value": "0.5 mm"},
            {"value": "100081"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_cma(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("cma_weather", text)
            self.assertNotIn("NAFP_CLDAS2.0_RT", text)
