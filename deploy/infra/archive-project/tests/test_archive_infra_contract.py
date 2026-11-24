"""Static and input-safety checks for the isolated farm archive stack."""

from __future__ import annotations

import importlib.util
import hashlib
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[4]
STACK = ROOT / "deploy" / "infra" / "archive-project"
SPEC = importlib.util.spec_from_file_location("restore_archive", STACK / "restore_archive.py")
restore_archive = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(restore_archive)


class ArchiveInfrastructureContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.main_tf = (STACK / "main.tf").read_text(encoding="utf-8")
        cls.variables_tf = (STACK / "variables.tf").read_text(encoding="utf-8")

    def test_all_persistent_resources_have_destroy_guards(self) -> None:
        for resource in (
            'google_storage_bucket" "terraform_state',
            'google_project" "archive',
            'google_project_service" "archive_services',
            'google_project_service" "archive_services',
            'google_storage_bucket" "archive',
            'google_storage_bucket" "restore_drill',
            'google_service_account_iam_member" "deployer_can_attach_exporter',
            'google_project_iam_member" "exporter_logs',
            'google_storage_bucket_iam_member" "exporter_reads_source',
            'google_storage_bucket_iam_member" "exporter_writes_only_pipeline_evidence',
            'google_storage_bucket_iam_member" "exporter_creates_archive',
            'google_storage_bucket_iam_member" "exporter_verifies_archive',
            'google_service_account" "exporter',
            'google_service_account" "scheduler',
            'google_cloud_run_v2_job_iam_member" "scheduler_can_run_export',
            'google_cloud_scheduler_job" "archive_export',
            'google_monitoring_notification_channel" "archive_budget',
            'google_billing_budget" "archive',
        ):
            with self.subTest(resource=resource):
                block = self.main_tf.split(resource, 1)[1]
                block = block.split("\nresource ", 1)[0]
                self.assertIn("prevent_destroy = true", block)

    def test_retention_is_unlocked_and_lifecycle_only_targets_snapshot_archives(self) -> None:
        self.assertIn("retention_period = var.retention_days * 86400", self.main_tf)
        self.assertIn("is_locked        = false", self.main_tf)
        self.assertIn('matches_prefix = ["field-archive/"]', self.main_tf)
        self.assertIn('matches_suffix = [".tar.gz"]', self.main_tf)
        self.assertIn("retention_days == 90", self.variables_tf)

    def test_scheduler_supports_one_hour_rpo_target(self) -> None:
        self.assertIn('schedule         = "*/30 * * * *"', self.main_tf)
        self.assertIn('time_zone        = "Asia/Tokyo"', self.main_tf)
        self.assertIn('role     = "roles/run.invoker"', self.main_tf)
        self.assertIn('name     = "farm-nightly-export"', self.main_tf)

    def test_cost_alert_is_project_scoped_and_requires_owner_inputs(self) -> None:
        self.assertIn('projects = ["projects/${google_project.archive.number}"]', self.main_tf)
        self.assertIn('currency_code = "TWD"', self.main_tf)
        self.assertIn("archive_monthly_budget_twd", self.variables_tf)
        self.assertIn("budget_alert_email", self.variables_tf)
        self.assertIn("floor(var.archive_monthly_budget_twd)", self.variables_tf)

    def test_no_sibling_resource_ids_are_configured(self) -> None:
        self.assertIn('default     = "seges-ai"', self.variables_tf)
        self.assertIn('default     = "farm-seges-ai-records"', self.variables_tf)
        self.assertIn('startswith(var.archive_project_id, "farm-seges-ai-records-archive")', self.variables_tf)
        self.assertNotIn('google_project_service" "source_services', self.main_tf)

    def test_restore_rejects_path_traversal_and_non_drill_target(self) -> None:
        for member in ("../escape.json", "/absolute.json", "dir\\escape.json"):
            with self.subTest(member=member), self.assertRaises(ValueError):
                restore_archive._safe_member_name(member)
        with self.assertRaisesRegex(ValueError, "dedicated"):
            restore_archive.restore("farm-seges-ai-records-archive", "field-archive/manifest/2026/one.json", "farm-seges-ai-records")

    def test_restore_verifies_archive_and_round_trips_every_member_to_scratch(self) -> None:
        member_name = "obs-1.json"
        member_bytes = b'{"id":"obs-1"}\n'
        archive_buffer = io.BytesIO()
        with tarfile.open(fileobj=archive_buffer, mode="w:gz") as archive:
            info = tarfile.TarInfo(member_name)
            info.size = len(member_bytes)
            archive.addfile(info, io.BytesIO(member_bytes))
        archive_bytes = archive_buffer.getvalue()
        manifest_bytes = json.dumps(
            {
                "archive_object": "20261125/record-snapshot.tar.gz",
                "sha256": hashlib.sha256(archive_bytes).hexdigest(),
                "members": 1,
                "bytes": len(archive_bytes),
            }
        ).encode("utf-8")
        objects = {
            "gs://farm-seges-ai-records-archive/field-archive/manifest/20261125/snapshot.json": manifest_bytes,
            "gs://farm-seges-ai-records-archive/field-archive/20261125/record-snapshot.tar.gz": archive_bytes,
        }

        def fake_gcloud(*args: str) -> str:
            if args[:2] == ("storage", "cp"):
                source, destination = args[2], Path(args[3])
                if source.startswith("gs://"):
                    destination.write_bytes(objects[source])
                    return ""
            if args[:2] == ("storage", "rsync"):
                source, target = Path(args[3]), args[4]
                for file in source.rglob("*"):
                    if file.is_file():
                        name = file.relative_to(source).as_posix()
                        objects[f"{target}/{name}"] = file.read_bytes()
                return ""
            if args[:3] == ("storage", "ls", "--recursive"):
                prefix = args[3]
                return "".join(f"{uri}\n" for uri in sorted(objects) if uri.startswith(prefix))
            raise AssertionError(f"unexpected gcloud call: {args!r}")

        with patch.object(restore_archive, "_run_gcloud", side_effect=fake_gcloud):
            receipt = restore_archive.restore(
                "farm-seges-ai-records-archive",
                "field-archive/manifest/20261125/snapshot.json",
                "farm-seges-ai-archive-restore",
            )

        self.assertTrue(receipt["ok"])
        self.assertFalse(receipt["production_bucket_written"])
        self.assertEqual(receipt["members"], 1)
        self.assertEqual(receipt["restored_objects"], 1)


if __name__ == "__main__":
    unittest.main()
