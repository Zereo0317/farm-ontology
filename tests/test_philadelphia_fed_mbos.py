import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.philadelphia_fed_mbos import (
    PHILADELPHIA_FED_MBOS_URL,
    record_series_header,
)

ROOT = Path(__file__).resolve().parents[1]
URL = PHILADELPHIA_FED_MBOS_URL


class PhiladelphiaFedMbosTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_an_index_value(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Federal Reserve Bank of Philadelphia")
        self.assertEqual(header["product"], "Manufacturing Business Outlook Survey")
        self.assertEqual(
            header["period"],
            "monthly; the survey page lists a 19 November 2026 release at 8:30 a.m.; "
            "the readme dated 7 March 2025 says historical monthly data run from "
            "May 1968 to the most current month; the user guide says the files are "
            "revised annually for seasonal factors",
        )
        self.assertEqual(
            header["unit"],
            "a diffusion index, the share reporting an increase minus the share "
            "reporting a decrease; current conditions and expectations six months "
            "ahead are named; no index value is stored",
        )
        self.assertEqual(
            header["administrative_area"],
            "manufacturing firms in the Third District; not national manufacturing supply",
        )
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "survey")
        self.assertFalse(header["permits_financial_use"])
        for key in ("value", "index_value", "forecast", "expectation"):
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
            "national supply",
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
            record_series_header(self.folder, citation_url="https://example.com/mbos.csv")
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
            "national supply",
            "Settlement",
            "YIELD",
            "Forecast",
            "Observation",
            "Completed Harvest",
            "Public Domain",
            "National Supply",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_the_survey(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("philadelphia_fed_mbos", text)
            self.assertNotIn("manufacturing-business-outlook-survey", text)
