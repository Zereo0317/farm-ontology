import json
import tempfile
import unittest
import urllib.request
import zlib
from pathlib import Path

from farm_ontology import nass_topsoil
from farm_ontology.policy import CLASS_C_POLICY
from farm_ontology.testing import online_gate


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AssertionError("the refetch does not follow another page")


def _pdf_literal_text(pdf: bytes) -> str:
    """Join literal PDF text strings. Encoded font bytes are left out."""

    parts = []
    start = 0
    while True:
        marker = pdf.find(b"stream", start)
        if marker < 0:
            break
        data_start = marker + len(b"stream")
        if pdf[data_start:data_start + 2] == b"\r\n":
            data_start += 2
        elif pdf[data_start:data_start + 1] == b"\n":
            data_start += 1
        end = pdf.find(b"endstream", data_start)
        if end < 0:
            break
        data = pdf[data_start:end].strip(b"\r\n")
        try:
            parts.append(zlib.decompress(data))
        except zlib.error:
            parts.append(data)
        start = end + len(b"endstream")
    blob = b"".join(parts)
    out = []
    index = 0
    size = len(blob)
    while True:
        opened = blob.find(b"(", index)
        if opened < 0:
            break
        cursor = opened + 1
        buf = bytearray()
        while cursor < size:
            byte = blob[cursor]
            if byte == 0x5C and cursor + 1 < size:
                buf.append(blob[cursor + 1])
                cursor += 2
                continue
            if byte == 0x29:
                break
            buf.append(byte)
            cursor += 1
        if buf:
            out.append(buf.decode("latin-1", errors="replace"))
        index = cursor + 1
    return "".join(out)


class NassTopsoilTest(unittest.TestCase):
    def test_stores_printed_topsoil_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nass-topsoil.json"
            nass_topsoil.record_nass_topsoil(path, nass_topsoil.NASS_TOPSOIL_URL)
            header = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            header,
            {
                "publisher": "USDA, National Agricultural Statistics Service",
                "table": (
                    "Topsoil Moisture Condition - Selected States: "
                    "Week Ending November 8, 2026"
                ),
                "period": "Week Ending November 8, 2026",
                "weighting": (
                    "[National topsoil moisture conditions for selected States "
                    "are weighted based on cropland acreage]"
                ),
                "rows": [
                    {
                        "state": "48 States",
                        "Very short": 11,
                        "Short": 23,
                        "Adequate": 58,
                        "Surplus": 8,
                        "unit": "percent",
                    },
                    {
                        "state": "Texas",
                        "Very short": 10,
                        "Short": 31,
                        "Adequate": 52,
                        "Surplus": 7,
                        "unit": "percent",
                    },
                ],
                "citation_url": nass_topsoil.NASS_TOPSOIL_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(header["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(header)
        self.assertNotIn("m3/m3", text)
        self.assertNotIn("volumetric", text)
        self.assertNotIn("SMAP", text)
        self.assertNotIn("Subsoil", text)
        self.assertNotIn("Previous week", text)

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nass-topsoil.json"
            with self.assertRaises(ValueError):
                nass_topsoil.record_nass_topsoil(path, None)
            with self.assertRaises(ValueError):
                nass_topsoil.record_nass_topsoil(path, "   ")
            self.assertFalse(path.exists())

    def test_other_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nass-topsoil.json"
            for citation in (
                nass_topsoil.NASS_TOPSOIL_URL + "/",
                "https://release.nass.usda.gov/reports/prog4526.pdf?download=1",
                "https://www.nass.usda.gov/",
            ):
                with self.assertRaises(ValueError):
                    nass_topsoil.record_nass_topsoil(path, citation)
            self.assertFalse(path.exists())

    def test_rejected_labels_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nass-topsoil.json"
            for label in (
                "volumetric water content",
                "m3/m3",
                "SMAP",
                "yield",
                "trade",
                "completed harvest",
            ):
                with self.assertRaises(ValueError):
                    nass_topsoil.record_nass_topsoil(
                        path,
                        nass_topsoil.NASS_TOPSOIL_URL,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                nass_topsoil.record_nass_topsoil(
                    path,
                    nass_topsoil.NASS_TOPSOIL_URL,
                    rows=[{"state": "48 States", "Very short": 0}],
                )
            with self.assertRaises(ValueError):
                nass_topsoil.record_nass_topsoil(
                    path,
                    nass_topsoil.NASS_TOPSOIL_URL,
                    permits_financial_use=True,
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_share(self) -> None:
        source = (
            Path(nass_topsoil.__file__).read_text(encoding="utf-8").replace("\n", " ")
        )
        self.assertIn("shares of cropland", source)
        self.assertIn("not volumetric water content", source)
        self.assertIn("not m3/m3", source)
        self.assertIn("not a SMAP sample", source)
        self.assertIn("not a completed harvest", source)
        self.assertIn("weighted based on cropland acreage", source)
        self.assertNotIn("field_save", source)

    @online_gate()
    def test_live_refetch_prints_the_topsoil_table(self) -> None:
        request = urllib.request.Request(
            nass_topsoil.NASS_TOPSOIL_URL,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        opener = urllib.request.build_opener(_NoRedirect)
        with opener.open(request, timeout=60) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.geturl(), nass_topsoil.NASS_TOPSOIL_URL)
            body = response.read()
        self.assertTrue(body.startswith(b"%PDF"))
        self.assertNotIn(b"earthdata login", body[:4000].lower())
        printed = _pdf_literal_text(body)
        self.assertIn("Topsoil Moisture Condition", printed)
        self.assertIn("Week Ending November 8, 2026", printed)
        self.assertIn("weighted based on cropland acreage", printed)
        self.assertIn("USDA, National Agricultural Statistics Service", printed)
        self.assertIn("(percent)", printed)
        self.assertIn("48 States", printed)
        self.assertIn("Texas", printed)
        self.assertIn("Very short", printed)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nass-topsoil.json"
            nass_topsoil.record_nass_topsoil(path, nass_topsoil.NASS_TOPSOIL_URL)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["rows"][0]["unit"], "percent")
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], "closed")
        self.assertNotIn("m3/m3", json.dumps(stored))


if __name__ == "__main__":
    unittest.main()
