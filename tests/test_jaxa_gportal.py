import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.jaxa_gportal import JAXA_GPORTAL_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = JAXA_GPORTAL_URL


class JaxaGportalTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Japan Aerospace Exploration Agency")
        self.assertEqual(header["product"], "Product Information / Operation")
        self.assertNotEqual(header["product"], "G-Portal")
        self.assertEqual(header["citation_url"], "https://www.gportal.jaxa.jp/information/product")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(header["class_c_policy"], "closed")
        self.assertEqual(
            set(header),
            {
                "publisher",
                "product",
                "citation_url",
                "permits_financial_use",
                "class_c_policy",
            },
        )
        for key in (
            "period",
            "unit",
            "administrative_area",
            "kind",
            "licence",
            "value",
            "price",
            "temperature",
            "rainfall",
            "yield",
            "trade",
            "scene",
            "pixel",
        ):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "GCOM-W",
            "GCOM-C",
            "GSMaP",
            "scene",
            "pixel",
            "yield",
            "price",
            "rainfall",
            "temperature",
            "trade",
            "period",
            "unit",
            "licence",
            "license",
            "kind",
            "completed harvest",
            "Terms of Use",
            "lang=en",
        ):
            self.assertNotIn(word, text, word)
        source = (ROOT / "farm_ontology" / "jaxa_gportal.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("https://www.gportal.jaxa.jp/ is not the citation.", flat)
        self.assertIn("https://www.gportal.jaxa.jp/?lang=en is not the citation.", flat)
        self.assertIn(
            "https://www.gportal.jaxa.jp/information/product?lang=en is not the citation.",
            flat,
        )
        self.assertIn(
            "https://www.gportal.jaxa.jp/information/product/ is not the citation.",
            flat,
        )
        self.assertIn("http://www.gportal.jaxa.jp/index.php is not the citation.", flat)
        self.assertIn("The citation is the printed canonical link.", flat)
        self.assertIn("The publisher is Japan Aerospace Exploration Agency.", flat)
        self.assertIn("G-Portal is the site name in the title, not a second publisher.", flat)
        self.assertIn("The product is Product Information / Operation.", flat)
        self.assertIn(
            "The document title is G-PortalProduct Information / Operation.",
            flat,
        )
        self.assertIn(
            "Information about products and their operation is provided by spacecraft. That sentence is not a second product.",
            flat,
        )
        self.assertIn("Period was not printed.", flat)
        self.assertIn("Unit was not printed.", flat)
        self.assertIn("Area was not printed.", flat)
        self.assertIn("Kind was not printed.", flat)
        self.assertIn("Licence was not printed. Terms of Use is a link, not a licence sentence.", flat)
        self.assertIn("Do not store a scene id.", flat)
        self.assertIn("Do not store a pixel.", flat)
        self.assertIn("Do not store a yield.", flat)
        self.assertIn("Do not store a price.", flat)
        self.assertIn("Do not store a rainfall amount.", flat)
        self.assertIn("Do not store a temperature.", flat)
        self.assertIn("Do not store a trade.", flat)
        self.assertIn("A catalog product is not a completed harvest.", flat)
        self.assertIn("Class C stays closed.", flat)
        self.assertIn("permits_financial_use stays false.", flat)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://www.gportal.jaxa.jp/",
            "https://www.gportal.jaxa.jp/?lang=en",
            "https://www.gportal.jaxa.jp/information/product?lang=en",
            "https://www.gportal.jaxa.jp/information/product/",
            "http://www.gportal.jaxa.jp/index.php",
            "https://www.gportal.jaxa.jp/gpr/index/eula",
            "https://www.gportal.jaxa.jp/auth/login",
            "https://example.com/gportal.html",
        ):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "settlement",
            "yield",
            "price",
            "trade",
            "rainfall",
            "rainfall amount",
            "temperature",
            "scene",
            "scene id",
            "pixel",
            "completed harvest",
            "2012",
            "2026-10-27",
            "Settlement",
            "YIELD",
            "Price",
            "PRICE",
            "Trade",
            "Completed Harvest",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_filled_fields_and_figures_write_nothing(self):
        attempts = (
            {"period": "July 2, 2012 – November 10, 2026"},
            {"unit": "GeoTiff"},
            {"administrative_area": "Japan"},
            {"kind": "catalog"},
            {"licence": "Terms of Use"},
            {"value": 1},
            {"value": "pixel"},
            {"value": "rainfall"},
            {"value": "temperature"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_jaxa_gportal(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("jaxa_gportal", text)
            self.assertNotIn("gportal.jaxa.jp", text)
            self.assertNotIn("Product Information / Operation", text)


if __name__ == "__main__":
    unittest.main()
