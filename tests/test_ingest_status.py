"""Offline tests for the ingest status read side and the service endpoint.

``/farm/ingest-status`` must report last runs from the record backend,
publish GAPS for jobs without rows, and stay readable when the backend
itself is unusable. All clocks injected; the endpoint test rebinds the
backend through the documented environment seam. task-9 additions
reproduce the prod-rev-00054 blindness with GCS-shaped fixtures.
"""

import json
import sys
import tempfile
import unittest
import unittest.mock
import urllib.parse
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
from farm_ontology.record_store import GcsBackend

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


# ---------------------------------------------------------------------------
# task-9 regressions: the prod-rev-00054 blindness class
# (env without the record-backend vars → reader silently fell back to an
# empty local store while the bucket held real run rows).


BUCKET = "farm-seges-ai-records"

#: The env EXACTLY as described on prod revision farm-seges-ai-00054
#: (SERVICE_VERSION prod-final-90c0992): GCP vars and the Planet secret,
#: but NEITHER FARM_RECORD_BACKEND nor FARM_RECORD_BUCKET.
PROD_REV_00054_ENV = {
    "GCP_PROJECT": "seges-ai",
    "EE_PROJECT": "seges-ai",
    "SERVICE_VERSION": "prod-final-90c0992",
}


class RealShapedGcsTransport:
    """GCS JSON API with REAL response metadata (generation, md5, crc32c,
    etag, contentType, storageClass, timeCreated/updated): the fixture
    class that proves the reader copes with genuine GCS shapes, not just
    the minimal in-memory stand-ins."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def __call__(self, method, url, headers, body):
        parsed = urllib.parse.urlsplit(url)
        query = urllib.parse.parse_qs(parsed.query)
        if method == "POST" and parsed.path == f"/upload/storage/v1/b/{BUCKET}/o":
            self.objects[query["name"][0]] = body
            return 200, {}, json.dumps({"name": query["name"][0]}).encode("utf-8")
        if method == "GET" and parsed.path == f"/storage/v1/b/{BUCKET}/o":
            prefix = query["prefix"][0]
            items = [
                {
                    "name": name,
                    "bucket": BUCKET,
                    "generation": "1763341200000000",
                    "metageneration": "1",
                    "contentType": "application/json",
                    "storageClass": "STANDARD",
                    "size": str(len(self.objects[name])),
                    "md5Hash": "rL0Y20zC+Fzt72VPzMSk2A==",
                    "crc32c": "vVSosQ==",
                    "etag": "CKaI4rDVuPECEAM=",
                    "timeCreated": "2026-11-18T02:00:00.123Z",
                    "updated": "2026-11-18T02:00:00.456Z",
                }
                for name in sorted(self.objects)
                if name.startswith(prefix)
            ]
            document = {"kind": "storage#objects", "totalSize": len(items)}
            if items:
                document["items"] = items
            return 200, {}, json.dumps(document).encode("utf-8")
        if method == "GET" and parsed.path.startswith(f"/storage/v1/b/{BUCKET}/o/"):
            name = urllib.parse.unquote(parsed.path.split("/o/", 1)[1])
            if name not in self.objects:
                return 404, {}, json.dumps(
                    {"error": {"code": 404, "message": f"No such object: {name}"}}
                ).encode("utf-8")
            if query.get("alt", [None])[0] == "media":
                return 200, {}, self.objects[name]
            return 200, {}, json.dumps(
                {"name": name, "updated": "2026-11-18T02:00:00.456Z"}
            ).encode("utf-8")
        return 400, {}, json.dumps({"error": {"code": 400, "message": "unexpected"}}).encode("utf-8")


def gcs_fixture_backend():
    """A seeded GCS backend with REAL-shaped transport: rows for all four jobs."""
    transport = RealShapedGcsTransport()
    backend = GcsBackend(BUCKET, "pipelines", request_fn=transport, token_fn=lambda: ("tok", 3600))
    base = datetime(2026, 11, 18, 2, 0, tzinfo=timezone.utc)
    for offset, job in enumerate(("weather-hourly", "planet-nightly", "hazard-daily", "ndvi-weekly")):
        ingest_core.append_run(
            backend, job=job, now=base,
            started=base, finished=base + timedelta(seconds=1 + offset),
            ok=True, row_count=1 + offset,
        )
    return backend


def scrubbed_env(**extra):
    """Env with the record-backend vars REMOVED (mimicking a prod shell)."""
    import os

    scrubbed = {key: os.environ[key] for key in os.environ if key in PROD_REV_00054_ENV or key == "FARM_PIPE_ROOT"}
    return unittest.mock.patch.dict(os.environ, {**scrubbed, **extra}, clear=True)


class ResolverHardeningTests(unittest.TestCase):
    def tearDown(self):
        unittest.mock.patch.stopall()

    def test_prod_rev_00054_env_resolves_to_local_shadow_and_blindspots(self):
        with tempfile.TemporaryDirectory() as home:
            with scrubbed_env(FARM_PIPE_ROOT=home):
                backend = ingest_core.open_pipe_backend()
        described = backend.describe()
        self.assertEqual(described["backend"], "local")
        # The DOCUMENTED root-cause shape: local store, no rows, per-job gaps.
        report = ingest_status(backend, now=NOW)
        for summary in report["jobs"].values():
            self.assertIsNone(summary["last_run"])
            self.assertIn("gap", summary)

    def test_bucket_var_alone_declares_durability_and_resolves_gcs(self):
        with scrubbed_env(FARM_RECORD_BUCKET=BUCKET):
            backend = ingest_core.open_pipe_backend()
        described = backend.describe()
        self.assertEqual(described["backend"], "gcs")
        self.assertEqual(described["bucket"], BUCKET)
        self.assertEqual(described["prefix"], "pipelines")

    def test_explicit_local_plus_bucket_is_refused_loudly(self):
        with scrubbed_env(FARM_RECORD_BACKEND="local", FARM_RECORD_BUCKET=BUCKET):
            with self.assertRaises(ValueError) as caught:
                ingest_core.open_pipe_backend()
        message = str(caught.exception)
        self.assertIn("FARM_RECORD_BACKEND=local", message)
        self.assertIn("FARM_RECORD_BUCKET", message)
        self.assertIn("silently read empty", message)

    def test_local_root_prefers_the_record_dir_seam_before_home(self):
        with tempfile.TemporaryDirectory() as record_dir:
            with scrubbed_env(FARM_RECORD_DIR=record_dir):
                backend = ingest_core.open_pipe_backend()
        self.assertEqual(backend.describe()["root"], str(Path(record_dir) / "pipelines"))

    def test_gcs_shaped_fixture_rows_are_visible_through_the_reader(self):
        backend = gcs_fixture_backend()
        report = ingest_status(backend, now=NOW)
        for job, summary in report["jobs"].items():
            self.assertIsNone(summary.get("gap"), msg=job)
            self.assertTrue(summary["last_run"].endswith(f"-{job}.json"), msg=job)
            self.assertGreaterEqual(summary["hours_since_last_run"], 0)


class ProdBlindspotEndpointTests(unittest.TestCase):
    def test_endpoint_carries_env_seen_for_instant_diagnosis(self):
        root = Path(tempfile.mkdtemp(prefix="ws2-fix-"))
        backend = ingest_core.local_pipe_backend(root)
        run_hazard_job(backend, now=NOW)
        env = {
            "FARM_RECORD_BACKEND": "local",
            "FARM_PIPE_ROOT": str(root),
        }
        with unittest.mock.patch.dict("os.environ", env, clear=False):
            status, payload, kind = hs.handle_target("/farm/ingest-status")
        self.assertEqual(status, 200)
        self.assertEqual(payload["env_seen"], {"FARM_RECORD_BACKEND": True, "FARM_RECORD_BUCKET": False})
        self.assertEqual(payload["jobs"]["hazard-daily"]["last_row_count"], 4)

    def test_endpoint_gap_names_the_env_conflict_when_local_shadows_a_bucket(self):
        env = {"FARM_RECORD_BACKEND": "local", "FARM_RECORD_BUCKET": BUCKET}
        with unittest.mock.patch.dict("os.environ", env, clear=False):
            status, payload, kind = hs.handle_target("/farm/ingest-status")
        self.assertEqual(status, 200)
        self.assertIn("gap", payload)
        self.assertIn("FARM_RECORD_BUCKET", payload["gap"])

    def test_endpoint_healed_shape_bucket_without_backend_var_reads_gcs_fixture(self):
        # After the resolver fix, the HALF-configured env (bucket declared,
        # backend var forgotten) reads the bucket: the exact regression that
        # blinded prod rev 00054, now cured in code as defense in depth.
        gcs_backend = gcs_fixture_backend()
        env = {"FARM_RECORD_BUCKET": BUCKET}
        with unittest.mock.patch.dict("os.environ", env, clear=False), \
                unittest.mock.patch(
                    "farm_ontology.ingest_core.open_pipe_backend",
                    return_value=gcs_backend,
                ), \
                unittest.mock.patch(
                    "farm_ontology.ingest_core.describe_backend",
                    return_value=gcs_backend.describe(),
                ):
            status, payload, kind = hs.handle_target("/farm/ingest-status")
        self.assertEqual(status, 200)
        self.assertEqual(payload["backend"]["backend"], "gcs")
        for job, summary in payload["jobs"].items():
            self.assertNotIn("gap", summary, msg=job)
            self.assertTrue(summary["last_ok"], msg=job)


if __name__ == "__main__":
    unittest.main()
