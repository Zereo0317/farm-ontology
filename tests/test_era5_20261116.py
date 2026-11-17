import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.era5_20261116 import ERROR, HTTP_STATUS, record_missing_image

ROOT = Path(__file__).resolve().parents[1]


class Era5MissingImageTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_records_the_printed_http_400_and_missing_image_error(self):
        saved = record_missing_image(
            self.folder,
            http_status=HTTP_STATUS,
            error=ERROR,
        )
        header = saved["header"]
        self.assertEqual(header["http_status"], 400)
        self.assertEqual(
            header["error"],
            "Image.load: Image asset 'ECMWF/ERA5_LAND/DAILY_AGGR/20261116' "
            "not found (does not exist or caller does not have access).",
        )
        self.assertIn("ECMWF/ERA5_LAND/DAILY_AGGR/20261116", header["error"])
        self.assertIn("not found", header["error"])
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(header["class_c_policy"], "closed")
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        self.assertIn("400", text)
        self.assertIn(
            "Image.load: Image asset 'ECMWF/ERA5_LAND/DAILY_AGGR/20261116' "
            "not found (does not exist or caller does not have access).",
            text,
        )
        for word in (
            "temperature_2m",
            "u_component_of_wind_10m",
            "v_component_of_wind_10m",
            "dewpoint_temperature_2m",
            "dewpoint",
            "relative humidity",
            "20261108",
        ):
            self.assertNotIn(word, text, word)
        source = (ROOT / "farm_ontology" / "era5_20261116.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("The compute for ECMWF/ERA5_LAND/DAILY_AGGR/20261116 returned HTTP 400.", flat)
        self.assertIn("Temperature was not printed.", flat)
        self.assertIn("Wind was not printed.", flat)
        self.assertIn("Dewpoint was not printed.", flat)
        self.assertIn("The 20261108 values are not stored.", flat)
        self.assertIn("permits_financial_use stays false.", flat)
        self.assertIn("Class C stays closed.", flat)
        with self.assertRaises(ValueError):
            record_missing_image(
                self.folder,
                http_status=400,
                error=ERROR,
                value=1,
            )
        with self.assertRaises(ValueError):
            record_missing_image(
                self.folder,
                http_status=400,
                error=ERROR,
                permits_financial_use=True,
            )
        self.assertEqual(len(list(self.folder.iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
