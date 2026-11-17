import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology import usgs_current_reading
from farm_ontology.policy import CLASS_C_POLICY

LIVE_BODY = json.dumps(
    {
        "value": {
            "timeSeries": [
                {
                    "sourceInfo": {
                        "siteName": "POTOMAC RIVER NEAR WASH, DC LITTLE FALLS PUMP STA",
                        "siteCode": [{"value": "01646500"}],
                    },
                    "variable": {
                        "variableCode": [{"value": "00060"}],
                        "unit": {"unitCode": "ft3/s"},
                    },
                    "values": [
                        {
                            "value": [
                                {
                                    "value": "1600",
                                    "dateTime": "2026-11-16T20:50:00.000-05:00",
                                }
                            ]
                        }
                    ],
                },
                {
                    "sourceInfo": {
                        "siteName": "POTOMAC RIVER NEAR WASH, DC LITTLE FALLS PUMP STA",
                        "siteCode": [{"value": "01646500"}],
                    },
                    "variable": {
                        "variableCode": [{"value": "00065"}],
                        "unit": {"unitCode": "ft"},
                    },
                    "values": [
                        {
                            "value": [
                                {
                                    "value": "2.73",
                                    "dateTime": "2026-11-16T20:50:00.000-05:00",
                                }
                            ]
                        }
                    ],
                },
            ]
        }
    }
)


class UsgsCurrentReadingTest(unittest.TestCase):
    def test_stores_the_printed_current_reading(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "usgs-current.json"
            usgs_current_reading.record_usgs_current(
                path,
                usgs_current_reading.USGS_URL,
                LIVE_BODY,
            )
            stored = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            stored,
            {
                "site": "POTOMAC RIVER NEAR WASH, DC LITTLE FALLS PUMP STA",
                "parameter": "00060",
                "value": 1600,
                "unit": "ft3/s",
                "observed_at": "2026-11-16T20:50:00.000-05:00",
                "citation_url": usgs_current_reading.USGS_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(stored)
        self.assertNotIn("19:50", text)
        self.assertNotIn("2.73", text)
        self.assertNotIn("01646580", text)

    def test_failed_request_or_empty_body_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "usgs-current.json"
            with self.assertRaises(ValueError):
                usgs_current_reading.record_usgs_current(
                    path,
                    usgs_current_reading.USGS_URL,
                    LIVE_BODY,
                    request_failed=True,
                )
            with self.assertRaises(ValueError):
                usgs_current_reading.record_usgs_current(
                    path,
                    usgs_current_reading.USGS_URL,
                    None,
                )
            with self.assertRaises(ValueError):
                usgs_current_reading.record_usgs_current(
                    path,
                    usgs_current_reading.USGS_URL,
                    '{"value": {"timeSeries": []}}',
                )
            self.assertFalse(path.exists())

    def test_missing_unit_or_time_writes_nothing(self) -> None:
        missing_time = json.dumps(
            {
                "value": {
                    "timeSeries": [
                        {
                            "sourceInfo": {
                                "siteName": "POTOMAC RIVER NEAR WASH, DC LITTLE FALLS PUMP STA",
                                "siteCode": [{"value": "01646500"}],
                            },
                            "variable": {
                                "variableCode": [{"value": "00060"}],
                                "unit": {"unitCode": "ft3/s"},
                            },
                            "values": [{"value": [{"value": "1600"}]}],
                        }
                    ]
                }
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "usgs-current.json"
            with self.assertRaises(ValueError):
                usgs_current_reading.record_usgs_current(
                    path,
                    usgs_current_reading.USGS_URL,
                    missing_time,
                )
            self.assertFalse(path.exists())

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "usgs-current.json"
            with self.assertRaises(ValueError):
                usgs_current_reading.record_usgs_current(path, None, LIVE_BODY)
            with self.assertRaises(ValueError):
                usgs_current_reading.record_usgs_current(
                    path,
                    usgs_current_reading.USGS_URL + "/",
                    LIVE_BODY,
                )
            self.assertFalse(path.exists())

    def test_rejected_labels_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "usgs-current.json"
            for label in ("trade", "settlement", "yield"):
                with self.assertRaises(ValueError):
                    usgs_current_reading.record_usgs_current(
                        path,
                        usgs_current_reading.USGS_URL,
                        LIVE_BODY,
                        label=label,
                    )
            self.assertFalse(path.exists())
            source = Path(usgs_current_reading.__file__).read_text(encoding="utf-8")
            self.assertNotIn("19:50", source)
            self.assertNotIn("01646580", source)


if __name__ == "__main__":
    unittest.main()
