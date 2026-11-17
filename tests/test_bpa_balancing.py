import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology import bpa_balancing
from farm_ontology.policy import CLASS_C_POLICY


class BpaBalancingTest(unittest.TestCase):
    def test_stores_the_last_filled_row(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bpa.json"
            bpa_balancing.record_bpa_balancing(path, bpa_balancing.BPA_URL)
            header = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            header,
            {
                "timestamp": "11/16/2026 17:50",
                "basis": "Based on 5-min MW readings",
                "unit": "MW",
                "load": {"role": "demand", "value": 8154},
                "generation": {
                    "VER": 128,
                    "Hydro": 9147,
                    "Fossil/Biomass": 1172,
                    "Nuclear": 1155,
                },
                "citation_url": bpa_balancing.BPA_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(header["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(header)
        self.assertNotIn("forecast", text)
        self.assertNotIn("settlement", text)
        self.assertNotIn("trade", text)
        self.assertNotIn("17:55", text)

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bpa.json"
            with self.assertRaises(ValueError):
                bpa_balancing.record_bpa_balancing(path, None)
            with self.assertRaises(ValueError):
                bpa_balancing.record_bpa_balancing(path, "   ")
            self.assertFalse(path.exists())

    def test_other_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bpa.json"
            with self.assertRaises(ValueError):
                bpa_balancing.record_bpa_balancing(path, bpa_balancing.BPA_URL + "/")
            self.assertFalse(path.exists())

    def test_rejected_labels_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bpa.json"
            for label in ("forecast", "settlement", "trade", "yield"):
                with self.assertRaises(ValueError):
                    bpa_balancing.record_bpa_balancing(
                        path, bpa_balancing.BPA_URL, label=label
                    )
            with self.assertRaises(ValueError):
                bpa_balancing.record_bpa_balancing(
                    path, bpa_balancing.BPA_URL, load=8154
                )
            self.assertFalse(path.exists())

    def test_field_save_keeps_load_as_demand(self) -> None:
        source = Path(bpa_balancing.__file__).read_text(encoding="utf-8")
        self.assertIn("Load is demand", source)
        self.assertIn("are generation", source)
        self.assertIn("not a forecast", source)
        self.assertNotIn("field_save", source)


if __name__ == "__main__":
    unittest.main()
