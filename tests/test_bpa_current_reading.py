import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology import bpa_current_reading
from farm_ontology.policy import CLASS_C_POLICY

LIVE_BODY = """BPA Balancing Authority Load & Total Wind Generation
Based on 5-min MW readings from the BPA SCADA system for points 45583, 177167, 79682, 164377, 70681
It does not include BPA loads served by transfer, scheduled out of region,
or scheduled to customers with their own BAs such as Seattle and Tacoma

Date/Time	Load	VER	Hydro	Fossil/Biomass	Nuclear
11/16/2026 17:50	8154	128	9147	1172	1155
11/16/2026 18:05	8137	126	9049	1172	1154
11/16/2026 18:10					
"""


class BpaCurrentReadingTest(unittest.TestCase):
    def test_stores_the_printed_current_reading(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bpa-current.json"
            bpa_current_reading.record_bpa_current(
                path,
                bpa_current_reading.BPA_URL,
                LIVE_BODY,
            )
            stored = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            stored,
            {
                "timestamp": "11/16/2026 18:05",
                "unit": "MW",
                "Load": 8137,
                "VER": 126,
                "Hydro": 9049,
                "Fossil/Biomass": 1172,
                "Nuclear": 1154,
                "basis": "Based on 5-min MW readings",
                "citation_url": bpa_current_reading.BPA_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(stored)
        self.assertNotIn("17:50", text)
        self.assertNotIn("8154", text)
        self.assertNotIn("9147", text)
        self.assertNotIn("Seattle", text)
        self.assertNotIn("Tacoma", text)

    def test_failed_request_or_empty_body_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bpa-current.json"
            with self.assertRaises(ValueError):
                bpa_current_reading.record_bpa_current(
                    path,
                    bpa_current_reading.BPA_URL,
                    LIVE_BODY,
                    request_failed=True,
                )
            with self.assertRaises(ValueError):
                bpa_current_reading.record_bpa_current(
                    path,
                    bpa_current_reading.BPA_URL,
                    None,
                )
            with self.assertRaises(ValueError):
                bpa_current_reading.record_bpa_current(
                    path,
                    bpa_current_reading.BPA_URL,
                    "BPA Balancing Authority\n11/16/2026 18:10\n",
                )
            self.assertFalse(path.exists())

    def test_missing_unit_or_time_writes_nothing(self) -> None:
        no_unit = LIVE_BODY.replace("Based on 5-min MW readings", "Based on 5-min readings")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bpa-current.json"
            with self.assertRaises(ValueError):
                bpa_current_reading.record_bpa_current(
                    path,
                    bpa_current_reading.BPA_URL,
                    no_unit,
                )
            self.assertFalse(path.exists())

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bpa-current.json"
            with self.assertRaises(ValueError):
                bpa_current_reading.record_bpa_current(path, None, LIVE_BODY)
            with self.assertRaises(ValueError):
                bpa_current_reading.record_bpa_current(
                    path,
                    bpa_current_reading.BPA_URL + "/",
                    LIVE_BODY,
                )
            self.assertFalse(path.exists())

    def test_rejected_labels_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bpa-current.json"
            for label in ("trade", "settlement", "yield"):
                with self.assertRaises(ValueError):
                    bpa_current_reading.record_bpa_current(
                        path,
                        bpa_current_reading.BPA_URL,
                        LIVE_BODY,
                        label=label,
                    )
            self.assertFalse(path.exists())
            source = Path(bpa_current_reading.__file__).read_text(encoding="utf-8")
            self.assertNotIn("8154", source)
            self.assertNotIn("Seattle", source)


if __name__ == "__main__":
    unittest.main()
