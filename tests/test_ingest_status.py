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
from farm_ontology.ingest_status import (
    WATCHED_JOBS,
    compose_status,
    ingest_status,
    job_of_row_name,
    summarize_job,
)
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
    the minimal in-memory stand-ins. Counts list vs media-get calls so
    the task-15 I/O-budget assertions can be exact."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}
        self.lists_count = 0
        self.media_gets_count = 0

    def __call__(self, method, url, headers, body):
        parsed = urllib.parse.urlsplit(url)
        query = urllib.parse.parse_qs(parsed.query)
        if method == "POST" and parsed.path == f"/upload/storage/v1/b/{BUCKET}/o":
            self.objects[query["name"][0]] = body
            return 200, {}, json.dumps({"name": query["name"][0]}).encode("utf-8")
        if method == "GET" and parsed.path == f"/storage/v1/b/{BUCKET}/o":
            self.lists_count += 1
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
                self.media_gets_count += 1
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


# ---------------------------------------------------------------------------
# task-15 / Sprint-G: cache + single-listing fast path.


def gcs_seeded_backend(*, rows_per_job: int, newest_failures: int = 0):
    """Fully-real-shaped GCS backend; per job: rows_per_job DATED rows,
    the NEWEST `newest_failures` of them failed. Returns (backend, transport).
    """
    transport = RealShapedGcsTransport()
    backend = GcsBackend(BUCKET, "pipelines", request_fn=transport, token_fn=lambda: ("tok", 3600))
    base = datetime(2026, 11, 1, 2, 0, tzinfo=timezone.utc)
    for job in ("weather-hourly", "planet-nightly", "hazard-daily", "ndvi-weekly"):
        for index in range(rows_per_job):
            moment = base + timedelta(days=index)
            failed = index >= rows_per_job - newest_failures
            ingest_core.append_run(
                backend, job=job, now=moment, started=moment,
                finished=moment + timedelta(seconds=1),
                ok=not failed, row_count=0 if failed else 1,
                error="synthetic decline" if failed else None,
            )
    return backend, transport


def fresh_caches():
    """Flush ALL process-wide caches for identical-identity isolation."""
    ingest_core.clear_row_caches()
    ingest_core.invalidate_ingest_status_cache("test-setup")


class FastComposeIoBudgetTests(unittest.TestCase):
    def setUp(self):
        fresh_caches()

    def test_name_parser_maps_dates_and_rejects_aliens(self):
        self.assertEqual(job_of_row_name("run-log/20261118-weather-hourly.json"), "weather-hourly")
        self.assertEqual(job_of_row_name("20261118-planet-nightly.json"), "planet-nightly")
        self.assertIsNone(job_of_row_name("20261118-mystery-job.json"))
        self.assertIsNone(job_of_row_name("not-a-run-row.json"))
        self.assertIsNone(job_of_row_name("20261118-.json"))

    def test_two_listings_and_minimal_gets_even_with_long_history(self):
        # 30 rows per job; the fast path must NOT read them all: it lists
        # twice (concurrently) and reads bounded newest strides.
        backend, transport = gcs_seeded_backend(rows_per_job=30)
        report = compose_status(backend, now=datetime(2026, 12, 1, 3, 0, tzinfo=timezone.utc))
        self.assertEqual(transport.lists_count, 2)
        # Successful newest rows: first stride (3) per job, walked in order.
        self.assertEqual(transport.media_gets_count, 12)
        for job, summary in report["jobs"].items():
            self.assertEqual(summary["consecutive_failures"], 0, msg=job)
            self.assertEqual(len(summary["recent_runs"]), 3, msg=job)

    def test_strike_walk_early_exits_and_counts_exact_streak(self):
        # Newest 5 rows failed, 25 older rows succeeded: strikes == 5 while
        # the full-history read would have cost 30 GETs.
        backend, transport = gcs_seeded_backend(rows_per_job=30, newest_failures=5)
        report = compose_status(backend, now=datetime(2026, 12, 1, 3, 0, tzinfo=timezone.utc))
        summary = report["jobs"]["weather-hourly"]
        self.assertEqual(summary["consecutive_failures"], 5)
        self.assertFalse(summary["last_ok"])
        self.assertTrue(summary["recent_runs"][0]["ok"] is False)
        # 3 (first stride) + 8 (failure extension) per job, bounded.
        self.assertEqual(transport.media_gets_count, 3 * 4 + 8 * 4)
        # All four jobs were seeded with the same newest-failures pattern.
        self.assertEqual(
            report["failures_at_threshold"],
            {job: True for job in WATCHED_JOBS},
        )

    def test_singleflight_avoids_duplicate_gets_inside_one_compose(self):
        backend, transport = gcs_seeded_backend(rows_per_job=3)
        compose_status(backend, now=datetime(2026, 12, 1, 3, 0, tzinfo=timezone.utc))
        gets_first = transport.media_gets_count
        compose_status(backend, now=datetime(2026, 12, 1, 3, 0, tzinfo=timezone.utc))
        # Second compose: everything warm from the row cache — ZERO GETs.
        self.assertEqual(transport.media_gets_count, gets_first)


