import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology import ams_soybean_average_current
from farm_ontology.policy import CLASS_C_POLICY

LIVE_TEXT = """
Closing Settlement Prices (¢/bu) as of 11/16/2026
CBOT
Soybeans
1229.00 (Jan 27)
US #2  Yellow Corn  (Bulk)
Country Elevators - Conventional
Region/Location
Sale Type
Basis (¢/Bu)
Basis Change
Price($/Bu)
Price Change
Average Year Ago
Freight
Delivery
Northwest
Bid
-6.00Z to 40.00Z
UNCH
4.4275-4.8875
UP 0.0325
4.6896
4.0097
DLVD-T
Current
Grain Report for 11/16/2026 - Final
US #1  Soybeans  (Bulk)
Country Elevators - Conventional
Region/Location
Sale Type
Basis (¢/Bu)
Basis Change
Price($/Bu)
Price Change
Average Year Ago
Freight
Delivery
Northwest
Bid
-150.00F to -95.00F
UNCH
10.7900-11.3400
DN 0.0250
11.1600
10.2308
DLVD-T
Current
Southwest
Bid
-105.00F to -90.00F
UNCH
11.2400-11.3900
DN 0.0250
11.3275
10.4350
DLVD-T
Current
US #1 Hard Red Winter Wheat  (Bulk)
"""


class AmsSoybeanAverageCurrentTest(unittest.TestCase):
    def test_stores_the_printed_average(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "soybean-average.json"
            ams_soybean_average_current.record_ams_soybean_average_current(
                path,
                ams_soybean_average_current.AMS_URL,
                LIVE_TEXT,
            )
            stored = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            stored,
            {
                "commodity": "US #1  Soybeans  (Bulk)",
                "elevators": "Country Elevators - Conventional",
                "region": "Northwest",
                "sale_type": "Bid",
                "delivery": "Current",
                "report_date": "11/16/2026",
                "average": "11.1600",
                "unit": "$/Bu",
                "citation_url": ams_soybean_average_current.AMS_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(stored)
        self.assertNotIn("10.7900", text)
        self.assertNotIn("10.2308", text)
        self.assertNotIn("1229.00", text)
        self.assertNotIn("11.3275", text)
        self.assertNotIn("4.6896", text)
        self.assertNotIn("settlement", text)
        self.assertNotIn("trade", text)

    def test_failed_request_or_empty_body_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "soybean-average.json"
            with self.assertRaises(ValueError):
                ams_soybean_average_current.record_ams_soybean_average_current(
                    path,
                    ams_soybean_average_current.AMS_URL,
                    LIVE_TEXT,
                    request_failed=True,
                )
            with self.assertRaises(ValueError):
                ams_soybean_average_current.record_ams_soybean_average_current(
                    path,
                    ams_soybean_average_current.AMS_URL,
                    None,
                )
            self.assertFalse(path.exists())

    def test_missing_average_writes_nothing(self) -> None:
        missing = LIVE_TEXT.replace("11.1600\n", "\n", 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "soybean-average.json"
            with self.assertRaises(ValueError):
                ams_soybean_average_current.record_ams_soybean_average_current(
                    path,
                    ams_soybean_average_current.AMS_URL,
                    missing,
                )
            self.assertFalse(path.exists())

    def test_missing_date_writes_nothing(self) -> None:
        missing = LIVE_TEXT.replace("Grain Report for 11/16/2026 - Final", "Grain Report", 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "soybean-average.json"
            with self.assertRaises(ValueError):
                ams_soybean_average_current.record_ams_soybean_average_current(
                    path,
                    ams_soybean_average_current.AMS_URL,
                    missing,
                )
            self.assertFalse(path.exists())

    def test_missing_citation_or_rejected_label_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "soybean-average.json"
            with self.assertRaises(ValueError):
                ams_soybean_average_current.record_ams_soybean_average_current(
                    path, None, LIVE_TEXT
                )
            with self.assertRaises(ValueError):
                ams_soybean_average_current.record_ams_soybean_average_current(
                    path,
                    ams_soybean_average_current.AMS_URL + "/",
                    LIVE_TEXT,
                )
            for label in ("settlement", "executed trade", "trade"):
                with self.assertRaises(ValueError):
                    ams_soybean_average_current.record_ams_soybean_average_current(
                        path,
                        ams_soybean_average_current.AMS_URL,
                        LIVE_TEXT,
                        label=label,
                    )
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
