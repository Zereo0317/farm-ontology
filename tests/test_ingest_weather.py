"""Offline tests for the WS2.1 hourly weather worker.

Clocks, backends, and the fetch result are all injected; the network is
never touched. Dedupe (equal phenomenon-hour+values), the always-written
run row, and the 3-strike alert are exercised end to end.
"""

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import ingest_core
from farm_ontology.ingest_weather import (
    WEATHER_JOB,
    run_weather_job,
    weather_observation,
)

NOW = datetime(2026, 11, 18, 2, 0, tzinfo=timezone.utc)


def wx_doc(value_mm=0.8, phenomenon="2026-11-18T01:00:00+00:00") -> dict:
    return {
        "captured_live": True,
        "model": "jma_msm",
        "issue_time": "2026-11-18T00:00:00+00:00",
        "availability_time": "2026-11-18T00:40:00+00:00",
        "valid_time": phenomenon,
        "valid_end": "2026-11-18T02:00:00+00:00",
        "value_mm": value_mm,
        "grid_deg": 0.05,
        "local": "jma-msm-live",
        "feature_local": "jma-msm-005deg-biratori",
    }


def day(offset: int) -> datetime:
    return NOW + timedelta(days=offset)


def new_backend():
    root = Path(tempfile.mkdtemp(prefix="ws2-wx-"))
    return root, ingest_core.local_pipe_backend(root)


class ShapeTests(unittest.TestCase):
    def test_observation_shape_names_support_and_times(self):
        row = weather_observation(wx_doc(), captured_at=NOW)
        self.assertEqual(row["kind"], WEATHER_JOB)
        self.assertEqual(row["model"], "jma_msm")
        self.assertEqual(row["spatial_support"], "grid-cell")
        self.assertEqual(row["grid_deg"], 0.05)
        self.assertEqual(row["phenomenon_hour"], "2026-11-18T01:00:00+00:00")
        self.assertEqual(row["captured_at"], NOW.isoformat())
        self.assertEqual(row["unit"], "mm")
        self.assertEqual(row["value_mm"], 0.8)


class DedupeTests(unittest.TestCase):
    def setUp(self):
        self.root, self.backend = new_backend()

    def test_second_equal_run_writes_nothing_new(self):
        first = run_weather_job(self.backend, now=NOW, live_document=wx_doc())
        second = run_weather_job(self.backend, now=NOW, live_document=wx_doc())
        self.assertEqual(first["row_count"], 1)
        self.assertEqual(second["row_count"], 0)
        self.assertIsNone(second["written_row"])
        rows = ingest_core.job_rows(self.backend, "weather", "wx-")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["value_mm"], 0.8)

    def test_changed_value_in_the_same_hour_is_new_evidence(self):
        run_weather_job(self.backend, now=NOW, live_document=wx_doc(value_mm=0.8))
        result = run_weather_job(self.backend, now=NOW, live_document=wx_doc(value_mm=1.4))
        self.assertEqual(result["row_count"], 1)
        rows = ingest_core.job_rows(self.backend, "weather", "wx-")
        self.assertEqual(sorted(row["value_mm"] for row in rows), [0.8, 1.4])

    def test_next_phenomenon_hour_is_always_new(self):
        run_weather_job(self.backend, now=NOW, live_document=wx_doc())
        later = wx_doc(phenomenon="2026-11-18T02:00:00+00:00")
        result = run_weather_job(self.backend, now=NOW, live_document=later)
        self.assertEqual(result["row_count"], 1)


class FailureTests(unittest.TestCase):
    def setUp(self):
        self.root, self.backend = new_backend()

    def test_failure_is_logged_not_raised(self):
        result = run_weather_job(self.backend, now=NOW, live_document={})
        self.assertFalse(result["ok"])
        self.assertIn("weather-hourly failed", result["error"])
        rows = ingest_core.run_rows(self.backend, WEATHER_JOB)
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["ok"])
        self.assertIn("'model'", rows[0]["error"])

    def test_three_failed_days_fire_the_alert(self):
        for offset in range(2):
            run_weather_job(self.backend, now=day(offset), live_document={})
        standing = ingest_core.standing_alerts(self.backend, WEATHER_JOB)
        self.assertEqual(standing, [])
        third = run_weather_job(self.backend, now=day(2), live_document={})
        self.assertEqual(third["consecutive_failures"], 3)
        self.assertIsNotNone(third["alert"])
        standing = ingest_core.standing_alerts(self.backend, WEATHER_JOB)
        self.assertEqual(len(standing), 1)
        alert = ingest_core.read_json(self.backend, standing[0])
        self.assertEqual(alert["job"], WEATHER_JOB)
        self.assertEqual(len(alert["evidence"]), 3)

    def test_recovery_resets_the_count(self):
        for offset in range(2):
            run_weather_job(self.backend, now=day(offset), live_document={})
        run_weather_job(self.backend, now=day(2), live_document=wx_doc())
        fourth = run_weather_job(self.backend, now=day(3), live_document={})
        self.assertEqual(fourth["consecutive_failures"], 1)
        self.assertIsNone(fourth["alert"])


if __name__ == "__main__":
    unittest.main()
