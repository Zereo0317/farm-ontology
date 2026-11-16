import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.fieldkit import GRID_DEG, SOYBEAN_ID
from farm_ontology.mcp_stdio import TOOLS, call_tool, handle
from farm_ontology.page_io import dispatch
from farm_ontology.record import add_note, list_notes, record_observation, status

AT = datetime(2026, 11, 17, 1, 0, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[1]


def _capture(grid=0.05):
    return {
        "response": {
            "utc_offset_seconds": 0,
            "timezone": "GMT",
            "hourly_units": {"precipitation": "mm"},
            "hourly": {
                "time": ["2026-11-17T01:00", "2026-11-17T02:00"],
                "precipitation": [0.0, 1.5],
            },
        },
        "issue_time": "2026-11-17T01:00:00+00:00",
        "availability_time": "2026-11-17T01:00:05+00:00",
        "grid_deg": grid,
        "model": "jma_msm",
        "local": "test-run",
        "feature_local": "jma-msm-native-grid-cell",
    }


class RecordTests(unittest.TestCase):
    def setUp(self):
        self._old = os.environ.get("FARM_RECORD_DIR")
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["FARM_RECORD_DIR"] = self._tmp.name

    def tearDown(self):
        if self._old is None:
            os.environ.pop("FARM_RECORD_DIR", None)
        else:
            os.environ["FARM_RECORD_DIR"] = self._old
        self._tmp.cleanup()

    def test_offline_observation_matches_fieldkit_rules(self):
        saved = record_observation(
            latitude=1.0,
            longitude=2.0,
            note="row A",
            sample_id="row-a",
            at=AT,
        )
        document = saved["observation"]
        record = Path(self._tmp.name)
        self.assertTrue(saved["file"].startswith("obs-"))
        self.assertTrue((record / saved["file"]).is_file())
        self.assertEqual(document["crop"], "soybean")
        self.assertEqual(document["crop_ontology_id"], SOYBEAN_ID)
        self.assertEqual(document["weather"]["native_resolution_deg"], GRID_DEG)
        self.assertFalse(document["weather"]["shrunk_to_plant"])
        self.assertIsNone(document["weather"]["value"])
        self.assertEqual(document["gps_accuracy"], "unknown")
        self.assertEqual(document["class_c_policy"], "closed")
        self.assertFalse(document["permits_financial_use"])
        self.assertFalse(document["trade_signal"])
        self.assertIsNone(document["yield"])
        self.assertIsNone(document["futures_price"])
        text = (ROOT / "farm_ontology" / "fieldkit.py").read_text(encoding="utf-8")
        self.assertNotIn("fetch_live_sample", text)
        self.assertEqual(status()["class_c_policy"], "closed")
        self.assertFalse(status()["permits_financial_use"])

    def test_weather_attach_keeps_the_grid_or_stays_empty(self):
        with patch("farm_ontology.adapters.open_meteo.fetch_live_sample", return_value=_capture()):
            saved = record_observation(
                latitude=1.0, longitude=2.0, attach_weather=True, at=AT
            )
        self.assertEqual(saved["observation"]["weather"]["value"], 1.5)
        self.assertEqual(saved["observation"]["weather"]["native_resolution_deg"], 0.05)
        self.assertFalse(saved["observation"]["weather"]["shrunk_to_plant"])
        self.assertFalse(saved["observation"]["permits_financial_use"])
        with patch("farm_ontology.adapters.open_meteo.fetch_live_sample", return_value=_capture(0.01)):
            refused = record_observation(
                latitude=1.0, longitude=2.0, attach_weather=True, at=AT
            )
        self.assertIsNone(refused["observation"]["weather"]["value"])
        self.assertIn("0.05", refused["observation"]["weather"]["attach_error"])

    def test_notes_and_mcp_tools_share_the_record(self):
        saved = record_observation(latitude=0.0, longitude=0.0, dry_run=True, at=AT)
        self.assertTrue(saved["observation"]["dry_run"])
        self.assertFalse(saved["observation"]["labeled_as_farm"])
        verified = add_note(kind="verification", text="row looked harvested", observation_file=saved["file"], at=AT)
        feedback = add_note(kind="feedback", text="moisture field was easy to skip", at=AT)
        record = Path(self._tmp.name)
        self.assertTrue(verified["file"].startswith("note-verification-"))
        self.assertTrue((record / "notes" / verified["file"]).is_file())
        self.assertTrue(feedback["file"].startswith("note-feedback-"))
        self.assertTrue((record / "notes" / feedback["file"]).is_file())
        self.assertEqual(verified["note"]["kind"], "verification")
        self.assertEqual(feedback["note"]["kind"], "feedback")
        self.assertFalse(feedback["note"]["permits_financial_use"])
        listed = list_notes()
        self.assertEqual(len(listed["observations"]), 1)
        self.assertEqual(len(listed["notes"]), 2)
        names = [tool["name"] for tool in TOOLS]
        self.assertEqual(
            names,
            [
                "show_status",
                "read_playbook",
                "read_sop",
                "record_field_observation",
                "list_notes",
                "add_note",
                "read_stored_header",
            ],
        )
        listed_tool = call_tool("list_notes", {})
        body = json.loads(listed_tool["content"][0]["text"])
        self.assertEqual(body["observations"][0]["crop_ontology_id"], "CO_336")
        reply = handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.assertEqual(reply["result"]["tools"][0]["name"], "show_status")
        self.assertIsNone(handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))

    def test_local_page_records_without_network(self):
        def refuse_network(*_args, **_kwargs):
            raise AssertionError("recording called the network")

        with (
            patch("socket.create_connection", side_effect=refuse_network),
            patch("urllib.request.urlopen", side_effect=refuse_network),
            patch("farm_ontology.adapters.open_meteo.fetch_live_sample", side_effect=refuse_network),
        ):
            saved = dispatch(
                {
                    "op": "observe",
                    "latitude": 1,
                    "longitude": 2,
                    "sample_id": "ui-row",
                    "dry_run": False,
                    "attach_weather": True,
                }
            )
            noted = dispatch(
                {
                    "op": "note",
                    "kind": "verification",
                    "text": "seen",
                    "observation_file": saved["file"],
                }
            )
        self.assertEqual(saved["observation"]["class_c_policy"], "closed")
        self.assertFalse(saved["observation"]["permits_financial_use"])
        self.assertIsNone(saved["observation"]["weather"]["value"])
        self.assertEqual(noted["note"]["kind"], "verification")
        bridge = (ROOT / "farm_ontology" / "page_io.py").read_text(encoding="utf-8")
        self.assertIn("attach_weather=False", bridge)
        self.assertNotIn("fetch_live_sample", bridge)
