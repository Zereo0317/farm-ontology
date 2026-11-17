import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import era5_ccby
from farm_ontology.era5_land import ERA5_LAND_URL
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]

LICENCE_PAGE = (
    "This dataset is released for use under the CC-BY licence. \n"
    "Highlights and  key features of the licence are provided "
    "[here](https://creativecommons.org/licenses/by/4.0/).\n"
    "Full legal text is provided "
    "[here](https://creativecommons.org/licenses/by/4.0/legalcode).\n"
    "2 m temperature 12.4\n"
)
DIFFERENT_WORDING = "Released for use under the CC-BY licence, with other wording.\n"


class Era5CcbyTests(unittest.TestCase):
    def test_stores_the_printed_ccby_sentence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "era5-ccby.json"
            era5_ccby.record_ccby_sentence(path, ERA5_LAND_URL, LICENCE_PAGE)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            stored,
            {
                "sentence": "This dataset is released for use under the CC-BY licence.",
                "citation_url": ERA5_LAND_URL,
                "licence_page": era5_ccby.LICENCE_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(stored)
        self.assertNotIn("12.4", text)
        self.assertNotIn("temperature", text)
        self.assertNotIn("4.0", text)
        self.assertNotIn("legalcode", text)
        self.assertNotIn("Highlights", text)
        self.assertNotIn("harvest", text)
        self.assertNotIn("trade", text)
        self.assertNotIn("value", stored)

    def test_different_wording_stores_the_printed_sentence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "era5-ccby.json"
            era5_ccby.record_ccby_sentence(path, ERA5_LAND_URL, DIFFERENT_WORDING)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            stored["sentence"],
            "Released for use under the CC-BY licence, with other wording.",
        )
        self.assertNotEqual(
            stored["sentence"],
            "This dataset is released for use under the CC-BY licence.",
        )

    def test_reading_the_stored_record_writes_no_trade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "era5-ccby.json"
            era5_ccby.record_ccby_sentence(path, ERA5_LAND_URL, LICENCE_PAGE)
            before = path.read_text(encoding="utf-8")
            stored = json.loads(before)
            after = path.read_text(encoding="utf-8")
            names = sorted(item.name for item in folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names, ["era5-ccby.json"])
        self.assertFalse((folder / "trade.json").exists())
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], "closed")
        self.assertNotIn("trade", stored)
        self.assertNotIn("harvest", stored)
        self.assertNotIn("trade", after)

    def test_other_pages_write_nothing(self) -> None:
        others = (
            "https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=download",
            "https://confluence.ecmwf.int/display/CKB/ERA5-Land",
            "https://creativecommons.org/licenses/by/4.0/legalcode",
            "https://spdx.org/licenses/CC-BY-4.0",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "era5-ccby.json"
            for licence_url in others:
                with self.assertRaises(ValueError):
                    era5_ccby.record_ccby_sentence(
                        path,
                        ERA5_LAND_URL,
                        LICENCE_PAGE,
                        licence_url=licence_url,
                    )
            for citation in (None, "", "   ", others[0]):
                with self.assertRaises(ValueError):
                    era5_ccby.record_ccby_sentence(path, citation, LICENCE_PAGE)
            with self.assertRaises(ValueError):
                era5_ccby.record_ccby_sentence(path, ERA5_LAND_URL, None)
            self.assertFalse(path.exists())

    def test_harvest_trade_or_weather_label_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "era5-ccby.json"
            for label in ("trade", "completed harvest", "weather", "temperature", "12.4"):
                with self.assertRaises(ValueError):
                    era5_ccby.record_ccby_sentence(
                        path,
                        ERA5_LAND_URL,
                        LICENCE_PAGE,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                era5_ccby.record_ccby_sentence(
                    path,
                    ERA5_LAND_URL,
                    LICENCE_PAGE,
                    permits_financial_use=True,
                )
            with self.assertRaises(ValueError):
                era5_ccby.record_ccby_sentence(
                    path,
                    ERA5_LAND_URL,
                    LICENCE_PAGE,
                    class_c_policy="open",
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_licence_page(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("era5_ccby", text)
            self.assertNotIn("cc-byv1_", text)


if __name__ == "__main__":
    unittest.main()
