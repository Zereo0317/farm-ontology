import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.header_schema import read_stored_header
from farm_ontology.jodi_oil import JODI_OIL_OVERVIEW_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = JODI_OIL_OVERVIEW_URL


class JodiOilTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_quantity(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Joint Organisations Data Initiative")
        self.assertEqual(header["product"], "JODI-Oil World Database")
        self.assertEqual(
            header["period"],
            "monthly; the full CSV runs from January 2002 through data about one "
            "month old; the extended Beyond 20/20 file starts in January 2009; "
            "the database is updated on or around the 20th of each month",
        )
        self.assertEqual(
            header["unit"],
            "barrels, tonnes, and litres are the units named for the database; "
            "no quantity is stored",
        )
        self.assertEqual(
            header["administrative_area"],
            "participating country; more than 90 countries submit; "
            "this is not a world balance",
        )
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "compilation")
        self.assertFalse(header["permits_financial_use"])
        for key in ("value", "quantity", "price", "balance", "vintage"):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "settlement",
            "yield",
            "trade",
            "observation",
            "forecast",
            "vintage",
            "completed harvest",
            "public domain",
        ):
            self.assertNotIn(word, text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_reading_the_stored_record_writes_no_trade(self):
        saved = record_series_header(self.folder, citation_url=URL)
        path = self.folder / saved["file"]
        before = path.read_text(encoding="utf-8")
        record = json.loads(before)
        names_before = sorted(item.name for item in self.folder.iterdir())
        read = read_stored_header(record)
        self.assertIs(record["permits_financial_use"], False)
        self.assertIs(read["permits_financial_use"], False)
        self.assertNotIn("trade", read)
        self.assertNotIn("quantity", read)
        self.assertNotIn("price", read)
        self.assertNotIn("value", read)
        self.assertNotIn("trade", before)
        self.assertEqual(path.read_text(encoding="utf-8"), before)
        self.assertEqual(sorted(item.name for item in self.folder.iterdir()), names_before)
        self.assertEqual(names_before, ["jodi-oil-world-database.json"])

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        with self.assertRaises(ValueError):
            record_series_header(self.folder, citation_url="https://example.com/jodi.csv")
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "settlement",
            "yield",
            "trade",
            "observation",
            "forecast",
            "vintage",
            "world balance",
            "completed harvest",
            "Settlement",
            "YIELD",
            "Forecast",
            "Vintage",
            "World Balance",
            "Completed Harvest",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_jodi_series(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("jodi_oil", text)
            self.assertNotIn("jodidata.org", text)
