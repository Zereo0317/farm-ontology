import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology import finance_gate
from farm_ontology.policy import CLASS_C_POLICY


class FinanceGateTest(unittest.TestCase):
    def test_gate_stays_closed_and_writes_no_price_or_trade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "finance-gate.json"
            result = finance_gate.record_finance_gate(path, None)
            stored = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(result["gate"], "closed")
        self.assertEqual(
            stored,
            {
                "gate": "closed",
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertFalse(stored["permits_financial_use"])
        self.assertNotIn("price", stored)
        self.assertNotIn("trade", stored)
        self.assertNotIn("yield", stored)
        self.assertNotIn("settlement", stored)

    def test_missing_records_stay_closed(self) -> None:
        cases = (
            {},
            {"license_page": {"http_status": 403, "body": "license"}},
            {"license_page": {"http_status": 200, "body": "403 Forbidden"}},
            {
                "license_page": {"http_status": 200, "body": "license page"},
                "license_text": {
                    "text": "storage is not permitted",
                    "permits_storing_settlement_prices": False,
                },
            },
            {
                "license_page": {"http_status": 200, "body": "license page"},
                "license_text": {
                    "text": "present",
                    "permits_storing_settlement_prices": True,
                },
                "settlement": {"kind": "settlement"},
            },
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "finance-gate.json"
            for records in cases:
                stored = finance_gate.record_finance_gate(path, records)
                self.assertEqual(stored["gate"], "closed")
                self.assertNotIn("price", stored)
                self.assertNotIn("trade", stored)

    def test_price_yield_and_trade_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "finance-gate.json"
            for kwargs in (
                {"price": "not stored"},
                {"yield_value": "not stored"},
                {"trade": "not stored"},
                {"label": "settlement"},
            ):
                with self.assertRaises(ValueError):
                    finance_gate.record_finance_gate(path, None, **kwargs)
            self.assertFalse(path.exists())

    def test_financial_use_is_not_set_true(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "finance-gate.json"
            with self.assertRaises(ValueError):
                finance_gate.record_finance_gate(
                    path,
                    None,
                    permits_financial_use=True,
                )
            self.assertFalse(path.exists())

    def test_opening_condition_is_stated_and_no_sample_is_stored(self) -> None:
        source = Path(finance_gate.__file__).read_text(encoding="utf-8")
        self.assertEqual(
            finance_gate.OPEN_CONDITION,
            "The gate returns open only when three records all exist: "
            "a license page that loaded (HTTP success, not a 403 body), "
            "license text that permits storing settlement prices, "
            "and one settlement print with a citation_url.",
        )
        self.assertIn("None of those records exist", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("cmegroup.com", source)
        self.assertEqual(finance_gate.gate_status(None), "closed")
        self.assertEqual(finance_gate.gate_status({}), "closed")


if __name__ == "__main__":
    unittest.main()
