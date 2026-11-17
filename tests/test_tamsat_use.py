import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import tamsat_use
from farm_ontology.policy import CLASS_C_POLICY
from farm_ontology.tamsat_rainfall import TAMSAT_RAINFALL_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
SENTENCE = tamsat_use.USE_SENTENCE
PAGE = (
    "<h2>Cost and Terms of use</h2><td>TAMSAT data are free to use and\u00a0"
    "are released for operational, research and commercial use under the "
    "terms of the Creative Commons Attribution 4.0 International license "
    "(CC BY 4.0).\u00a0<span>To view a copy of this license, visit "
    "https://creativecommons.org/licenses/by/4.0/.</span></td>"
    "<p>rainfall amount 12.5 mm</p>"
    "<p>\u00a9 Copyright University of Reading</p>"
)
COMMERCIAL_ONLY = (
    "The data are released for operational, research and commercial use."
)
CC_BY_ONLY = "The estimates are published under CC BY 4.0."
COPYRIGHT_ONLY = "\u00a9 Copyright University of Reading."
DEED = "https://creativecommons.org/licenses/by/4.0/"


class TamsatUseTests(unittest.TestCase):
    def test_header_still_rejects_a_figure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaises(ValueError):
                record_series_header(folder, citation_url=TAMSAT_RAINFALL_URL, value="12.5")
            self.assertEqual(list(folder.iterdir()), [])

    def test_stores_the_printed_terms_sentence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tamsat-use.json"
            tamsat_use.record_use_sentence(path, TAMSAT_RAINFALL_URL, PAGE)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            stored,
            {
                "sentence": SENTENCE,
                "citation_url": TAMSAT_RAINFALL_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(stored)
        self.assertNotIn("12.5", text)
        self.assertNotIn("Copyright", text)
        self.assertNotIn("creativecommons.org", text)
        self.assertNotIn("To view a copy", text)
        self.assertNotIn("value", stored)
        self.assertNotIn("trade", text)
        self.assertNotIn("harvest", text)
        self.assertIn("commercial use", stored["sentence"])
        self.assertIn("CC BY 4.0", stored["sentence"])
        self.assertFalse(stored["permits_financial_use"])

    def test_commercial_or_cc_by_wording_stores_that_sentence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tamsat-use.json"
            tamsat_use.record_use_sentence(path, TAMSAT_RAINFALL_URL, COMMERCIAL_ONLY)
            commercial = json.loads(path.read_text(encoding="utf-8"))
            tamsat_use.record_use_sentence(path, TAMSAT_RAINFALL_URL, CC_BY_ONLY)
            cc_by = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(commercial["sentence"], COMMERCIAL_ONLY)
        self.assertEqual(cc_by["sentence"], CC_BY_ONLY)
        self.assertFalse(commercial["permits_financial_use"])
        self.assertFalse(cc_by["permits_financial_use"])
        self.assertEqual(commercial["class_c_policy"], "closed")

    def test_copyright_line_or_other_page_writes_nothing(self) -> None:
        others = (
            DEED,
            "https://ourresearch.reading.ac.uk/tamsat/",
            "https://ourresearch.reading.ac.uk/tamsat/faq-rainfall/",
            "https://www.reading.ac.uk",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tamsat-use.json"
            with self.assertRaises(ValueError):
                tamsat_use.record_use_sentence(path, TAMSAT_RAINFALL_URL, COPYRIGHT_ONLY)
            for source_url in others:
                with self.assertRaises(ValueError):
                    tamsat_use.record_use_sentence(
                        path,
                        TAMSAT_RAINFALL_URL,
                        PAGE,
                        source_url=source_url,
                    )
            for citation in (None, "", "   ", others[0], others[1]):
                with self.assertRaises(ValueError):
                    tamsat_use.record_use_sentence(path, citation, PAGE)
            self.assertFalse(path.exists())

    def test_reading_the_stored_record_writes_no_trade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "tamsat-use.json"
            tamsat_use.record_use_sentence(path, TAMSAT_RAINFALL_URL, PAGE)
            before = path.read_text(encoding="utf-8")
            stored = json.loads(before)
            after = path.read_text(encoding="utf-8")
            names = sorted(item.name for item in folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names, ["tamsat-use.json"])
        self.assertFalse((folder / "trade.json").exists())
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], "closed")
        self.assertNotIn("trade", after)

    def test_rainfall_trade_or_open_class_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tamsat-use.json"
            for label in ("trade", "completed harvest", "rainfall amount", "12.5"):
                with self.assertRaises(ValueError):
                    tamsat_use.record_use_sentence(
                        path,
                        TAMSAT_RAINFALL_URL,
                        PAGE,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                tamsat_use.record_use_sentence(
                    path,
                    TAMSAT_RAINFALL_URL,
                    PAGE,
                    permits_financial_use=True,
                )
            with self.assertRaises(ValueError):
                tamsat_use.record_use_sentence(
                    path,
                    TAMSAT_RAINFALL_URL,
                    PAGE,
                    class_c_policy="open",
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_terms_sentence(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("tamsat_use", text)
            self.assertNotIn("tamsat_rainfall", text)
            self.assertNotIn("tamsat/rainfall", text)


if __name__ == "__main__":
    unittest.main()
