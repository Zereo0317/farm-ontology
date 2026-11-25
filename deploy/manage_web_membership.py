"""Review and update one farm web membership using the active gcloud identity.

Input is a private JSON file so OIDC subjects never appear in command history.
The command previews by default; pass --apply to write with a GCS generation
precondition so a concurrent membership edit cannot be silently overwritten.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_BUCKET = "farm-seges-ai-access-control"
GCS_API = "https://storage.googleapis.com/storage/v1"
GCS_UPLOAD_API = "https://storage.googleapis.com/upload/storage/v1"
MAX_MEMBERSHIP_BYTES = 32 * 1024
FARM_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{2,127}$")
RFC3339 = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?"
    r"(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$"
)


class MembershipError(ValueError):
    """A membership request or remote membership is invalid."""


def parse_time(value: Any, label: str) -> dt.datetime:
    if not isinstance(value, str) or not RFC3339.fullmatch(value):
        raise MembershipError(f"{label} must be an RFC3339 timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MembershipError(f"{label} must be an RFC3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise MembershipError(f"{label} must include a timezone")
    return parsed.astimezone(dt.timezone.utc)


def format_time(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def actor_hash(issuer: Any, subject: Any) -> str:
    if not isinstance(issuer, str) or not issuer.startswith("https://"):
        raise MembershipError("issuer must be the exact HTTPS OIDC issuer")
    normalized_issuer = issuer.rstrip("/")
    if not isinstance(subject, str) or not subject or subject.strip() != subject or "\x00" in subject:
        raise MembershipError("subject must be the exact non-empty OIDC subject")
    return hashlib.sha256(f"{normalized_issuer}\0{subject}".encode("utf-8")).hexdigest()


def membership_path(farm_id: str, digest: str) -> str:
    if not isinstance(farm_id, str) or not FARM_ID.fullmatch(farm_id):
        raise MembershipError("farm_id must use lowercase letters, digits, and interior hyphens")
    if not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise MembershipError("actor hash is invalid")
    return f"farms/{farm_id}/members/{digest}.json"


def validate_current(value: Any, farm_id: str, digest: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MembershipError("existing membership must be a JSON object")
    if value.get("schema_version") != 1 or value.get("farm_id") != farm_id or value.get("actor_hash") != digest:
        raise MembershipError("existing membership identity or schema does not match")
    if not isinstance(value.get("role"), str) or value["role"] not in {"viewer", "operator", "admin"}:
        raise MembershipError("existing membership role is invalid")
    if not isinstance(value.get("status"), str) or value["status"] not in {"active", "revoked"}:
        raise MembershipError("existing membership status is invalid")
    granted_at = parse_time(value.get("granted_at"), "granted_at")
    expires_at = parse_time(value.get("expires_at"), "expires_at")
    updated_at = parse_time(value.get("updated_at"), "updated_at")
    if expires_at <= granted_at or updated_at < granted_at:
        raise MembershipError("existing membership timestamps violate grant chronology")
    return value


def make_membership(request: Any, current: Any, now: dt.datetime | None = None) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise MembershipError("input must be a JSON object")
    action = request.get("action")
    farm_id = request.get("farm_id")
    if not isinstance(farm_id, str) or not FARM_ID.fullmatch(farm_id):
        raise MembershipError("farm_id must use lowercase letters, digits, and interior hyphens")
    digest = actor_hash(request.get("issuer"), request.get("subject"))
    membership_path(farm_id, digest)
    now = now or dt.datetime.now(dt.timezone.utc)
    now = now.astimezone(dt.timezone.utc)

    if current is not None:
        current = validate_current(current, farm_id, digest)

    if action == "grant":
        role = request.get("role")
        if not isinstance(role, str) or role not in {"viewer", "operator", "admin"}:
            raise MembershipError("grant role must be viewer, operator, or admin")
        expires = parse_time(request.get("expires_at"), "expires_at")
        if expires <= now:
            raise MembershipError("expires_at must be in the future")
        reference = request.get("change_reference")
        if not isinstance(reference, str) or not REFERENCE.fullmatch(reference):
            raise MembershipError("change_reference must be a non-PII authorization record ID")
        if current is not None and current["status"] == "active" and parse_time(current["expires_at"], "expires_at") > now:
            raise MembershipError("an unexpired active membership already exists; revoke it before replacing it")
        return {
            "schema_version": 1,
            "farm_id": farm_id,
            "actor_hash": digest,
            "role": role,
            "status": "active",
            "granted_at": format_time(now),
            "expires_at": format_time(expires),
            "updated_at": format_time(now),
            "change_reference": reference,
        }

    if action == "revoke":
        reference = request.get("change_reference")
        if not isinstance(reference, str) or not REFERENCE.fullmatch(reference):
            raise MembershipError("change_reference must be a non-PII revocation record ID")
        if current is None:
            raise MembershipError("membership does not exist; nothing can be revoked")
        if current["status"] == "revoked":
            raise MembershipError("membership is already revoked")
        revoked = dict(current)
        revoked["status"] = "revoked"
        revoked["updated_at"] = format_time(now)
        revoked["change_reference"] = reference
        return revoked

    raise MembershipError("action must be grant or revoke")


def gcloud_access_token() -> str:
    try:
        result = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise MembershipError("could not obtain an access token from the active gcloud login") from exc
    token = result.stdout.strip()
    if not token or any(character.isspace() for character in token):
        raise MembershipError("gcloud returned an invalid access token")
    return token


def gcs_request(token: str, url: str, method: str = "GET", body: bytes | None = None) -> bytes | None:
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = response.read(MAX_MEMBERSHIP_BYTES + 1)
            if len(data) > MAX_MEMBERSHIP_BYTES:
                raise MembershipError("membership object exceeds the 32 KiB safety limit")
            return data
    except urllib.error.HTTPError as exc:
        if exc.code == 404 and method == "GET":
            return None
        raise MembershipError(f"Cloud Storage request failed with HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise MembershipError("Cloud Storage could not be reached") from exc


def gcs_object(token: str, bucket: str, path: str) -> tuple[dict[str, Any] | None, str | None]:
    encoded = urllib.parse.quote(path, safe="")
    metadata_url = f"{GCS_API}/b/{urllib.parse.quote(bucket, safe='')}/o/{encoded}"
    metadata = gcs_request(token, metadata_url)
    if metadata is None:
        return None, None
    try:
        generation = json.loads(metadata).get("generation")
        if not isinstance(generation, str) or not generation.isdigit():
            raise MembershipError("Cloud Storage returned an invalid object generation")
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError) as exc:
        raise MembershipError("Cloud Storage returned invalid object metadata") from exc
    media = gcs_request(token, metadata_url + "?alt=media")
    if media is None:
        raise MembershipError("membership disappeared while it was being read")
    try:
        current = json.loads(media)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MembershipError("existing membership is not valid UTF-8 JSON") from exc
    return current, generation


def upload_membership(token: str, bucket: str, path: str, generation: str | None, document: dict[str, Any]) -> None:
    query = urllib.parse.urlencode(
        {
            "uploadType": "media",
            "name": path,
            "ifGenerationMatch": generation or "0",
        }
    )
    url = f"{GCS_UPLOAD_API}/b/{urllib.parse.quote(bucket, safe='')}/o?{query}"
    body = serialize_membership(document)
    response = gcs_request(token, url, method="POST", body=body)
    if response is None:
        raise MembershipError("Cloud Storage did not confirm the membership write")


def serialize_membership(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def load_request(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        if len(raw) > MAX_MEMBERSHIP_BYTES:
            raise MembershipError("input file exceeds the 32 KiB safety limit")
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MembershipError("input file could not be read as UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise MembershipError("input must be a JSON object")
    return value


def prepare_membership(input_path: Path, bucket: str) -> dict[str, Any]:
    if bucket != DEFAULT_BUCKET:
        raise MembershipError(f"bucket is fixed to {DEFAULT_BUCKET}")
    request = load_request(input_path)
    digest = actor_hash(request.get("issuer"), request.get("subject"))
    path = membership_path(request.get("farm_id", ""), digest)
    token = gcloud_access_token()
    current, generation = gcs_object(token, bucket, path)
    document = make_membership(request, current)
    document_sha256 = hashlib.sha256(serialize_membership(document)).hexdigest()
    return {
        "_token": token,
        "_generation": generation,
        "_document": document,
        "_path": path,
        "summary": {
        "action": request["action"],
        "farm_id": request["farm_id"],
        "actor_hash": digest,
        "object": f"gs://{bucket}/{path}",
        "status": document["status"],
        "role": document["role"],
        "change_reference": document["change_reference"],
        "updated_at": document["updated_at"],
        "expires_at": document["expires_at"],
        "document_sha256": document_sha256,
        "applied": False,
        },
    }


def apply_membership_plan(plan: dict[str, Any], confirmed_sha256: str) -> dict[str, Any]:
    summary = plan["summary"]
    if not isinstance(confirmed_sha256, str) or confirmed_sha256 != summary["document_sha256"]:
        raise MembershipError("membership write requires typing the exact preview SHA-256")
    upload_membership(plan["_token"], DEFAULT_BUCKET, plan["_path"], plan["_generation"], plan["_document"])
    return {**summary, "applied": True}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="private JSON request file; never pass OIDC subject as a CLI argument")
    parser.add_argument("--bucket", default=DEFAULT_BUCKET, help="dedicated farm access-control bucket")
    parser.add_argument("--apply", action="store_true", help="preview then require typing the exact document SHA-256 before writing")
    args = parser.parse_args(argv)
    try:
        plan = prepare_membership(args.input, args.bucket)
        print(json.dumps(plan["summary"], sort_keys=True))
        if not args.apply:
            return 0
        confirmation = input("Type the exact document_sha256 above to apply this membership change: ").strip()
        result = apply_membership_plan(plan, confirmation)
    except MembershipError as exc:
        print(f"membership update refused: {exc}", file=sys.stderr)
        return 2
    except (EOFError, KeyboardInterrupt):
        print("membership update cancelled", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
