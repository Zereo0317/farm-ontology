import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import meti_terms
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]

FOOTER_LINK = (
    '<li><a href="https://www.meti.go.jp/main/rules.html">利用規約</a></li>'
)
TERMS_PAGE = """
<h1>利用規約</h1>
<p>経済産業省ウェブサイト（以下「当ウェブサイト」といいます。）で掲載・発信している情報（以下「コンテンツ」といいます。）の著作権は、特記されていない限り経済産業省に帰属し、権利表記の記載がない限り「<a href="https://www.digital.go.jp/resources/open_data/public_data_license_v1.0">公共データ利用規約（第1.0版）</a>」（PDL1.0）に準拠した利用条件の下で、利用することができます。</p>
<p>PDL1.0のうち、本サイト独自の出典記載例や本ルールの適用を受けないコンテンツ等サイトによって内容が異なる部分の情報については「PDL1.0に関する重要情報」を参照してください。</p>
<p>コンテンツを利用する際は出典を記載してください。出典の記載方法は以下のとおりです。</p>
<p>コンテンツを編集・加工等して利用する場合は、上記出典とは別に、編集・加工等を行ったことを記載してください。</p>
"""
DOWNLOAD_ONLY = '<a href="b2020_result-2.html">時系列データ等ダウンロード</a>'
BOOKLET_ONLY = '<a href="result/pdf/press/b2020_202609kj.pdf">概要、指数値一覧の冊子</a>'


class MetiTermsTests(unittest.TestCase):
    def test_linked_terms_page_prints_no_copying_sentence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "meti-terms.json"
            with self.assertRaises(ValueError):
                meti_terms.record_copying_sentence(
                    path,
                    meti_terms.RESULTS_URL,
                    FOOTER_LINK,
                    TERMS_PAGE,
                )
            self.assertEqual(list(folder.iterdir()), [])
            self.assertFalse(path.exists())
            self.assertFalse((folder / "trade.json").exists())

    def test_results_page_without_a_terms_link_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "meti-terms.json"
            for page in (
                '<script src="https://www.meti.go.jp/js_2017/footer.js"></script>',
                DOWNLOAD_ONLY,
                BOOKLET_ONLY,
                None,
                "   ",
            ):
                with self.assertRaises(ValueError):
                    meti_terms.record_copying_sentence(
                        path,
                        meti_terms.RESULTS_URL,
                        page,
                        TERMS_PAGE,
                    )
            self.assertFalse(path.exists())

    def test_missing_citation_or_other_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "meti-terms.json"
            for citation in (None, "", "   ", meti_terms.TERMS_URL):
                with self.assertRaises(ValueError):
                    meti_terms.record_copying_sentence(
                        path,
                        citation,
                        FOOTER_LINK,
                        TERMS_PAGE,
                    )
            self.assertFalse(path.exists())

    def test_index_or_trade_label_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "meti-terms.json"
            for label in ("trade", "quantity of goods", "index", "percent", "前月比"):
                with self.assertRaises(ValueError):
                    meti_terms.record_copying_sentence(
                        path,
                        meti_terms.RESULTS_URL,
                        FOOTER_LINK,
                        TERMS_PAGE,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                meti_terms.record_copying_sentence(
                    path,
                    meti_terms.RESULTS_URL,
                    FOOTER_LINK,
                    TERMS_PAGE,
                    permits_financial_use=True,
                )
            with self.assertRaises(ValueError):
                meti_terms.record_copying_sentence(
                    path,
                    meti_terms.RESULTS_URL,
                    FOOTER_LINK,
                    TERMS_PAGE,
                    class_c_policy="open",
                )
            self.assertFalse(path.exists())

    def test_a_printed_copying_sentence_is_not_an_index_or_a_trade(self) -> None:
        terms = "<p>Copying the page needs permission.</p>"
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "meti-terms.json"
            meti_terms.record_copying_sentence(
                path,
                meti_terms.RESULTS_URL,
                FOOTER_LINK,
                terms,
            )
            before = path.read_text(encoding="utf-8")
            stored = json.loads(before)
            after = path.read_text(encoding="utf-8")
            names = sorted(item.name for item in folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names, ["meti-terms.json"])
        self.assertFalse((folder / "trade.json").exists())
        self.assertEqual(stored["sentence"], "Copying the page needs permission.")
        self.assertEqual(stored["citation_url"], meti_terms.TERMS_URL)
        self.assertEqual(stored["kind"], "terms")
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertEqual(stored["class_c_policy"], "closed")
        for key in ("value", "index", "percent", "trade", "quantity"):
            self.assertNotIn(key, stored)
        self.assertNotIn("trade", after)
        self.assertNotIn("%", after)
        self.assertNotIn("＝", after)

    def test_an_index_mark_inside_a_copying_sentence_writes_nothing(self) -> None:
        terms = "<p>Copying the index 2020年＝100 is not stored.</p>"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "meti-terms.json"
            with self.assertRaises(ValueError):
                meti_terms.record_copying_sentence(
                    path,
                    meti_terms.RESULTS_URL,
                    FOOTER_LINK,
                    terms,
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_terms_page(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("meti_terms", text)
            self.assertNotIn("main/rules.html", text)


if __name__ == "__main__":
    unittest.main()
