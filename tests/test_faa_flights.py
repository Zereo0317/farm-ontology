import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.faa_flights import FAA_BY_THE_NUMBERS_URL, record_flights

ROOT = Path(__file__).resolve().parents[1]
URL = FAA_BY_THE_NUMBERS_URL


class FaaFlightsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_the_printed_flight_and_passenger_figures(self):
        saved = record_flights(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Federal Aviation Administration")
        self.assertEqual(header["product"], "Air Traffic By The Numbers")
        self.assertEqual(header["period"], "FY24")
        self.assertEqual(header["flights"], "more than 44,000")
        self.assertEqual(header["passengers"], "more than 3 million")
        self.assertEqual(header["citation_url"], "https://www.faa.gov/air_traffic/by_the_numbers")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(header["class_c_policy"], "closed")
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        self.assertNotIn("29 million", text)
        self.assertNotIn("866", text)
        self.assertNotIn("20591", text)
        source = (ROOT / "farm_ontology" / "faa_flights.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("The page prints more than 44,000 flights.", flat)
        self.assertIn("The page prints more than 3 million airline passengers.", flat)
        self.assertIn("more than 29 million square miles is airspace, not a flight figure.", flat)
        self.assertIn("The linked PDF was not opened.", flat)
        self.assertIn("permits_financial_use stays false.", flat)
        self.assertIn("Class C stays closed.", flat)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_flights(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://www.faa.gov/",
            "https://www.faa.gov/air_traffic/by_the_numbers/",
            "https://www.faa.gov/air_traffic/by_the_numbers/air-traffic-by-the-numbers-FY2024.pdf",
        ):
            with self.assertRaises(ValueError):
                record_flights(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_replaced_figures_and_trade_write_nothing(self):
        for label in ("yield", "trade", "Trade"):
            with self.assertRaises(ValueError):
                record_flights(self.folder, citation_url=URL, label=label)
        with self.assertRaises(ValueError):
            record_flights(self.folder, citation_url=URL, flights="44,000")
        with self.assertRaises(ValueError):
            record_flights(self.folder, citation_url=URL, passengers="3 million")
        with self.assertRaises(ValueError):
            record_flights(self.folder, citation_url=URL, permits_financial_use=True)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_faa_flights(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("faa_flights", text)
            self.assertNotIn("more than 44,000", text)


if __name__ == "__main__":
    unittest.main()
