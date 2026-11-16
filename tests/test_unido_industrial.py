import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.unido_industrial import (
    UNIDO_INDUSTRIAL_URL,
    record_series_header,
)

ROOT = Path(__file__).resolve().parents[1]
URL = UNIDO_INDUSTRIAL_URL
NOT_OPENED = "the field was not opened"
PERIOD = "annual data from 2005 to 2020"
UNIT = "current prices, in both national currency and United States dollars"
AREA = "worldwide"


class UnidoIndustrialTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_series_header_without_a_figure(self):
        saved = record_series_header(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["publisher"], "UNIDO")
        self.assertEqual(
            header["product"],
            "The UNIDO Industrial Statistics (INDSTAT) Revision 4 Database",
        )
        self.assertEqual(header["period"], PERIOD)
        self.assertEqual(header["unit"], UNIT)
        self.assertEqual(header["administrative_area"], AREA)
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["kind"], NOT_OPENED)
        self.assertNotEqual(header["kind"], "index")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(
            set(header),
            {
                "publisher",
                "product",
                "period",
                "unit",
                "administrative_area",
                "citation_url",
                "kind",
                "permits_financial_use",
            },
        )
        for key in ("value", "price", "index_level", "growth", "trade", "figure", "copyright"):
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
            "index",
            "growth",
            "licence",
            "license",
            "110",
            "economies",
            "Access database",
            "updated annually",
            "monetary values",
        ):
            self.assertNotIn(word, text)
        source = (ROOT / "farm_ontology" / "unido_industrial.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("Database Descriptions | UNIDO Statistics Portal", flat)
        self.assertIn("The product heading also prints INDSTAT Revision 4.", flat)
        self.assertIn("https://stat.unido.org/ is not the citation.", flat)
        self.assertIn(
            "The period sentence is the database span, not one observation.",
            flat,
        )
        self.assertIn(
            "The unit sentence is the printed price basis, not a stored value.",
            flat,
        )
        self.assertIn("Worldwide is the printed coverage word.", flat)
        self.assertIn(
            "About 110 economies is the same coverage sentence and is not a second area.",
            flat,
        )
        self.assertIn("The (Access database) link was not opened.", flat)
        self.assertIn("Licence text was not printed.", flat)
        self.assertIn("The header is not marked public domain.", flat)
        self.assertIn(
            "Do not relabel this header as an index, a yield, a forecast, or a completed harvest.",
            flat,
        )
        self.assertIn("No index value, growth rate, or trade is stored.", flat)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        for citation in (
            "https://stat.unido.org/",
            "https://stat.unido.org",
            "https://stat.unido.org/data/database-descriptions/",
            "https://example.com/unido.html",
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
            "index",
            "index value",
            "growth",
            "growth rate",
            "figure",
            "1.4",
            "2.5%",
            "110",
            "Settlement",
            "YIELD",
            "Trade",
            "Forecast",
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

    def test_replaced_fields_and_figures_write_nothing(self):
        attempts = (
            {"period": NOT_OPENED},
            {"period": PERIOD},
            {"period": "2020"},
            {"unit": NOT_OPENED},
            {"unit": UNIT},
            {"unit": "index 2021=100"},
            {"administrative_area": NOT_OPENED},
            {"administrative_area": AREA},
            {"administrative_area": "about 110 economies"},
            {"kind": NOT_OPENED},
            {"kind": "index"},
            {"value": 101.2},
            {"value": "growth rate"},
            {"value": "110"},
        )
        for attempt in attempts:
            with self.assertRaises(ValueError):
                record_series_header(self.folder, citation_url=URL, **attempt)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_unido(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("unido_industrial", text)
            self.assertNotIn("database-descriptions", text)
