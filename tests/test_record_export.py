"""Offline tests for the nightly record export (pipelines/record_export.py)."""

import hashlib
import io
import json
import sys
import tarfile
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.ingest_core import (
    LocalBackend,
    run_rows,
    standing_alerts,
)
from pipelines import fault_drill, record_export

NOW = datetime(2026, 11, 18, 18, 30, 0, tzinfo=timezone.utc)
MEMBERS = {
    "biratori-pin.json": {"label": "pin"},
    "obs-20261116T130426Z.json": {"crop": "soybean", "value": 1},
    "obs-20261116T130945Z.json": {"crop": "soybean", "value": 2},
    "notes/note-feedback-20261116T131001Z.json": {"kind": "feedback"},
    "boundaries/parcel/walk.json": {"kind": "boundary"},
    "leads/20261118/lead.json": {"kind": "lead"},
}


class ExportCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.record = LocalBackend(root / "field-notes")
        for name, document in MEMBERS.items():
            self.record.write(name, (json.dumps(document) + "\n").encode("utf-8"))
        self.archive = LocalBackend(root / "field-archive")
        self.pipe = LocalBackend(root / "pipelines")
        # Route ingest_core's env-driven backend into the tmp tree for
        # every test in this case (run rows must never reach $HOME).
        self._env_patch = patch.dict(
            "os.environ",
            {"FARM_RECORD_BACKEND": "local", "FARM_PIPE_ROOT": str(root)},
        )
        self._env_patch.start()

    def tearDown(self):
        self._env_patch.stop()
        self.tmp.cleanup()

    def _successful_run(self, *, now=NOW):
        return record_export.run_export(self.record, self.archive, now=now)


class ArchiveConfigurationTests(unittest.TestCase):
    def test_gcs_archive_requires_a_different_bucket(self):
        with patch.dict("os.environ", {"FARM_RECORD_BACKEND": "gcs", "FARM_RECORD_BUCKET": "source"}, clear=True):
            with self.assertRaisesRegex(ValueError, "separate archive bucket"):
                record_export.archive_backend()
            with patch.dict("os.environ", {"FARM_ARCHIVE_BUCKET": "source"}):
                with self.assertRaisesRegex(ValueError, "separate archive bucket"):
                    record_export.archive_backend()
            with patch.dict("os.environ", {"FARM_ARCHIVE_BUCKET": "archive"}):
                self.assertEqual(record_export.archive_backend().bucket, "archive")


class CompositionTests(ExportCase):
    def test_archive_is_a_valid_deterministic_tar_of_every_record_object(self):
        first = self._successful_run()
        second = self._successful_run()
        self.assertTrue(first["ok"] and second["ok"])
        expected_name = f"20261118/record-snapshot-20261118T183000Z-{first['sha256']}.tar.gz"
        self.assertEqual(first["archive_object"], expected_name)
        self.assertEqual(first["members"], len(MEMBERS))
        self.assertGreater(first["bytes"], 0)
        # Determinism: identical inputs and clock -> byte-identical archive.
        self.assertEqual(first["sha256"], second["sha256"])

        payload = self.archive.read_bytes(expected_name)
        self.assertEqual(hashlib.sha256(payload).hexdigest(), first["sha256"])
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tar:
            self.assertEqual(sorted(tar.getnames()), sorted(MEMBERS))
            member = tar.extractfile("obs-20261116T130426Z.json")
            self.assertEqual(json.loads(member.read()), MEMBERS["obs-20261116T130426Z.json"])

    def test_manifest_day_file_receives_one_deduplicated_row_per_snapshot(self):
        self._successful_run()
        self._successful_run()  # idempotent rerun: same clock, same snapshot
        rows = record_export._read_manifest_lines(self.archive, "20261118")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["archive_object"], f"20261118/record-snapshot-20261118T183000Z-{row['sha256']}.tar.gz")
        self.assertEqual(row["members"], len(MEMBERS))
        self.assertIn("sha256", row)
        self.assertIn("record-retention-policy.md", row["manifest_note"])

    def test_changed_contents_same_second_preserve_both_snapshots_and_manifests(self):
        first = self._successful_run()
        self.record.write("new.json", b'{"new": true}')
        second = self._successful_run()
        self.assertNotEqual(first["archive_object"], second["archive_object"])
        self.assertTrue(self.archive.exists(first["archive_object"]))
        self.assertTrue(self.archive.exists(second["archive_object"]))
        self.assertEqual(len(record_export._read_manifest_lines(self.archive, "20261118")), 2)

    def test_simultaneous_identical_exports_share_one_snapshot_and_manifest(self):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(lambda _: self._successful_run(), range(5)))
        self.assertEqual(len({item["archive_object"] for item in results}), 1)
        self.assertEqual(len(record_export._read_manifest_lines(self.archive, "20261118")), 1)
        self.assertEqual(len(run_rows(self.pipe, job="record-export")), 5)

    def test_conflicting_immutable_manifest_is_refused(self):
        first = self._successful_run()
        self.archive.write(first["manifest"], b"not the expected manifest")
        with self.assertRaisesRegex(RuntimeError, "immutable object conflict"):
            self._successful_run()

    def test_legacy_manifest_rows_are_still_readable(self):
        self.archive.write("manifest/20261118.ndjson", b'{"archive_object":"old"}\n')
        self._successful_run()
        self.assertEqual(len(record_export._read_manifest_lines(self.archive, "20261118")), 2)

    def test_second_run_at_a_different_time_appends_a_row(self):
        self._successful_run()
        self._successful_run(now=NOW.replace(hour=20))
        rows = record_export._read_manifest_lines(self.archive, "20261118")
        self.assertEqual(len(rows), 2)
        self.assertEqual(len({row["archive_object"] for row in rows}), 2)

    def test_run_log_row_is_written_through_ingest_core(self):
        self._successful_run()
        rows = run_rows(self.pipe, job="record-export")
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["ok"])
        self.assertEqual(rows[0]["row_count"], len(MEMBERS))
        self.assertEqual(
            rows[0]["archive_object"], f"20261118/record-snapshot-20261118T183000Z-{rows[0]['sha256']}.tar.gz"
        )

    def test_byte_integrity_is_verified_by_readback(self):
        class MutatingArchive(LocalBackend):
            def write_once(self, rel, data):
                super().write_once(rel, data[:-1])

        archive = MutatingArchive(Path(self.tmp.name) / "field-archive-mutant")
        with self.assertRaisesRegex(RuntimeError, "does not match the composed bytes"):
            record_export.run_export(self.record, archive, now=NOW)

    def test_empty_record_refused(self):
        empty = LocalBackend(Path(self.tmp.name) / "empty-record")
        with self.assertRaisesRegex(ValueError, "refusing to snapshot emptiness"):
            record_export.run_export(empty, self.archive, now=NOW)


