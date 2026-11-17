import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology import ams_soybean_bid
from farm_ontology.policy import CLASS_C_POLICY


class AmsSoybeanBidTest(unittest.TestCase):
    def test_stores_the_printed_cash_bid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "soybean-bid.json"
            ams_soybean_bid.record_ams_soybean_bid(path, ams_soybean_bid.AMS_URL)
            header = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            header,
            {
                "commodity": "US #1  Soybeans  (Bulk)",
                "elevators": "Country Elevators - Conventional",
                "region": "Northwest",
                "sale_type": "Bid",
                "delivery": "Current",
                "report_date": "11/16/2026",
                "price_range": "10.7900-11.3400",
                "average": "11.1600",
                "unit": "$/Bu",
                "citation_url": ams_soybean_bid.AMS_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(header["class_c_policy"], CLASS_C_POLICY)
        self.assertEqual(header["average"], "11.1600")
        text = json.dumps(header)
        self.assertNotIn("1229.00", text)
        self.assertNotIn("10.2308", text)
        self.assertNotIn("settlement", text)
        self.assertNotIn("trade", text)
        self.assertNotIn("Southwest", text)

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "soybean-bid.json"
            with self.assertRaises(ValueError):
                ams_soybean_bid.record_ams_soybean_bid(path, None)
            with self.assertRaises(ValueError):
                ams_soybean_bid.record_ams_soybean_bid(path, "   ")
            self.assertFalse(path.exists())

    def test_other_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "soybean-bid.json"
            with self.assertRaises(ValueError):
                ams_soybean_bid.record_ams_soybean_bid(
                    path, "https://mymarketnews.ams.usda.gov/viewReport/3225"
                )
            self.assertFalse(path.exists())

    def test_rejected_labels_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "soybean-bid.json"
            for label in ("settlement", "Closing Settlement Prices", "trade"):
                with self.assertRaises(ValueError):
                    ams_soybean_bid.record_ams_soybean_bid(
                        path, ams_soybean_bid.AMS_URL, label=label
                    )
            with self.assertRaises(ValueError):
                ams_soybean_bid.record_ams_soybean_bid(
                    path, ams_soybean_bid.AMS_URL, average="11.16"
                )
            self.assertFalse(path.exists())

    def test_field_save_leaves_the_settlement_block_out(self) -> None:
        source = Path(ams_soybean_bid.__file__).read_text(encoding="utf-8")
        self.assertIn("Closing Settlement Prices is not stored", source)
        self.assertIn("not labeled a settlement", source)
        self.assertNotIn("1229.00", source)
        self.assertNotIn("field_save", source)


if __name__ == "__main__":
    unittest.main()
