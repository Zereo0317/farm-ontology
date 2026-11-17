import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import meti_printed_figures
from farm_ontology.meti_iip import METI_IIP_URL, record_series_header
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
PAGE = """
<h2>結果の概要【2026年9月分】</h2>
<div>製造工業生産能力指数は、94.4で前月比0.2％の上昇。</div>
<table>
<caption>鉱工業指数、2020年＝100</caption>
<tr>
<th scope="row">生産<br><span class="sub_tl">(速報値)</span></th>
<td>103.9<br><span class="sub_tl">(104.1)</span></td>
<td>2.0<br>&nbsp;</td>
<td>107.7<br><span class="sub_tl">(107.9)</span></td>
<td>1.7<br>&nbsp;</td>
</tr>
<tr>
<th scope="row">在庫率<br><span class="sub_tl">(速報値)</span></th>
<td>108.9<br><span class="sub_tl">(108.4)</span></td>
<td>2.4<br>&nbsp;</td>
<td>104.6<br><span class="sub_tl">(104.1)</span></td>
<td>3.4<br>&nbsp;</td>
</tr>
</table>
"""
DOWNLOAD = "https://www.meti.go.jp/statistics/tyo/iip/b2020_result-2.html"
TERMS = "https://www.meti.go.jp/main/rules.html"


class MetiPrintedFiguresTests(unittest.TestCase):
    def test_header_still_rejects_a_number(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaises(ValueError):
                record_series_header(folder, citation_url=METI_IIP_URL, value="107.7")
            self.assertEqual(list(folder.iterdir()), [])

    def test_stores_each_printed_figure_with_its_label(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "meti-printed-figures.json"
            meti_printed_figures.record_printed_figures(path, METI_IIP_URL, PAGE)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            stored["figures"],
            [
                {"value": "107.7", "label": "原指数"},
                {"value": "104.1", "label": "速報値"},
                {"value": "2.0", "label": "前月比（％）"},
                {"value": "1.7", "label": "前年同月比（％）"},
            ],
        )
        self.assertEqual(stored["base"], "2020年＝100")
        self.assertEqual(stored["base_label"], "base")
        self.assertEqual(stored["period"], "2026年9月分")
        self.assertEqual(stored["series"], "生産")
        self.assertEqual(stored["citation_url"], METI_IIP_URL)
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertEqual(stored["class_c_policy"], "closed")
        self.assertNotIn("permits_financial_use_test", stored)
        values = [item["value"] for item in stored["figures"]]
        self.assertNotIn("103.9", values)
        self.assertNotIn(stored["base"], values)
        text = json.dumps(stored)
        for leftover in (
            "103.9",
            "107.9",
            "94.4",
            "108.9",
            "108.4",
            "104.6",
            "3.4",
            "0.2",
            "trade",
            "permits_financial_use_test",
        ):
            self.assertNotIn(leftover, text)

    def test_missing_row_or_other_page_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "meti-printed-figures.json"
            with self.assertRaises(ValueError):
                meti_printed_figures.record_printed_figures(
                    path,
                    METI_IIP_URL,
                    "結果の概要【2026年9月分】鉱工業指数、2020年＝100",
                )
            for source in (DOWNLOAD, TERMS):
                with self.assertRaises(ValueError):
                    meti_printed_figures.record_printed_figures(
                        path,
                        METI_IIP_URL,
                        PAGE,
                        source_url=source,
                    )
            self.assertFalse(path.exists())

    def test_reading_the_figures_writes_no_trade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "meti-printed-figures.json"
            meti_printed_figures.record_printed_figures(path, METI_IIP_URL, PAGE)
            before = path.read_text(encoding="utf-8")
            stored = json.loads(before)
            after = path.read_text(encoding="utf-8")
            names = sorted(item.name for item in folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names, ["meti-printed-figures.json"])
        self.assertFalse((folder / "trade.json").exists())
        self.assertEqual(stored["base_label"], "base")
        self.assertFalse(stored["permits_financial_use"])
        self.assertNotIn("103.9", after)
        self.assertNotIn("trade", after)

    def test_trade_or_test_switch_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "meti-printed-figures.json"
            for label in ("trade", "quantity of goods", "2.0％"):
                with self.assertRaises(ValueError):
                    meti_printed_figures.record_printed_figures(
                        path,
                        METI_IIP_URL,
                        PAGE,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                meti_printed_figures.record_printed_figures(
                    path,
                    METI_IIP_URL,
                    PAGE,
                    permits_financial_use=True,
                )
            with self.assertRaises(ValueError):
                meti_printed_figures.record_printed_figures(
                    path,
                    METI_IIP_URL,
                    PAGE,
                    permits_financial_use_test=True,
                )
            with self.assertRaises(ValueError):
                meti_printed_figures.record_printed_figures(
                    path,
                    METI_IIP_URL,
                    PAGE,
                    class_c_policy="open",
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_figures(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("meti_printed_figures", text)
            self.assertNotIn("meti_iip", text)
            self.assertNotIn("tyo/iip/result-1", text)


if __name__ == "__main__":
    unittest.main()
