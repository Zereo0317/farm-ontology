import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology import conab_soja
from farm_ontology.policy import CLASS_C_POLICY


class ConabSojaTest(unittest.TestCase):
    def test_stores_printed_brasil_cells(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "conab-soja.json"
            conab_soja.record_conab_soja(path, conab_soja.CONAB_SOJA_URL)
            header = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            header,
            {
                "source": "Conab",
                "product": "SOJA - BRASIL",
                "row": "BRASIL",
                "cells": [
                    {
                        "sheet": "Produção",
                        "series": "Série Histórica de Produção",
                        "row": "BRASIL",
                        "column": "2025/26",
                        "value": 180406.6,
                        "unit": "Em mil toneladas",
                    },
                    {
                        "sheet": "Produção",
                        "series": "Série Histórica de Produção",
                        "row": "BRASIL",
                        "column": "2026/27 Previsão (¹)",
                        "value": 181616.6,
                        "unit": "Em mil toneladas",
                        "label": "forecast",
                        "legend": "Legenda: (¹) Estimativa em novembro/2026.",
                    },
                    {
                        "sheet": "Área",
                        "series": "Série Histórica de Área Plantada",
                        "row": "BRASIL",
                        "column": "2025/26",
                        "value": 48608.6,
                        "unit": "Em mil hectares",
                    },
                    {
                        "sheet": "Produtividade",
                        "series": "Série Histórica de Produtividade",
                        "row": "BRASIL",
                        "column": "2025/26",
                        "value": 3711.4147229091154,
                        "unit": "Em kg/ha",
                    },
                ],
                "citation_url": conab_soja.CONAB_SOJA_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(header["class_c_policy"], CLASS_C_POLICY)
        production = header["cells"][0]
        forecast = header["cells"][1]
        productivity = header["cells"][3]
        self.assertNotIn("Previsão", production["column"])
        self.assertNotIn("label", production)
        self.assertEqual(forecast["label"], "forecast")
        self.assertNotEqual(productivity["value"], 3711)
        self.assertIn("3711.4147229091154", json.dumps(header))

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "conab-soja.json"
            with self.assertRaises(ValueError):
                conab_soja.record_conab_soja(path, None)
            with self.assertRaises(ValueError):
                conab_soja.record_conab_soja(path, "   ")
            self.assertFalse(path.exists())

    def test_other_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "conab-soja.json"
            for citation in (
                conab_soja.CONAB_SOJA_URL + "/",
                "https://www.gov.br/conab/pt-br",
                "https://www.conab.gov.br/",
            ):
                with self.assertRaises(ValueError):
                    conab_soja.record_conab_soja(path, citation)
            self.assertFalse(path.exists())

    def test_yield_label_and_derived_value_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "conab-soja.json"
            for label in ("yield", "farm yield", "price", "trade", "completed harvest"):
                with self.assertRaises(ValueError):
                    conab_soja.record_conab_soja(
                        path,
                        conab_soja.CONAB_SOJA_URL,
                        label=label,
                    )
            with self.assertRaises(ValueError):
                conab_soja.record_conab_soja(
                    path,
                    conab_soja.CONAB_SOJA_URL,
                    cells=[{"value": None}],
                )
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_cell(self) -> None:
        source = (
            Path(conab_soja.__file__).read_text(encoding="utf-8").replace("\n", " ")
        )
        self.assertIn("not a farm yield", source)
        self.assertIn("not a completed harvest", source)
        self.assertIn("not derived from production and area", source)
        self.assertIn("Fonte: Conab", source)
        self.assertIn("Estimativa em novembro/2026.", source)
        self.assertNotIn("field_save", source)


if __name__ == "__main__":
    unittest.main()
