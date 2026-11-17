import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology import smap_l1a_radiometer
from farm_ontology.policy import CLASS_C_POLICY


class SmapL1aTimeTest(unittest.TestCase):
    def test_stores_the_printed_time_range(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "smap-l1a.json"
            smap_l1a_radiometer.record_smap_l1a_time(path, smap_l1a_radiometer.ISO_URL)
            header = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            header,
            {
                "product": "L1A_Radiometer",
                "begin": "2026-11-16T21:58:29.862Z",
                "end": "2026-11-16T22:51:51.299Z",
                "citation_url": smap_l1a_radiometer.ISO_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(header["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(header)
        self.assertNotIn("0.554946899414062", text)
        self.assertNotIn("brightness", text)
        self.assertNotIn("-76.93", text)

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "smap-l1a.json"
            with self.assertRaises(ValueError):
                smap_l1a_radiometer.record_smap_l1a_time(path, None)
            with self.assertRaises(ValueError):
                smap_l1a_radiometer.record_smap_l1a_time(path, "   ")
            self.assertFalse(path.exists())

    def test_other_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "smap-l1a.json"
            with self.assertRaises(ValueError):
                smap_l1a_radiometer.record_smap_l1a_time(
                    path, smap_l1a_radiometer.ISO_URL + "/"
                )
            with self.assertRaises(ValueError):
                smap_l1a_radiometer.record_smap_l1a_time(
                    path, "https://nsidc.org/data/spl1ap"
                )
            self.assertFalse(path.exists())

    def test_rejected_labels_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "smap-l1a.json"
            for label in (
                "pixel",
                "soil moisture",
                "brightness temperature",
                "Percent of Missing Data",
                "yield",
            ):
                with self.assertRaises(ValueError):
                    smap_l1a_radiometer.record_smap_l1a_time(
                        path,
                        smap_l1a_radiometer.ISO_URL,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                smap_l1a_radiometer.record_smap_l1a_time(
                    path,
                    smap_l1a_radiometer.ISO_URL,
                    begin="2026-11-16T21:58:29.862Z",
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_invent_a_temperature(self) -> None:
        source = (
            Path(smap_l1a_radiometer.__file__).read_text(encoding="utf-8").replace("\n", " ")
        )
        self.assertIn("Percent of Missing Data is not soil moisture", source)
        self.assertIn("not a measurement of the ground", source)
        self.assertIn("No brightness temperature is invented", source)
        self.assertIn("swath polygon is not stored", source)
        self.assertNotIn("field_save", source)


if __name__ == "__main__":
    unittest.main()
