import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import mospi_quick_estimate
from farm_ontology.mospi_iip import MOSPI_IIP_URL, record_series_header
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
RELEASE = mospi_quick_estimate.RELEASE_URL
PRINTED = (
    "Quick Estimates of Index of Industrial Production for the Month of "
    "September 2026 (Base 2022-23=100). "
    "The Quick Estimate of IIP stands at 124.3 against 116.5 in September 2025. "
    "The IIP growth rate for the month of September 2026 is 6.7 percent. "
    "The indices of Industrial Production for Mining and Manufacturing "
    "stand at 90.4 and 128.0."
)


class MospiQuickEstimateTests(unittest.TestCase):
    def test_header_still_rejects_an_index_number(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaises(ValueError):
                record_series_header(folder, citation_url=MOSPI_IIP_URL, value="124.3")
            self.assertEqual(list(folder.iterdir()), [])

    def test_stores_the_printed_all_india_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mospi-quick-estimate.json"
            mospi_quick_estimate.record_quick_estimate(path, RELEASE, PRINTED)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["value"], "124.3")
        self.assertEqual(stored["period"], "September 2026")
        self.assertEqual(stored["administrative_area"], "all India")
        self.assertEqual(stored["kind"], "index")
        self.assertEqual(stored["citation_url"], RELEASE)
        self.assertFalse(stored["permits_financial_use"])
        self.assertTrue(stored["permits_financial_use_test"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertEqual(stored["class_c_policy"], "closed")
        text = json.dumps(stored)
        for leftover in (
            "116.5",
            "90.4",
            "128.0",
            "6.7",
            "%",
            "trade",
            "settlement",
            "price",
            "harvest",
            "esankhyiki",
        ):
            self.assertNotIn(leftover, text)
        self.assertNotIn("settlement", stored)
        self.assertNotEqual(stored["kind"], "trade")

    def test_missing_number_or_other_citation_writes_nothing(self) -> None:
        growth_only = "The IIP growth rate for September 2026 is 6.7 percent."
        two_levels = (
            "The Quick Estimate of IIP stands at 124.3. "
            "The Quick Estimate of IIP stands at 116.5."
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mospi-quick-estimate.json"
            for body in (growth_only, two_levels, ""):
                with self.assertRaises(ValueError):
                    mospi_quick_estimate.record_quick_estimate(path, RELEASE, body)
            with self.assertRaises(ValueError):
                mospi_quick_estimate.record_quick_estimate(path, MOSPI_IIP_URL, PRINTED)
            self.assertFalse(path.exists())

    def test_reading_the_index_writes_no_trade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "mospi-quick-estimate.json"
            mospi_quick_estimate.record_quick_estimate(path, RELEASE, PRINTED)
            before = path.read_text(encoding="utf-8")
            stored = json.loads(before)
            after = path.read_text(encoding="utf-8")
            names = sorted(item.name for item in folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names, ["mospi-quick-estimate.json"])
        self.assertFalse((folder / "trade.json").exists())
        self.assertFalse(stored["permits_financial_use"])
        self.assertTrue(stored["permits_financial_use_test"])
        self.assertEqual(stored["value"], "124.3")
        self.assertNotIn("trade", after)
        self.assertNotIn("settlement", after)

    def test_trade_or_open_class_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mospi-quick-estimate.json"
            for label in ("trade", "settlement price", "quantity of goods", "6.7%"):
                with self.assertRaises(ValueError):
                    mospi_quick_estimate.record_quick_estimate(
                        path,
                        RELEASE,
                        PRINTED,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                mospi_quick_estimate.record_quick_estimate(
                    path,
                    RELEASE,
                    PRINTED,
                    permits_financial_use=True,
                )
            with self.assertRaises(ValueError):
                mospi_quick_estimate.record_quick_estimate(
                    path,
                    RELEASE,
                    PRINTED,
                    permits_financial_use_test=False,
                )
            with self.assertRaises(ValueError):
                mospi_quick_estimate.record_quick_estimate(
                    path,
                    RELEASE,
                    PRINTED,
                    class_c_policy="open",
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_estimate(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("mospi_quick_estimate", text)
            self.assertNotIn("mospi_iip", text)
            self.assertNotIn("54-index-of-industrial-production", text)


if __name__ == "__main__":
    unittest.main()
