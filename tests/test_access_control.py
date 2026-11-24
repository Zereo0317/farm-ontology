from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from farm_ontology.access_control import (
    actor_hash,
    membership_object_name,
    normalize_farm_id,
    validate_membership,
)


class FarmAccessTests(unittest.TestCase):
    NOW = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)
    ISSUER = "https://issuer.example"
    SUBJECT = "user-123"
    FARM_ID = "biratori-a"

    @property
    def fingerprint(self) -> str:
        return actor_hash(self.ISSUER, self.SUBJECT)

    def membership(self) -> dict:
        return {
            "schema_version": 1,
            "farm_id": self.FARM_ID,
            "actor_hash": self.fingerprint,
            "role": "operator",
            "status": "active",
            "granted_at": "2026-11-25T11:00:00Z",
            "expires_at": "2026-12-25T11:00:00Z",
            "updated_at": "2026-11-25T11:00:00Z",
        }

    def test_actor_hash_is_stable_and_membership_key_has_no_raw_subject(self):
        self.assertEqual(
            self.fingerprint,
            "46100edfd3a81243a77da9bfb3a102f6b34d148b4413ae38519113b51277f19d",
        )
        key = membership_object_name(self.FARM_ID, self.fingerprint)
        self.assertEqual(
            key,
            "farms/biratori-a/members/46100edfd3a81243a77da9bfb3a102f6b34d148b4413ae38519113b51277f19d.json",
        )
        self.assertNotIn(self.SUBJECT, key)

    def test_farm_ids_require_canonical_safe_slugs(self):
        self.assertEqual(normalize_farm_id("farm-123"), "farm-123")
        for value in ("../other", "Farm-A", "farm/a", " farm-a", "farm-a ", ""):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_farm_id(value)

    def test_active_membership_requires_exact_actor_tenant_and_expiry(self):
        self.assertEqual(
            validate_membership(
                self.membership(),
                farm_id=self.FARM_ID,
                fingerprint=self.fingerprint,
                at=self.NOW,
            ),
            (True, "active"),
        )
        for farm_id, fingerprint, reason in (
            ("other-farm", self.fingerprint, "membership-binding-mismatch"),
            (self.FARM_ID, "0" * 64, "membership-binding-mismatch"),
        ):
            with self.subTest(farm_id=farm_id):
                self.assertEqual(
                    validate_membership(
                        self.membership(), farm_id=farm_id, fingerprint=fingerprint, at=self.NOW
                    ),
                    (False, reason),
                )

    def test_expired_revoked_malformed_and_future_memberships_deny(self):
        cases = (
            ({**self.membership(), "status": "revoked"}, "membership-not-active"),
            ({**self.membership(), "expires_at": "2026-11-25T11:59:59Z"}, "membership-expired"),
            ({**self.membership(), "expires_at": "2026-10-25T11:00:00Z"}, "membership-born-expired"),
            ({**self.membership(), "role": "owner"}, "unknown-membership-role"),
            ({**self.membership(), "schema_version": True}, "unsupported-membership-schema"),
            ({**self.membership(), "farm_id": "other-farm"}, "membership-binding-mismatch"),
            ({**self.membership(), "updated_at": "2026-11-25T13:00:00Z"}, "membership-from-the-future"),
            ({**self.membership(), "granted_at": "2026-11-25T11:00:00"}, "membership-time-missing-or-naive"),
        )
        for document, reason in cases:
            with self.subTest(reason=reason):
                self.assertEqual(
                    validate_membership(
                        document,
                        farm_id=self.FARM_ID,
                        fingerprint=self.fingerprint,
                        at=self.NOW,
                    ),
                    (False, reason),
                )

    def test_untrusted_clock_cannot_authorize_with_naive_time(self):
        self.assertEqual(
            validate_membership(
                self.membership(),
                farm_id=self.FARM_ID,
                fingerprint=self.fingerprint,
                at=datetime.now() - timedelta(seconds=1),
            ),
            (False, "validation-time-is-naive"),
        )

    def test_invalid_issuer_and_subject_refuse_fingerprinting(self):
        for issuer, subject in (
            ("http://issuer.example", self.SUBJECT),
            ("https://", self.SUBJECT),
            ("https://user:pass@issuer.example", self.SUBJECT),
            (self.ISSUER, ""),
            (self.ISSUER, "bad\nsubject"),
        ):
            with self.subTest(issuer=issuer, subject=subject):
                with self.assertRaises(ValueError):
                    actor_hash(issuer, subject)


if __name__ == "__main__":
    unittest.main()
