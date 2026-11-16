"""The Next page bridge writes the same record and does not call weather."""

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


if __name__ == "__main__":
    unittest.main()
