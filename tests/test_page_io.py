"""The Next page bridge writes the same record and does not call weather."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.page_io import dispatch


class PageIoTests(unittest.TestCase):
    def setUp(self):
        self._old = os.environ.get("FARM_RECORD_DIR")
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["FARM_RECORD_DIR"] = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()
        if self._old is None:
            os.environ.pop("FARM_RECORD_DIR", None)
        else:
            os.environ["FARM_RECORD_DIR"] = self._old

    def test_observe_ignores_weather_and_stays_closed(self):
        saved = dispatch(
            {
                "op": "observe",
                "latitude": 1,
                "longitude": 2,
                "sample_id": "bridge-row",
                "note": "standing at the row",
                "attach_weather": True,
                "dry_run": False,
            }
        )
        obs = saved["observation"]
        self.assertEqual(obs["class_c_policy"], "closed")
        self.assertFalse(obs["permits_financial_use"])
        self.assertIsNone(obs["weather"]["value"])
        self.assertNotIn("attach_error", obs["weather"])
        self.assertEqual(obs["crop_ontology_id"], "CO_336")
        record = Path(self._tmp.name)
        self.assertTrue(saved["file"].startswith("obs-"))
        self.assertTrue(saved["file"].endswith(".json"))
        self.assertTrue((record / saved["file"]).is_file())
        listed = dispatch({"op": "list"})
        self.assertEqual(listed["observations"][0]["file"], saved["file"])
        note = dispatch(
            {
                "op": "note",
                "kind": "feedback",
                "text": "the type is large enough",
                "observation_file": saved["file"],
            }
        )
        self.assertEqual(note["note"]["kind"], "feedback")
        self.assertFalse(note["note"]["permits_financial_use"])
        self.assertTrue(note["file"].startswith("note-feedback-"))
        self.assertTrue((record / "notes" / note["file"]).is_file())

    def test_next_sources_do_not_call_weather_or_maps(self):
        root = Path(__file__).resolve().parents[1] / "web"
        parts = []
        for path in root.rglob("*"):
            if path.suffix not in {".ts", ".tsx", ".css", ".js"}:
                continue
            if "node_modules" in path.parts or ".next" in path.parts:
                continue
            parts.append(path.read_text(encoding="utf-8"))
        text = "\n".join(parts).lower()
        self.assertNotIn("open-meteo", text)
        self.assertNotIn("attach_weather", text)
        self.assertNotIn("maps.googleapis", text)
        self.assertNotIn("earthengine", text)
        self.assertIn("zh-tw", text)
        self.assertIn("zh-cn", text)
        self.assertIn('"ja"', text)
        self.assertIn("geolocation", text)
        self.assertNotIn("openstreetmap", text)

    def test_mcp_and_fieldkit_write_the_same_coordinates(self):
        from farm_ontology.fieldkit import main
        from farm_ontology.mcp_stdio import call_tool

        kit_dir = tempfile.TemporaryDirectory()
        self.addCleanup(kit_dir.cleanup)
        out = Path(kit_dir.name) / "kit.json"
        self.assertEqual(
            main(["--lat", "1.25", "--lon", "2.5", "--sample-id", "shared-row", "--out", str(out)]),
            0,
        )
        kit = json.loads(out.read_text(encoding="utf-8"))
        saved = call_tool(
            "record_field_observation",
            {
                "latitude": 1.25,
                "longitude": 2.5,
                "sample_id": "shared-row",
                "attach_weather": False,
            },
        )
        body = json.loads(saved["content"][0]["text"])
        obs = body["observation"]
        record = Path(self._tmp.name)
        self.assertTrue(body["file"].startswith("obs-"))
        self.assertTrue((record / body["file"]).is_file())
        self.assertEqual(list(record.glob("kit.json")), [])
        self.assertEqual(set(kit), set(obs))
        self.assertEqual(set(kit["weather"]), set(obs["weather"]))
        self.assertEqual(kit["latitude"], obs["latitude"])
        self.assertEqual(kit["longitude"], obs["longitude"])
        self.assertEqual(kit["row_or_sample_id"], obs["row_or_sample_id"])
        self.assertEqual(obs["class_c_policy"], "closed")
        self.assertFalse(obs["permits_financial_use"])
        self.assertFalse(kit["permits_financial_use"])
        self.assertIsNone(obs["weather"]["value"])
        flags = (Path(__file__).resolve().parents[1] / "farm_ontology" / "fieldkit.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"--lat"', flags)
        self.assertIn('"--lon"', flags)


if __name__ == "__main__":
    unittest.main()
