"""Fail-closed validation for the farm web OIDC production configuration.

The service description is metadata only. Secret payloads are never read or
printed by this helper.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


class PromotionConfigError(ValueError):
    pass


def verify_promotion_acceptance(image_digest: str, acceptance_digest: str, deployer_ready: str) -> None:
    if not isinstance(image_digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", image_digest):
        raise PromotionConfigError("promotion requires a full immutable sha256 digest")
    if not isinstance(acceptance_digest, str) or acceptance_digest != image_digest:
        raise PromotionConfigError("protected farmer acceptance digest is missing or does not match")
    if deployer_ready != "true":
        raise PromotionConfigError("dedicated farm web deployer is not marked ready")


def _members_of(binding: dict) -> list:
    members = binding.get("members")
    return members if isinstance(members, list) else []


WEB_RUNTIME_SERVICE_ACCOUNT = "farm-web-runtime@seges-ai.iam.gserviceaccount.com"
WEB_DEPLOYER_SERVICE_ACCOUNT = "farm-web-deployer@seges-ai.iam.gserviceaccount.com"
WEB_POLICY_READER_ROLE = "projects/seges-ai/roles/farmWebPolicyReader"


def verify_service(document: dict) -> tuple[str, str]:
    try:
        template = document["spec"]["template"]
        spec = template["spec"]
        containers = spec["containers"]
        env_rows = containers[0]["env"]
        service_account = spec["serviceAccountName"]
    except (KeyError, IndexError, TypeError) as error:
        raise PromotionConfigError("Cloud Run service metadata is incomplete") from error

    env = {row.get("name"): row for row in env_rows if isinstance(row, dict)}
    required_plain = (
        "FARM_OIDC_ISSUER", "FARM_OIDC_CLIENT_ID", "FARM_OIDC_REDIRECT_URI",
        "FARM_ACCESS_BUCKET", "FARM_RECORD_BACKEND", "FARM_RECORD_BUCKET",
        "FARM_RECORD_GCS_PREFIX", "FARM_REQUIRE_TENANT_CONTEXT",
        "FARM_REQUIRE_IDEMPOTENCY",
    )
    required_secret = ("FARM_OIDC_CLIENT_SECRET", "FARM_SESSION_SECRET", "PLANET_API_KEY")
    for name in required_plain:
        row = env.get(name)
        value = row.get("value") if row else None
        if not isinstance(value, str) or not value.strip():
            raise PromotionConfigError(f"missing required runtime setting: {name}")

    issuer = env["FARM_OIDC_ISSUER"]["value"].strip()
    redirect = env["FARM_OIDC_REDIRECT_URI"]["value"].strip()
    for name, value in (("FARM_OIDC_ISSUER", issuer), ("FARM_OIDC_REDIRECT_URI", redirect)):
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise PromotionConfigError(f"{name} must be an absolute HTTPS URL")
    if not redirect.endswith("/api/auth/callback"):
        raise PromotionConfigError("FARM_OIDC_REDIRECT_URI must end in /api/auth/callback")
    expected_runtime = {
        "FARM_RECORD_BACKEND": "gcs",
        "FARM_RECORD_BUCKET": "farm-seges-ai-records",
        "FARM_RECORD_GCS_PREFIX": "field-notes",
        "FARM_REQUIRE_TENANT_CONTEXT": "1",
        "FARM_REQUIRE_IDEMPOTENCY": "1",
    }
    for name, expected in expected_runtime.items():
        if env[name]["value"].strip().lower() != expected:
            raise PromotionConfigError(f"{name} must be configured as {expected}")
    if "WEB_ACCESS_TOKEN" in env:
        raise PromotionConfigError("legacy shared web token must be removed from OIDC revisions")

    expected_secret_names = {
        "FARM_OIDC_CLIENT_SECRET": "farm-web-oidc-client-secret",
        "FARM_SESSION_SECRET": "farm-web-session-secret",
        "PLANET_API_KEY": "Planet-labs",
    }
    for name in required_secret:
        row = env.get(name)
        ref = None
        if row:
            value_from = row.get("valueFrom")
            ref = value_from.get("secretKeyRef") if isinstance(value_from, dict) else None
            if ref is None:
                value_source = row.get("valueSource")
                ref = value_source.get("secretKeyRef") if isinstance(value_source, dict) else None
        if not isinstance(ref, dict) or not (ref.get("name") or ref.get("secret")) or not (ref.get("key") or ref.get("version")):
            raise PromotionConfigError(f"{name} must reference Secret Manager")
        secret_name = ref.get("name") or ref.get("secret")
        if not isinstance(secret_name, str):
            raise PromotionConfigError(f"{name} must reference a named Secret Manager entry")
        if secret_name.split("/")[-1] != expected_secret_names[name]:
            raise PromotionConfigError(f"{name} must reference its dedicated farm Secret Manager entry")

    if service_account != WEB_RUNTIME_SERVICE_ACCOUNT:
        raise PromotionConfigError(
            f"web runtime must use the dedicated {WEB_RUNTIME_SERVICE_ACCOUNT} service account"
        )

    return service_account, env["FARM_ACCESS_BUCKET"]["value"].strip()


#: GCS projects primitive project-roles (owner/editor/viewer) onto every
#: bucket as legacy* bindings regardless of UBLA; they are projections of
#: project-level IAM, not bucket grants, and any exact-set comparison must
#: ignore them or promotion is unsatisfiable on every real bucket.
_LEGACY_STORAGE_ROLES = frozenset({
    "roles/storage.legacyBucketOwner",
    "roles/storage.legacyBucketReader",
    "roles/storage.legacyObjectOwner",
    "roles/storage.legacyObjectReader",
})

def _direct_bindings(document: dict, description: str) -> set[tuple[str, str]]:
    bindings = document.get("bindings") if isinstance(document, dict) else None
    if not isinstance(bindings, list):
        raise PromotionConfigError(f"{description} IAM policy is unreadable")
    normalized: set[tuple[str, str]] = set()
    for row in bindings:
        if not isinstance(row, dict) or row.get("condition"):
            raise PromotionConfigError(f"{description} IAM policy contains an unreadable or conditional binding")
        role = row.get("role")
        if role in _LEGACY_STORAGE_ROLES:
            continue  # project-role projection, not a bucket grant
        members = _members_of(row)
        if not isinstance(role, str) or not members or any(not isinstance(member, str) for member in members):
            raise PromotionConfigError(f"{description} IAM policy contains an incomplete binding")
        normalized.update((role, member) for member in members)
    return normalized


def verify_bucket_policy(document: dict, service_account: str, membership_admin: str) -> None:
    actual = _direct_bindings(document, "access-bucket")
    expected = {
        ("roles/storage.objectViewer", f"serviceAccount:{service_account}"),
        ("roles/storage.objectUser", membership_admin),
        (WEB_POLICY_READER_ROLE, f"serviceAccount:{WEB_DEPLOYER_SERVICE_ACCOUNT}"),
    }
    if actual != expected:
        raise PromotionConfigError(
            "access bucket must contain only the runtime viewer, authorized membership administrator, and deployer policy-reader grants"
        )


def verify_project_policy(document: dict, service_account: str) -> None:
    bindings = document.get("bindings") if isinstance(document, dict) else None
    if not isinstance(bindings, list):
        raise PromotionConfigError("project IAM policy is unreadable")
    runtime_member = f"serviceAccount:{service_account}"
    deployer_member = f"serviceAccount:{WEB_DEPLOYER_SERVICE_ACCOUNT}"
    runtime_roles = set()
    deployer_roles = set()
    for row in bindings:
        if not isinstance(row, dict) or not isinstance(row.get("role"), str):
            raise PromotionConfigError("project IAM policy contains an incomplete binding")
        members = _members_of(row)
        if runtime_member in members:
            runtime_roles.add(row["role"])
        if deployer_member in members:
            if row.get("condition"):
                raise PromotionConfigError("web deployer project policy-reader grant must not be conditional")
            deployer_roles.add(row["role"])
    if runtime_roles:
        raise PromotionConfigError("dedicated web runtime service account must have no project-level IAM bindings")
    if deployer_roles != {"projects/seges-ai/roles/farmWebProjectPolicyReader"}:
        raise PromotionConfigError("web deployer must have only its narrow project policy-reader binding")


def verify_record_folder_policy(document: dict, service_account: str) -> None:
    actual = _direct_bindings(document, "tenant-record managed-folder")
    runtime_member = f"serviceAccount:{service_account}"
    deployer_member = f"serviceAccount:{WEB_DEPLOYER_SERVICE_ACCOUNT}"
    expected = {
        ("roles/storage.objectViewer", runtime_member),
        ("roles/storage.objectCreator", runtime_member),
        (WEB_POLICY_READER_ROLE, deployer_member),
    }
    if actual != expected:
        raise PromotionConfigError(
            "tenant-record folder must contain only runtime viewer/creator and deployer policy-reader grants"
        )


def verify_record_bucket_policy(document: dict, service_account: str) -> None:
    bindings = document.get("bindings") if isinstance(document, dict) else None
    if not isinstance(bindings, list):
        raise PromotionConfigError("farm records bucket IAM policy is unreadable")
    runtime_member = f"serviceAccount:{service_account}"
    for row in bindings:
        if not isinstance(row, dict) or not isinstance(row.get("role"), str):
            raise PromotionConfigError("farm records bucket IAM policy contains an incomplete binding")
        if runtime_member in _members_of(row):
            raise PromotionConfigError(
                "web runtime must have no direct bucket-level grants on the records bucket; use the tenant managed-folder grants only"
            )


def verify_revision_runtime(document: dict) -> None:
    try:
        service_account = document["spec"]["serviceAccountName"]
    except (KeyError, TypeError) as error:
        raise PromotionConfigError("candidate revision service-account metadata is incomplete") from error
    if service_account != WEB_RUNTIME_SERVICE_ACCOUNT:
        raise PromotionConfigError("candidate revision does not use the dedicated farm web runtime service account")


def serving_revision(document: dict) -> str:
    try:
        traffic = document["status"]["traffic"]
    except (KeyError, TypeError) as error:
        raise PromotionConfigError("Cloud Run serving traffic metadata is incomplete") from error
    serving = [row for row in traffic if isinstance(row, dict) and row.get("percent") == 100]
    if len(serving) != 1 or not isinstance(serving[0].get("revisionName"), str):
        raise PromotionConfigError("expected exactly one 100% serving revision")
    return serving[0]["revisionName"]


def main() -> int:
    if len(sys.argv) != 7:
        print("usage: verify_web_promotion_config.py SERVICE_JSON ACCESS_BUCKET_IAM_JSON PROJECT_IAM_JSON RECORD_BUCKET_IAM_JSON RECORD_FOLDER_IAM_JSON MEMBERSHIP_ADMIN_PRINCIPAL", file=sys.stderr)
        return 2
    try:
        if not re.fullmatch(r"(?:user|group):\S+", sys.argv[6]):
            raise PromotionConfigError("membership administrator must match the explicit Terraform user: or group: principal")
        document = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        service_account, bucket = verify_service(document)
        bucket_policy = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        verify_bucket_policy(bucket_policy, service_account, sys.argv[6])
        project_policy = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
        verify_project_policy(project_policy, service_account)
        record_bucket_policy = json.loads(Path(sys.argv[4]).read_text(encoding="utf-8"))
        verify_record_bucket_policy(record_bucket_policy, service_account)
        record_folder_policy = json.loads(Path(sys.argv[5]).read_text(encoding="utf-8"))
        verify_record_folder_policy(record_folder_policy, service_account)
    except (OSError, json.JSONDecodeError, PromotionConfigError) as error:
        print(f"web promotion blocked: {error}", file=sys.stderr)
        return 1
    # Deliberately prints only non-secret identifiers, never env values or
    # Secret Manager payloads.
    print(f"web OIDC runtime metadata valid; service account={service_account}; access bucket={bucket}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
