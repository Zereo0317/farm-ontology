"""Offline tests for the WS2 ingestion plumbing (ingest_core).

Clocks and backends are injected; nothing reads a wall clock, and no
network exists in these tests (GCS is exercised through an in-memory
stand-in for the transport function, the recorded-discipline way).
"""

import hashlib
import json
import re
import sys
import tempfile
import unittest
import unittest.mock
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import ingest_core
from farm_ontology.record_store import GcsBackend, LocalBackend

NOW = datetime(2026, 11, 18, 2, 0, tzinfo=timezone.utc)
BUCKET = "farm-seges-ai-records"


def new_backend() -> tuple:
    root = Path(tempfile.mkdtemp(prefix="ws2-core-"))
    return root, ingest_core.local_pipe_backend(root)


def tree_digest(root: Path, *subdirs: str) -> dict:
    """rel -> sha256 for every file under the named pipelines subdirs."""
    digests = {}
    for subdir in subdirs:
        base = root / "pipelines" / subdir
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file():
                rel = path.relative_to(root).as_posix()
                digests[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


def day(offset: int) -> datetime:
    return NOW + timedelta(days=offset)


def failed_run() -> dict:
    return {
        "ok": False,
        "error": "boom: feed unreachable",
        "row_count": 0,
        "started": "2026-11-18T02:00:00+00:00",
        "finished": "2026-11-18T02:00:01+00:00",
        "file": "",
    }


class MockGcsTransport:
    """In-memory GCS JSON API surface: write/read/list/object-get."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def __call__(self, method, url, headers, body):
        parsed = urllib.parse.urlsplit(url)
        query = urllib.parse.parse_qs(parsed.query)
        base = f"/storage/v1/b/{BUCKET}/o"
        if method == "POST" and parsed.path == f"/upload/storage/v1/b/{BUCKET}/o":
            name = query["name"][0]
            self.objects[name] = body
            return 200, {}, json.dumps({"name": name}).encode("utf-8")
        if method == "GET" and parsed.path == base:
            prefix = query["prefix"][0]
            names = sorted(n for n in self.objects if n.startswith(prefix))
            items = [
                {"name": n, "bucket": BUCKET, "updated": "2026-11-18T00:00:00Z"}
                for n in names
            ]
            return 200, {}, json.dumps({"items": items}).encode("utf-8")
        if method == "GET" and parsed.path.startswith(base + "/"):
            name = urllib.parse.unquote(parsed.path[len(base) + 1:])
            if name not in self.objects:
                return 404, {}, json.dumps({"error": {"code": 404, "message": "no"}}).encode("utf-8")
            if query.get("alt", [None])[0] == "media":
                return 200, {}, self.objects[name]
            return 200, {}, json.dumps({"name": name, "updated": "2026-11-18T00:00:00.500Z"}).encode("utf-8")
        return 400, {}, json.dumps({"error": {"code": 400, "message": "bad"}}).encode("utf-8")


def fake_token() -> tuple:
    return "token-for-tests", 3600


class BackendLayoutTests(unittest.TestCase):
    def test_run_log_lands_in_the_pipelines_run_log_dir(self):
        root, backend = new_backend()
        rel = ingest_core.append_run(
            backend, job="weather-hourly", now=NOW,
            started=NOW, finished=NOW, ok=True, row_count=1,
        )
        self.assertEqual(rel, "run-log/20261118-weather-hourly.json")
        self.assertTrue((root / "pipelines" / "run-log" / rel.split("/", 1)[1]).is_file())

    def test_env_backend_places_the_same_rel_under_the_pipelines_subtree(self):
        import os
        root = Path(tempfile.mkdtemp(prefix="ws2-env-"))
        with unittest.mock.patch.dict(
            os.environ,
            {"FARM_RECORD_BACKEND": "local", "FARM_PIPE_ROOT": str(root)},
            clear=False,
        ):
            backend = ingest_core.open_pipe_backend()
        ingest_core.append_run(
            backend, job="hazard-daily", now=NOW,
            started=NOW, finished=NOW, ok=True, row_count=0,
        )
        self.assertTrue(
            (root / "pipelines" / "run-log" / f"20261118-hazard-daily.json").is_file()
        )


class RunRowTests(unittest.TestCase):
    def test_fixed_schema_is_present_and_error_is_capped(self):
        _root, backend = new_backend()
        ingest_core.append_run(
            backend, job="planet-nightly", now=NOW,
            started=NOW, finished=NOW, ok=False, row_count=0,
            error="x" * 900, extra_detail="hi",
        )
        rows = ingest_core.run_rows(backend, "planet-nightly")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        for key in ("job", "started", "finished", "ok", "row_count", "error"):
            self.assertIn(key, row)
        self.assertEqual(len(row["error"]), 400)
        self.assertEqual(row["extra_detail"], "hi")
        self.assertFalse(row["ok"])

    def test_same_day_same_job_appends_are_one_dated_row(self):
        _root, backend = new_backend()
        ingest_core.append_run(
            backend, job="ndvi-weekly", now=NOW, started=NOW, finished=NOW,
            ok=True, row_count=1,
        )
        ingest_core.append_run(
            backend, job="ndvi-weekly", now=NOW, started=NOW, finished=NOW,
            ok=True, row_count=0,
        )
        rows = ingest_core.run_rows(backend, "ndvi-weekly")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["row_count"], 0)

    def test_env_gcs_backend_rel_matches_local_object_names(self):
        transport = MockGcsTransport()
        backend = GcsBackend(BUCKET, "pipelines", request_fn=transport, token_fn=fake_token)
        rel = ingest_core.append_run(
            backend, job="weather-hourly", now=NOW, started=NOW, finished=NOW,
            ok=True, row_count=3,
        )
        self.assertIn("pipelines/run-log/20261118-weather-hourly.json", transport.objects)
        rows = ingest_core.run_rows(backend, "weather-hourly")
        self.assertEqual(rows[0]["row_count"], 3)
        self.assertEqual(rel, "run-log/20261118-weather-hourly.json")


class StrikeTests(unittest.TestCase):
    def test_no_alert_before_three_consecutive_failed_days(self):
        _root, backend = new_backend()
        results = []
        for offset in range(2):
            ingest_core.append_run(
                backend, job="weather-hourly", now=day(offset),
                started=day(offset), finished=day(offset), ok=False,
                row_count=0, error="feed down",
            )
            results.append(ingest_core.on_run_finished(
                backend, job="weather-hourly", now=day(offset), run=failed_run()
            ))
        self.assertTrue(all(r["alert"] is None for r in results))

    def test_third_consecutive_failure_writes_the_alert_artifact(self):
        root, backend = new_backend()
        alert_rel = None
        for offset in range(3):
            ingest_core.append_run(
                backend, job="weather-hourly", now=day(offset),
                started=day(offset), finished=day(offset), ok=False,
                row_count=0, error=f"strike {offset}",
            )
            alert_rel = ingest_core.on_run_finished(
                backend, job="weather-hourly", now=day(offset), run=failed_run()
            )["alert"]
        self.assertIsNotNone(alert_rel)
        self.assertEqual(alert_rel, "alerts/20261120-weather-hourly-ALERT.json")
        alert = ingest_core.read_json(backend, alert_rel)
        self.assertEqual(alert["consecutive_failures"], 3)
        self.assertEqual(len(alert["evidence"]), 3)
        self.assertTrue(all(item["ok"] is False for item in alert["evidence"]))
        self.assertIn("artifact-only", alert["notification_policy"])
        # evidence trail names the actual run rows
        for item in alert["evidence"]:
            self.assertRegex(item["file"], r"\d{8}-weather-hourly\.json")
        self.assertTrue((root / "pipelines" / "alerts" / alert_rel.split("/", 1)[1]).is_file())

    def test_a_success_resets_the_strike_counter(self):
        _root, backend = new_backend()
        for offset, ok in ((0, False), (1, False), (2, True), (3, False)):
            ingest_core.append_run(
                backend, job="hazard-daily", now=day(offset),
                started=day(offset), finished=day(offset), ok=ok,
                row_count=0, error=None if ok else "down",
            )
            outcome = ingest_core.on_run_finished(
                backend, job="hazard-daily", now=day(offset),
                run=failed_run() if not ok else {**failed_run(), "ok": True, "error": None},
            )
        self.assertIsNone(outcome["alert"])
        self.assertEqual(outcome["consecutive_failures"], 1)

    def test_fourth_failure_day_refreshes_the_alert_for_that_day(self):
        _root, backend = new_backend()
        first_alert = None
        for offset in range(3):
            ingest_core.append_run(
                backend, job="ndvi-weekly", now=day(offset),
                started=day(offset), finished=day(offset), ok=False,
                row_count=0, error="still down",
            )
            first_alert = ingest_core.on_run_finished(
                backend, job="ndvi-weekly", now=day(offset), run=failed_run()
            )["alert"]
        ingest_core.append_run(
            backend, job="ndvi-weekly", now=day(3),
            started=day(3), finished=day(3), ok=False, row_count=0, error="down",
        )
        second = ingest_core.on_run_finished(
            backend, job="ndvi-weekly", now=day(3), run=failed_run()
        )
        self.assertEqual(second["consecutive_failures"], 4)
        self.assertNotEqual(first_alert, second["alert"])
        self.assertEqual(second["alert"], "alerts/20261121-ndvi-weekly-ALERT.json")


class DataRowTests(unittest.TestCase):
    def test_rows_carry_job_and_record_honesty_keys(self):
        _root, backend = new_backend()
        rel = ingest_core.write_data_row(
            backend, "weather", "wx-x.json", {"value_mm": 1.0},
            job="weather-hourly", now=NOW,
        )
        row = ingest_core.read_json(backend, rel)
        self.assertEqual(row["job"], "weather-hourly")
        self.assertFalse(row["permits_financial_use"])
        self.assertEqual(row["use_class"], "Screening")
        self.assertEqual(row["record_owner"], "seges-ai")

    def test_equal_value_detection_compares_the_declared_keys_only(self):
        existing = [{"kind": "weather-hourly", "phenomenon_hour": "h1", "issued": "i1", "value_mm": 0.5}]
        incoming = {"kind": "weather-hourly", "phenomenon_hour": "h1", "issued": "i1", "value_mm": 0.5, "captured_at": "later"}
        self.assertTrue(ingest_core.already_equal_value_row(
            existing, incoming, ("kind", "phenomenon_hour", "issued", "value_mm")
        ))
        changed = dict(incoming, value_mm=0.7)
        self.assertFalse(ingest_core.already_equal_value_row(
            existing, changed, ("kind", "phenomenon_hour", "issued", "value_mm")
        ))


if __name__ == "__main__":
    unittest.main()
