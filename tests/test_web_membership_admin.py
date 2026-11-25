import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from deploy import manage_web_membership as admin
from deploy.manage_web_membership import MembershipError, actor_hash, make_membership, membership_path


NOW = dt.datetime(2026, 11, 25, 3, 0, tzinfo=dt.timezone.utc)
ISSUER = "https://issuer.example/"
SUBJECT = "verified-oidc-subject"
FARM = "biratori-hokkaido"
EXPIRY = "2027-11-25T00:00:00Z"


def request(action="grant", **overrides):
    value = {
        "action": action,
        "farm_id": FARM,
        "issuer": ISSUER,
        "subject": SUBJECT,
        "role": "viewer",
        "expires_at": EXPIRY,
        "change_reference": "grant-record-123",
    }
    value.update(overrides)
    return value


def current_record(**overrides):
    value = {
        "schema_version": 1,
        "farm_id": FARM,
        "actor_hash": actor_hash(ISSUER, SUBJECT),
        "role": "operator",
        "status": "active",
        "granted_at": "2026-10-01T00:00:00Z",
        "expires_at": EXPIRY,
        "updated_at": "2026-10-01T00:00:00Z",
        "change_reference": "grant-record-123",
    }
    value.update(overrides)
    return value


class WebMembershipAdminTests(unittest.TestCase):
    def test_actor_hash_and_storage_path_match_runtime_contract(self):
        digest = actor_hash(ISSUER, SUBJECT)
        self.assertEqual(len(digest), 64)
        self.assertEqual(membership_path(FARM, digest), f"farms/{FARM}/members/{digest}.json")
        self.assertEqual(digest, actor_hash(ISSUER.rstrip("/"), SUBJECT))

    def test_grant_creates_runtime_compatible_minimal_record(self):
        membership = make_membership(request(), None, NOW)
        self.assertEqual(membership["schema_version"], 1)
        self.assertEqual(membership["actor_hash"], actor_hash(ISSUER, SUBJECT))
        self.assertEqual(membership["status"], "active")
        self.assertEqual(membership["role"], "viewer")
        self.assertEqual(membership["granted_at"], "2026-11-25T03:00:00.000Z")
        self.assertEqual(membership["change_reference"], "grant-record-123")

    def test_revoke_preserves_grant_provenance_and_changes_only_revocation_fields(self):
        existing = current_record()
        updated = make_membership(request("revoke", change_reference="revocation-123"), existing, NOW)
        self.assertEqual(updated["status"], "revoked")
        self.assertEqual(updated["role"], existing["role"])
        self.assertEqual(updated["granted_at"], existing["granted_at"])
        self.assertEqual(updated["expires_at"], existing["expires_at"])
        self.assertEqual(updated["updated_at"], "2026-11-25T03:00:00.000Z")
        self.assertEqual(updated["change_reference"], "revocation-123")

    def test_active_membership_cannot_be_overwritten_and_revoked_member_can_be_regranted(self):
        with self.assertRaisesRegex(MembershipError, "already exists"):
            make_membership(request(), current_record(), NOW)
        regrant = make_membership(request(), current_record(status="revoked"), NOW)
        self.assertEqual(regrant["status"], "active")

    def test_rejects_bad_subject_scope_role_reference_and_expiration(self):
        bad_inputs = [
            request(subject=" subject"),
            request(farm_id="../other"),
            request(role="owner"),
            request(change_reference="farmer@example.jp"),
            request(expires_at="2026-11-24T00:00:00Z"),
            request(issuer="http://issuer.example"),
        ]
        for value in bad_inputs:
            with self.subTest(value={key: item for key, item in value.items() if key != "subject"}):
                with self.assertRaises(MembershipError):
                    make_membership(value, None, NOW)

    def test_revoke_requires_an_existing_unrevoked_membership(self):
        with self.assertRaisesRegex(MembershipError, "does not exist"):
            make_membership(request("revoke"), None, NOW)
        with self.assertRaisesRegex(MembershipError, "already revoked"):
            make_membership(request("revoke"), current_record(status="revoked"), NOW)

    def test_rejects_mismatched_existing_actor_and_timezone_free_expiry(self):
        with self.assertRaisesRegex(MembershipError, "identity or schema"):
            make_membership(request("revoke"), current_record(actor_hash="0" * 64), NOW)
        with self.assertRaisesRegex(MembershipError, "RFC3339"):
            make_membership(request(expires_at="2027-11-25T00:00:00"), None, NOW)

    def test_preview_reads_current_cloud_record_and_never_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "request.json"
            input_path.write_text(json.dumps(request()), encoding="utf-8")
            with patch.object(admin, "gcloud_access_token", return_value="test-token"), \
                    patch.object(admin, "gcs_object", return_value=(current_record(), "7")), \
                    patch.object(admin, "upload_membership") as upload:
                with self.assertRaisesRegex(MembershipError, "already exists"):
                    admin.prepare_membership(input_path, admin.DEFAULT_BUCKET)
                upload.assert_not_called()

    def test_apply_uses_existing_generation_as_write_precondition(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "request.json"
            input_path.write_text(json.dumps(request("revoke", change_reference="revoke-123")), encoding="utf-8")
            current = current_record()
            with patch.object(admin, "gcloud_access_token", return_value="test-token"), \
                    patch.object(admin, "gcs_object", return_value=(current, "17")), \
                    patch.object(admin, "upload_membership") as upload:
                plan = admin.prepare_membership(input_path, admin.DEFAULT_BUCKET)
                result = admin.apply_membership_plan(plan, plan["summary"]["document_sha256"])
            self.assertTrue(result["applied"])
            upload.assert_called_once()
            self.assertEqual(upload.call_args.args[3], "17")
            self.assertEqual(upload.call_args.args[4]["status"], "revoked")

    def test_apply_requires_exact_reviewed_document_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "request.json"
            input_path.write_text(json.dumps(request()), encoding="utf-8")
            with patch.object(admin, "gcloud_access_token", return_value="test-token"), \
                    patch.object(admin, "gcs_object", return_value=(None, None)), \
                    patch.object(admin, "upload_membership") as upload:
                with self.assertRaisesRegex(MembershipError, "exact preview"):
                    plan = admin.prepare_membership(input_path, admin.DEFAULT_BUCKET)
                    admin.apply_membership_plan(plan, "0" * 64)
                upload.assert_not_called()


if __name__ == "__main__":
    unittest.main()
