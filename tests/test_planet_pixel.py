import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.planet_pixel import NO_PIXEL, record_planet_pixel
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
RESPONSE = (ROOT / "tests" / "fixtures" / "planet-hokkaido-pixel.json").read_text(encoding="utf-8")


class PlanetPixelTests(unittest.TestCase):
    def test_the_asset_call_stores_nothing(self) -> None:
        payload = json.loads(RESPONSE)
        self.assertNotIn("bands", payload)
        self.assertEqual(payload["assets_http_status"], 200)
        self.assertEqual(payload["assets"], [])
        self.assertEqual(payload["permissions"], [])
        self.assertEqual(payload["publishing_stage"], "preview")
        self.assertEqual(payload["message"], NO_PIXEL)
        for status in payload["asset_requests"].values():
            self.assertEqual(status, 404)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "planet-pixel.json"
            with self.assertRaises(ValueError) as caught:
                record_planet_pixel(path, RESPONSE)
            self.assertEqual(str(caught.exception), NO_PIXEL)
            self.assertFalse(path.exists())

    def test_printed_bands_keep_the_scene_and_the_point(self) -> None:
        printed = {
            "scene_id": "20261117_011638_27_2570",
            "bands": {"blue": 1, "green": 2, "red": 3, "nir": 4},
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "planet-pixel.json"
            record_planet_pixel(path, json.dumps(printed))
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["scene_id"], "20261117_011638_27_2570")
        self.assertEqual(stored["latitude"], "42.7018152")
        self.assertEqual(stored["longitude"], "142.4071291")
        self.assertEqual(stored["bands"], {"blue": 1, "green": 2, "red": 3, "nir": 4})
        self.assertNotIn("yield", stored)
        self.assertNotIn("reflectance", stored)
        self.assertTrue(stored["not_the_biratori_field_harvest"])
        self.assertTrue(stored["not_a_trade"])
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertNotIn("permits_financial_use_test", stored)

    def test_a_trade_switch_writes_nothing(self) -> None:
        printed = json.dumps(
            {"scene_id": "20261117_011638_27_2570", "bands": {"blue": 1}}
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "planet-pixel.json"
            with self.assertRaises(ValueError):
                record_planet_pixel(path, "")
            with self.assertRaises(ValueError):
                record_planet_pixel(path, printed, label="yield")
            with self.assertRaises(ValueError):
                record_planet_pixel(path, printed, permits_financial_use=True)
            with self.assertRaises(ValueError):
                record_planet_pixel(path, printed, permits_financial_use_test=True)
            with self.assertRaises(ValueError):
                record_planet_pixel(path, printed, class_c_policy="open")
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_pixel(self) -> None:
        source = (ROOT / "farm_ontology" / "planet_pixel.py").read_text(encoding="utf-8")
        self.assertNotIn("planet-api-key", source)
        self.assertNotIn("20261117_031202_96_2588", source)
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("planet_pixel", text)


if __name__ == "__main__":
    unittest.main()
