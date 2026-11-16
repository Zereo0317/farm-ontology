import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.bmkg_potensi import BMKG_POTENSI_URL, PERIOD, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = BMKG_POTENSI_URL
SPANS = (
    "16 Nov 2026",
    "Periode 17 \u2013 23 November 2026",
    "12 Nov 2026",
    "Periode 13 \u2013 19 November 2026",
    "10 Nov 2026",
    "Periode 10 \u2013 16 November 2026",
    "6 Nov 2026",
    "Periode 6 \u2013 12 November 2026",
    "5 Nov 2026",
    "Periode 3 \u2013 10 November 2026",
    "29 Oct 2026",
    "Periode 30 Oktober \u2013 5 November 2026",
    "26 Oct 2026",
    "Periode 27 Oktober\u20132 November 2026",
    "22 Oct 2026",
    "Periode 23\u201329 Oktober 2026",
    "20 Oct 2026",
    "Periode 20\u201326 Oktober 2026",
    "15 Oct 2026",
    "Periode 16\u201322 Oktober 2026",
    "12 Oct 2026",
    "Periode 13\u201319 Oktober 2026",
    "8 Oct 2026",
    "Periode 9\u201315 Oktober 2026",
)


class BmkgPotensiTests(unittest.TestCase):
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
        self.assertEqual(header["product"], "Potensi Hujan Sepekan ke Depan")
        self.assertEqual(header["period"], PERIOD)
        self.assertIn("untuk sepekan ke depan", header["period"])
        for span in SPANS:
            self.assertIn(span, header["period"], span)
        self.assertNotIn("unit", header)
        self.assertNotIn("administrative_area", header)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "Potensi Hujan Sepekan ke Depan")
        self.assertEqual(header["kind"], header["product"])
        self.assertNotEqual(header["kind"], "forecast")
        self.assertNotEqual(header["kind"], "Cuaca")
        self.assertNotEqual(header["kind"], "Prakiraan")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(
            set(header),
            {
                "publisher",
                "product",
                "period",
                "citation_url",
                "kind",
                "permits_financial_use",
            },
        )
        for key in (
            "value",
            "price",
            "temperature",
            "rainfall",
            "trade",
            "figure",
            "unit",
            "administrative_area",
        ):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "Prakiraan",
            "prakiraan",
            "Cuaca",
            "Ikhtisar",
            "Ringkasan",
            "Ketentuan",
            "wilayah",
            "Indonesia",
            "mm",
            "rainfall",
            "temperature",
            "yield",
            "price",
            "trade",
            "settlement",
            "completed harvest",
            "forecast",
            "217",
            "Manampilkan",
            "Laman",
            "unit",
            "administrative",
            "pdf",
            "dataweb",
            "Jakarta",
            "licence",
            "license",
            "index",
            "position",
        ):
            self.assertNotIn(word, text, word)
        source = (ROOT / "farm_ontology" / "bmkg_potensi.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("https://www.bmkg.go.id/ is not the citation.", flat)
        self.assertIn(
            "https://www.bmkg.go.id/cuaca/prakiraan-cuaca is not the citation.",
            flat,
        )
        self.assertIn(
            "https://www.bmkg.go.id/cuaca/ikhtisar-cuaca-harian is not the citation.",
            flat,
        )
        self.assertIn("https://data.bmkg.go.id/prakiraan-cuaca/ is not the citation.", flat)
        self.assertIn(
            "The document title is Potensi Hujan Sepekan ke Depan - Cuaca - BMKG.",
            flat,
        )
        self.assertIn(
            "Potensi Hujan Sepekan ke Depan is the h1. It is the product and the kind.",
            flat,
        )
        self.assertIn("BMKG is a printed short name inside the one publisher.", flat)
        self.assertIn("The word hujan in the title is not a rainfall amount.", flat)
        self.assertIn("Cuaca is not a second kind.", flat)
        self.assertIn("Prakiraan is not a second kind.", flat)
        self.assertIn("Child article links were not opened.", flat)
        self.assertIn("Ikhtisar Cuaca Harian was not opened.", flat)
        self.assertIn("Ketentuan Penggunaan was not opened.", flat)
        self.assertIn(
            "The stored period includes untuk sepekan ke depan and the printed Periode spans.",
            flat,
        )
        self.assertIn("Unit is omitted.", flat)
        self.assertIn("Administrative area is omitted.", flat)
        self.assertIn(
            "The description sentence was not used to fill an administrative area.",
            flat,
        )
        self.assertIn(
            "Province names printed beside rainfall figures were not stored.",
            flat,
        )
        self.assertIn("Do not store a rainfall amount.", flat)
        self.assertIn("Do not store a temperature.", flat)
        self.assertIn("A forecast is not a completed harvest.", flat)
        self.assertIn("An index is not a quantity of goods.", flat)
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
            "https://www.bmkg.go.id/cuaca/ikhtisar-cuaca-harian",
            "https://www.bmkg.go.id/cuaca/potensi-hujan-sepekan/",
            "http://www.bmkg.go.id/cuaca/potensi-hujan-sepekan",
            "https://data.bmkg.go.id/prakiraan-cuaca/",
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
            "Prakiraan",
            "12.5",
            "217",
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
            {"period": PERIOD},
            {"period": "untuk sepekan ke depan"},
            {"period": "Periode 17 \u2013 23 November 2026"},
            {"unit": "mm"},
            {"unit": "temperature"},
            {"unit": "rainfall"},
            {"administrative_area": "di wilayah Indonesia"},
            {"administrative_area": "Jakarta Pusat"},
            {"administrative_area": "Indonesia"},
            {"value": 12.5},
            {"value": "rainfall"},
            {"value": "temperature"},
            {"value": "price"},
            {"value": "50 mm"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_bmkg_potensi(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("bmkg_potensi", text)
            self.assertNotIn("potensi-hujan-sepekan", text)


if __name__ == "__main__":
    unittest.main()
