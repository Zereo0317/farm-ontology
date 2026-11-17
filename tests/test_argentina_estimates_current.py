import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology.argentina_estimates import CITATION_URL
from farm_ontology.argentina_estimates_current import record_argentina_estimate_current
from farm_ontology.policy import CLASS_C_POLICY

FILE_URL = (
    "https://datos.magyp.gob.ar/dataset/9e1e77ba-267e-4eaa-a59f-3296e86b5f36/"
    "resource/95d066e6-8a0f-4a80-b59d-6f28f88eacd5/download/"
    "estimaciones-agricolas-2026-03.csv"
)
CATALOG = f"""
<h1>Agricultura - Estimaciones agrícolas</h1>
<p>Cobertura temporal (Inicio) 1969-01-01</p>
<li class="resource-item" data-id="2f3d94e1-9e58-5e51-a25d-d6c2bbc697fe">
  <a class="heading" href="/dataset/estimaciones-agricolas/resource/2f3d94e1-9e58-5e51-a25d-d6c2bbc697fe" title="Estimaciones agrícolas">
    Estimaciones agrícolas<span class="format-label">CSV</span>
  </a>
  <a class="dropdown-item resource-url-analytics" href="{FILE_URL}">Ir al recurso</a>
</li>
<li class="resource-item">
  <a class="heading" title="Serie de Tiempo Estimación de Trigo Pan">Serie de Tiempo</a>
  <a href="https://datos.magyp.gob.ar/serie-de-tiempo-trigo.csv">Descargar</a>
</li>
"""
FILE_BODY = """cultivo,anio,campania,provincia,provincia_id,departamento,departamento_id,superficie_sembrada_ha,superficie_cosechada_ha,produccion_tm,rendimiento_kgxha
algodón,2024,2024/2025,Catamarca,10,Capayán,10021,400,400,1080,2700
trigo total,2024,2024/2025,Buenos Aires,06,General Arenales,06294,28000,28000,117600,4200
yerba mate,2024,2023/2024,Misiones,54,Guaraní,54056,15839,13996,74180,5300
"""


class ArgentinaEstimateCurrentTest(unittest.TestCase):
    def test_stores_one_printed_production_figure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "estimate.json"
            record_argentina_estimate_current(path, CITATION_URL, CATALOG, FILE_BODY)
            stored = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            stored,
            {
                "series": "trigo total",
                "period": "2024/2025",
                "province": "Buenos Aires",
                "department": "General Arenales",
                "figure": "produccion_tm",
                "value": 117600,
                "unit": "tm",
                "kind": "estimate",
                "citation_url": FILE_URL,
                "file_url": FILE_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertNotEqual(stored["citation_url"], CITATION_URL)
        text = json.dumps(stored)
        for word in ("4200", "28000", "74180", "1080", "kg/ha", "kgxha", "farm", "trade", "yield", "completed harvest"):
            self.assertNotIn(word, text)

    def test_failed_request_or_empty_catalog_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "estimate.json"
            with self.assertRaises(ValueError):
                record_argentina_estimate_current(
                    path,
                    CITATION_URL,
                    CATALOG,
                    FILE_BODY,
                    request_failed=True,
                )
            with self.assertRaises(ValueError):
                record_argentina_estimate_current(path, CITATION_URL, None, FILE_BODY)
            self.assertFalse(path.exists())

    def test_missing_figure_or_link_writes_nothing(self) -> None:
        no_link = "<h1>Estimaciones agrícolas</h1><p>1969-01-01</p>"
        no_figure = "cultivo,campania,provincia,departamento,produccion_tm,superficie_sembrada_ha,superficie_cosechada_ha\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "estimate.json"
            with self.assertRaises(ValueError):
                record_argentina_estimate_current(path, CITATION_URL, no_link, FILE_BODY)
            with self.assertRaises(ValueError):
                record_argentina_estimate_current(path, CITATION_URL, CATALOG, no_figure)
            with self.assertRaises(ValueError):
                record_argentina_estimate_current(path, CITATION_URL, CATALOG, None)
            self.assertFalse(path.exists())

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "estimate.json"
            with self.assertRaises(ValueError):
                record_argentina_estimate_current(path, None, CATALOG, FILE_BODY)
            with self.assertRaises(ValueError):
                record_argentina_estimate_current(
                    path,
                    CITATION_URL + "/",
                    CATALOG,
                    FILE_BODY,
                )
            self.assertFalse(path.exists())

    def test_reading_the_stored_record_writes_no_trade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "estimate.json"
            record_argentina_estimate_current(path, CITATION_URL, CATALOG, FILE_BODY)
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(stored["series"], "trigo total")
            self.assertEqual(stored["period"], "2024/2025")
            self.assertEqual(stored["province"], "Buenos Aires")
            self.assertEqual(stored["department"], "General Arenales")
            self.assertEqual(stored["value"], 117600)
            self.assertNotIn("trade", stored)
            self.assertNotIn("farm", stored)
            self.assertNotIn("yield", stored)
            self.assertFalse(stored["permits_financial_use"])
            self.assertFalse((folder / "trade.json").exists())
            self.assertEqual([item.name for item in folder.iterdir()], ["estimate.json"])
            for label in ("trade", "farm", "yield", "completed harvest"):
                rejected = folder / "rejected.json"
                with self.assertRaises(ValueError):
                    record_argentina_estimate_current(
                        rejected,
                        CITATION_URL,
                        CATALOG,
                        FILE_BODY,
                        label=label,
                    )
                self.assertFalse(rejected.exists())


if __name__ == "__main__":
    unittest.main()
