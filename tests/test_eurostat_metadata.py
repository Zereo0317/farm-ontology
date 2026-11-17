import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import eurostat_metadata
from farm_ontology.eurostat_industrial import EUROSTAT_INDUSTRIAL_URL, METADATA_PAGE
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]

PAGE = """
<html><title>Short-term business statistics (sts)</title>
<p>The objective of the number of dwelling building permit index is to show
the future development of construction activity in terms of residential units.</p>
<p>Industrial production increased by 1.2%.</p>
<footer>
<a href="https://commission.europa.eu/legal-notice_en">Legal notice</a>
</footer>
</html>
"""
LICENCE_PAGE = "<p>All rights reserved.</p>"


class EurostatMetadataTests(unittest.TestCase):
    def test_opened_metadata_page_prints_no_licence_sentence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "eurostat-metadata.json"
            eurostat_metadata.record_metadata_licence(
                path,
                EUROSTAT_INDUSTRIAL_URL,
                PAGE,
            )
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            stored,
            {
                "citation_url": EUROSTAT_INDUSTRIAL_URL,
                "metadata_page": METADATA_PAGE,
                "statement": (
                    "the metadata page was opened and no licence sentence was printed"
                ),
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(stored["metadata_page"], eurostat_metadata.METADATA_PAGE)
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(stored)
        self.assertNotIn("sentence", stored)
        self.assertNotIn("1.2", text)
        self.assertNotIn("%", text)
        self.assertNotIn("index", text)
        self.assertNotIn("growth", text)
        self.assertNotIn("trade", text)
        self.assertNotIn("Legal notice", text)
        self.assertNotIn("copyright", text)
        self.assertIn("no licence sentence was printed", text)

    def test_reading_the_stored_record_writes_no_trade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "eurostat-metadata.json"
            eurostat_metadata.record_metadata_licence(
                path,
                EUROSTAT_INDUSTRIAL_URL,
                PAGE,
            )
            before = path.read_text(encoding="utf-8")
            stored = json.loads(before)
            after = path.read_text(encoding="utf-8")
            names = sorted(item.name for item in folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names, ["eurostat-metadata.json"])
        self.assertFalse((folder / "trade.json").exists())
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], "closed")
        self.assertNotIn("trade", stored)
        self.assertNotIn("value", stored)
        self.assertNotIn("growth", stored)
        self.assertNotIn("trade", after)

    def test_printed_licence_sentence_is_stored_without_a_figure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "eurostat-metadata.json"
            eurostat_metadata.record_metadata_licence(
                path,
                EUROSTAT_INDUSTRIAL_URL,
                LICENCE_PAGE,
            )
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["sentence"], "All rights reserved.")
        self.assertNotIn("statement", stored)
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], "closed")
        self.assertNotIn("value", stored)
        self.assertNotIn("index", stored)
        self.assertNotIn("growth", stored)
        self.assertNotIn("trade", stored)

    def test_missing_page_or_other_citation_writes_nothing(self) -> None:
        download = (
            "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/sts_inpr_m"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "eurostat-metadata.json"
            for citation, body, metadata in (
                (None, PAGE, None),
                ("", PAGE, None),
                (EUROSTAT_INDUSTRIAL_URL, None, None),
                (EUROSTAT_INDUSTRIAL_URL, "   ", None),
                (METADATA_PAGE, PAGE, None),
                (
                    "https://ec.europa.eu/eurostat/databrowser/product/page/sts_inpr_m",
                    PAGE,
                    None,
                ),
                (download, PAGE, None),
                (EUROSTAT_INDUSTRIAL_URL, PAGE, download),
            ):
                with self.assertRaises(ValueError):
                    eurostat_metadata.record_metadata_licence(
                        path,
                        citation,
                        body,
                        metadata_url=metadata,
                    )
            self.assertFalse(path.exists())

    def test_index_or_trade_label_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "eurostat-metadata.json"
            for label in ("trade", "quantity of goods", "index", "growth rate", "1.2%"):
                with self.assertRaises(ValueError):
                    eurostat_metadata.record_metadata_licence(
                        path,
                        EUROSTAT_INDUSTRIAL_URL,
                        PAGE,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                eurostat_metadata.record_metadata_licence(
                    path,
                    EUROSTAT_INDUSTRIAL_URL,
                    PAGE,
                    permits_financial_use=True,
                )
            with self.assertRaises(ValueError):
                eurostat_metadata.record_metadata_licence(
                    path,
                    EUROSTAT_INDUSTRIAL_URL,
                    PAGE,
                    class_c_policy="open",
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_metadata_page(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("eurostat_metadata", text)
            self.assertNotIn("sts_esms", text)


if __name__ == "__main__":
    unittest.main()
