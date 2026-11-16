import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.indec_ipi import INDEC_IPI_URL, record_series_header

ROOT = Path(__file__).resolve().parents[1]
URL = INDEC_IPI_URL


class IndecIpiTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_an_index_or_percent(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "Instituto Nacional de Estadística y Censos")
        self.assertEqual(header["product"], "Índice de producción industrial manufacturero")
        self.assertEqual(header["period"], "Septiembre de 2026")
        self.assertEqual(header["unit"], "base 2004=100, en números índice")
        self.assertEqual(header["administrative_area"], "total del país")
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], "report")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(
            header["copyright_notice"],
            "Esta publicación utiliza una licencia Creative Commons. "
            "Se permite su reproducción con atribución de la fuente.",
        )
        self.assertNotIn("by-sa", header["copyright_notice"].lower())
        for key in (
            "value",
            "price",
            "index_level",
            "index_value",
            "percent",
            "quantity",
            "forecast",
            "start_year",
            "licence",
            "license",
        ):
            self.assertNotIn(key, header)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "settlement",
            "yield",
            "trade",
            "forecast",
            "observation",
            "completed harvest",
            "public domain",
            "benchmark",
            "trading right",
            "quantity of goods",
            "2016",
            "porcentual",
            "%",
            "％",
            "creativecommons.org",
            "by-sa",
            ".xls",
            "Estimador mensual industrial",
            "Ciudad Autónoma",
            "Buenos Aires",
            "Argentina",
            "2545-6636",
            "2545-6733",
            "Vol. 10",
            "©",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "indec_ipi.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("not Estimador mensual industrial", flat)
        self.assertIn("EMI archive page was not opened", flat)
        self.assertIn("ISSN 2545-6636", flat)
        self.assertIn("ISSN 2545-6733", flat)
        self.assertIn("nº 274", flat)
        self.assertIn("nº 37", flat)
        self.assertIn("Buenos Aires, noviembre de 2026", flat)
        self.assertIn("la cobertura geográfica es para el total del país", flat)
        self.assertIn("Ciudad Autónoma de Buenos Aires, Argentina", flat)
        self.assertIn("variación porcentual", flat)
        self.assertIn("https://creativecommons.org/licenses/by-sa/4.0/deed.es", flat)
        self.assertIn("deed page was not opened", flat)
        self.assertIn("Política de difusión del INDEC PDF", flat)
        self.assertIn("© 2026", flat)
        self.assertIn("sh_ipi_manufacturero_2026.xls", flat)
        self.assertIn("desde enero de 2016", flat)
        self.assertIn("2016 is not a verified start", flat)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://creativecommons.org/licenses/by-sa/4.0/deed.es",
            "https://www.indec.gob.ar/ftp/cuadros/economia/sh_ipi_manufacturero_2026.xls",
            "https://example.com/ipi.pdf",
        ):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_rejected_labels_write_nothing(self):
        labels = (
            "settlement",
            "yield",
            "trade",
            "forecast",
            "observation",
            "completed harvest",
            "public domain",
            "benchmark",
            "quantity of goods",
            "trading right",
            "verified start",
            "index level",
            "percent",
            "variación porcentual",
            "2016",
            "2004=100",
            "1.2%",
            "Settlement",
            "YIELD",
            "Trade",
            "Forecast",
            "Observation",
            "Completed Harvest",
            "Public Domain",
            "Benchmark",
        )
        for label in labels:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_stored_numbers_write_nothing(self):
        attempts = (
            {"value": 100},
            {"value": "1.2"},
            {"unit": "101.5"},
            {"period": "enero de 2016"},
            {"administrative_area": "Ciudad Autónoma de Buenos Aires"},
            {"unit": "variación porcentual"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_indec(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("indec_ipi", text)
            self.assertNotIn("ipi_manufacturero_11", text)
