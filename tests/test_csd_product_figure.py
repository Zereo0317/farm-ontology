import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import csd_product_figure
from farm_ontology.csd_industrial import CSD_INDUSTRIAL_URL, record_series_header
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
PAGE = (
    "<p>Index of Industrial Production for Manufacturing and Waste Management "
    "Sectors (Year 2015=100)</p>"
    "<p>Manufacturing (Year-on-year % change)</p>"
    '<a href="web_table.html?id=610-65001"></a>'
    '<script>var cdm_text_file = "page_Mnf_lang.json";</script>'
)
WEB_TABLE = "https://www.censtatd.gov.hk/en/web_table.html?id=610-65001"


class CsdProductFigureTests(unittest.TestCase):
    def test_header_still_rejects_a_figure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaises(ValueError):
                record_series_header(folder, citation_url=CSD_INDUSTRIAL_URL, value="100")
            self.assertEqual(list(folder.iterdir()), [])

    def test_stores_the_printed_product_line_figure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "csd-product-figure.json"
            csd_product_figure.record_product_figure(path, CSD_INDUSTRIAL_URL, PAGE)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["value"], "100")
        self.assertEqual(stored["period"], "Year 2015")
        self.assertEqual(stored["kind"], "index")
        self.assertEqual(stored["citation_url"], CSD_INDUSTRIAL_URL)
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertEqual(stored["class_c_policy"], "closed")
        self.assertNotIn("unit", stored)
        self.assertNotIn("administrative_area", stored)
        self.assertNotIn("permits_financial_use_test", stored)
        text = json.dumps(stored)
        for leftover in (
            "610-65001",
            "web_table",
            "Hong Kong",
            "%",
            "trade",
            "quantity",
            "page_Mnf_lang",
            "permits_financial_use_test",
        ):
            self.assertNotIn(leftover, text)

    def test_missing_figure_or_web_table_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "csd-product-figure.json"
            with self.assertRaises(ValueError):
                csd_product_figure.record_product_figure(
                    path,
                    CSD_INDUSTRIAL_URL,
                    "<p>Manufacturing (Year-on-year % change)</p>",
                )
            with self.assertRaises(ValueError):
                csd_product_figure.record_product_figure(
                    path,
                    CSD_INDUSTRIAL_URL,
                    PAGE,
                    source_url=WEB_TABLE,
                )
            with self.assertRaises(ValueError):
                csd_product_figure.record_product_figure(path, WEB_TABLE, PAGE)
            self.assertFalse(path.exists())

    def test_reading_the_figure_writes_no_trade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "csd-product-figure.json"
            csd_product_figure.record_product_figure(path, CSD_INDUSTRIAL_URL, PAGE)
            before = path.read_text(encoding="utf-8")
            stored = json.loads(before)
            after = path.read_text(encoding="utf-8")
            names = sorted(item.name for item in folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names, ["csd-product-figure.json"])
        self.assertFalse((folder / "trade.json").exists())
        self.assertEqual(stored["value"], "100")
        self.assertFalse(stored["permits_financial_use"])
        self.assertNotIn("trade", after)

    def test_trade_or_test_switch_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "csd-product-figure.json"
            for label in ("trade", "quantity of goods", "100"):
                with self.assertRaises(ValueError):
                    csd_product_figure.record_product_figure(
                        path,
                        CSD_INDUSTRIAL_URL,
                        PAGE,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                csd_product_figure.record_product_figure(
                    path,
                    CSD_INDUSTRIAL_URL,
                    PAGE,
                    permits_financial_use=True,
                )
            with self.assertRaises(ValueError):
                csd_product_figure.record_product_figure(
                    path,
                    CSD_INDUSTRIAL_URL,
                    PAGE,
                    permits_financial_use_test=True,
                )
            with self.assertRaises(ValueError):
                csd_product_figure.record_product_figure(
                    path,
                    CSD_INDUSTRIAL_URL,
                    PAGE,
                    class_c_policy="open",
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_figure(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("csd_product_figure", text)
            self.assertNotIn("csd_industrial", text)
            self.assertNotIn("scode310", text)


if __name__ == "__main__":
    unittest.main()
