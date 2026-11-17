import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import indec_ipi_nivel
from farm_ontology.indec_ipi import (
    COPYRIGHT_NOTICE,
    INDEC_IPI_URL,
    record_series_header,
)
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = "https://www.indec.gob.ar/ftp/cuadros/economia/sh_ipi_manufacturero_2026.xls"
INFORME = (
    "Índice de producción industrial manufacturero Septiembre de 2026 "
    "Esta publicación utiliza una licencia Creative Commons. "
    "Se permite su reproducción con atribución de la fuente. "
    "la cobertura geográfica es para el total del país. "
    "base 2004=100, en números índice y variación porcentual. "
    "2026* Enero 106,2 -3,9 -3,9 118,5 2,3 116,5 0,2 "
    "Agosto 119,2 -3,1 -2,7 114,2 2,3 115,2 -0,5 "
    "Septiembre 122,4 -1,8 -2,6 115,1 0,7 114,7 -0,4 "
    + WORKBOOK
)
OTHER_LEVEL = (
    "Índice de producción industrial manufacturero Septiembre de 2026 "
    "Esta publicación utiliza una licencia Creative Commons. "
    "Se permite su reproducción con atribución de la fuente. "
    "total del país base 2004=100 "
    "2026* Enero 1,0 1,0 1,0 1,0 1,0 1,0 1,0 "
    "Septiembre 99,9 -1,0 -2,0 88,8 0,1 77,7 -0,2"
)


class IndecIpiNivelTests(unittest.TestCase):
    def test_header_still_rejects_a_number(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaises(ValueError):
                record_series_header(folder, citation_url=INDEC_IPI_URL, value="122,4")
            self.assertEqual(list(folder.iterdir()), [])

    def test_stores_the_printed_original_level_with_the_attribution_sentence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "indec-ipi-nivel.json"
            indec_ipi_nivel.record_index_level(path, INDEC_IPI_URL, INFORME)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            stored,
            {
                "copyright_notice": COPYRIGHT_NOTICE,
                "product": "Índice de producción industrial manufacturero",
                "period": "Septiembre de 2026",
                "administrative_area": "total del país",
                "unit": "base 2004=100",
                "series": "serie original",
                "value": "122,4",
                "kind": "index",
                "citation_url": INDEC_IPI_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(stored)
        for leftover in (
            "-1,8",
            "-2,6",
            "115,1",
            "0,7",
            "114,7",
            "-0,4",
            "%",
            ".xls",
            "trade",
            "harvest",
            "quantity",
        ):
            self.assertNotIn(leftover, text)
        self.assertNotEqual(stored["kind"], "trade")
        self.assertNotEqual(stored["kind"], "quantity of goods")

    def test_a_different_printed_level_is_not_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "indec-ipi-nivel.json"
            indec_ipi_nivel.record_index_level(path, INDEC_IPI_URL, OTHER_LEVEL)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["value"], "99,9")
        self.assertNotEqual(stored["value"], "122,4")
        self.assertEqual(stored["copyright_notice"], COPYRIGHT_NOTICE)

    def test_reading_the_stored_level_writes_no_trade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "indec-ipi-nivel.json"
            indec_ipi_nivel.record_index_level(path, INDEC_IPI_URL, INFORME)
            before = path.read_text(encoding="utf-8")
            stored = json.loads(before)
            after = path.read_text(encoding="utf-8")
            names = sorted(item.name for item in folder.iterdir())
        self.assertEqual(after, before)
        self.assertEqual(names, ["indec-ipi-nivel.json"])
        self.assertFalse((folder / "trade.json").exists())
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], "closed")
        self.assertNotIn("trade", after)

    def test_percent_only_or_workbook_writes_nothing(self) -> None:
        percent_only = (
            "Índice de producción industrial manufacturero Septiembre de 2026 "
            + COPYRIGHT_NOTICE
            + " total del país base 2004=100 una caída de 1,8% "
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "indec-ipi-nivel.json"
            with self.assertRaises(ValueError):
                indec_ipi_nivel.record_index_level(path, INDEC_IPI_URL, percent_only)
            with self.assertRaises(ValueError):
                indec_ipi_nivel.record_index_level(
                    path,
                    INDEC_IPI_URL,
                    INFORME,
                    source_url=WORKBOOK,
                )
            for citation in (None, "", "   ", WORKBOOK):
                with self.assertRaises(ValueError):
                    indec_ipi_nivel.record_index_level(path, citation, INFORME)
            self.assertFalse(path.exists())

    def test_trade_or_open_class_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "indec-ipi-nivel.json"
            for label in ("trade", "quantity of goods", "1,8%", "variación porcentual"):
                with self.assertRaises(ValueError):
                    indec_ipi_nivel.record_index_level(
                        path,
                        INDEC_IPI_URL,
                        INFORME,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                indec_ipi_nivel.record_index_level(
                    path,
                    INDEC_IPI_URL,
                    INFORME,
                    permits_financial_use=True,
                )
            with self.assertRaises(ValueError):
                indec_ipi_nivel.record_index_level(
                    path,
                    INDEC_IPI_URL,
                    INFORME,
                    class_c_policy="open",
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_level(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("indec_ipi_nivel", text)
            self.assertNotIn("sh_ipi_manufacturero_2026.xls", text)


if __name__ == "__main__":
    unittest.main()
