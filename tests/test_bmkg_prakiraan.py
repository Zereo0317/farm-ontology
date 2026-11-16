import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.bmkg_prakiraan import BMKG_PRAKIRAAN_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = BMKG_PRAKIRAAN_URL


class BmkgPrakiraanTests(unittest.TestCase):
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
            "Badan Meteorologi, Klimatologi, dan Geofisika",
        )
        self.assertEqual(header["product"], "Prakiraan Cuaca")
        self.assertNotIn("period", header)
        self.assertNotIn("unit", header)
        self.assertEqual(header["administrative_area"], "di seluruh wilayah Indonesia")
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Prakiraan Cuaca")
        self.assertEqual(header["kind"], header["product"])
        self.assertNotEqual(header["kind"], "forecast")
        self.assertNotEqual(header["product"], "public weather forecast")
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
            "BMKG",
            "settlement",
            "yield",
            "price",
            "trade",
            "forecast",
            "observation",
            "completed harvest",
            "public domain",
            "benchmark",
            "index",
            "rainfall",
            "temperature",
            "Kelurahan",
            "Peringatan",
            "Provinsi",
            "Aceh",
            "Jakarta",
            "Kemayoran",
            "Ketentuan",
            "2026",
            "Ikhtisar",
            "Potensi",
            "Hujan",
            "gempa",
            "data.bmkg.go.id",
            "licence",
            "license",
            "the field was not opened",
            "period",
            "unit",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "bmkg_prakiraan.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("https://www.bmkg.go.id/ is not the citation.", flat)
        self.assertIn("https://data.bmkg.go.id/prakiraan-cuaca/ is not the citation.", flat)
        self.assertIn(
            "The homepage title is BMKG - Badan Meteorologi, Klimatologi, dan Geofisika.",
            flat,
        )
        self.assertIn("That title is the publisher. It is not a forecast product title.", flat)
        self.assertIn("BMKG is a printed short name, not a second publisher.", flat)
        self.assertIn(
            "The forecast page title is Prakiraan Cuaca | BMKG - Badan Meteorologi, Klimatologi, dan Geofisika.",
            flat,
        )
        self.assertIn("Prakiraan Cuaca Kelurahan/Desa is menu text, not the product.", flat)
        self.assertIn("Ikhtisar Cuaca Harian was not opened.", flat)
        self.assertIn("Potensi Hujan Sepekan ke Depan was not opened.", flat)
        self.assertIn("Period was not opened and is omitted.", flat)
        self.assertIn("Unit was not opened and is omitted.", flat)
        self.assertIn("The stored administrative area is di seluruh wilayah Indonesia.", flat)
        self.assertIn(
            "Peringatan dini di wilayah Indonesia. is not the administrative area.",
            flat,
        )
        self.assertIn("Provinsi Lainnya is not the administrative area.", flat)
        self.assertIn(
            "Jl. Angkasa I No.2 Kemayoran, Jakarta Pusat 10610, PO Box 3540 Jkt. is not the administrative area.",
            flat,
        )
        self.assertIn("© 2026 is a copyright line, not a period.", flat)
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
            "https://www.bmkg.go.id/cuaca/prakiraan-cuaca/",
            "https://data.bmkg.go.id/prakiraan-cuaca/",
            "http://www.bmkg.go.id/cuaca/prakiraan-cuaca",
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
            {"period": "the field was not opened"},
            {"unit": "the field was not opened"},
            {"administrative_area": "di seluruh wilayah Indonesia"},
            {"period": "Ikhtisar Cuaca Harian"},
            {"period": "Potensi Hujan Sepekan ke Depan"},
            {"unit": "temperature"},
            {"unit": "rainfall"},
            {"administrative_area": "Peringatan dini di wilayah Indonesia."},
            {"administrative_area": "DKI Jakarta"},
            {"administrative_area": "Indonesia"},
            {"value": 12.5},
            {"value": "rainfall"},
            {"value": "temperature"},
            {"value": "price"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_bmkg_prakiraan(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("bmkg_prakiraan", text)
            self.assertNotIn("cuaca/prakiraan-cuaca", text)


if __name__ == "__main__":
    unittest.main()
