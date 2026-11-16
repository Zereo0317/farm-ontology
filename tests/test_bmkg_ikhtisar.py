import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.bmkg_ikhtisar import BMKG_IKHTISAR_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = BMKG_IKHTISAR_URL


class BmkgIkhtisarTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(
            header["publisher"],
            "BMKG / Badan Meteorologi, Klimatologi, dan Geofisika",
        )
        self.assertEqual(header["product"], "Ikhtisar Cuaca Harian")
        self.assertNotIn("period", header)
        self.assertNotIn("unit", header)
        self.assertEqual(header["administrative_area"], "di wilayah Indonesia")
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Ikhtisar Cuaca Harian")
        self.assertEqual(header["kind"], header["product"])
        self.assertNotEqual(header["kind"], "forecast")
        self.assertNotEqual(header["kind"], "Ringkasan")
        self.assertNotEqual(header["kind"], "Cuaca")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(
            set(header),
            {
                "publisher",
                "product",
                "administrative_area",
                "citation_url",
                "kind",
                "permits_financial_use",
            },
        )
        for key in ("value", "price", "temperature", "rainfall", "trade", "figure", "copyright"):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "Ringkasan",
            "pdf",
            "dataweb",
            "dokumen",
            "prakiraan",
            "Potensi",
            "Hujan",
            "Ketentuan",
            "Jakarta",
            "temperature",
            "rainfall",
            "yield",
            "price",
            "trade",
            "settlement",
            "completed harvest",
            "forecast",
            "observation",
            "public domain",
            "benchmark",
            "index",
            "period",
            "unit",
            "2026",
            "website",
            "dddd",
            "docs.google.com",
            "gempa",
            "licence",
            "license",
        ):
            self.assertNotIn(word, text, word)
        source = (ROOT / "farm_ontology" / "bmkg_ikhtisar.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("https://www.bmkg.go.id/ is not the citation.", flat)
        self.assertIn(
            "https://www.bmkg.go.id/cuaca/prakiraan-cuaca is not the citation.",
            flat,
        )
        self.assertIn("https://data.bmkg.go.id/prakiraan-cuaca/ is not the citation.", flat)
        self.assertIn(
            "https://dataweb.bmkg.go.id/cuaca/dokumen/ikhtisar-cuaca-harian.pdf was not opened.",
            flat,
        )
        self.assertIn("https://docs.google.com/viewer was not opened.", flat)
        self.assertIn(
            "https://www.bmkg.go.id/cuaca/potensi-hujan-sepekan was not opened.",
            flat,
        )
        self.assertIn(
            "The document title is Ikhtisar Cuaca Harian - Cuaca - BMKG.",
            flat,
        )
        self.assertIn(
            "Ikhtisar Cuaca Harian is the h1. It is the product and the kind.",
            flat,
        )
        self.assertIn("BMKG is a printed short name inside the one publisher.", flat)
        self.assertIn("Ringkasan is not a second kind.", flat)
        self.assertIn("Cuaca is a title segment, not a second kind.", flat)
        self.assertIn("Prakiraan Cuaca is a menu heading, not the product.", flat)
        self.assertIn("Period is omitted.", flat)
        self.assertIn("Unit is omitted.", flat)
        self.assertIn("The word harian stays inside the product. It is not a period.", flat)
        self.assertIn(
            "dddd, D MMMM YYYY is an empty-element attribute, not a printed date.",
            flat,
        )
        self.assertIn("The stored administrative area is di wilayah Indonesia.", flat)
        self.assertIn(
            "Jakarta Pusat is the office address, not the administrative area.",
            flat,
        )
        self.assertIn("Ketentuan Penggunaan was not opened.", flat)
        self.assertIn("Do not store a rainfall amount.", flat)
        self.assertIn("Do not store a temperature.", flat)
        self.assertIn("A forecast is not a completed harvest.", flat)
        self.assertIn("The header is not marked public domain.", flat)
        self.assertIn("permits_financial_use stays false.", flat)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://www.bmkg.go.id/",
            "https://www.bmkg.go.id",
            "https://www.bmkg.go.id/cuaca/",
            "https://www.bmkg.go.id/cuaca/prakiraan-cuaca",
            "https://www.bmkg.go.id/cuaca/ikhtisar-cuaca-harian/",
            "https://data.bmkg.go.id/prakiraan-cuaca/",
            "https://dataweb.bmkg.go.id/cuaca/dokumen/ikhtisar-cuaca-harian.pdf",
            "https://docs.google.com/viewer?url=https://dataweb.bmkg.go.id/cuaca/dokumen/ikhtisar-cuaca-harian.pdf&embedded=true",
            "https://www.bmkg.go.id/cuaca/potensi-hujan-sepekan",
            "http://www.bmkg.go.id/cuaca/ikhtisar-cuaca-harian",
            "https://example.com/bmkg.html",
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
            "observation",
            "completed harvest",
            "public domain",
            "benchmark",
            "index",
            "rainfall amount",
            "temperature",
            "figure",
            "Ringkasan",
            "Cuaca",
            "12.5",
            "2026",
            "Settlement",
            "YIELD",
            "Price",
            "PRICE",
            "Trade",
            "Observation",
            "Completed Harvest",
            "Public Domain",
            "Benchmark",
            "Index",
            "INDEX",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_filled_fields_and_figures_write_nothing(self):
        attempts = (
            {"period": "harian"},
            {"period": "Ringkasan"},
            {"period": "dddd, D MMMM YYYY"},
            {"unit": "temperature"},
            {"unit": "rainfall"},
            {"administrative_area": "di wilayah Indonesia"},
            {"administrative_area": "Jakarta Pusat"},
            {"administrative_area": "Ringkasan kondisi cuaca harian di wilayah Indonesia"},
            {"value": 12.5},
            {"value": "rainfall"},
            {"value": "temperature"},
            {"value": "price"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_bmkg_ikhtisar(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("bmkg_ikhtisar", text)
            self.assertNotIn("ikhtisar-cuaca-harian", text)


if __name__ == "__main__":
    unittest.main()
