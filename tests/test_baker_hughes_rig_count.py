import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.baker_hughes_rig_count import (
    BAKER_HUGHES_RIG_COUNT_URL,
    record_series_header,
)

ROOT = Path(__file__).resolve().parents[1]
URL = BAKER_HUGHES_RIG_COUNT_URL


class BakerHughesRigCountTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_rig_count(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Baker Hughes Company")
        self.assertEqual(header["product"], "rig count")
        self.assertEqual(
            header["period"],
            "North America is a weekly census released Friday at noon Central, "
            "described as the last workday of the week; the international count is a "
            "monthly average of weekly counts, and since February 2020 it is released "
            "on the last working day of the first week of the month; the overview says "
            "counts have been issued since 1944, when weekly U.S. and Canadian counts "
            "began, and that the monthly international count began in 1975; a "
            "historical-file page lists annual archives that include 1968 through 1999; "
            "this pass did not confirm a file for every year back to 1944",
        )
        self.assertEqual(
            header["unit"],
            "a census of active drilling rigs; this is drilling activity, not oil "
            "supply; no rig count is stored",
        )
        self.assertEqual(
            header["administrative_area"],
            "North America covers rigs exploring for or developing oil, natural gas, "
            "or geothermal energy in the United States and Canada; the international "
            "count is outside North America; the FAQ says it does not include rigs "
            "drilling in Russia, the Caspian region, Iran, Sudan, Cuba, North Korea, "
            "or onshore China; Iraq was excluded from September 1990 to May 2012; "
            "Syria has been excluded since February 2012; Saudi Arabia reports "
            "operating rigs rather than the active-rig definition used elsewhere",
        )
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "survey")
        self.assertFalse(header["permits_financial_use"])
        for key in ("value", "rig_count", "count", "barrels", "forecast", "oil_supply"):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "settlement",
            "yield",
            "trade",
            "forecast",
            "observation",
            "completed harvest",
            "public domain",
            "benchmark",
            "barrel",
        ):
            self.assertNotIn(word, text)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        with self.assertRaises(ValueError):
            record_series_header(self.folder, citation_url="https://example.com/rigs.xlsx")
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "settlement",
            "yield",
            "trade",
            "forecast",
            "observation",
            "completed harvest",
            "public domain",
            "benchmark",
            "oil supply",
            "Settlement",
            "YIELD",
            "Forecast",
            "Observation",
            "Completed Harvest",
            "Public Domain",
            "Benchmark",
            "Oil Supply",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_rig_count(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("baker_hughes_rig_count", text)
            self.assertNotIn("rigcount.bakerhughes.com", text)
