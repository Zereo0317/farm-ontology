import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.planet_scenes import record_planet_scenes
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
RESPONSE = (ROOT / "tests" / "fixtures" / "planet-hokkaido-china.json").read_text(encoding="utf-8")


class PlanetSceneTests(unittest.TestCase):
    def test_stores_the_printed_scene_headers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "planet-scenes.json"
            record_planet_scenes(path, RESPONSE)
            stored = json.loads(path.read_text(encoding="utf-8"))
        regions = {region["region"]: region for region in stored["regions"]}
        self.assertEqual(
            (
                regions["hokkaido"]["scene_id"],
                regions["hokkaido"]["item_type"],
                regions["hokkaido"]["acquired"],
            ),
            ("20261117_011638_27_2570", "PSScene", "2026-11-17T01:16:38.278446Z"),
        )
        self.assertEqual(regions["hokkaido"]["latitude"], "42.7018152")
        self.assertEqual(regions["hokkaido"]["longitude"], "142.4071291")
        self.assertTrue(regions["hokkaido"]["not_the_biratori_field_harvest"])
        self.assertEqual(
            (
                regions["china"]["scene_id"],
                regions["china"]["item_type"],
                regions["china"]["acquired"],
            ),
            ("20261117_031202_96_2588", "PSScene", "2026-11-17T03:12:02.962777Z"),
        )
        self.assertEqual(regions["china"]["search"], "country extent")
        self.assertTrue(regions["china"]["not_a_farm_coordinate"])
        self.assertNotIn("latitude", regions["china"])
        for region in regions.values():
            self.assertTrue(region["not_a_trade"])
            for absent in ("pixel", "reflectance", "yield", "harvest"):
                self.assertNotIn(absent, region)
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertNotIn("permits_financial_use_test", stored)

    def test_a_refused_region_stores_no_scene(self) -> None:
        payload = json.loads(RESPONSE)
        payload["china"] = {"http_status": 403, "feature_count": 0, "error": "forbidden"}
        payload["hokkaido"]["reflectance"] = 0.2
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "planet-scenes.json"
            record_planet_scenes(path, json.dumps(payload))
            stored = json.loads(path.read_text(encoding="utf-8"))
        regions = {region["region"]: region for region in stored["regions"]}
        self.assertEqual(regions["china"]["http_status"], 403)
        for field in ("scene_id", "item_type", "acquired"):
            self.assertNotIn(field, regions["china"])
        self.assertNotIn("reflectance", regions["hokkaido"])
        self.assertEqual(regions["hokkaido"]["scene_id"], "20261117_011638_27_2570")

    def test_a_trade_switch_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "planet-scenes.json"
            with self.assertRaises(ValueError):
                record_planet_scenes(path, "")
            with self.assertRaises(ValueError):
                record_planet_scenes(path, RESPONSE, label="yield")
            with self.assertRaises(ValueError):
                record_planet_scenes(path, RESPONSE, permits_financial_use=True)
            with self.assertRaises(ValueError):
                record_planet_scenes(path, RESPONSE, permits_financial_use_test=True)
            with self.assertRaises(ValueError):
                record_planet_scenes(path, RESPONSE, class_c_policy="open")
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_scenes(self) -> None:
        source = (ROOT / "farm_ontology" / "planet_scenes.py").read_text(encoding="utf-8")
        self.assertNotIn("planet-api-key", source)
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("planet_scenes", text)


if __name__ == "__main__":
    unittest.main()
