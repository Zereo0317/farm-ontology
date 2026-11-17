import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.era5_biratori import ERA5_BIRATORI_URL, record_era5_bands

ROOT = Path(__file__).resolve().parents[1]
URL = ERA5_BIRATORI_URL


class Era5BiratoriTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_returned_bands_with_the_request_url(self):
        saved = record_era5_bands(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["image_id"], "ECMWF/ERA5_LAND/DAILY_AGGR/20261108")
        self.assertEqual(
            [(item["band"], item["value"]) for item in header["bands"]],
            [
                ("temperature_2m", 273.0963548024495),
                ("u_component_of_wind_10m", 2.654146194458008),
                ("v_component_of_wind_10m", -1.241633415222168),
            ],
        )
        for item in header["bands"]:
            self.assertEqual(item["citation_url"], URL)
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(header["class_c_policy"], "closed")
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        self.assertIn("273.0963548024495", text)
        self.assertIn("2.654146194458008", text)
        self.assertIn("-1.241633415222168", text)
        self.assertIn(
            "https://earthengine.googleapis.com/v1/projects/seges-ai/value:compute?prettyPrint=false&alt=json",
            text,
        )
        for word in (
            "dewpoint",
            "relative_humidity",
            "relative humidity",
            "developers.google.com",
            "yield",
            "price",
            "trade",
            "1794096000000",
        ):
            self.assertNotIn(word, text, word)
        source = (ROOT / "farm_ontology" / "era5_biratori.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("The client exposed the request URL.", flat)
        self.assertIn("A catalog page is not the citation.", flat)
        self.assertIn("Relative humidity was not derived.", flat)
        self.assertIn("Dewpoint was not requested.", flat)
        self.assertIn("A reanalysis is not a completed harvest.", flat)
        self.assertIn("permits_financial_use stays false.", flat)
        self.assertIn("Class C stays closed.", flat)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_era5_bands(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_DAILY_AGGR",
            "https://earthengine.googleapis.com/v1/projects/seges-ai/value:compute",
            "https://earthengine.googleapis.com/v1/projects/seges-ai/value:compute?alt=json&prettyPrint=false",
            "https://earthengine.googleapis.com/v1/projects/seges-ai/value:compute?prettyPrint=false&alt=json/",
            "https://example.com/era5",
        ):
            with self.assertRaises(ValueError):
                record_era5_bands(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_yield_label_writes_nothing(self):
        for label in ("yield", "Yield", "YIELD"):
            with self.assertRaises(ValueError):
                record_era5_bands(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_trade_label_writes_nothing(self):
        for label in ("trade", "Trade", "TRADE", "price", "completed harvest"):
            with self.assertRaises(ValueError):
                record_era5_bands(self.folder, citation_url=URL, label=label)
        with self.assertRaises(ValueError):
            record_era5_bands(self.folder, citation_url=URL, value=1)
        with self.assertRaises(ValueError):
            record_era5_bands(self.folder, citation_url=URL, permits_financial_use=True)
        with self.assertRaises(ValueError):
            record_era5_bands(self.folder, citation_url=URL, class_c_policy="open")
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_era5_biratori(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("era5_biratori", text)
            self.assertNotIn("value:compute", text)


if __name__ == "__main__":
    unittest.main()
