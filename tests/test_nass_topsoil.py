import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology import nass_topsoil
from farm_ontology.policy import CLASS_C_POLICY


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


if __name__ == "__main__":
    unittest.main()
