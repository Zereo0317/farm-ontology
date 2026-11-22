import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from farm_ontology import ingest_core
from farm_ontology.ingest_watchdog import evaluate
from farm_ontology.record_store import LocalBackend
from pipelines import ingest_watchdog

NOW = datetime(2026, 11, 22, 12, tzinfo=timezone.utc)

class WatchdogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.backend = LocalBackend(Path(self.tmp.name))
        self.limits = {"weather-hourly": timedelta(hours=2)}
    def add(self, when, ok=True):
        ingest_core.append_run(self.backend, job="weather-hourly", now=when, started=when, finished=when, ok=ok, row_count=0)
    def report(self):
        return evaluate(self.backend, now=NOW, max_age=self.limits)["jobs"]["weather-hourly"]
    def test_missing_and_stale_last_success_are_gaps(self):
        self.assertIn("missing-run", self.report()["reasons"])
        self.add(NOW - timedelta(hours=3))
        self.add(NOW - timedelta(minutes=1), ok=False)
        self.assertIn("stale-success", self.report()["reasons"])
    def test_three_failures_do_not_hide_fresh_success(self):
        self.add(NOW - timedelta(hours=1))
        for minutes in (30, 20, 10): self.add(NOW - timedelta(minutes=minutes), False)
        result = self.report()
        self.assertEqual(result["consecutive_failures"], 3)
        self.assertEqual(result["reasons"], ["consecutive-failures"])
        self.add(NOW)
        self.assertTrue(self.report()["healthy"])
    def test_future_and_malformed_evidence_refused(self):
        self.add(NOW - timedelta(minutes=1))
        self.add(NOW + timedelta(minutes=1))
        ingest_core.write_json(self.backend, "run-log/20261122-weather-hourly.json", {"job": "weather-hourly", "ok": True, "finished": "bad"})
        self.assertIn("invalid-run-evidence", self.report()["reasons"])
    def test_empty_config_and_naive_clock_refused(self):
        with self.assertRaises(ValueError): evaluate(self.backend, now=NOW, max_age={})
        with self.assertRaises(ValueError): evaluate(self.backend, now=NOW.replace(tzinfo=None))

class DeliveryTests(unittest.TestCase):
    def test_missing_or_unsafe_receiver_fails_before_evaluation(self):
        for receiver in ("", "http://example.org", "https://user:pass@example.org"):
            with self.subTest(receiver=receiver), patch.dict("os.environ", {"FARM_WATCHDOG_RECEIVER": receiver}), redirect_stdout(io.StringIO()):
                self.assertEqual(ingest_watchdog.main(["--deliver"]), 2)
    def test_deliver_only_calls_explicit_receiver_and_reports_failure(self):
        with patch.dict("os.environ", {"FARM_WATCHDOG_RECEIVER": "https://alerts.example.org/hook"}), patch.object(ingest_watchdog, "open_pipe_backend", return_value=object()), patch.object(ingest_watchdog, "evaluate", return_value={"healthy": False}), patch.object(ingest_watchdog, "send_report", side_effect=OSError("private detail")) as send, redirect_stdout(io.StringIO()), patch("sys.stderr", new_callable=io.StringIO) as stderr:
            self.assertEqual(ingest_watchdog.main(["--deliver"]), 2)
            send.assert_called_once()
            self.assertNotIn("private detail", stderr.getvalue())
    def test_http_transport_requires_2xx(self):
        class Response:
            def __init__(self, status): self.status = status
            def __enter__(self): return self
            def __exit__(self, *_): return False
        calls = []
        def transport(request, timeout):
            calls.append((request, timeout))
            return Response(202)
        ingest_watchdog.send_report({"healthy": False}, "https://alerts.example.org/hook", opener=transport)
        self.assertEqual(calls[0][0].method, "POST")
        self.assertEqual(json.loads(calls[0][0].data), {"healthy": False})
        with self.assertRaises(RuntimeError):
            ingest_watchdog.send_report({}, "https://alerts.example.org/hook", opener=lambda *_args, **_kwargs: Response(500))

    def test_no_delivery_without_explicit_flag(self):
        with patch.object(ingest_watchdog, "open_pipe_backend", return_value=object()), patch.object(ingest_watchdog, "evaluate", return_value={"healthy": False}), patch.object(ingest_watchdog, "send_report") as send, redirect_stdout(io.StringIO()):
            self.assertEqual(ingest_watchdog.main([]), 1)
            send.assert_not_called()
