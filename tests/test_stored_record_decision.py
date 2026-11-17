import tempfile
import unittest
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY
from farm_ontology.stored_record_decision import (
    decision_statement,
    record_decision_statement,
)

STATEMENT = (
    "A stored national crop total is not a farm yield and not a completed harvest "
    "when the source marks the column as a forecast.\n"
    "A stored reanalysis temperature, wind component, or dewpoint is not relative "
    "humidity and not a harvest.\n"
    "A stored topsoil class share is not volumetric soil moisture.\n"
    "A stored water withdrawal and a stored flight count are not prices.\n"
    "An index is not a quantity of goods.\n"
    "A request to record a trade, a settlement, or financial use raises and writes "
    "nothing while permits_financial_use is false.\n"
)


class StoredRecordDecisionTest(unittest.TestCase):
    def test_statement_refuses_trade_settlement_and_financial_use(self) -> None:
        statement = decision_statement()
        self.assertEqual(statement, STATEMENT)
        self.assertEqual(CLASS_C_POLICY, "closed")
        self.assertFalse(any(character.isdigit() for character in statement))

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stored-record-decision.txt"
            for ask in ("trade", "settlement", "financial use", " Trade ", "Settlement"):
                with self.assertRaises(ValueError):
                    record_decision_statement(path, ask=ask)
                self.assertFalse(path.exists())
            with self.assertRaises(ValueError):
                record_decision_statement(path, permits_financial_use=True)
            self.assertFalse(path.exists())

            written = record_decision_statement(path)
            self.assertEqual(written, statement)
            self.assertEqual(path.read_text(encoding="utf-8"), statement)
