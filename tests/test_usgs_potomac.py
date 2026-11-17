import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology import usgs_potomac
from farm_ontology.policy import CLASS_C_POLICY


class UsgsPotomacTest(unittest.TestCase):
    def test_stores_the_printed_observation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "potomac.json"
            usgs_potomac.record_usgs_potomac(path, usgs_potomac.USGS_URL)
            header = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            header,
            {
                "site": "POTOMAC RIVER NEAR WASH, DC LITTLE FALLS PUMP STA",
                "observed_at": "2026-11-16T19:50:00.000-05:00",
                "qualifier": "P",
                "streamflow": {"value": 1600, "unit": "ft3/s"},
                "gage_height": {"value": 2.73, "unit": "ft"},
                "citation_url": usgs_potomac.USGS_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(header["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(header)
        self.assertNotIn("2015", text)
        self.assertNotIn("withdrawal", text)
        self.assertNotIn("settlement", text)
        self.assertNotIn("trade", text)

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "potomac.json"
            with self.assertRaises(ValueError):
                usgs_potomac.record_usgs_potomac(path, None)
            with self.assertRaises(ValueError):
                usgs_potomac.record_usgs_potomac(path, "   ")
            self.assertFalse(path.exists())

    def test_other_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "potomac.json"
            swapped = (
                "https://waterservices.usgs.gov/nwis/iv/?sites=01646500"
                "&format=json&parameterCd=00060,00065&siteStatus=all"
            )
            with self.assertRaises(ValueError):
                usgs_potomac.record_usgs_potomac(path, swapped)
            with self.assertRaises(ValueError):
                usgs_potomac.record_usgs_potomac(path, usgs_potomac.USGS_URL + "/")
            self.assertFalse(path.exists())

    def test_rejected_labels_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "potomac.json"
            for label in ("annual withdrawal", "2015", "settlement", "trade"):
                with self.assertRaises(ValueError):
                    usgs_potomac.record_usgs_potomac(
                        path, usgs_potomac.USGS_URL, label=label
                    )
            with self.assertRaises(ValueError):
                usgs_potomac.record_usgs_potomac(
                    path, usgs_potomac.USGS_URL, streamflow=1600
                )
            self.assertFalse(path.exists())

    def test_field_save_is_not_an_annual_withdrawal(self) -> None:
        source = Path(usgs_potomac.__file__).read_text(encoding="utf-8")
        self.assertIn("not the 2015 annual withdrawal", source)
        self.assertNotIn("field_save", source)


if __name__ == "__main__":
    unittest.main()
