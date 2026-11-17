import json
import tempfile
import unittest
from pathlib import Path

from farm_ontology import fao_ffpi_current
from farm_ontology.policy import CLASS_C_POLICY

LIVE_BODY = """
<p>The FAO Food Price Index (FFPI)* averaged 133.9 points in October 2026,
down 1.6 points (1.2 percent) from its revised September level.</p>
<p>The FAO Cereal Price Index averaged 116.8 points in October,
down 5.5 points from September.</p>
"""


class FaoFfpiCurrentTest(unittest.TestCase):
    def test_stores_the_printed_october_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ffpi.json"
            fao_ffpi_current.record_fao_ffpi_current(
                path,
                fao_ffpi_current.FAO_FFPI_URL,
                LIVE_BODY,
            )
            stored = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            stored,
            {
                "index": "FAO Food Price Index",
                "month": "October 2026",
                "value": 133.9,
                "unit": "points",
                "citation_url": fao_ffpi_current.FAO_FFPI_URL,
                "permits_financial_use": False,
                "class_c_policy": "closed",
            },
        )
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        text = json.dumps(stored)
        self.assertNotIn("116.8", text)
        self.assertNotIn("1.6", text)
        self.assertNotIn("September", text)
        self.assertNotIn("trade", text)
        self.assertNotIn("traded price", text)

    def test_october_2026_index_is_not_a_traded_price(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "ffpi.json"
            fao_ffpi_current.record_fao_ffpi_current(
                path,
                fao_ffpi_current.FAO_FFPI_URL,
                LIVE_BODY,
            )
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(stored["index"], "FAO Food Price Index")
            self.assertEqual(stored["month"], "October 2026")
            self.assertEqual(stored["value"], 133.9)
            self.assertEqual(stored["unit"], "points")
            self.assertNotIn("price", stored)
            self.assertNotIn("trade", stored)
            self.assertFalse(stored["permits_financial_use"])
            self.assertFalse((folder / "trade.json").exists())
            self.assertEqual([item.name for item in folder.iterdir()], ["ffpi.json"])
            for label in ("traded price", "trade"):
                rejected = folder / "rejected.json"
                with self.assertRaises(ValueError):
                    fao_ffpi_current.record_fao_ffpi_current(
                        rejected,
                        fao_ffpi_current.FAO_FFPI_URL,
                        LIVE_BODY,
                        label=label,
                    )
                self.assertFalse(rejected.exists())

    def test_failed_request_or_empty_body_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ffpi.json"
            with self.assertRaises(ValueError):
                fao_ffpi_current.record_fao_ffpi_current(
                    path,
                    fao_ffpi_current.FAO_FFPI_URL,
                    LIVE_BODY,
                    request_failed=True,
                )
            with self.assertRaises(ValueError):
                fao_ffpi_current.record_fao_ffpi_current(
                    path,
                    fao_ffpi_current.FAO_FFPI_URL,
                    None,
                )
            self.assertFalse(path.exists())

    def test_missing_month_writes_nothing(self) -> None:
        missing = LIVE_BODY.replace(" in October 2026", "", 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ffpi.json"
            with self.assertRaises(ValueError):
                fao_ffpi_current.record_fao_ffpi_current(
                    path,
                    fao_ffpi_current.FAO_FFPI_URL,
                    missing,
                )
            self.assertFalse(path.exists())

    def test_missing_citation_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ffpi.json"
            with self.assertRaises(ValueError):
                fao_ffpi_current.record_fao_ffpi_current(path, None, LIVE_BODY)
            with self.assertRaises(ValueError):
                fao_ffpi_current.record_fao_ffpi_current(
                    path,
                    fao_ffpi_current.FAO_FFPI_URL.rstrip("/"),
                    LIVE_BODY,
                )
            self.assertFalse(path.exists())

    def test_traded_price_label_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ffpi.json"
            for label in ("traded price", "trade"):
                with self.assertRaises(ValueError):
                    fao_ffpi_current.record_fao_ffpi_current(
                        path,
                        fao_ffpi_current.FAO_FFPI_URL,
                        LIVE_BODY,
                        label=label,
                    )
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
