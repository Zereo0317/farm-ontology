import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import meti_production_level
from farm_ontology.meti_iip import METI_IIP_URL, record_series_header
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
PAGE = """
<h2>結果の概要【2026年9月分】</h2>
<div>製造工業生産能力指数は、94.4で前月比0.2％の上昇。</div>
<div>製造工業稼働率指数は、104.8で前月比1.6％の上昇。</div>
<table>
<caption>鉱工業指数、2020年＝100</caption>
<tr>
<th scope="row">生産<br><span class="sub_tl">(速報値)</span></th>
<td>103.9<br><span class="sub_tl">(104.1)</span></td>
<td>2.0<br>&nbsp;</td>
<td>107.7<br><span class="sub_tl">(107.9)</span></td>
<td>1.7<br>&nbsp;</td>
</tr>
</table>
<a href="b2020_result-2.html">時系列データ等ダウンロード</a>
"""
DOWNLOAD = "https://www.meti.go.jp/statistics/tyo/iip/b2020_result-2.html"
TERMS = "https://www.meti.go.jp/main/rules.html"


class MetiProductionLevelTests(unittest.TestCase):
    def test_header_still_rejects_a_number(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaises(ValueError):
                record_series_header(folder, citation_url=METI_IIP_URL, value="103.9")
            self.assertEqual(list(folder.iterdir()), [])

    def test_stores_the_printed_production_level(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "meti-production-level.json"
            meti_production_level.record_production_level(path, METI_IIP_URL, PAGE)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["value"], "103.9")
        self.assertEqual(stored["series"], "生産")
        self.assertEqual(stored["presentation"], "季節調整済指数")
        self.assertEqual(stored["period"], "2026年9月分")
        self.assertEqual(stored["base"], "2020年＝100")
        self.assertEqual(stored["base_label"], "base")
        self.assertNotEqual(stored["value"], stored["base"])
        self.assertEqual(stored["kind"], "level")
        self.assertEqual(stored["citation_url"], METI_IIP_URL)
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertEqual(stored["class_c_policy"], "closed")
        self.assertNotIn("permits_financial_use_test", stored)
        text = json.dumps(stored)
        for leftover in (
            "104.1",
            "107.7",
            "107.9",
            "2.0",
            "1.7",
            "94.4",
            "104.8",
            "0.2",
            "1.6",
            "%",
            "％",
            "trade",
            "permits_financial_use_test",
        ):
            self.assertNotIn(leftover, text)

    def test_percent_only_or_other_page_writes_nothing(self) -> None:
        percent_only = "結果の概要【2026年9月分】鉱工業指数、2020年＝100 前月比2.0％"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "meti-production-level.json"
            with self.assertRaises(ValueError):
                meti_production_level.record_production_level(
                    path,
                    METI_IIP_URL,
                    percent_only,
                )
            for source in (DOWNLOAD, TERMS):
                with self.assertRaises(ValueError):
                    meti_production_level.record_production_level(
                        path,
                        METI_IIP_URL,
                        PAGE,
                        source_url=source,
                    )
            self.assertFalse(path.exists())

    def test_reading_the_level_writes_no_trade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "meti-production-level.json"
            meti_production_level.record_production_level(path, METI_IIP_URL, PAGE)
            before = path.read_text(encoding="utf-8")
            stored = json.loads(before)
            after = path.read_text(encoding="utf-8")
            names = sorted(item.name for item in folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names, ["meti-production-level.json"])
        self.assertFalse((folder / "trade.json").exists())
        self.assertEqual(stored["value"], "103.9")
        self.assertEqual(stored["base_label"], "base")
        self.assertFalse(stored["permits_financial_use"])
        self.assertNotIn("trade", after)

    def test_trade_or_test_switch_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "meti-production-level.json"
            for label in ("trade", "quantity of goods", "前月比", "2.0％", "base"):
                with self.assertRaises(ValueError):
                    meti_production_level.record_production_level(
                        path,
                        METI_IIP_URL,
                        PAGE,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                meti_production_level.record_production_level(
                    path,
                    METI_IIP_URL,
                    PAGE,
                    permits_financial_use=True,
                )
            with self.assertRaises(ValueError):
                meti_production_level.record_production_level(
                    path,
                    METI_IIP_URL,
                    PAGE,
                    permits_financial_use_test=True,
                )
            with self.assertRaises(ValueError):
                meti_production_level.record_production_level(
                    path,
                    METI_IIP_URL,
                    PAGE,
                    class_c_policy="open",
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_level(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("meti_production_level", text)
            self.assertNotIn("meti_iip", text)
            self.assertNotIn("tyo/iip/result-1", text)


if __name__ == "__main__":
    unittest.main()
