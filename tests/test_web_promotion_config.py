import unittest
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from deploy.verify_web_promotion_config import main as promotion_main
from deploy.verify_web_promotion_config import (
    PromotionConfigError,
    verify_bucket_policy,
    verify_project_policy,
    verify_record_folder_policy,
    verify_record_bucket_policy,
    serving_revision,
    verify_service,
    verify_promotion_acceptance,
    verify_revision_runtime,
)


def service_document():
    return {
        "spec": {
            "template": {
                "spec": {
                    "serviceAccountName": "farm-web-runtime@seges-ai.iam.gserviceaccount.com",
                    "containers": [
                        {
                            "env": [
                                {"name": "FARM_OIDC_ISSUER", "value": "https://accounts.example.jp"},
                                {"name": "FARM_OIDC_CLIENT_ID", "value": "client-id"},
                                {"name": "FARM_OIDC_REDIRECT_URI", "value": "https://farm.example.jp/api/auth/callback"},
                                {"name": "FARM_ACCESS_BUCKET", "value": "farm-seges-ai-access-v2"},
                                {"name": "FARM_RECORD_BACKEND", "value": "gcs"},
                                {"name": "FARM_RECORD_BUCKET", "value": "farm-seges-ai-records"},
                                {"name": "FARM_RECORD_GCS_PREFIX", "value": "field-notes"},
                                {"name": "FARM_REQUIRE_TENANT_CONTEXT", "value": "1"},
                                {"name": "FARM_REQUIRE_IDEMPOTENCY", "value": "1"},
                                {"name": "FARM_OIDC_CLIENT_SECRET", "valueFrom": {"secretKeyRef": {"name": "farm-web-oidc-client-secret", "key": "latest"}}},
                                {"name": "FARM_SESSION_SECRET", "valueFrom": {"secretKeyRef": {"name": "farm-web-session-secret", "key": "latest"}}},
                                {"name": "PLANET_API_KEY", "valueFrom": {"secretKeyRef": {"name": "Planet-labs", "key": "latest"}}},
                            ]
                        }
                    ],
                }
            }
        }
    }


