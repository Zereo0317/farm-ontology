"""Offline tests for the pipelines/run_worker.py dispatcher.

Includes the acceptance proof the workstream is judged by: RUNNING A
JOB TWICE WRITES NOTHING NEW THE SECOND TIME (data-tree digest
unchanged; only the dated run row legitimately turns over).
"""

import io
import json
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipelines import run_worker
from farm_ontology import ingest_core

NOW = datetime(2026, 11, 18, 5, 20, tzinfo=timezone.utc)
WX_DOC = {
    "captured_live": True,
    "model": "jma_msm",
    "issue_time": "2026-11-18T00:00:00+00:00",
    "availability_time": "2026-11-18T00:40:00+00:00",
    "valid_time": "2026-11-18T01:00:00+00:00",
    "valid_end": "2026-11-18T02:00:00+00:00",
    "value_mm": 0.0,
    "grid_deg": 0.05,
    "local": "jma-msm-live",
    "feature_local": "jma-msm-005deg-biratori",
}
PLANET_DOC = {
    "matched": 1,
    "scenes": [
        {
            "id": "20261118_012345_88",
            "acquired": "2026-11-18T01:23:45.000Z",
            "cloud_cover": 0.0,
            "instrument": "PSB.SD",
            "publishing_stage": "final",
            "quality_category": "standard",
            "strip_id": "2266544",
        }
    ],
}


def digest(root: Path, subdirs=("weather", "planet", "hazards", "ndvi")) -> dict:
    out = {}
    for name in subdirs:
        base = root / "pipelines" / name
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.json")):
            out[path.relative_to(root).as_posix()] = path.read_bytes()
    return out


def new_root() -> Path:
    return Path(tempfile.mkdtemp(prefix="ws2-worker-"))


class SchedulerContractTests(unittest.TestCase):
    DEPLOY_SH = Path(__file__).resolve().parents[1] / "deploy" / "create-schedulers.sh"

    def crons_in_deploy_script(self) -> dict:
        text = self.DEPLOY_SH.read_text(encoding="utf-8")
        crons = {}
        for job, cron in run_worker.SCHEDULER_CRONS_JST:
            pattern = rf'{re.escape(job)}\)\s+echo\s+"{re.escape(cron)}"\s+;;'
            if re.search(pattern, text):
                crons[job] = cron
        return crons

    def test_code_mirror_covers_every_worker_job(self):
        self.assertEqual(
            {job for job, _cron in run_worker.SCHEDULER_CRONS_JST},
            set(run_worker.WORKER_JOBS),
        )

    def test_deploy_script_and_code_agree_on_crons(self):
        mirrored = self.crons_in_deploy_script()
        self.assertEqual(
            mirrored, dict(run_worker.SCHEDULER_CRONS_JST)
        )


class DispatchTests(unittest.TestCase):
    def test_unknown_job_is_refused(self):
        root = new_root()
        with self.assertRaises(ValueError):
            run_worker.run_job("mars-weather", ingest_core.local_pipe_backend(root), now=NOW)

    def test_hazard_job_dispatches_offline_by_default(self):
        root = new_root()
        result = run_worker.run_job("hazard-daily", ingest_core.local_pipe_backend(root), now=NOW)
        self.assertTrue(result["ok"])
        self.assertEqual(result["row_count"], 4)

    def test_ndvi_unarmed_dispatch_fails_the_run_honestly(self):
        root = new_root()
        result = run_worker.run_job("ndvi-weekly", ingest_core.local_pipe_backend(root), now=NOW)
        self.assertFalse(result["ok"])
        self.assertIn("not armed", result["error"])


class MainEntrypointTests(unittest.TestCase):
    def run_main(self, *argv) -> tuple:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = run_worker.main(list(argv))
        return code, buffer.getvalue()

    def test_weather_via_document_file_and_local_root(self):
        root = new_root()
        doc_path = root / "wx-inject.json"
        doc_path.write_text(json.dumps(WX_DOC), encoding="utf-8")
        code, output = self.run_main(
            "weather-hourly", "--now", "2026-11-18T05:20:00+09:00",
            "--local-root", str(root / "store"),
            "--document", str(doc_path),
        )
        self.assertEqual(code, 0)
        payload = json.loads(output)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["row_count"], 1)

    def test_planet_twice_is_one_dataset_then_nothing(self):
        root = new_root()
        doc_path = root / "planet-inject.json"
        doc_path.write_text(json.dumps(PLANET_DOC), encoding="utf-8")
        common = (
            "planet-nightly", "--now", "2026-11-18T22:00:00+09:00",
            "--local-root", str(root / "store"),
            "--document", str(doc_path),
        )
        code, first = self.run_main(*common)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(first)["row_count"], 1)
        code, second = self.run_main(*common)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(second)["row_count"], 0)


class IdempotenceProofTests(unittest.TestCase):
    """THE acceptance proof: the second run writes nothing new."""

    def test_weather_double_run_leaves_data_tree_byte_identical(self):
        root = new_root()
        backend = ingest_core.local_pipe_backend(root)
        run_worker.run_job("weather-hourly", backend, now=NOW, live_document=dict(WX_DOC))
        before = digest(root)
        self.assertEqual(len(before), 1)
        second = run_worker.run_job("weather-hourly", backend, now=NOW, live_document=dict(WX_DOC))
        self.assertEqual(digest(root), before)
        self.assertEqual(second["row_count"], 0)
        self.assertIsNone(second["written_row"])

    def test_planet_double_run_leaves_data_tree_byte_identical(self):
        root = new_root()
        backend = ingest_core.local_pipe_backend(root)
        run_worker.run_job("planet-nightly", backend, now=NOW, search_document=PLANET_DOC)
        before = digest(root)
        self.assertEqual(len(before), 1)
        run_worker.run_job("planet-nightly", backend, now=NOW, search_document=PLANET_DOC)
        self.assertEqual(digest(root), before)

    def test_hazard_double_run_leaves_data_tree_byte_identical(self):
        root = new_root()
        backend = ingest_core.local_pipe_backend(root)
        run_worker.run_job("hazard-daily", backend, now=NOW)
        before = digest(root)
        self.assertEqual(len(before), 4)
        run_worker.run_job("hazard-daily", backend, now=NOW)
        self.assertEqual(digest(root), before)

    def test_ndvi_double_run_same_week_overwrites_one_identical_row(self):
        root = new_root()
        backend = ingest_core.local_pipe_backend(root)
        stats = {"aggregation": {"interval": [{"bins": {"ndvi B0": {"mean": 0.4}}}]}}

        def fake(request_body, *, now):
            return json.loads(json.dumps(stats))

        run_worker.run_job("ndvi-weekly", backend, now=NOW, latitude=42.7, longitude=142.4, transport=fake)
        before = digest(root)
        self.assertEqual(len(before), 1)
        second = run_worker.run_job("ndvi-weekly", backend, now=NOW, latitude=42.7, longitude=142.4, transport=fake)
        self.assertEqual(digest(root), before)
        self.assertEqual(second["row_count"], 1)


if __name__ == "__main__":
    unittest.main()
