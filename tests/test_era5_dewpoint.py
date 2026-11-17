import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.era5_dewpoint import ERA5_DEWPOINT_URL, record_dewpoint

ROOT = Path(__file__).resolve().parents[1]
URL = ERA5_DEWPOINT_URL


class Era5DewpointTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_dewpoint_with_the_request_url(self):
        saved = record_dewpoint(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["image_id"], "ECMWF/ERA5_LAND/DAILY_AGGR/20261108")
        self.assertEqual(header["band"], "dewpoint_temperature_2m")
        self.assertEqual(header["label"], "dewpoint")
        self.assertNotEqual(header["label"], "relative humidity")
        self.assertEqual(header["value"], 268.03877385457355)
        self.assertEqual(header["citation_url"], URL)
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(header["class_c_policy"], "closed")
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        self.assertIn("268.03877385457355", text)
        self.assertNotIn("relative humidity", text)
        self.assertNotIn("273.0963548024495", text)
        self.assertNotIn("u_component_of_wind_10m", text)
        self.assertNotIn("v_component_of_wind_10m", text)
        source = (ROOT / "farm_ontology" / "era5_dewpoint.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("The returned value is labeled dewpoint.", flat)
        self.assertIn("It is not relative humidity.", flat)
        self.assertIn("Relative humidity was not calculated.", flat)
        self.assertIn("A reanalysis is not a harvest.", flat)
        self.assertIn("permits_financial_use stays false.", flat)
        self.assertIn("Class C stays closed.", flat)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_dewpoint(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_DAILY_AGGR",
            "https://earthengine.googleapis.com/v1/projects/seges-ai/value:compute",
            "https://earthengine.googleapis.com/v1/projects/seges-ai/value:compute?alt=json&prettyPrint=false",
        ):
            with self.assertRaises(ValueError):
                record_dewpoint(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_yield_and_trade_labels_write_nothing(self):
        for label in ("yield", "Yield", "trade", "Trade", "relative humidity", "humidity"):
            with self.assertRaises(ValueError):
                record_dewpoint(self.folder, citation_url=URL, label=label)
        with self.assertRaises(ValueError):
            record_dewpoint(self.folder, citation_url=URL, value=1)
        with self.assertRaises(ValueError):
            record_dewpoint(self.folder, citation_url=URL, permits_financial_use=True)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_era5_dewpoint(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("era5_dewpoint", text)


if __name__ == "__main__":
    unittest.main()