class WebPromotionConfigTests(unittest.TestCase):
    def test_promotion_requires_matching_protected_acceptance_and_ready_deployer(self):
        digest = "sha256:" + "a" * 64
        verify_promotion_acceptance(digest, digest, "true")
        for input_digest, acceptance, ready in (
            (digest, "", "true"),
            (digest, "sha256:" + "b" * 64, "true"),
            (digest, digest, "false"),
            ("latest", "latest", "true"),
        ):
            with self.subTest(input_digest=input_digest, acceptance=acceptance, ready=ready), self.assertRaises(PromotionConfigError):
                verify_promotion_acceptance(input_digest, acceptance, ready)

    def test_valid_dedicated_oidc_configuration(self):
        self.assertEqual(
            verify_service(service_document()),
            ("farm-web-runtime@seges-ai.iam.gserviceaccount.com", "farm-seges-ai-access-v2"),
        )

    def test_missing_oidc_configuration_fails_closed(self):
        doc = service_document()
        doc["spec"]["template"]["spec"]["containers"][0]["env"] = []
        with self.assertRaisesRegex(PromotionConfigError, "FARM_OIDC_ISSUER"):
            verify_service(doc)

    def test_inline_client_secret_is_rejected(self):
        doc = service_document()
        env = doc["spec"]["template"]["spec"]["containers"][0]["env"]
        index = next(i for i, row in enumerate(env) if row["name"] == "FARM_OIDC_CLIENT_SECRET")
        env[index] = {"name": "FARM_OIDC_CLIENT_SECRET", "value": "must-not-be-inline"}
        with self.assertRaisesRegex(PromotionConfigError, "Secret Manager"):
            verify_service(doc)

    def test_unmanaged_secret_reference_is_rejected(self):
        doc = service_document()
        secret = next(
            row for row in doc["spec"]["template"]["spec"]["containers"][0]["env"]
            if row["name"] == "FARM_OIDC_CLIENT_SECRET"
        )
        secret["valueFrom"]["secretKeyRef"]["name"] = "some-other-secret"
        with self.assertRaisesRegex(PromotionConfigError, "dedicated farm"):
            verify_service(doc)

    def test_shared_default_service_account_is_rejected(self):
        doc = service_document()
        doc["spec"]["template"]["spec"]["serviceAccountName"] = "451400509859-compute@developer.gserviceaccount.com"
        with self.assertRaisesRegex(PromotionConfigError, "dedicated"):
            verify_service(doc)

    def test_http_issuer_is_rejected(self):
        doc = service_document()
        env = doc["spec"]["template"]["spec"]["containers"][0]["env"]
        env[0]["value"] = "http://accounts.example.jp"
        with self.assertRaisesRegex(PromotionConfigError, "HTTPS"):
            verify_service(doc)

    def test_missing_tenant_guards_or_legacy_token_fails_closed(self):
        doc = service_document()
        env = doc["spec"]["template"]["spec"]["containers"][0]["env"]
        next(x for x in env if x["name"] == "FARM_REQUIRE_IDEMPOTENCY")["value"] = "0"
        with self.assertRaisesRegex(PromotionConfigError, "FARM_REQUIRE_IDEMPOTENCY"):
            verify_service(doc)
        doc = service_document()
        doc["spec"]["template"]["spec"]["containers"][0]["env"].append(
            {"name": "WEB_ACCESS_TOKEN", "valueFrom": {"secretKeyRef": {"name": "web-access-token", "key": "latest"}}}
        )
        with self.assertRaisesRegex(PromotionConfigError, "legacy shared web token"):
            verify_service(doc)

    def test_legacy_projection_bindings_are_not_bucket_grants(self):
        service_account, _bucket = verify_service(service_document())
        # reality: every UBLA bucket reports legacy* bindings projected from
        # the project's primitive roles; the verifier must not fail on them.
        legacy = [
            {"role": "roles/storage.legacyBucketOwner", "members": ["projectEditor:seges-ai"]},
            {"role": "roles/storage.legacyBucketReader", "members": ["projectViewer:seges-ai"]},
            {"role": "roles/storage.legacyObjectOwner", "members": ["projectEditor:seges-ai"]},
            {"role": "roles/storage.legacyObjectReader", "members": ["projectViewer:seges-ai"]},
        ]
        expected = [
            {"role": "roles/storage.objectViewer", "members": [f"serviceAccount:{service_account}"]},
            {"role": "roles/storage.objectUser", "members": ["user:farmer-admin@example.jp"]},
            {"role": "projects/seges-ai/roles/farmWebPolicyReader", "members": ["serviceAccount:farm-web-deployer@seges-ai.iam.gserviceaccount.com"]},
        ]
        verify_bucket_policy({"bindings": legacy + expected}, service_account, "user:farmer-admin@example.jp")
        # a NON-legacy extra grant is still an error
        with self.assertRaisesRegex(PromotionConfigError, "access bucket"):
            verify_bucket_policy(
                {"bindings": expected + [{"role": "roles/storage.objectCreator", "members": ["group:x@example.jp"]}]},
                service_account,
                "user:farmer-admin@example.jp",
            )

    def test_membership_bucket_requires_read_only_runtime_binding(self):
        service_account, _bucket = verify_service(service_document())
        verify_bucket_policy(
            {"bindings": [
                {"role": "roles/storage.objectViewer", "members": [f"serviceAccount:{service_account}"]},
                {"role": "roles/storage.objectUser", "members": ["user:farmer-admin@example.jp"]},
                {"role": "projects/seges-ai/roles/farmWebPolicyReader", "members": ["serviceAccount:farm-web-deployer@seges-ai.iam.gserviceaccount.com"]},
            ]},
            service_account,
            "user:farmer-admin@example.jp",
        )
        with self.assertRaisesRegex(PromotionConfigError, "access bucket"):
            verify_bucket_policy({"bindings": []}, service_account, "user:farmer-admin@example.jp")

    def test_membership_bucket_rejects_direct_write_binding(self):
        service_account, _bucket = verify_service(service_document())
        with self.assertRaisesRegex(PromotionConfigError, "access bucket"):
            verify_bucket_policy(
                {"bindings": [
                    {"role": "roles/storage.objectViewer", "members": [f"serviceAccount:{service_account}"]},
                    {"role": "roles/storage.objectUser", "members": [f"serviceAccount:{service_account}"]},
                ]},
                service_account,
                "user:farmer-admin@example.jp",
            )

    def test_membership_bucket_rejects_custom_writer_and_conditional_viewer(self):
        service_account, _bucket = verify_service(service_document())
        member = f"serviceAccount:{service_account}"
        allowed = [
            {"role": "roles/storage.objectViewer", "members": [member]},
            {"role": "roles/storage.objectUser", "members": ["user:farmer-admin@example.jp"]},
            {"role": "projects/seges-ai/roles/farmWebPolicyReader", "members": ["serviceAccount:farm-web-deployer@seges-ai.iam.gserviceaccount.com"]},
        ]
        for bindings in (
            allowed + [{"role": "projects/seges-ai/roles/customStorageWriter", "members": ["group:unexpected@example.jp"]}],
            [{"role": "roles/storage.objectViewer", "members": [member], "condition": {"title": "wrong-prefix"}}],
        ):
            with self.subTest(bindings=bindings), self.assertRaisesRegex(PromotionConfigError, "access.bucket"):
                verify_bucket_policy({"bindings": bindings}, service_account, "user:farmer-admin@example.jp")

    def test_project_iam_rejects_broad_runtime_permissions(self):
        service_account, _bucket = verify_service(service_document())
        member = f"serviceAccount:{service_account}"
        deployer = "serviceAccount:farm-web-deployer@seges-ai.iam.gserviceaccount.com"
        verify_project_policy({"bindings": [
            {"role": "roles/viewer", "members": ["user:unrelated@example.jp"], "condition": {"title": "unrelated"}},
            {"role": "projects/seges-ai/roles/farmWebProjectPolicyReader", "members": [deployer]},
        ]}, service_account)
        with self.assertRaisesRegex(PromotionConfigError, "no project-level"):
            verify_project_policy({"bindings": [{"role": "projects/seges-ai/roles/customStorageWriter", "members": [member]}]}, service_account)
        with self.assertRaisesRegex(PromotionConfigError, "only its narrow"):
            verify_project_policy({"bindings": [{"role": "roles/owner", "members": [deployer]}]}, service_account)

    def test_record_prefix_allows_append_and_read_without_delete(self):
        service_account, _bucket = verify_service(service_document())
        member = f"serviceAccount:{service_account}"
        verify_record_folder_policy(
            {"bindings": [
                {"role": "roles/storage.objectViewer", "members": [member]},
                {"role": "roles/storage.objectCreator", "members": [member]},
                {"role": "projects/seges-ai/roles/farmWebPolicyReader", "members": ["serviceAccount:farm-web-deployer@seges-ai.iam.gserviceaccount.com"]},
            ]},
            service_account,
        )
        for bindings in (
            [{"role": "roles/storage.objectViewer", "members": [member]}],
            [
                {"role": "roles/storage.objectViewer", "members": [member]},
                {"role": "roles/storage.objectCreator", "members": [member]},
                {"role": "roles/storage.objectAdmin", "members": [member]},
            ],
        ):
            with self.subTest(bindings=bindings), self.assertRaisesRegex(PromotionConfigError, "viewer/creator"):
                verify_record_folder_policy({"bindings": bindings}, service_account)

    def test_record_bucket_rejects_parent_runtime_grant_even_when_folder_is_scoped(self):
        service_account, _bucket = verify_service(service_document())
        verify_record_folder_policy({"bindings": [
            {"role": "roles/storage.objectViewer", "members": [f"serviceAccount:{service_account}"]},
            {"role": "roles/storage.objectCreator", "members": [f"serviceAccount:{service_account}"]},
            {"role": "projects/seges-ai/roles/farmWebPolicyReader", "members": ["serviceAccount:farm-web-deployer@seges-ai.iam.gserviceaccount.com"]},
        ]}, service_account)
        verify_record_bucket_policy({"bindings": [
            {"role": "roles/storage.objectViewer", "members": ["serviceAccount:unrelated@seges-ai.iam.gserviceaccount.com"]},
        ]}, service_account)
        with self.assertRaisesRegex(PromotionConfigError, "no direct bucket-level"):
            verify_record_bucket_policy({"bindings": [
                {"role": "roles/storage.objectAdmin", "members": [f"serviceAccount:{service_account}"]},
            ]}, service_account)

    def test_serving_revision_skips_tagged_zero_traffic_rows(self):
        self.assertEqual(
            serving_revision({"status": {"traffic": [
                {"tag": "auth-candidate", "percent": 0, "revisionName": "candidate"},
                {"percent": 100, "revisionName": "known-good"},
            ]}}),
            "known-good",
        )
        with self.assertRaisesRegex(PromotionConfigError, "exactly one 100%"):
            serving_revision({"status": {"traffic": [{"percent": 0, "revisionName": "candidate"}]}})

    def test_runtime_identity_and_candidate_revision_are_exact(self):
        doc = service_document()
        doc["spec"]["template"]["spec"]["serviceAccountName"] = "other@seges-ai.iam.gserviceaccount.com"
        with self.assertRaisesRegex(PromotionConfigError, "dedicated"):
            verify_service(doc)
        verify_revision_runtime({"spec": {"serviceAccountName": "farm-web-runtime@seges-ai.iam.gserviceaccount.com"}})
        with self.assertRaisesRegex(PromotionConfigError, "dedicated"):
            verify_revision_runtime({"spec": {"serviceAccountName": "451400509859-compute@developer.gserviceaccount.com"}})

    def test_cli_checks_access_parent_bucket_and_tenant_folder_policies(self):
        runtime = "serviceAccount:farm-web-runtime@seges-ai.iam.gserviceaccount.com"
        deployer = "serviceAccount:farm-web-deployer@seges-ai.iam.gserviceaccount.com"
        policies = (
            service_document(),
            {"bindings": [
                {"role": "roles/storage.objectViewer", "members": [runtime]},
                {"role": "roles/storage.objectUser", "members": ["user:farmer-admin@example.jp"]},
                {"role": "projects/seges-ai/roles/farmWebPolicyReader", "members": [deployer]},
            ]},
            {"bindings": [{"role": "projects/seges-ai/roles/farmWebProjectPolicyReader", "members": [deployer]}]},
            {"bindings": []},
            {"bindings": [
                {"role": "roles/storage.objectViewer", "members": [runtime]},
                {"role": "roles/storage.objectCreator", "members": [runtime]},
                {"role": "projects/seges-ai/roles/farmWebPolicyReader", "members": [deployer]},
            ]},
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = []
            for index, document in enumerate(policies):
                path = Path(temp_dir) / f"policy-{index}.json"
                path.write_text(json.dumps(document), encoding="utf-8")
                paths.append(str(path))
            with patch.object(sys, "argv", ["verify_web_promotion_config.py", *paths, "user:farmer-admin@example.jp"]):
                self.assertEqual(promotion_main(), 0)
            # Parent bucket binding is an escalation path even if the scoped
            # managed-folder policy itself is valid.
            policies = list(policies)
            policies[3] = {"bindings": [{"role": "roles/storage.objectAdmin", "members": [runtime]}]}
            paths[3] = str(Path(temp_dir) / "parent-escalation.json")
            Path(paths[3]).write_text(json.dumps(policies[3]), encoding="utf-8")
            with patch.object(sys, "argv", ["verify_web_promotion_config.py", *paths, "user:farmer-admin@example.jp"]):
                self.assertEqual(promotion_main(), 1)


if __name__ == "__main__":
    unittest.main()
