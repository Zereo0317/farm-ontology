import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import mospi_iip_release
from farm_ontology.mospi_iip import MOSPI_IIP_URL, record_series_header
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
RELEASE = mospi_iip_release.RELEASE_URL
BULK = "https://esankhyiki.mospi.gov.in/macroindicators?product=iip"
PRINTED = (
    "The Quick Estimate of IIP stands at 124.3 against 116.5 in September 2025. "
    "The IIP growth rate for the month of September 2026 is 6.7 percent. "
    "The indices of Industrial Production for Mining & Quarrying, Manufacturing, "
    "Electricity & Gas Supply and Water Supply stand at 90.4, 128.0, 128.6 and 146.4. "
    "Detailed data pertaining to IIP is available at "
    "https://esankhyiki.mospi.gov.in/macroindicators?product=iip."
)
WITH_SENTENCE = (
    PRINTED
    + " Reproduction of this release is permitted with attribution of the source."
)


class MospiIipReleaseTests(unittest.TestCase):
    def test_header_still_rejects_an_index_number(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaises(ValueError):
                record_series_header(folder, citation_url=MOSPI_IIP_URL, value="124.3")
            self.assertEqual(list(folder.iterdir()), [])

    def test_release_without_a_reproduction_sentence_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mospi-iip-release.json"
            with self.assertRaises(ValueError) as caught:
                mospi_iip_release.record_release_level(
                    path,
                    MOSPI_IIP_URL,
                    PRINTED,
                    release_url=RELEASE,
                )
            self.assertIn("no reproduction sentence", str(caught.exception))
            self.assertFalse(path.exists())
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_keeps_the_reproduction_sentence_with_the_all_india_level(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mospi-iip-release.json"
            mospi_iip_release.record_release_level(
                path,
                MOSPI_IIP_URL,
                WITH_SENTENCE,
                release_url=RELEASE,
            )
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["value"], "124.3")
        self.assertEqual(
            stored["sentence"],
            "Reproduction of this release is permitted with attribution of the source.",
        )
        self.assertEqual(stored["period"], "September 2026")
        self.assertEqual(stored["administrative_area"], "all India")
        self.assertEqual(stored["kind"], "index")
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertEqual(stored["class_c_policy"], "closed")
        text = json.dumps(stored)
        for leftover in ("116.5", "90.4", "128.0", "128.6", "146.4", "6.7", "%", "esankhyiki"):
            self.assertNotIn(leftover, text)
        self.assertNotIn("trade", text)
        self.assertNotIn("quantity", text)

    def test_sector_growth_or_bulk_file_writes_nothing(self) -> None:
        growth_only = (
            "The IIP growth rate for the month of September 2026 is 6.7 percent. "
            "Reproduction of this release is permitted with attribution of the source."
        )
        two_levels = (
            "The Quick Estimate of IIP stands at 124.3. "
            "The Quick Estimate of IIP stands at 116.5. "
            "Reproduction of this release is permitted with attribution of the source."
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mospi-iip-release.json"
            for body in (growth_only, two_levels):
                with self.assertRaises(ValueError):
                    mospi_iip_release.record_release_level(
                        path,
                        MOSPI_IIP_URL,
                        body,
                        release_url=RELEASE,
                    )
            with self.assertRaises(ValueError):
                mospi_iip_release.record_release_level(
                    path,
                    MOSPI_IIP_URL,
                    WITH_SENTENCE,
                    release_url=BULK,
                )
            self.assertFalse(path.exists())

    def test_reading_a_stored_level_writes_no_trade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "mospi-iip-release.json"
            mospi_iip_release.record_release_level(
                path,
                MOSPI_IIP_URL,
                WITH_SENTENCE,
                release_url=RELEASE,
            )
            before = path.read_text(encoding="utf-8")
            stored = json.loads(before)
            after = path.read_text(encoding="utf-8")
            names = sorted(item.name for item in folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names, ["mospi-iip-release.json"])
        self.assertFalse((folder / "trade.json").exists())
        self.assertFalse(stored["permits_financial_use"])
        self.assertNotIn("trade", after)

    def test_trade_or_open_class_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mospi-iip-release.json"
            for label in ("trade", "quantity of goods", "growth rate", "6.7%"):
                with self.assertRaises(ValueError):
                    mospi_iip_release.record_release_level(
                        path,
                        MOSPI_IIP_URL,
                        WITH_SENTENCE,
                        release_url=RELEASE,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                mospi_iip_release.record_release_level(
                    path,
                    MOSPI_IIP_URL,
                    WITH_SENTENCE,
                    release_url=RELEASE,
                    permits_financial_use=True,
                )
            with self.assertRaises(ValueError):
                mospi_iip_release.record_release_level(
                    path,
                    MOSPI_IIP_URL,
                    WITH_SENTENCE,
                    release_url=RELEASE,
                    class_c_policy="open",
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_release(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("mospi_iip_release", text)
            self.assertNotIn("esankhyiki.mospi.gov.in", text)


if __name__ == "__main__":
    unittest.main()
