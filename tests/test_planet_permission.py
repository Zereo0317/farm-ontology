import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.planet_permission import record_planet_permission
from farm_ontology.policy import CLASS_C_POLICY

ROOT = Path(__file__).resolve().parents[1]
RESPONSE = (ROOT / "tests" / "fixtures" / "planet-permission-search.json").read_text(encoding="utf-8")
REASON = (
    "4950 items checked, HTTP 200; 4949 items had empty permissions; "
    "20261117_011638_27_2570 was skipped; no item with permissions was returned"
)


class PlanetPermissionTests(unittest.TestCase):
    def test_empty_permissions_store_nothing(self) -> None:
        payload = json.loads(RESPONSE)
        self.assertNotIn("stored", payload)
        self.assertEqual(payload["items_checked"], 4950)
        self.assertEqual(payload["http_status"], [200])
        self.assertEqual(payload["empty_permissions"], 4949)
        self.assertEqual(payload["skipped_scene"], "20261117_011638_27_2570")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "planet-permission.json"
            with self.assertRaises(ValueError) as caught:
                record_planet_permission(path, RESPONSE)
            self.assertEqual(str(caught.exception), REASON)
            self.assertFalse(path.exists())

    def test_printed_permission_fields_are_kept(self) -> None:
        printed = {
            "stored": {
                "scene_id": "printed-by-response",
                "acquired": "printed-time",
                "publishing_stage": "printed-stage",
                "quality_category": "printed-quality",
                "permissions": ["printed-permission"],
                "pixel": 1,
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "planet-permission.json"
            record_planet_permission(path, json.dumps(printed))
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["scene_id"], "printed-by-response")
        self.assertEqual(stored["acquired"], "printed-time")
        self.assertEqual(stored["publishing_stage"], "printed-stage")
        self.assertEqual(stored["quality_category"], "printed-quality")
        self.assertEqual(stored["permissions"], ["printed-permission"])
        self.assertEqual(stored["latitude"], "42.7018152")
        self.assertEqual(stored["longitude"], "142.4071291")
        self.assertNotIn("pixel", stored)
        self.assertNotIn("yield", stored)
        self.assertTrue(stored["not_a_yield"])
        self.assertTrue(stored["not_a_trade"])
        self.assertFalse(stored["permits_financial_use"])
        self.assertEqual(stored["class_c_policy"], CLASS_C_POLICY)
        self.assertNotIn("permits_financial_use_test", stored)

    def test_the_skipped_scene_is_not_stored(self) -> None:
        printed = {
            "stored": {
                "scene_id": "20261117_011638_27_2570",
                "permissions": ["printed-permission"],
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "planet-permission.json"
            with self.assertRaises(ValueError):
                record_planet_permission(path, json.dumps(printed))
            self.assertFalse(path.exists())

    def test_a_trade_switch_writes_nothing(self) -> None:
        printed = json.dumps(
            {"stored": {"scene_id": "printed-by-response", "permissions": ["printed-permission"]}}
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "planet-permission.json"
            with self.assertRaises(ValueError):
                record_planet_permission(path, "")
            with self.assertRaises(ValueError):
                record_planet_permission(path, printed, label="yield")
            with self.assertRaises(ValueError):
                record_planet_permission(path, printed, permits_financial_use=True)
            with self.assertRaises(ValueError):
                record_planet_permission(path, printed, permits_financial_use_test=True)
            with self.assertRaises(ValueError):
                record_planet_permission(path, printed, class_c_policy="open")
            self.assertFalse(path.exists())

    def test_field_save_does_not_ingest_the_search(self) -> None:
        source = (ROOT / "farm_ontology" / "planet_permission.py").read_text(encoding="utf-8")
        self.assertNotIn("planet-api-key", source)
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("planet_permission", text)


if __name__ == "__main__":
    unittest.main()
