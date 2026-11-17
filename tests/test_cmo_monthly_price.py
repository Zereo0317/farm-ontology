import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology import cmo_monthly_price
from farm_ontology.policy import CLASS_C_POLICY


class CmoMonthlyPriceTest(unittest.TestCase):
    def test_stores_the_printed_price_cell(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cmo-monthly-price.json"
            cmo_monthly_price.record_cmo_monthly_price(
                path,
                cmo_monthly_price.CMO_MONTHLY_URL,
            )
            header = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            header,
            {
                "series": "Crude oil, average",
                "period": "2026M10",
                "unit": "($/bbl)",
                "value": 108.5,
                "citation_url": cmo_monthly_price.CMO_MONTHLY_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(header["class_c_policy"], CLASS_C_POLICY)
        self.assertIs(header["permits_financial_use"], False)
        text = json.dumps(header)
        self.assertNotIn("settlement", text)
        self.assertNotIn("yield", text)
        self.assertNotIn("trade", text)

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cmo-monthly-price.json"
            with self.assertRaises(ValueError):
                cmo_monthly_price.record_cmo_monthly_price(path, None)
            with self.assertRaises(ValueError):
                cmo_monthly_price.record_cmo_monthly_price(path, "   ")
            self.assertFalse(path.exists())

    def test_other_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cmo-monthly-price.json"
            for citation in (
                cmo_monthly_price.CMO_MONTHLY_URL + "/",
                "https://www.worldbank.org/en/research/commodity-markets",
            ):
                with self.assertRaises(ValueError):
                    cmo_monthly_price.record_cmo_monthly_price(path, citation)
            self.assertFalse(path.exists())

    def test_settlement_yield_or_trade_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cmo-monthly-price.json"
            for label in ("settlement", "yield", "trade", "Settlement", "YIELD"):
                with self.assertRaises(ValueError):
                    cmo_monthly_price.record_cmo_monthly_price(
                        path,
                        cmo_monthly_price.CMO_MONTHLY_URL,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                cmo_monthly_price.record_cmo_monthly_price(
                    path,
                    cmo_monthly_price.CMO_MONTHLY_URL,
                    permits_financial_use=True,
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_price(self) -> None:
        source = (
            Path(cmo_monthly_price.__file__).read_text(encoding="utf-8").replace("\n", " ")
        )
        self.assertIn("not a settlement, not a yield, and not a trade", source)
        self.assertIn("permits_financial_use stays false", source)
        self.assertNotIn("field_save", source)


if __name__ == "__main__":
    unittest.main()
