import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import bps_production_level
from farm_ontology.bps_manufacturing_index import (
    BPS_MANUFACTURING_INDEX_URL,
    record_series_header,
)
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
FETCHED = (
    "<title>Just a moment...</title>"
    "<p>Indeks Produksi Bulanan Industri Besar dan Sedang Menurut KBLI 2 Digit "
    "[KBLI 2020] (2010=100)</p>"
)
ONE = (
    "Indeks Produksi Bulanan Industri Besar dan Sedang (2010=100). "
    "Manufaktur September 2026 112,4."
)
TWO = (
    "Manufaktur September 2026 112,4. "
    "Manufaktur Oktober 2026 113,1. (2010=100)"
)
BULK = "https://www.bps.go.id/id/statistics-table/2/MjA3NyMy/download.xlsx"


class BpsProductionLevelTests(unittest.TestCase):
    def test_header_still_rejects_a_number(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaises(ValueError):
                record_series_header(
                    folder,
                    citation_url=BPS_MANUFACTURING_INDEX_URL,
                    label="2010=100",
                )
            self.assertEqual(list(folder.iterdir()), [])

    def test_fetched_page_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bps-production-level.json"
            with self.assertRaises(ValueError) as caught:
                bps_production_level.record_production_level(
                    path,
                    BPS_MANUFACTURING_INDEX_URL,
                    FETCHED,
                )
            self.assertIn("no production index level", str(caught.exception))
            self.assertFalse(path.exists())

    def test_one_printed_level_keeps_its_period_and_label(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bps-production-level.json"
            bps_production_level.record_production_level(
                path,
                BPS_MANUFACTURING_INDEX_URL,
                ONE,
            )
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["value"], "112,4")
        self.assertEqual(stored["period"], "September 2026")
        self.assertEqual(stored["label"], "Manufaktur")
        self.assertEqual(stored["base"], "2010=100")
        self.assertEqual(stored["base_label"], "base")
        self.assertNotEqual(stored["value"], stored["base"])
        self.assertEqual(stored["citation_url"], BPS_MANUFACTURING_INDEX_URL)
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertNotIn("permits_financial_use_test", stored)
        self.assertNotIn("administrative_area", stored)
        text = json.dumps(stored)
        for leftover in ("province", "national", "nasional", "Indonesia", "trade"):
            self.assertNotIn(leftover, text)

    def test_two_levels_or_a_bulk_file_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bps-production-level.json"
            with self.assertRaises(ValueError):
                bps_production_level.record_production_level(
                    path,
                    BPS_MANUFACTURING_INDEX_URL,
                    TWO,
                )
            with self.assertRaises(ValueError):
                bps_production_level.record_production_level(
                    path,
                    BPS_MANUFACTURING_INDEX_URL,
                    ONE,
                    source_url=BULK,
                )
            self.assertFalse(path.exists())

    def test_trade_or_test_switch_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bps-production-level.json"
            for label in ("trade", "quantity of goods", "nasional", "province", "112,4"):
                with self.assertRaises(ValueError):
                    bps_production_level.record_production_level(
                        path,
                        BPS_MANUFACTURING_INDEX_URL,
                        ONE,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                bps_production_level.record_production_level(
                    path,
                    BPS_MANUFACTURING_INDEX_URL,
                    ONE,
                    permits_financial_use=True,
                )
            with self.assertRaises(ValueError):
                bps_production_level.record_production_level(
                    path,
                    BPS_MANUFACTURING_INDEX_URL,
                    ONE,
                    permits_financial_use_test=True,
                )
            with self.assertRaises(ValueError):
                bps_production_level.record_production_level(
                    path,
                    BPS_MANUFACTURING_INDEX_URL,
                    ONE,
                    class_c_policy="open",
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_level(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("bps_production_level", text)
            self.assertNotIn("bps_manufacturing_index", text)
            self.assertNotIn("MjA3NyMy", text)


if __name__ == "__main__":
    unittest.main()
