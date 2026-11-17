import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import mospi_comparison
from farm_ontology.mospi_iip import MOSPI_IIP_URL, record_series_header
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
RELEASE = mospi_comparison.RELEASE_URL
PRINTED = (
    "The Quick Estimate of IIP stands at 124.3 against 116.5 in September 2025. "
    "The indices stand at 90.4 and 128.0."
)


class MospiComparisonTests(unittest.TestCase):
    def test_header_still_rejects_an_index_number(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaises(ValueError):
                record_series_header(folder, citation_url=MOSPI_IIP_URL, value="116.5")
            self.assertEqual(list(folder.iterdir()), [])

    def test_stores_the_printed_september_2025_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mospi-comparison.json"
            mospi_comparison.record_september_2025_comparison(path, RELEASE, PRINTED)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["value"], "116.5")
        self.assertEqual(stored["label"], "printed September 2025 comparison")
        self.assertEqual(stored["period"], "September 2025")
        self.assertEqual(stored["kind"], "comparison")
        self.assertNotEqual(stored["kind"], "index")
        self.assertNotEqual(stored["period"], "September 2026")
        self.assertEqual(stored["administrative_area"], "all India")
        self.assertEqual(stored["citation_url"], RELEASE)
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertEqual(stored["class_c_policy"], "closed")
        self.assertNotIn("permits_financial_use_test", stored)
        text = json.dumps(stored)
        for leftover in ("124.3", "90.4", "128.0", "settlement", "price", "trade"):
            self.assertNotIn(leftover, text)
        self.assertNotIn("permits_financial_use_test", text)

    def test_other_numbers_or_citations_write_nothing(self) -> None:
        index_only = "The Quick Estimate of IIP stands at 124.3."
        two_comparisons = (
            "against 116.5 in September 2025. against 100.0 in September 2025."
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mospi-comparison.json"
            for body in (index_only, two_comparisons, ""):
                with self.assertRaises(ValueError):
                    mospi_comparison.record_september_2025_comparison(path, RELEASE, body)
            with self.assertRaises(ValueError):
                mospi_comparison.record_september_2025_comparison(
                    path,
                    MOSPI_IIP_URL,
                    PRINTED,
                )
            self.assertFalse(path.exists())

    def test_reading_the_comparison_writes_no_trade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "mospi-comparison.json"
            mospi_comparison.record_september_2025_comparison(path, RELEASE, PRINTED)
            before = path.read_text(encoding="utf-8")
            stored = json.loads(before)
            after = path.read_text(encoding="utf-8")
            names = sorted(item.name for item in folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names, ["mospi-comparison.json"])
        self.assertFalse((folder / "trade.json").exists())
        self.assertEqual(stored["value"], "116.5")
        self.assertFalse(stored["permits_financial_use"])
        self.assertNotIn("permits_financial_use_test", stored)
        self.assertNotIn("trade", after)
        self.assertNotIn("124.3", after)

    def test_index_label_or_open_class_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mospi-comparison.json"
            for label in ("settlement price", "September 2026 index", "index", "124.3"):
                with self.assertRaises(ValueError):
                    mospi_comparison.record_september_2025_comparison(
                        path,
                        RELEASE,
                        PRINTED,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                mospi_comparison.record_september_2025_comparison(
                    path,
                    RELEASE,
                    PRINTED,
                    permits_financial_use=True,
                )
            with self.assertRaises(ValueError):
                mospi_comparison.record_september_2025_comparison(
                    path,
                    RELEASE,
                    PRINTED,
                    permits_financial_use_test=True,
                )
            with self.assertRaises(ValueError):
                mospi_comparison.record_september_2025_comparison(
                    path,
                    RELEASE,
                    PRINTED,
                    class_c_policy="open",
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_comparison(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("mospi_comparison", text)
            self.assertNotIn("mospi_iip", text)
            self.assertNotIn("54-index-of-industrial-production", text)


if __name__ == "__main__":
    unittest.main()
