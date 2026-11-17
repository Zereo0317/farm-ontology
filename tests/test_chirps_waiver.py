import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import chirps_waiver
from farm_ontology.chirps_rainfall import CHIRPS_RAINFALL_URL
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
SENTENCE = chirps_waiver.WAIVER_SENTENCE
PAGE = (
    "<div><em>To the extent possible under the law, Pete Peterson has "
    "waived all copyright and related or neighboring rights to CHIRPS. "
    "CHIRPS data is in the public domain as registered with Creative "
    "Commons. This work is published from: the United States.</em></div>"
    "<ul><li>©2026</li><li>The Regents of the University of California.</li>"
    "<li>All Rights Reserved.</li></ul>"
    "<p>rainfall amount 12.5 mm</p>"
    '<a href="https://www.chc.ucsb.edu/data/chirps3">CHIRPS v3</a>'
    '<a href="https://data.chc.ucsb.edu/products/CHIRPS-2.0/">data</a>'
)
DIFFERENT = (
    "Under another wording, Pete Peterson has waived all copyright and "
    "related or neighboring rights to CHIRPS. CHIRPS data is in the "
    "public domain as registered with Creative Commons."
)
REGENTS = (
    "<ul><li>©2026</li><li>The Regents of the University of California.</li>"
    "<li>All Rights Reserved.</li></ul>"
)


class ChirpsWaiverTests(unittest.TestCase):
    def test_stores_the_printed_waiver_sentence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "chirps-waiver.json"
            chirps_waiver.record_waiver_sentence(path, CHIRPS_RAINFALL_URL, PAGE)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            stored,
            {
                "sentence": SENTENCE,
                "citation_url": CHIRPS_RAINFALL_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(stored)
        self.assertNotIn("United States", text)
        self.assertNotIn("Regents", text)
        self.assertNotIn("All Rights Reserved", text)
        self.assertNotIn("12.5", text)
        self.assertNotIn("rainfall", text)
        self.assertNotIn("2026", text)
        self.assertNotIn("chirps3", text)
        self.assertNotIn("CHIRPS-2.0", text)
        self.assertNotIn("trade", text)
        self.assertNotIn("harvest", text)
        self.assertNotIn("value", stored)

    def test_different_wording_stores_the_printed_sentence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "chirps-waiver.json"
            chirps_waiver.record_waiver_sentence(path, CHIRPS_RAINFALL_URL, DIFFERENT)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["sentence"], DIFFERENT)
        self.assertNotEqual(stored["sentence"], SENTENCE)
        self.assertFalse(stored["permits_financial_use"])

    def test_reading_the_stored_record_writes_no_trade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "chirps-waiver.json"
            chirps_waiver.record_waiver_sentence(path, CHIRPS_RAINFALL_URL, PAGE)
            before = path.read_text(encoding="utf-8")
            stored = json.loads(before)
            after = path.read_text(encoding="utf-8")
            names = sorted(item.name for item in folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names, ["chirps-waiver.json"])
        self.assertFalse((folder / "trade.json").exists())
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], "closed")
        self.assertNotIn("trade", stored)
        self.assertNotIn("trade", after)

    def test_regents_line_v3_page_or_data_file_writes_nothing(self) -> None:
        others = (
            "https://www.chc.ucsb.edu/data/chirps3",
            "https://data.chc.ucsb.edu/products/CHIRPS-2.0/",
            "https://data.chc.ucsb.edu/products/CHIRPS-2.0/README-CHIRPS2-Daily.txt",
            "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily.tif",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "chirps-waiver.json"
            with self.assertRaises(ValueError):
                chirps_waiver.record_waiver_sentence(path, CHIRPS_RAINFALL_URL, REGENTS)
            for source_url in others:
                with self.assertRaises(ValueError):
                    chirps_waiver.record_waiver_sentence(
                        path,
                        CHIRPS_RAINFALL_URL,
                        PAGE,
                        source_url=source_url,
                    )
            for citation in (None, "", "   ", others[0], others[1]):
                with self.assertRaises(ValueError):
                    chirps_waiver.record_waiver_sentence(path, citation, PAGE)
            self.assertFalse(path.exists())

    def test_rainfall_trade_or_open_class_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "chirps-waiver.json"
            for label in ("trade", "completed harvest", "rainfall amount", "12.5"):
                with self.assertRaises(ValueError):
                    chirps_waiver.record_waiver_sentence(
                        path,
                        CHIRPS_RAINFALL_URL,
                        PAGE,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                chirps_waiver.record_waiver_sentence(
                    path,
                    CHIRPS_RAINFALL_URL,
                    PAGE,
                    permits_financial_use=True,
                )
            with self.assertRaises(ValueError):
                chirps_waiver.record_waiver_sentence(
                    path,
                    CHIRPS_RAINFALL_URL,
                    PAGE,
                    class_c_policy="open",
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_waiver(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("chirps_waiver", text)
            self.assertNotIn("chirps3", text)
            self.assertNotIn("data.chc.ucsb.edu", text)


if __name__ == "__main__":
    unittest.main()
