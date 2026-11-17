import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology import eia_spot_prices
from farm_ontology.policy import CLASS_C_POLICY


class EiaSpotPricesTest(unittest.TestCase):
    def test_stores_the_printed_louisiana_cells(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "eia.json"
            eia_spot_prices.record_eia_spot_prices(path, eia_spot_prices.EIA_URL)
            header = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            header,
            {
                "page_date": "November 16, 2026",
                "table": "Select Spot Prices for Delivery Today",
                "cells": [
                    {
                        "region": "Louisiana",
                        "product": "Natural Gas",
                        "value": 3.26,
                        "unit": "$/million Btu",
                    },
                    {
                        "region": "Louisiana",
                        "product": "Electricity",
                        "value": 29.75,
                        "unit": "$/MWh",
                    },
                ],
                "citation_url": eia_spot_prices.EIA_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(header["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(header)
        self.assertNotIn("NA", text)
        self.assertNotIn("6.96", text)
        self.assertNotIn("New England", text)
        self.assertNotIn("Nymex", text)
        self.assertNotIn("settlement", text)
        self.assertNotIn("trade", text)

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "eia.json"
            with self.assertRaises(ValueError):
                eia_spot_prices.record_eia_spot_prices(path, None)
            with self.assertRaises(ValueError):
                eia_spot_prices.record_eia_spot_prices(path, "   ")
            self.assertFalse(path.exists())

    def test_other_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "eia.json"
            with self.assertRaises(ValueError):
                eia_spot_prices.record_eia_spot_prices(
                    path, eia_spot_prices.EIA_URL + "/"
                )
            self.assertFalse(path.exists())

    def test_rejected_labels_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "eia.json"
            for label in ("futures", "NA", "settlement", "trade"):
                with self.assertRaises(ValueError):
                    eia_spot_prices.record_eia_spot_prices(
                        path, eia_spot_prices.EIA_URL, label=label
                    )
            with self.assertRaises(ValueError):
                eia_spot_prices.record_eia_spot_prices(
                    path, eia_spot_prices.EIA_URL, cells=[]
                )
            self.assertFalse(path.exists())

    def test_field_save_leaves_futures_and_na_out(self) -> None:
        source = Path(eia_spot_prices.__file__).read_text(encoding="utf-8")
        self.assertIn("futures table is not stored", source)
        self.assertIn("A cell that prints NA is not stored", source)
        self.assertIn("spark spread is not stored", source)
        self.assertNotIn("6.96", source)
        self.assertNotIn("field_save", source)


if __name__ == "__main__":
    unittest.main()
