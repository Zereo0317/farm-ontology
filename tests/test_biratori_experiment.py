import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.biratori_experiment import (
    MAP_URL,
    PLACE,
    PLUS_CODE,
    PURPOSE,
    UNSTORED_CLASSES,
    financial_mode_print,
    record_experiment_point,
)
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]


class BiratoriExperimentTests(unittest.TestCase):
    def test_stores_the_given_place(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "biratori-experiment.json"
            record_experiment_point(path)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["plus_code"], PLUS_CODE)
        self.assertEqual(stored["plus_code"], "PC24+PVC")
        self.assertEqual(stored["place"], PLACE)
        self.assertEqual(stored["place"], "Biratori, Hokkaido, Japan")
        self.assertEqual(stored["locality"], "Biratori")
        self.assertEqual(stored["prefecture"], "Hokkaido")
        self.assertEqual(stored["country"], "Japan")
        self.assertEqual(stored["map_url"], MAP_URL)
        self.assertEqual(stored["purpose"], PURPOSE)
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertNotIn("permits_financial_use_test", stored)
        text = json.dumps(stored)
        for key in (
            "latitude",
            "longitude",
            "satellite",
            "weather",
            "soil",
            "water",
            "yield",
            "demand",
        ):
            self.assertNotIn(key, text)

    def test_invented_values_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "biratori-experiment.json"
            for kwargs in (
                {"latitude": 42.5},
                {"longitude": 142.2},
                {"satellite": 1},
                {"weather": 1},
                {"soil": 1},
                {"water": 1},
                {"yield_value": 1},
                {"demand": 1},
                {"permits_financial_use": True},
                {"permits_financial_use_test": True},
                {"class_c_policy": "open"},
                {"plus_code": "other"},
            ):
                with self.assertRaises(ValueError):
                    record_experiment_point(path, **kwargs)
            self.assertFalse(path.exists())

    def test_financial_mode_print_lists_the_place_and_is_not_a_trade(self) -> None:
        text = financial_mode_print()
        print(text)
        self.assertIn(PLUS_CODE, text)
        self.assertIn(PLACE, text)
        self.assertIn(MAP_URL, text)
        self.assertIn(PURPOSE, text)
        self.assertEqual(len(UNSTORED_CLASSES), 6)
        for sentence in UNSTORED_CLASSES:
            self.assertIn(sentence, text)
        self.assertIn("this print is not a trade", text)
        self.assertNotIn("permits_financial_use_test", text)

    def test_field_save_does_not_ingest_the_place(self) -> None:
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("biratori_experiment", text)
            self.assertNotIn("PC24+PVC", text)
            self.assertNotIn("maps.app.goo.gl/dKfj9uWuQm8U1aQi9", text)


if __name__ == "__main__":
    unittest.main()
