"""Offline tests for the WS2.2 Planet nightly delta worker.

Scene-id set diffs against the injected snapshot; the nightly cadence's
idempotence and the new-acquisition artefacts are proven without any
network (the quick-search document is injected).
"""

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import ingest_core
from farm_ontology.ingest_planet import (
    PLANET_JOB,
    SNAPSHOT_REL,
    diff_new_scenes,
    load_snapshot,
    run_planet_job,
    scene_row,
)

NOW = datetime(2026, 11, 18, 22, 0, tzinfo=timezone.utc)


def scene(sid: str, acquired="2026-11-18T06:12:11.000Z", cc=0.0) -> dict:
    return {
        "id": sid,
        "acquired": acquired,
        "cloud_cover": cc,
        "instrument": "PSB.SD",
        "publishing_stage": "final",
        "quality_category": "standard",
        "strip_id": "2266544",
    }


def doc(*scenes) -> dict:
    return {
        "matched": len(scenes),
        "scenes": list(scenes),
        "auth_scheme": "Basic",
        "retrieved_at": "2026-11-18T21:59:00+00:00",
    }


def new_backend():
    root = Path(tempfile.mkdtemp(prefix="ws2-pl-"))
    return root, ingest_core.local_pipe_backend(root)


class DiffTests(unittest.TestCase):
    def test_new_ids_are_those_absent_from_the_snapshot(self):
        snapshot = {"seen_scene_ids": ["A", "B"]}
        self.assertEqual(
            [s["id"] for s in diff_new_scenes(snapshot, [scene("B"), scene("C")])],
            ["C"],
        )

    def test_scene_row_strips_everything_but_headers(self):
        row = scene_row(scene("X"), job_day="20261118")
        for key in ("acquired", "cloud_cover", "instrument", "publishing_stage", "quality_category", "strip_id"):
            self.assertIn(key, row)
        self.assertEqual(row["scene_id"], "X")
        self.assertFalse(row["pixels_downloaded"])


class NightlyDeltaTests(unittest.TestCase):
    def setUp(self):
        self.root, self.backend = new_backend()

    def test_baseline_run_writes_every_scene_then_second_run_is_a_noop(self):
        first = run_planet_job(self.backend, now=NOW, search_document=doc(scene("A"), scene("B")))
        self.assertEqual(first["row_count"], 2)
        self.assertEqual(sorted(first["new_scene_ids"]), ["A", "B"])
        snapshot = load_snapshot(self.backend)
        self.assertEqual(set(snapshot["seen_scene_ids"]), {"A", "B"})
        acquisitions = [n for n in ingest_core.standing_alerts(self.backend, PLANET_JOB) if "acquisitions" in n]
        self.assertEqual(len(acquisitions), 2)

        before = {
            p.relative_to(self.root).as_posix(): p.read_bytes()
            for p in (self.root / "pipelines" / "planet").rglob("*.json")
        }
        second = run_planet_job(self.backend, now=NOW, search_document=doc(scene("A"), scene("B")))
        self.assertEqual(second["row_count"], 0)
        after = {
            p.relative_to(self.root).as_posix(): p.read_bytes()
            for p in (self.root / "pipelines" / "planet").rglob("*.json")
        }
        self.assertEqual(before, after)
        acquisitions = [n for n in ingest_core.standing_alerts(self.backend, PLANET_JOB) if "acquisitions" in n]
        self.assertEqual(len(acquisitions), 2)

    def test_new_acquisition_appends_only_the_new_scene(self):
        run_planet_job(self.backend, now=NOW, search_document=doc(scene("A")))
        third = run_planet_job(self.backend, now=NOW, search_document=doc(scene("A"), scene("C")))
        self.assertEqual(third["row_count"], 1)
        snapshot = load_snapshot(self.backend)
        self.assertEqual(set(snapshot["seen_scene_ids"]), {"A", "C"})

    def test_disappearing_scenes_leave_the_record_append_only(self):
        run_planet_job(self.backend, now=NOW, search_document=doc(scene("A"), scene("B")))
        shrunk = run_planet_job(self.backend, now=NOW, search_document=doc(scene("A")))
        self.assertEqual(shrunk["row_count"], 0)
        snapshot = load_snapshot(self.backend)
        self.assertEqual(set(snapshot["seen_scene_ids"]), {"A", "B"})
        rows = ingest_core.job_rows(self.backend, "planet", "scene-")
        self.assertEqual({row["scene_id"] for row in rows}, {"A", "B"})

    def test_gap_answer_is_a_failed_run_and_touches_no_state(self):
        result = run_planet_job(
            self.backend, now=NOW,
            search_document={"gap": "Planet rejected the mounted key (HTTP 403)"},
        )
        self.assertFalse(result["ok"])
        self.assertIn("gap", result["error"])
        self.assertEqual(load_snapshot(self.backend)["seen_scene_ids"], [])
        rows = ingest_core.run_rows(self.backend, PLANET_JOB)
        self.assertFalse(rows[0]["ok"])

    def test_row_honesty_flags_travel(self):
        run_planet_job(self.backend, now=NOW, search_document=doc(scene("Z")))
        rel = ingest_core.job_rows(self.backend, "planet", "scene-")[0]["file"]
        row = ingest_core.read_json(self.backend, rel)
        self.assertFalse(row["permits_financial_use"])
        self.assertEqual(row["record_owner"], "seges-ai")

    def test_snapshot_markers_survive_a_resnapshot(self):
        run_planet_job(self.backend, now=NOW, search_document=doc(scene("A")))
        snapshot = ingest_core.read_json(self.backend, SNAPSHOT_REL)
        self.assertTrue(snapshot["headers_only"])
        self.assertEqual(snapshot["snapshot_job"], PLANET_JOB)


if __name__ == "__main__":
    unittest.main()
