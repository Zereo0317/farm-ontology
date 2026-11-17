import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.usgs_water_use import USGS_WATER_USE_URL, record_water_use

ROOT = Path(__file__).resolve().parents[1]
URL = USGS_WATER_USE_URL


class UsgsWaterUseTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_the_printed_2015_withdrawal(self):
        saved = record_water_use(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "U.S. Geological Survey")
        self.assertEqual(header["product"], "Total Water Use")
        self.assertEqual(header["period"], "2015")
        self.assertEqual(header["withdrawal"], "322,000 million gallons per day")
        self.assertEqual(header["unit"], "million gallons per day")
        self.assertEqual(
            header["citation_url"],
            "https://www.usgs.gov/mission-areas/water-resources/science/total-water-use",
        )
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(header["class_c_policy"], "closed")
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        self.assertIn("322,000 million gallons per day", text)
        self.assertNotIn("361,000", text)
        self.assertNotIn("87 percent", text)
        source = (ROOT / "farm_ontology" / "usgs_water_use.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("The page prints a 2015 total of 322,000 million gallons per day.", flat)
        self.assertIn("No volume was guessed.", flat)
        self.assertIn("permits_financial_use stays false.", flat)
        self.assertIn("Class C stays closed.", flat)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_water_use(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://www.usgs.gov/",
            URL + "/",
            "https://pubs.usgs.gov/circ/1441/circ1441.pdf",
        ):
            with self.assertRaises(ValueError):
                record_water_use(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_replaced_volume_and_trade_write_nothing(self):
        for label in ("yield", "trade", "Trade"):
            with self.assertRaises(ValueError):
                record_water_use(self.folder, citation_url=URL, label=label)
        with self.assertRaises(ValueError):
            record_water_use(self.folder, citation_url=URL, withdrawal="321,000 million gallons per day")
        with self.assertRaises(ValueError):
            record_water_use(self.folder, citation_url=URL, permits_financial_use=True)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_usgs_water_use(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("usgs_water_use", text)
            self.assertNotIn("322,000 million gallons per day", text)


if __name__ == "__main__":
    unittest.main()