class StrikeTests(ExportCase):
    """Distinct failed executions trigger strikes, including on separate days."""

    def test_three_failed_days_fire_one_alert(self):
        for offset in range(3):
            record_export._record_failure(
                self.pipe,
                started=NOW + timedelta(days=offset),
                moment=NOW + timedelta(days=offset, minutes=1),
                error=ValueError("boom"),
            )
        rows = run_rows(self.pipe, job="record-export")
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(not row["ok"] for row in rows))
        alerts = standing_alerts(self.pipe, job="record-export")
        self.assertEqual(len(alerts), 1)

    def test_a_success_resets_the_streak(self):
        for offset in range(2):
            record_export._record_failure(
                self.pipe,
                started=NOW + timedelta(days=offset),
                moment=NOW + timedelta(days=offset, minutes=1),
                error=ValueError("boom"),
            )
        self.assertEqual(standing_alerts(self.pipe, job="record-export"), [])
        self._successful_run(now=NOW + timedelta(days=2))
        result = record_export.on_run_finished(
            self.pipe,
            job="record-export",
            now=NOW + timedelta(days=2, minutes=5),
            run={"job": "record-export", "ok": True, "row_count": 1, "error": None},
        )
        self.assertEqual(result["consecutive_failures"], 0)

    def test_run_export_logs_its_own_success_but_failures_go_through_record_failure(self):
        self._successful_run()
        rows = run_rows(self.pipe, job="record-export")
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["ok"])


class MainEntryTests(ExportCase):
    def setUp(self):
        super().setUp()
        self._env_dir_patch = patch.dict(
            "os.environ",
            {"FARM_RECORD_DIR": str(Path(self.tmp.name) / "field-notes")},
        )
        self._env_dir_patch.start()

    def tearDown(self):
        self._env_dir_patch.stop()
        super().tearDown()

    def test_main_reports_a_successful_round_trip(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = record_export.main(["--now", NOW.isoformat()])
        summary = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(summary["ok"])
        self.assertEqual(summary["members"], len(MEMBERS))
        self.assertTrue(summary["archive_object"].endswith(".tar.gz"))

    def test_main_returns_nonzero_when_the_record_is_empty(self):
        for name in MEMBERS:
            (Path(self.tmp.name) / "field-notes" / name).unlink()
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = record_export.main(["--now", NOW.isoformat()])
        self.assertEqual(exit_code, 1)
        body = json.loads(buffer.getvalue())
        self.assertFalse(body["ok"])
        rows = run_rows(self.pipe, job="record-export")
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["ok"])


class FaultDrillTests(unittest.TestCase):
    def test_fault_marker_is_stable_and_raises(self):
        self.assertIn("task-10", fault_drill.FAULT_MARKER)
        self.assertIn("controlled fault drill", fault_drill.FAULT_MARKER)
        with self.assertRaisesRegex(RuntimeError, "controlled fault drill"):
            fault_drill.explode()


if __name__ == "__main__":
    unittest.main()