class CacheFacadeTests(unittest.TestCase):
    def setUp(self):
        fresh_caches()
        self.backend, self.transport = gcs_seeded_backend(rows_per_job=2)
        self.now = datetime(2026, 11, 3, 3, 0, tzinfo=timezone.utc)

    def test_first_call_misses_second_hits_within_ttl(self):
        first = ingest_status(self.backend, now=self.now)
        second = ingest_status(self.backend, now=self.now)
        self.assertFalse(first["cache"]["hit"])
        self.assertTrue(second["cache"]["hit"])
        lists_after_first = self.transport.lists_count
        self.transport.lists_count = 0
        ingest_status(self.backend, now=self.now)
        self.assertEqual(self.transport.lists_count, 0)  # hit: zero storage
        self.assertEqual(lists_after_first, 2)

    def test_ttl_expiry_rebuilds_using_the_monotonic_clock(self):
        ingest_status(self.backend, now=self.now)
        frozen = ingest_core.status_clock()
        with unittest.mock.patch.object(ingest_core, "status_clock", lambda: frozen + 61):
            expired = ingest_status(self.backend, now=self.now)
        self.assertFalse(expired["cache"]["hit"])
        self.assertEqual(expired["jobs"]["weather-hourly"]["last_ok"], True)

    def test_append_run_invalidates_operators_never_see_stale_strikes(self):
        ingest_status(self.backend, now=self.now)  # warm
        hit = ingest_status(self.backend, now=self.now)
        self.assertTrue(hit["cache"]["hit"])
        self.assertEqual(hit["jobs"]["weather-hourly"]["consecutive_failures"], 0)
        later = self.now + timedelta(days=1)
        ingest_core.append_run(
            self.backend, job="weather-hourly", now=later,
            started=later, finished=later, ok=False, row_count=0,
            error="fresh failure the operator must see",
        )
        fresh = ingest_status(self.backend, now=later + timedelta(minutes=1))
        self.assertFalse(fresh["cache"]["hit"])
        self.assertEqual(fresh["jobs"]["weather-hourly"]["consecutive_failures"], 1)
        self.assertIn("fresh failure", fresh["jobs"]["weather-hourly"]["last_error"])

    def test_alert_writes_invalidate_and_surface_promptly(self):
        # Warm the cache, then manufacture a 3-strike ALERT on the store.
        ingest_status(self.backend, now=self.now)
        hit = ingest_status(self.backend, now=self.now)
        self.assertTrue(hit["cache"]["hit"])
        failures = gcs_seeded_backend  # noqa: F841 (documentation anchor)
        later = self.now + timedelta(days=2)
        for offset in range(3):
            moment = later + timedelta(days=offset)
            ingest_core.append_run(
                self.backend, job="hazard-daily", now=moment,
                started=moment, finished=moment, ok=False, row_count=0,
                error="declined",
            )
            ingest_core.on_run_finished(
                self.backend, job="hazard-daily", now=moment,
                run={"ok": False, "error": "declined", "row_count": 0,
                     "started": ingest_core.iso(moment),
                     "finished": ingest_core.iso(moment), "file": ""},
            )
        report = ingest_status(self.backend, now=later + timedelta(days=3))
        self.assertFalse(report["cache"]["hit"])
        # 2 seeded successes then 3 fresh failures -> a 3-streak + the ALERT.
        self.assertEqual(report["jobs"]["hazard-daily"]["consecutive_failures"], 3)
        self.assertEqual(len(report["jobs"]["hazard-daily"]["alerts_standing"]), 1)

    def test_cross_backend_isolation(self):
        ingest_status(self.backend, now=self.now)
        empty_root = Path(tempfile.mkdtemp(prefix="ws2-empty-"))
        empty_backend = ingest_core.local_pipe_backend(empty_root)
        empty_report = ingest_status(empty_backend, now=self.now)
        self.assertIn("gap", empty_report["jobs"]["weather-hourly"])
        back = ingest_status(self.backend, now=self.now)
        self.assertNotIn("gap", back["jobs"]["weather-hourly"])
        self.assertTrue(back["cache"]["hit"])

    def test_fast_and_legacy_composers_agree(self):
        varied, _transport = gcs_seeded_backend(rows_per_job=6, newest_failures=2)
        now = datetime(2026, 12, 2, 4, 0, tzinfo=timezone.utc)
        fast = compose_status(varied, now=now)
        legacy_jobs = {}
        for job in WATCHED_JOBS:
            legacy_jobs[job] = summarize_job(varied, job, now=now)
        for job in WATCHED_JOBS:
            for key in ("last_run", "last_ok", "last_row_count", "last_error",
                        "hours_since_last_run", "stale", "staleness_limit",
                        "consecutive_failures", "alerts_standing", "recent_runs"):
                self.assertEqual(
                    fast["jobs"][job][key], legacy_jobs[job][key],
                    msg=f"{job}.{key}",
                )
        self.assertEqual(
            fast["failures_at_threshold"],
            {job: legacy_jobs[job]["consecutive_failures"] >= ingest_core.CONSECUTIVE_FAILURE_ALERT_AT
             for job in WATCHED_JOBS},
        )

    def test_endpoint_carries_cache_bookkeeping(self):
        root = Path(tempfile.mkdtemp(prefix="ws2-cep-"))
        backend = ingest_core.local_pipe_backend(root)
        run_hazard_job(backend, now=NOW)
        env = {"FARM_RECORD_BACKEND": "local", "FARM_PIPE_ROOT": str(root)}
        with unittest.mock.patch.dict("os.environ", env, clear=False):
            first = hs.handle_target("/farm/ingest-status")[1]
            second = hs.handle_target("/farm/ingest-status")[1]
        self.assertFalse(first["cache"]["hit"])
        self.assertTrue(second["cache"]["hit"])
        self.assertEqual(second["jobs"], first["jobs"])


if __name__ == "__main__":
    unittest.main()
