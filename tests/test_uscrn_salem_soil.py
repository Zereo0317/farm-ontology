import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology import uscrn_salem_soil
from farm_ontology.policy import CLASS_C_POLICY


class UscrnSalemSoilTest(unittest.TestCase):
    def _record(self, path: Path) -> None:
        uscrn_salem_soil.record_uscrn_salem_soil(
            path,
            uscrn_salem_soil.SALEM_DAILY_URL,
            unit_citation_url=uscrn_salem_soil.README_URL,
        )

    def test_stores_the_printed_soil_moisture_cell(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "salem-soil.json"
            self._record(path)
            header = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            header,
            {
                "station": "MO_Salem_10_W",
                "lst_date": "20261115",
                "series": "SOIL_MOISTURE_5_DAILY",
                "value": 0.123,
                "citation_url": uscrn_salem_soil.SALEM_DAILY_URL,
                "unit": "m^3/m^3",
                "unit_citation_url": uscrn_salem_soil.README_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(header["class_c_policy"], CLASS_C_POLICY)
        self.assertNotEqual(header["unit"], "m3/m3")
        text = json.dumps(header)
        self.assertNotIn("Biratori", text)
        self.assertNotIn("0.156", text)
        self.assertNotIn("NASS", text)

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "salem-soil.json"
            with self.assertRaises(ValueError):
                uscrn_salem_soil.record_uscrn_salem_soil(path, None)
            with self.assertRaises(ValueError):
                uscrn_salem_soil.record_uscrn_salem_soil(
                    path,
                    uscrn_salem_soil.SALEM_DAILY_URL,
                    unit_citation_url=None,
                )
            with self.assertRaises(ValueError):
                uscrn_salem_soil.record_uscrn_salem_soil(
                    path,
                    "   ",
                    unit_citation_url=uscrn_salem_soil.README_URL,
                )
            self.assertFalse(path.exists())

    def test_other_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "salem-soil.json"
            with self.assertRaises(ValueError):
                uscrn_salem_soil.record_uscrn_salem_soil(
                    path,
                    uscrn_salem_soil.README_URL,
                    unit_citation_url=uscrn_salem_soil.README_URL,
                )
            with self.assertRaises(ValueError):
                uscrn_salem_soil.record_uscrn_salem_soil(
                    path,
                    uscrn_salem_soil.SALEM_DAILY_URL + "/",
                    unit_citation_url=uscrn_salem_soil.README_URL,
                )
            self.assertFalse(path.exists())

    def test_rejected_labels_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "salem-soil.json"
            for label in ("Biratori", "NASS", "condition class", "yield", "trade"):
                with self.assertRaises(ValueError):
                    uscrn_salem_soil.record_uscrn_salem_soil(
                        path,
                        uscrn_salem_soil.SALEM_DAILY_URL,
                        unit_citation_url=uscrn_salem_soil.README_URL,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                uscrn_salem_soil.record_uscrn_salem_soil(
                    path,
                    uscrn_salem_soil.SALEM_DAILY_URL,
                    unit_citation_url=uscrn_salem_soil.README_URL,
                    value=0.123,
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_invent_the_unit(self) -> None:
        source = (
            Path(uscrn_salem_soil.__file__).read_text(encoding="utf-8").replace("\n", " ")
        )
        self.assertIn("not Biratori", source)
        self.assertIn("does not print a unit", source)
        self.assertIn("m^3/m^3", source)
        self.assertIn("NASS condition classes are not converted", source)
        self.assertNotIn("field_save", source)


if __name__ == "__main__":
    unittest.main()
