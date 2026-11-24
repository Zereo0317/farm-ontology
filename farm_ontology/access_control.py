"""Tenant identifiers and membership-record validation.

Memberships bind an OIDC issuer/subject to one farm. Raw identity claims are
never written into field records or membership object names. Storage adapters
must still authenticate the membership source and fail closed on read errors.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit

FARM_ID_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
MEMBERSHIP_ROLES = frozenset({"viewer", "operator", "admin"})
MEMBERSHIP_STATUSES = frozenset({"active", "revoked"})


def normalize_farm_id(value: object) -> str:
    """Validate the opaque storage/API slug; do not silently normalize it."""
    if not isinstance(value, str) or not FARM_ID_RE.fullmatch(value):
        raise ValueError("farm_id must be a lowercase slug using letters, digits, and hyphens")
    return value


def actor_hash(issuer: str, subject: str) -> str:
    """Return a stable pseudonymous identifier for an exact OIDC principal."""
    if not isinstance(issuer, str) or not isinstance(subject, str):
        raise ValueError("OIDC issuer and subject must be strings")
    if issuer != issuer.strip() or subject != subject.strip():
        raise ValueError("OIDC issuer and subject must not contain surrounding whitespace")
    parsed = urlsplit(issuer)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ValueError("OIDC issuer must be an absolute HTTPS issuer URL")
    if not subject or len(subject) > 2048 or any(ord(char) < 0x20 for char in subject):
        raise ValueError("OIDC subject is empty or malformed")
    return hashlib.sha256(f"{issuer}\0{subject}".encode("utf-8")).hexdigest()


def membership_object_name(farm_id: str, fingerprint: str) -> str:
    """GCS object key shared with the web authorization adapter."""
    normalize_farm_id(farm_id)
    if not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
        raise ValueError("actor_hash must be a lowercase SHA-256 hex digest")
    return f"farms/{farm_id}/members/{fingerprint}.json"


def _aware_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    raw = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None and parsed.utcoffset() is not None else None


def validate_membership(
    document: object,
    *,
    farm_id: str,
    fingerprint: str,
    at: datetime | None = None,
) -> tuple[bool, str]:
    """Validate a membership for this exact tenant and actor.

    A malformed object, wrong path binding, revoked status, or expired grant
    denies access. Callers must treat lookup/transport failures as denial too.
    """
    try:
        normalize_farm_id(farm_id)
        if not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
            return False, "invalid-actor-hash"
    except ValueError:
        return False, "invalid-membership-target"
    if not isinstance(document, dict):
        return False, "membership-not-an-object"
    if type(document.get("schema_version")) is not int or document["schema_version"] != 1:
        return False, "unsupported-membership-schema"
    if document.get("farm_id") != farm_id or document.get("actor_hash") != fingerprint:
        return False, "membership-binding-mismatch"
    if document.get("role") not in MEMBERSHIP_ROLES:
        return False, "unknown-membership-role"
    if document.get("status") != "active":
        return False, "membership-not-active"
    granted_at = _aware_datetime(document.get("granted_at"))
    expires_at = _aware_datetime(document.get("expires_at"))
    updated_at = _aware_datetime(document.get("updated_at"))
    if granted_at is None or expires_at is None or updated_at is None:
        return False, "membership-time-missing-or-naive"
    now = at or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        return False, "validation-time-is-naive"
    now = now.astimezone(timezone.utc)
    if granted_at > now or updated_at > now:
        return False, "membership-from-the-future"
    if expires_at <= granted_at:
        return False, "membership-born-expired"
    if expires_at <= now:
        return False, "membership-expired"
    return True, "active"
