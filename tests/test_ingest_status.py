"""Offline tests for the ingest status read side and the service endpoint.

``/farm/ingest-status`` must report last runs from the record backend,
publish GAPS for jobs without rows, and stay readable when the backend
itself is unusable. All clocks injected; the endpoint test rebinds the
backend through the documented environment seam.
"""

import sys
import tempfile
import unittest
import unittest.mock
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import http_service as hs
from farm_ontology import ingest_core
from farm_ontology.ingest_status import ingest_status, summarize_job
from farm_ontology.pipelines.hazards import run_hazard_job
from farm_ontology.ingest_weather import run_weather_job
from farm_ontology.ingest_planet import run_planet_job
from farm_ontology.ingest_ndvi import run_ndvi_job

NOW = datetime(2026, 11, 18, 3, 0, tzinfo=timezone.utc)
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


def new_backend():
    root = Path(tempfile.mkdtemp(prefix="ws2-st-"))
    return root, ingest_core.local_pipe_backend(root)


class StatusReadTests(unittest.TestCase):
    def setUp(self):
        self.root, self.backend = new_backend()

    def test_empty_backend_reports_gaps_not_health(self):
        report = ingest_status(self.backend, now=NOW)
        self.assertEqual(len(report["jobs"]), 4)
        for job, summary in report["jobs"].items():
            self.assertIsNone(summary["last_run"])
            self.assertIn("gap", summary)
        self.assertFalse(any(report["failures_at_threshold"].values()))

    def test_recent_successful_weather_run_is_not_stale(self):
        run_weather_job(self.backend, now=NOW, live_document=WX_DOC)
        summary = summarize_job(self.backend, "weather-hourly", now=NOW + timedelta(minutes=30))
        self.assertEqual(summary["last_ok"], True)
        self.assertFalse(summary["stale"])
        self.assertEqual(summary["last_row_count"], 1)

    def test_weather_run_past_two_hours_is_stale(self):
        run_weather_job(self.backend, now=NOW, live_document=WX_DOC)
        summary = summarize_job(self.backend, "weather-hourly", now=NOW + timedelta(hours=2, minutes=5))
        self.assertTrue(summary["stale"])

    def test_three_failed_days_surface_in_the_report(self):
        for offset in range(3):
            run_weather_job(self.backend, now=NOW + timedelta(days=offset), live_document={})
        report = ingest_status(self.backend, now=NOW + timedelta(days=3, hours=1))
        summary = report["jobs"]["weather-hourly"]
        self.assertEqual(summary["consecutive_failures"], 3)
        self.assertTrue(report["failures_at_threshold"]["weather-hourly"])
        self.assertEqual(len(summary["alerts_standing"]), 1)
        self.assertFalse(summary["last_ok"])

    def test_other_jobs_remain_gaps_while_one_job_runs(self):
        run_hazard_job(self.backend, now=NOW)
        report = ingest_status(self.backend, now=NOW)
        self.assertIsNone(report["jobs"]["ndvi-weekly"]["last_run"])
        self.assertEqual(report["jobs"]["hazard-daily"]["last_row_count"], 4)


class EndpointTests(unittest.TestCase):
    def test_endpoint_registered_in_banner_and_routes(self):
        self.assertIn("/farm/ingest-status", hs.STATUS_JSON["endpoints"])

    def test_endpoint_reads_through_the_env_backend(self):
        root, backend = new_backend()
        run_hazard_job(backend, now=NOW)
        run_weather_job(backend, now=NOW, live_document=WX_DOC)
        env = {
            "FARM_RECORD_BACKEND": "local",
            "FARM_PIPE_ROOT": str(root),
        }
        with unittest.mock.patch.dict("os.environ", env, clear=False):
            status, payload, kind = hs.handle_target("/farm/ingest-status")
        self.assertEqual(status, 200)
        self.assertEqual(kind, "json")
        self.assertIn("jobs", payload)
        self.assertEqual(payload["jobs"]["hazard-daily"]["last_row_count"], 4)
        self.assertTrue(payload["jobs"]["weather-hourly"]["last_ok"])

    def test_unusable_backend_degrades_to_an_explicit_gap(self):
        with unittest.mock.patch.dict(
            "os.environ",
            {"FARM_RECORD_BACKEND": "gcs", "FARM_RECORD_BUCKET": ""},
            clear=False,
        ):
            status, payload, kind = hs.handle_target("/farm/ingest-status")
        self.assertEqual(status, 200)
        self.assertIn("gap", payload)


if __name__ == "__main__":
    unittest.main()
