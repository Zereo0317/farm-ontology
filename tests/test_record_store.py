"""Offline tests for the record storage shim.

No network: HTTP is mocked with recorded fixture payloads from the GCS
JSON API (tests/fixtures/record_store/) and an in-memory stand-in. The
token comes from an injected function, never from the metadata server.
"""

import io
import json
import os
import re
import sys
import tempfile
import unittest
import urllib.parse
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.record import add_note, list_notes, record_observation, status
from farm_ontology.record_store import (
    DEFAULT_BUCKET,
    DEFAULT_PREFIX,
    UPLOAD_API,
    GcsBackend,
    LocalBackend,
    open_backend,
)

AT = datetime(2026, 11, 17, 1, 0, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "record_store"
BUCKET = "farm-seges-ai-records"


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def iso_to_ns(text: str) -> int:
    moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return round(moment.timestamp() * 1_000_000_000)


def recorded_token(state: list) -> tuple[str, int]:
    document = json.loads(fixture("metadata_token.json"))
    state.append(1)
    return document["access_token"], int(document["expires_in"])


class Scripted:
    """Fake transport: pops one recorded (status, headers, body) per call."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, method, url, headers, body):
        self.calls.append(
            {"method": method, "url": url, "headers": dict(headers), "body": body}
        )
        return self.responses.pop(0)


class MemoryGcs:
    """In-memory stand-in for the GCS JSON API surface the shim uses."""

    def __init__(self, bucket: str = BUCKET):
        self.bucket = bucket
        self.objects: dict[str, bytes] = {}
        self.updated: dict[str, str] = {}
        self.clock = 1763341200.0  # 2026-11-17T01:00:00Z

    def _stamp(self) -> str:
        self.clock += 0.5
        moment = datetime.fromtimestamp(self.clock, timezone.utc)
        return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"

    def put(self, name: str, data: bytes) -> None:
        self.objects[name] = data
        self.updated[name] = self._stamp()

    def __call__(self, method, url, headers, body):
        self.last_authorization = headers["Authorization"]
        parsed = urllib.parse.urlsplit(url)
        query = urllib.parse.parse_qs(parsed.query)
        if method == "GET" and parsed.path == f"/storage/v1/b/{self.bucket}/o":
            prefix = query["prefix"][0]
            limit = int(query.get("maxResults", ["1000"])[0])
            offset = int(query.get("pageToken", ["0"])[0])
            names = sorted(n for n in self.objects if n.startswith(prefix))
            window = names[offset : offset + limit]
            document = {"kind": "storage#objects", "totalSize": len(names)}
            if window:
                document["items"] = [
                    {"name": n, "bucket": self.bucket, "updated": self.updated[n]}
                    for n in window
                ]
            following = offset + len(window)
            if following < len(names):
                document["nextPageToken"] = str(following)
            return 200, {}, json.dumps(document).encode("utf-8")
        if method == "POST" and parsed.path == f"/upload/storage/v1/b/{self.bucket}/o":
            name = query["name"][0]
            if query.get("ifGenerationMatch") == ["0"] and name in self.objects:
                return 412, {}, b"precondition failed"
            self.put(name, body)
            meta = {"name": name, "bucket": self.bucket, "updated": self.updated[name]}
            return 200, {}, json.dumps(meta).encode("utf-8")
        match = re.fullmatch(rf"/storage/v1/b/{self.bucket}/o/(.+)", parsed.path)
        if match and method == "GET":
            name = urllib.parse.unquote(match.group(1))
            if name not in self.objects:
                missing = {"error": {"code": 404, "message": f"No such object: {name}"}}
                return 404, {}, json.dumps(missing).encode("utf-8")
            if query.get("alt", [None])[0] == "media":
                return 200, {}, self.objects[name]
            meta = {"name": name, "bucket": self.bucket, "updated": self.updated[name]}
            return 200, {}, json.dumps(meta).encode("utf-8")
        raise AssertionError(f"memory GCS unrouted: {method} {url}")


class EnvironmentCase(unittest.TestCase):
    def setUp(self):
        self.saved = {
            key: os.environ.pop(key, None)
            for key in ("FARM_RECORD_BACKEND", "FARM_RECORD_BUCKET", "FARM_RECORD_GCS_PREFIX")
        }

    def tearDown(self):
        for key, value in self.saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class FactoryTests(EnvironmentCase):
    def test_default_backend_is_local(self):
        backend = open_backend(Path("somewhere"))
        self.assertIsInstance(backend, LocalBackend)
        self.assertEqual(backend.describe(), {"backend": "local", "root": "somewhere"})

    def test_gcs_requires_a_bucket(self):
        os.environ["FARM_RECORD_BACKEND"] = "gcs"
        with self.assertRaisesRegex(ValueError, "FARM_RECORD_BUCKET"):
            open_backend(Path("."))

    def test_unknown_backend_is_refused(self):
        os.environ["FARM_RECORD_BACKEND"] = "nfs"
        with self.assertRaisesRegex(ValueError, "FARM_RECORD_BACKEND"):
            open_backend(Path("."))

    def test_gcs_backend_carries_bucket_and_prefix(self):
        os.environ["FARM_RECORD_BACKEND"] = "gcs"
        os.environ["FARM_RECORD_BUCKET"] = "my-records"
        backend = open_backend(Path("."))
        self.assertEqual(backend.describe(), {"backend": "gcs", "bucket": "my-records", "prefix": DEFAULT_PREFIX, "api": "storage.googleapis.com"})
        self.assertEqual(DEFAULT_BUCKET, "farm-seges-ai-records")

    def test_gcs_prefix_override_is_normalised(self):
        os.environ["FARM_RECORD_BACKEND"] = "gcs"
        os.environ["FARM_RECORD_BUCKET"] = BUCKET
        os.environ["FARM_RECORD_GCS_PREFIX"] = "/records/extra//"
        backend = open_backend(Path("."))
        self.assertEqual(backend.prefix, "records/extra")


class LocalBackendTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.backend = LocalBackend(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_write_creates_parents_and_reads_back_identical_bytes(self):
        payload = json.dumps({"value": "per mille ‰"}).encode("utf-8")
        self.backend.write("notes/note-x.json", payload)
        self.assertEqual(self.backend.read_text("notes/note-x.json"), payload.decode("utf-8"))

    def test_write_once_never_replaces_existing_data(self):
        self.backend.write_once("obs-a.json", b"first")
        with self.assertRaises(FileExistsError):
            self.backend.write_once("obs-a.json", b"second")
        self.assertEqual(self.backend.read_bytes("obs-a.json"), b"first")

    def test_simultaneous_creates_do_not_overwrite(self):
        from concurrent.futures import ThreadPoolExecutor
        def create(value):
            try:
                self.backend.write_once("same.json", value)
                return True
            except FileExistsError:
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(create, [str(i).encode() for i in range(8)]))
        self.assertEqual(sum(results), 1)
        self.assertIn(self.backend.read_bytes("same.json"), [str(i).encode() for i in range(8)])

    def test_concurrent_mutable_writes_use_independent_staging_files(self):
        from concurrent.futures import ThreadPoolExecutor
        payloads = [str(i).encode() * 10000 for i in range(20)]
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda data: self.backend.write("mutable.json", data), payloads))
        self.assertIn(self.backend.read_bytes("mutable.json"), payloads)
        self.assertFalse(list(Path(self.tmp.name).glob(".record-*")))

    def test_exists_and_mtime_match_the_file(self):
        self.backend.write("obs-a.json", b"{}")
        path = Path(self.tmp.name) / "obs-a.json"
        self.assertTrue(self.backend.exists("obs-a.json"))
        self.assertFalse(self.backend.exists("notes"))
        self.assertEqual(self.backend.mtime_ns("obs-a.json"), path.stat().st_mtime_ns)
        self.assertIsNone(self.backend.mtime_ns("obs-absent.json"))

    def test_lists_filter_on_the_file_name_only(self):
        self.backend.write("obs-a.json", b"{}")
        self.backend.write("notes/note-b.json", b"{}")
        self.assertEqual(self.backend.list_paths("", "obs-*.json"), ["obs-a.json"])
        self.assertEqual(self.backend.list_paths("notes/", "note-*.json"), ["notes/note-b.json"])

    def test_missing_read_raises_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.backend.read_text("obs-none.json")


class GcsRequestShapeTests(unittest.TestCase):
    """Assert the exact JSON API requests, against recorded payloads."""

    def setUp(self):
        self.tokens: list = []
        self.token = lambda: recorded_token(self.tokens)  # noqa: E731

    def test_upload_request_shape_and_authorization(self):
        scripted = Scripted((200, {}, fixture("upload_object.json")))
        backend = GcsBackend(BUCKET, request_fn=scripted, token_fn=self.token)
        payload = json.dumps({"latitude": 1.0}).encode("utf-8")
        backend.write("obs-20261117T010000Z.json", payload)
        call = scripted.calls[0]
        self.assertEqual(call["method"], "POST")
        self.assertTrue(call["url"].startswith(UPLOAD_API))
        self.assertIn(f"/b/{BUCKET}/o?uploadType=media&name=", call["url"])
        self.assertIn("name=field-notes%2Fobs-20261117T010000Z.json", call["url"])
        self.assertEqual(call["headers"]["Content-Type"], "application/json")
        self.assertEqual(
            call["headers"]["Authorization"], "Bearer ya29.RECORDED-FIXTURE-TOKEN"
        )
        self.assertEqual(call["body"], payload)
        self.assertEqual(len(self.tokens), 1)

    def test_create_uses_generation_precondition_and_reports_conflict(self):
        scripted = Scripted((412, {}, b"conflict"))
        backend = GcsBackend(BUCKET, request_fn=scripted, token_fn=self.token)
        with self.assertRaises(FileExistsError):
            backend.write_once("obs-x.json", b"{}")
        self.assertIn("ifGenerationMatch=0", scripted.calls[0]["url"])

    def test_list_pagination_walks_recorded_pages(self):
        scripted = Scripted(
            (200, {}, fixture("list_page1.json")),
            (200, {}, fixture("list_page2.json")),
        )
        backend = GcsBackend(BUCKET, request_fn=scripted, token_fn=self.token)
        found = backend.list_paths("", "note-*.json")
        self.assertEqual(
            found,
            [
                "notes/note-feedback-20261117T010002Z.json",
                "notes/note-verification-20261117T010001Z.json",
            ],
        )
        first, second = scripted.calls
        self.assertNotIn("pageToken", first["url"])
        self.assertIn("pageToken=RECORDED-PAGE-2", second["url"])
        self.assertIn("prefix=field-notes%2F", second["url"])

    def test_read_streams_the_object_body(self):
        scripted = Scripted((200, {}, b'{"latitude": 1.0}'))
        backend = GcsBackend(BUCKET, request_fn=scripted, token_fn=self.token)
        self.assertEqual(backend.read_text("obs-x.json"), '{"latitude": 1.0}')
        self.assertTrue(scripted.calls[0]["url"].endswith("?alt=media"))

    def test_read_missing_object_raises_file_not_found(self):
        missing = json.dumps({"error": {"code": 404, "message": "No such object"}}).encode()
        scripted = Scripted((404, {}, missing))
        backend = GcsBackend(BUCKET, request_fn=scripted, token_fn=self.token)
        with self.assertRaises(FileNotFoundError):
            backend.read_text("obs-none.json")

    def test_exists_separates_found_from_missing(self):
        missing = json.dumps({"error": {"code": 404, "message": "No such object"}}).encode()
        scripted = Scripted((200, {}, fixture("upload_object.json")), (404, {}, missing))
        backend = GcsBackend(BUCKET, request_fn=scripted, token_fn=self.token)
        self.assertTrue(backend.exists("obs-20261117T010000Z.json"))
        self.assertFalse(backend.exists("obs-gone.json"))

    def test_api_error_is_sanitised_and_hides_the_token(self):
        scripted = Scripted((429, {}, fixture("error_quota.json")))
        backend = GcsBackend(BUCKET, request_fn=scripted, token_fn=self.token)
        with self.assertRaises(RuntimeError) as caught:
            backend.write("obs-x.json", b"{}")
        message = str(caught.exception)
        self.assertIn("RATE LIMIT EXCEEDED", message)
        self.assertNotIn("ya29.RECORDED-FIXTURE-TOKEN", message)

    def test_unreadable_metadata_is_refused(self):
        scripted = Scripted((200, {}, b"<html>Gateway busy</html>"))
        backend = GcsBackend(BUCKET, request_fn=scripted, token_fn=self.token)
        with self.assertRaisesRegex(RuntimeError, "unreadable object metadata"):
            backend.mtime_ns("obs-x.json")

    def test_mtime_comes_from_the_recorded_timestamp(self):
        scripted = Scripted((200, {}, fixture("upload_object.json")))
        backend = GcsBackend(BUCKET, request_fn=scripted, token_fn=self.token)
        self.assertEqual(
            backend.mtime_ns("obs-20261117T010000Z.json"),
            iso_to_ns("2026-11-17T01:00:00.500Z"),
        )

    def test_token_is_cached_until_it_expires(self):
        calls = {"n": 0}

        def short_token():
            calls["n"] += 1
            return "ya29.SHORT", 0

        scripted = Scripted(
            (200, {}, b'{"updated": "2026-11-17T01:00:00.000Z"}'),
            (200, {}, b'{"updated": "2026-11-17T01:00:00.000Z"}'),
            (200, {}, b'{"updated": "2026-11-17T01:00:00.000Z"}'),
        )
        backend = GcsBackend(BUCKET, request_fn=scripted, token_fn=short_token)
        clocks = iter([0.0, 0.0, 5000.0])
        with patch("farm_ontology.record_store.time.monotonic", side_effect=lambda: next(clocks)):
            backend.mtime_ns("a.json")
            backend.mtime_ns("a.json")
            self.assertEqual(calls["n"], 1)
            backend.mtime_ns("a.json")
            self.assertEqual(calls["n"], 2)


class GcsThroughRecordModuleTests(unittest.TestCase):
    """The seam in record.py must behave identically on the GCS backend."""

    def setUp(self):
        self.memory = MemoryGcs()
        self.backend = GcsBackend(BUCKET, request_fn=self.memory, token_fn=lambda: ("ya29.MEMORY", 3600))
        self.patcher = patch("farm_ontology.record._store", return_value=self.backend)
        self.patcher.start()
        self.old_dir = os.environ.pop("FARM_RECORD_DIR", None)
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["FARM_RECORD_DIR"] = self.tmp.name

    def tearDown(self):
        self.patcher.stop()
        if self.old_dir is None:
            os.environ.pop("FARM_RECORD_DIR", None)
        else:
            os.environ["FARM_RECORD_DIR"] = self.old_dir
        self.tmp.cleanup()

    def test_observation_and_note_round_trip(self):
        saved = record_observation(latitude=1.0, longitude=2.0, note="row A", sample_id="row-a", at=AT)
        self.assertTrue(saved["file"].startswith("obs-"))
        object_name = f"{DEFAULT_PREFIX}/{saved['file']}"
        stored = json.loads(self.memory.objects[object_name].decode("utf-8"))
        self.assertEqual(stored["crop"], "soybean")
        self.assertFalse(stored["permits_financial_use"])
        noted = add_note(kind="verification", text="checked", observation_file=saved["file"], at=AT)
        self.assertTrue(noted["file"].startswith("note-verification-"))
        note_object = f"{DEFAULT_PREFIX}/notes/{noted['file']}"
        self.assertIn("checked", self.memory.objects[note_object].decode("utf-8"))
        listed = list_notes()
        self.assertEqual(len(listed["observations"]), 1)
        self.assertEqual(len(listed["notes"]), 1)
        self.assertEqual(listed["observations"][0]["sample_id"], "row-a")
        self.assertEqual(listed["notes"][0]["text"], "checked")
        self.assertEqual(status()["observation_count"], 1)
        self.assertTrue(self.memory.last_authorization.startswith("Bearer "))

    def test_same_second_observation_lands_under_a_distinct_name(self):
        first = record_observation(latitude=1.0, longitude=2.0, at=AT)
        second = record_observation(latitude=3.0, longitude=4.0, at=AT)
        self.assertNotEqual(first["file"], second["file"])
        self.assertTrue(second["file"].startswith("obs-20261117T010000Z-"))
        self.assertEqual(len(self.memory.objects), 2)


class DrillMainTests(EnvironmentCase):
    def test_drill_main_reports_an_offline_round_trip(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            from farm_ontology.record_store import main

            exit_code = main([])
        summary = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(summary["backend"]["backend"], "local")
        self.assertTrue(summary["written"].startswith("obs-"))
        self.assertGreaterEqual(summary["observation_count"], 1)
        self.assertFalse(summary["permits_financial_use"])


if __name__ == "__main__":
    unittest.main()
