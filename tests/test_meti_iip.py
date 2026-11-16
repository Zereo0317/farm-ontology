import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.meti_iip import METI_IIP_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = METI_IIP_URL


class MetiIipTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_an_index_or_percent(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "経済産業省")
        self.assertEqual(
            header["product"],
            "鉱工業指数(生産・出荷・在庫、生産能力・稼働率)、製造工業生産予測指数",
        )
        self.assertEqual(header["period"], "2026年9月分")
        self.assertEqual(header["unit"], "2020年＝100")
        self.assertEqual(header["administrative_area"], "日本")
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "report")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(
            header["copyright_notice"],
            "Copyright Ministry of Economy, Trade and Industry. All Rights Reserved.",
        )
        self.assertIn("製造工業生産予測指数", header["product"])
        for key in (
            "value",
            "price",
            "index_level",
            "index_value",
            "percent",
            "quantity",
            "forecast",
            "licence",
            "license",
        ):
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
            "trading right",
            "quantity of goods",
            "％",
            "%",
            "前月比",
            "前年同月比",
            "11月16日",
            "確報",
            "english/statistics",
            "時系列データ等ダウンロード",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "meti_iip.py").read_text(encoding="utf-8")
        self.assertIn(
            "https://www.meti.go.jp/english/statistics/tyo/iip/index.html",
            source,
        )
        self.assertIn("page-not-found", source)
        self.assertIn("結果の概要【2026年9月分】", source)
        self.assertIn("（2026年11月16日発表）", source)
        self.assertIn("鉱工業指数概況【2026年9月分確報】", source)
        self.assertIn("製造業の動きから見る日本の景気", source)
        self.assertIn("鉱工業指数、2020年＝100", source)
        self.assertIn("製造工業生産能力指数、2020年＝100", source)
        self.assertIn("製造工業稼働率指数、2020年＝100", source)
        self.assertIn("前月比（％）", source)
        self.assertIn("前年同月比（％）", source)
        self.assertIn("production plan for the next two months", source)
        self.assertIn("利用規約", source)
        self.assertIn("時系列データ等ダウンロード", source)
        self.assertIn("bulk history file was not opened", source)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://www.meti.go.jp/english/statistics/tyo/iip/index.html",
            "https://example.com/iip.html",
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
            "quantity of goods",
            "trading right",
            "予測",
            "前月比",
            "100",
            "2020年＝100",
            "前月比（％）",
            "Settlement",
            "YIELD",
            "Trade",
            "Forecast",
            "Observation",
            "Completed Harvest",
            "Public Domain",
            "Benchmark",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_stored_numbers_write_nothing(self):
        attempts = (
            {"value": 100},
            {"value": "1.2"},
            {"unit": "101.5"},
            {"period": "0.3"},
            {"administrative_area": "100"},
            {"unit": "前月比（％）"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_meti(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("meti_iip", text)
            self.assertNotIn("tyo/iip/result-1", text)
