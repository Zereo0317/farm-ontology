"""Live refetch of the cited SMAP L1A ISO metadata.

The citation is the ISO XML already cited.
The refetch stores halfOrbitStartDateTime and halfOrbitEndDateTime
only when that body prints them.
It does not store a soil-moisture pixel.
permits_financial_use stays false. Class C stays closed.
"""

import re
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.policy import CLASS_C_POLICY
from farm_ontology.smap_l1a_orbit import (
    ORBIT_END,
    ORBIT_END_NAME,
    ORBIT_START,
    ORBIT_START_NAME,
    SMAP_L1A_ORBIT_URL,
    record_orbit_times,
)

ROOT = Path(__file__).resolve().parents[1]
URL = SMAP_L1A_ORBIT_URL


class SmapL1aOrbitTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_live_refetch_stores_the_printed_orbit_times(self):
        saved = record_orbit_times(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["orbit_start"], "2026-11-16T22:00:29.000Z")
        self.assertEqual(header["orbit_start"], ORBIT_START)
        self.assertEqual(header["orbit_end"], "2026-11-16T22:49:43.000Z")
        self.assertEqual(header["orbit_end"], ORBIT_END)
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(header["class_c_policy"], "closed")
        self.assertEqual(header["class_c_policy"], CLASS_C_POLICY)
        self.assertEqual(
            set(header),
            {
                "citation_url",
                "orbit_start",
                "orbit_end",
                "permits_financial_use",
                "class_c_policy",
            },
        )
        request = urllib.request.Request(
            URL,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/xml,text/xml,*/*",
            },
        )
        with urllib.request.urlopen(request, timeout=90) as response:
            self.assertEqual(response.status, 200)
            final_url = response.geturl()
            body = response.read()
        text_body = body.decode("utf-8")
        self.assertNotEqual(final_url, URL)
        self.assertIn(f">{ORBIT_START_NAME}<", text_body)
        self.assertIn(f">{ORBIT_END_NAME}<", text_body)
        self.assertIn(
            f"<gco:CharacterString>{ORBIT_START}</gco:CharacterString>",
            text_body,
        )
        self.assertIn(
            f"<gco:CharacterString>{ORBIT_END}</gco:CharacterString>",
            text_body,
        )
        begin = re.search(
            r"<gml:beginPosition[^>]*>([^<]+)</gml:beginPosition>",
            text_body,
        ).group(1)
        end = re.search(
            r"<gml:endPosition[^>]*>([^<]+)</gml:endPosition>",
            text_body,
        ).group(1)
        self.assertNotEqual(header["orbit_start"], begin)
        self.assertNotEqual(header["orbit_end"], end)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        self.assertIn(URL, text)
        self.assertIn(ORBIT_START, text)
        self.assertIn(ORBIT_END, text)
        self.assertNotIn(begin, text)
        self.assertNotIn(end, text)
        self.assertNotIn(final_url, text)
        for word in (
            "pixel",
            "soil",
            "brightness",
            "yield",
            "price",
            "trade",
            "latitude",
            "longitude",
            "Signature=",
        ):
            self.assertNotIn(word, text, word)
        source = (ROOT / "farm_ontology" / "smap_l1a_orbit.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("halfOrbitStartDateTime prints 2026-11-16T22:00:29.000Z.", flat)
        self.assertIn("halfOrbitEndDateTime prints 2026-11-16T22:49:43.000Z.", flat)
        self.assertIn("The temporal extent is not the orbit time.", flat)
        self.assertIn("A soil-moisture pixel is not stored.", flat)
        self.assertIn("The redirect URL is not stored.", flat)
        self.assertIn("permits_financial_use stays false.", flat)
        self.assertIn("Class C stays closed.", flat)
        self.assertIn("A body with no orbit time writes nothing.", flat)
        self.assertNotIn(begin, source)
        self.assertNotIn(end, source)
        self.assertNotIn(final_url, source)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        with patch(
            "farm_ontology.smap_l1a_orbit._open",
            side_effect=AssertionError("fetched"),
        ):
            for citation in (None, "", "   "):
                with self.assertRaises(ValueError):
                    record_orbit_times(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        with patch(
            "farm_ontology.smap_l1a_orbit._open",
            side_effect=AssertionError("fetched"),
        ):
            for citation in (
                "https://nsidc.org/data/smap",
                "https://smap.jpl.nasa.gov/",
                URL + "/",
                "https://example.com/SMAP_L1A_RADIOMETER.iso.xml",
            ):
                with self.assertRaises(ValueError):
                    record_orbit_times(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_soil_moisture_pixel_writes_nothing(self):
        with patch(
            "farm_ontology.smap_l1a_orbit._open",
            side_effect=AssertionError("fetched"),
        ):
            for label in ("pixel", "soil moisture", "brightness temperature", "yield", "price", "trade"):
                with self.assertRaises(ValueError):
                    record_orbit_times(self.folder, citation_url=URL, label=label)
            with self.assertRaises(ValueError):
                record_orbit_times(self.folder, citation_url=URL, pixel=1)
            with self.assertRaises(ValueError):
                record_orbit_times(self.folder, citation_url=URL, soil_moisture=0.2)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_replaced_time_or_open_class_writes_nothing(self):
        with patch(
            "farm_ontology.smap_l1a_orbit._open",
            side_effect=AssertionError("fetched"),
        ):
            with self.assertRaises(ValueError):
                record_orbit_times(
                    self.folder,
                    citation_url=URL,
                    orbit_start="2020-01-01T00:00:00.000Z",
                    orbit_end="2020-01-01T01:00:00.000Z",
                )
            with self.assertRaises(ValueError):
                record_orbit_times(self.folder, citation_url=URL, permits_financial_use=True)
            with self.assertRaises(ValueError):
                record_orbit_times(self.folder, citation_url=URL, class_c_policy="open")
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_body_without_a_time_writes_nothing(self):
        class _Response:
            status = 200

            def read(self):
                return b"<?xml version=\"1.0\"?><gmd:MD_Metadata></gmd:MD_Metadata>"

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

        with patch("farm_ontology.smap_l1a_orbit._open", return_value=_Response()):
            with self.assertRaises(ValueError):
                record_orbit_times(self.folder, citation_url=URL)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_smap_l1a_orbit(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("smap_l1a_orbit", text)
            self.assertNotIn("halfOrbitStartDateTime", text)
            self.assertNotIn("SMAP_L1A_RADIOMETER_62995", text)


if __name__ == "__main__":
    unittest.main()
