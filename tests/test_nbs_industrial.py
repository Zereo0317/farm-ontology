import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.header_schema import read_stored_header
from farm_ontology.nbs_industrial import (
    NBS_INDUSTRIAL_URL,
    REPRODUCTION_SENTENCE,
    TERMS_URL,
    record_series_header,
)
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
URL = NBS_INDUSTRIAL_URL
NOT_OPENED = "the field was not opened"


class NbsIndustrialTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_growth_rate(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "国家统计局")
        self.assertEqual(header["product"], "规模以上工业增加值")
        self.assertEqual(header["period"], "2026年10月份")
        self.assertEqual(header["unit"], NOT_OPENED)
        self.assertEqual(header["administrative_area"], NOT_OPENED)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "report")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(header["copyright_notice"], "版权所有: 国家统计局")
        self.assertEqual(header["source_line"], "来源：国家统计局")
        for key in (
            "value",
            "price",
            "index_level",
            "index_value",
            "percent",
            "growth",
            "quantity",
            "forecast",
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
            "增长",
            "%",
            "％",
            "2000",
            "10:00",
            "11/16",
            "免报",
            "全国",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "nbs_industrial.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("2026/11/16 10:00", flat)
        self.assertIn("规模以上工业的统计范围为年主营业务收入2000万元及以上的工业企业。", flat)
        self.assertIn("规模以上工业企业工业生产报表按月进行全面调查（1月份数据免报）。", flat)
        self.assertIn("not an output value", flat)
        self.assertIn("growth figure in the title was not copied", flat)
        self.assertIn("linked page was opened", flat)
        self.assertIn("printed sentence about reprinting or quoting", flat)
        self.assertNotIn("service-terms page was not opened", flat)
        self.assertIn("bulk history file was not opened", flat)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        with self.assertRaises(ValueError):
            record_series_header(self.folder, citation_url="https://example.com/nbs.html")
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
            "growth rate",
            "增长",
            "4.9%",
            "2000万元",
            "10:00",
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

    def test_filled_fields_and_growth_rates_write_nothing(self):
        attempts = (
            {"unit": NOT_OPENED},
            {"unit": "%"},
            {"administrative_area": NOT_OPENED},
            {"administrative_area": "全国"},
            {"value": 4.9},
            {"value": "4.9%"},
            {"period": "4.9%"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_reading_the_stored_record_writes_no_trade(self):
        saved = record_series_header(self.folder, citation_url=URL)
        path = self.folder / saved["file"]
        before = path.read_text(encoding="utf-8")
        names_before = sorted(item.name for item in self.folder.iterdir())
        record = json.loads(before)
        read = read_stored_header(record)
        after = path.read_text(encoding="utf-8")
        names_after = sorted(item.name for item in self.folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names_after, names_before)
        self.assertEqual(names_after, ["nbs-industrial.json"])
        self.assertEqual(record["reproduction_sentence"], REPRODUCTION_SENTENCE)
        self.assertEqual(record["terms_url"], TERMS_URL)
        self.assertEqual(record["copyright_notice"], "版权所有: 国家统计局")
        self.assertIs(record["permits_financial_use"], False)
        self.assertIs(read["permits_financial_use"], False)
        self.assertEqual(CLASS_C_POLICY, "closed")
        self.assertNotIn("trade", record)
        self.assertNotIn("trade", read)
        self.assertNotIn("quantity", record)
        self.assertNotIn("growth", record)
        self.assertNotIn("value", record)
        self.assertNotIn("%", after)
        self.assertNotIn("％", after)
        self.assertNotIn("增长", after)
        self.assertFalse((self.folder / "trade.json").exists())

    def test_field_save_does_not_ingest_nbs(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("nbs_industrial", text)
            self.assertNotIn("t20261116_1965842", text)
