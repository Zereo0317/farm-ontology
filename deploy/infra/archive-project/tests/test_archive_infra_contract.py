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
VERIFY_SPEC = importlib.util.spec_from_file_location(
    "verify_state_bucket", STACK / "verify_state_bucket.py"
)
verify_state_bucket = importlib.util.module_from_spec(VERIFY_SPEC)
assert VERIFY_SPEC.loader is not None
VERIFY_SPEC.loader.exec_module(verify_state_bucket)


class ArchiveInfrastructureContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.main_tf = (STACK / "main.tf").read_text(encoding="utf-8")
        cls.variables_tf = (STACK / "variables.tf").read_text(encoding="utf-8")

    def test_all_persistent_resources_have_destroy_guards(self) -> None:
        for resource in (
            'google_storage_bucket" "terraform_state',
            'google_service_account" "web_runtime',
            'google_service_account" "web_deployer',
            'google_project_iam_custom_role" "web_policy_reader',
            'google_project_iam_custom_role" "web_project_policy_reader',
            'google_service_account_iam_member" "github_main_can_use_web_deployer',
            'google_project_iam_member" "web_deployer_reads_project_policy',
            'google_artifact_registry_repository_iam_member" "web_deployer_reads_images',
            'google_cloud_run_v2_service_iam_member" "web_deployer_updates_web',
            'google_storage_bucket" "web_access',
            'google_storage_bucket_iam_member" "web_runtime_reads_memberships',
            'google_storage_bucket_iam_member" "web_membership_administrator',
            'google_storage_managed_folder" "web_tenant_records',
            'google_storage_managed_folder_iam_member" "web_runtime_reads_tenant_records',
            'google_storage_managed_folder_iam_member" "web_runtime_creates_tenant_records',
            'google_secret_manager_secret_iam_member" "web_runtime_reads_planet_thumbnail',
            'google_storage_bucket_iam_member" "web_deployer_reads_access_policy',
            'google_storage_bucket_iam_member" "web_deployer_reads_records_policy',
            'google_storage_managed_folder_iam_member" "web_deployer_reads_records_folder_policy',
            'google_secret_manager_secret" "web_oidc_client',
            'google_secret_manager_secret" "web_session',
            'google_secret_manager_secret_iam_member" "web_runtime_reads_oidc_client',
            'google_secret_manager_secret_iam_member" "web_runtime_reads_session_secret',
            'google_secret_manager_secret_iam_member" "web_deployer_lists_oidc_client_versions',
            'google_secret_manager_secret_iam_member" "web_deployer_lists_session_versions',
            'google_service_account_iam_member" "web_deployer_can_attach_runtime',
            'google_secret_manager_secret_iam_member" "web_secret_operator_adds_oidc_versions',
            'google_secret_manager_secret_iam_member" "web_secret_operator_adds_session_versions',
            'google_project" "archive',
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
        self.assertIn('with_state     = "LIVE"', self.main_tf)
        self.assertNotIn("is_live", self.main_tf)
        self.assertIn("retention_days == 90", self.variables_tf)
        self.assertIn("days_since_noncurrent_time = var.retention_days", self.main_tf)
        self.assertIn("days_since_noncurrent_time = 7", self.main_tf)
        self.assertEqual(self.main_tf.count("days_since_noncurrent_time ="), 2)

    def test_scheduler_is_unmanaged_until_explicit_post_drill_activation(self) -> None:
        self.assertIn('schedule         = "*/30 * * * *"', self.main_tf)
        self.assertIn('time_zone        = "Asia/Tokyo"', self.main_tf)
        self.assertIn('role     = "roles/run.invoker"', self.main_tf)
        self.assertIn('name     = "farm-nightly-export"', self.main_tf)
        self.assertIn('count = var.enable_archive_schedule ? 1 : 0', self.main_tf)
        variables = (STACK / "variables.tf").read_text(encoding="utf-8")
        self.assertIn('variable "enable_archive_schedule"', variables)
        self.assertIn("default     = false", variables)
        self.assertIn("google_cloud_scheduler_job.archive_export[0]", (STACK / "README.md").read_text(encoding="utf-8"))

    def test_state_bucket_is_in_archive_project_with_explicit_operator_grant(self) -> None:
        state_block = self.main_tf.split('google_storage_bucket" "terraform_state', 1)[1].split("\nresource ", 1)[0]
        self.assertIn("provider                    = google.archive", state_block)
        self.assertIn("project                     = google_project.archive.project_id", state_block)
        state_iam = self.main_tf.split('google_storage_bucket_iam_member" "terraform_state_operator', 1)[1].split("\nresource ", 1)[0]
        self.assertIn('role   = "roles/storage.objectAdmin"', state_iam)
        self.assertIn("var.terraform_state_operator_member", state_iam)
        self.assertIn("inherited", (STACK / "README.md").read_text(encoding="utf-8"))
        state_iam = self.main_tf.split('google_storage_bucket_iam_member" "terraform_state_operator', 1)[1].split("\nresource ", 1)[0]
        self.assertIn("create_before_destroy = true", state_iam)
        self.assertNotIn("prevent_destroy = true", state_iam)

    def test_state_bootstrap_accepts_flat_snake_case_gcloud_json(self) -> None:
        sample = {
            "name": "farm-seges-ai-iac-state",
            "location": "ASIA-EAST1",
            "uniform_bucket_level_access": True,
            "public_access_prevention": "enforced",
            "versioning": True,
        }
        verify_state_bucket.verify_bucket_json(
            sample, bucket="farm-seges-ai-iac-state", region="asia-east1"
        )
        nested = {
            "name": "farm-seges-ai-iac-state",
            "location": "asia-east1",
            "uniform_bucket_level_access": {"enabled": True},
            "iam_configuration": {
                "public_access_prevention": "enforced",
            },
            "versioning": {"enabled": True},
        }
        verify_state_bucket.verify_bucket_json(
            nested, bucket="farm-seges-ai-iac-state", region="asia-east1"
        )
        with self.assertRaisesRegex(ValueError, "versioning"):
            verify_state_bucket.verify_bucket_json(
                {**sample, "versioning": False},
                bucket="farm-seges-ai-iac-state",
                region="asia-east1",
            )
        bootstrap_script = (STACK / "bootstrap-state.ps1").read_text(encoding="utf-8")
        self.assertIn("verify_state_bucket.py", bootstrap_script)
        self.assertNotIn("gcloud storage buckets create", bootstrap_script)
        self.assertNotIn("iamConfiguration", bootstrap_script)

    def test_web_runtime_identity_has_private_read_only_membership_foundation(self) -> None:
        readme = (STACK / "README.md").read_text(encoding="utf-8")
        self.assertIn('google_storage_bucket_iam_member" "web_runtime_reads_memberships', self.main_tf)
        self.assertIn('role   = "roles/storage.objectViewer"', self.main_tf)
        self.assertIn('role      = "roles/secretmanager.secretAccessor"', self.main_tf)
        self.assertIn('var.web_runtime_service_account_id == "farm-web-runtime"', self.variables_tf)
        self.assertIn('var.web_deployer_service_account_id == "farm-web-deployer"', self.variables_tf)
        self.assertIn('account_id   = "farm-seges-ai-arch-sched"', self.main_tf)
        self.assertIn("Web access-control foundation", readme)
        self.assertIn("separate private membership bucket", readme)
        self.assertIn('role           = "roles/storage.objectCreator"', self.main_tf)
        self.assertIn("principal://iam.googleapis.com", self.main_tf)
        self.assertNotIn("var.exporter_deployer_service_account}", self.main_tf.split('resource "google_service_account_iam_member" "web_deployer_can_attach_runtime"', 1)[1].split("\nresource ", 1)[0])

    def test_web_project_policy_reader_is_narrow_and_membership_admin_is_explicit(self) -> None:
        project_role = self.main_tf.split('resource "google_project_iam_custom_role" "web_project_policy_reader"', 1)[1].split("\nresource ", 1)[0]
        self.assertIn('permissions = ["resourcemanager.projects.getIamPolicy"]', project_role)
        self.assertNotIn("roles/iam.securityReviewer", self.main_tf)
        membership_admin = self.main_tf.split('resource "google_storage_bucket_iam_member" "web_membership_administrator"', 1)[1].split("\nresource ", 1)[0]
        self.assertIn('role   = "roles/storage.objectUser"', membership_admin)
        self.assertIn("var.web_membership_administrator_member", membership_admin)
        self.assertIn('variable "web_membership_administrator_member"', self.variables_tf)

    def test_restore_enforces_manifest_and_download_bounds_before_copy(self) -> None:
        with self.assertRaisesRegex(ValueError, "member count"):
            restore_archive._validate_manifest_limits(
                restore_archive.MAX_ARCHIVE_MEMBERS + 1, 100
            )
        with self.assertRaisesRegex(ValueError, "byte count"):
            restore_archive._validate_manifest_limits(1, restore_archive.MAX_ARCHIVE_BYTES + 1)

        with tempfile.TemporaryDirectory() as directory:
            for object_name, limit, remote_size in (
                (
                    "field-archive/manifest/20261125/snapshot.json",
                    restore_archive.MAX_MANIFEST_BYTES,
                    restore_archive.MAX_MANIFEST_BYTES + 1,
                ),
                (
                    "field-archive/20261125/snapshot.tar.gz",
                    restore_archive.MAX_ARCHIVE_BYTES,
                    restore_archive.MAX_ARCHIVE_BYTES + 1,
                ),
            ):
                with self.subTest(object_name=object_name):
                    destination = Path(directory) / "bounded-object"
                    with patch.object(
                        restore_archive,
                        "_run_gcloud",
                        return_value=json.dumps({"size": remote_size}),
                    ) as run_gcloud:
                        with self.assertRaisesRegex(ValueError, "download limit"):
                            restore_archive._download(
                                "farm-seges-ai-records-archive",
                                object_name,
                                destination,
                                max_bytes=limit,
                            )
                    self.assertEqual(run_gcloud.call_count, 1)

    def test_restore_rejects_oversized_per_member_and_aggregate_metadata(self) -> None:
        too_large = tarfile.TarInfo("large.json")
        too_large.size = restore_archive.MAX_MEMBER_BYTES + 1
        with self.assertRaisesRegex(ValueError, "per-file"):
            restore_archive._validate_member_metadata([too_large], 1)

        members = []
        for index in range(129):
            member = tarfile.TarInfo(f"{index}.json")
            member.size = restore_archive.MAX_MEMBER_BYTES
            members.append(member)
        with self.assertRaisesRegex(ValueError, "aggregate"):
            restore_archive._validate_member_metadata(members, len(members))

        def over_count():
            for index in range(restore_archive.MAX_ARCHIVE_MEMBERS + 1):
                yield tarfile.TarInfo(f"{index}.json")

        with self.assertRaisesRegex(ValueError, "member count"):
            restore_archive._validate_member_metadata(
                over_count(), restore_archive.MAX_ARCHIVE_MEMBERS + 1
            )

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
            if args[:3] == ("storage", "objects", "describe"):
                return json.dumps({"size": len(objects[args[3]])})
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
