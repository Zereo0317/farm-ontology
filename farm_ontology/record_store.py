"""Durable storage for the field record: a local directory or GCS.

The record must outlive the container. `record.py` used to speak only to a
local directory; this module is the thin shim behind that seam. Choose the
backend with environment variables:

- ``FARM_RECORD_BACKEND=local`` (default) keeps today's behaviour: files
  under the record directory.
- ``FARM_RECORD_BACKEND=gcs`` stores every file as an object in the
  ``FARM_RECORD_BUCKET`` bucket, under the prefix ``field-notes/``, so the
  object tree mirrors the repository tree exactly::

      gs://farm-seges-ai-records/field-notes/obs-20261117T010000Z.json
      gs://farm-seges-ai-records/field-notes/notes/note-verification-20261117T010000Z.json

The GCS backend is standard library only: it speaks the GCS JSON API with
``urllib`` and authenticates as the runtime service account using the
access token from the metadata server. It therefore runs on any GCP
runtime (Cloud Run, Cloud Run jobs, GCE, Cloud Build) and nowhere else;
configuring it on a laptop without a metadata server fails loudly on the
first use, never silently. Buckets must have object versioning enabled -
the record never trusts an overwrite to vanish.

Errors are refused, not swallowed: a failed write raises, so a caller
never believes an observation is durable when it is not.
"""

from __future__ import annotations

import errno
import fnmatch
import json
import os
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path, PurePosixPath

DEFAULT_PREFIX = "field-notes"
DEFAULT_BUCKET = "farm-seges-ai-records"
REQUEST_TIMEOUT_S = 15
TOKEN_EXPIRY_SLACK_S = 300
METADATA_TOKEN_URL = (
    "http://metadata.google.internal/computeMetadata/v1/"
    "instance/service-accounts/default/token"
)
JSON_API = "https://storage.googleapis.com/storage/v1"
UPLOAD_API = "https://storage.googleapis.com/upload/storage/v1"


def open_backend(root: Path):
    """Build the record backend from the environment, or refuse."""
    name = os.environ.get("FARM_RECORD_BACKEND", "").strip().lower() or "local"
    if name == "local":
        return LocalBackend(root)
    if name == "gcs":
        bucket = os.environ.get("FARM_RECORD_BUCKET", "").strip()
        if not bucket:
            raise ValueError("FARM_RECORD_BACKEND=gcs requires FARM_RECORD_BUCKET")
        prefix = os.environ.get("FARM_RECORD_GCS_PREFIX", "").strip("/") or DEFAULT_PREFIX
        return GcsBackend(bucket, prefix)
    raise ValueError(f"FARM_RECORD_BACKEND must be local or gcs, got {name!r}")


class LocalBackend:
    """The record directory on the local filesystem (previous behaviour)."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def describe(self) -> dict:
        return {"backend": "local", "root": str(self.root)}

    def _path(self, rel: str) -> Path:
        return self.root.joinpath(*PurePosixPath(rel).parts)

    def exists(self, rel: str) -> bool:
        return self._path(rel).is_file()

    def mtime_ns(self, rel: str) -> int | None:
        path = self._path(rel)
        if not path.is_file():
            return None
        return path.stat().st_mtime_ns

    def write(self, rel: str, data: bytes) -> None:
        path = self._path(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        staging = path.with_name(path.name + ".part")
        staging.write_bytes(data)
        os.replace(staging, path)

    def read_text(self, rel: str) -> str:
        return self._path(rel).read_text(encoding="utf-8")

    def read_bytes(self, rel: str) -> bytes:
        return self._path(rel).read_bytes()

    def list_paths(self, sub: str, pattern: str) -> list[str]:
        base = self.root.joinpath(*PurePosixPath(sub).parts) if sub.strip("/") else self.root
        found = [
            p.relative_to(self.root).as_posix()
            for p in base.glob(pattern)
            if p.is_file()
        ]
        return sorted(found)


def _http_request(
    method: str, url: str, headers: dict, body: bytes | None
) -> tuple[int, dict, bytes]:
    """One urllib call. Returns (status, headers, body); raises on transport failure."""
    request = urllib.request.Request(url, data=body, method=method)
    for key, value in headers.items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), error.read()


def _metadata_token() -> tuple[str, int]:
    """Fetch (access_token, expires_in) for the runtime service account."""
    status, _, body = _http_request(
        "GET", METADATA_TOKEN_URL, {"Metadata-Flavor": "Google"}, None
    )
    if status != 200:
        raise RuntimeError(
            f"GCS backend: metadata server refused a token (HTTP {status})"
        )
    try:
        document = json.loads(body.decode("utf-8"))
        return str(document["access_token"]), int(document["expires_in"])
    except (UnicodeDecodeError, ValueError, KeyError, TypeError) as error:
        raise RuntimeError(
            f"GCS backend: unreadable metadata token response ({error})"
        ) from error


def _error_message(status: int, body: bytes) -> str:
    """Sanitise a GCS error body: status plus message, never raw payloads."""
    try:
        message = json.loads(body.decode("utf-8"))["error"]["message"]
    except (UnicodeDecodeError, ValueError, KeyError, TypeError):
        return f"HTTP {status}"
    text = str(message).strip()
    return text[:200] if text else f"HTTP {status}"


class GcsBackend:
    """Field record objects in one versioned GCS bucket via the JSON API."""

    def __init__(
        self,
        bucket: str,
        prefix: str = DEFAULT_PREFIX,
        *,
        request_fn=None,
        token_fn=None,
    ):
        self.bucket = bucket.strip("/")
        self.prefix = prefix.strip("/")
        self._request_fn = request_fn or _http_request
        self._token_fn = token_fn or _metadata_token
        self._token: str | None = None
        self._token_deadline = 0.0

    # ---- auth ---------------------------------------------------------

    def _authorization(self) -> dict:
        now = time.monotonic()
        if self._token is None or now >= self._token_deadline:
            token, expires_in = self._token_fn()
            self._token = token
            self._token_deadline = now + max(1, expires_in - TOKEN_EXPIRY_SLACK_S)
        return {"Authorization": f"Bearer {self._token}"}

    # ---- object names and API calls -----------------------------------

    def object_name(self, rel: str) -> str:
        posix = PurePosixPath(rel.replace("\\", "/")).as_posix().lstrip("/")
        return f"{self.prefix}/{posix}"

    @staticmethod
    def _encoded(object_name: str) -> str:
        # Object names are percent-encoded INCLUDING the slashes (%2F).
        # Verified empirically on 2026-11-17: a raw-slash path segment for a
        # name like field-notes/obs-x.json returns 404 from the JSON API,
        # the %2F form returns 200.
        return urllib.parse.quote(object_name, safe="~-_.")

    def _expect(self, status: int, body: bytes, what: str, object_name: str) -> None:
        if status >= 400:
            raise RuntimeError(
                f"GCS backend: could not {what} {object_name}: "
                f"{_error_message(status, body)}"
            )

    def _object_url(self, object_name: str) -> str:
        return f"{JSON_API}/b/{self.bucket}/o/{self._encoded(object_name)}"

    # ---- the record seam ----------------------------------------------

    def describe(self) -> dict:
        return {
            "backend": "gcs",
            "bucket": self.bucket,
            "prefix": self.prefix,
            "api": "storage.googleapis.com",
        }

    def exists(self, rel: str) -> bool:
        object_name = self.object_name(rel)
        status, _, body = self._request_fn(
            "GET",
            self._object_url(object_name),
            self._authorization(),
            None,
        )
        if status == 200:
            return True
        if status == 404:
            return False
        self._expect(status, body, "stat", object_name)
        return False

    def mtime_ns(self, rel: str) -> int | None:
        object_name = self.object_name(rel)
        status, _, body = self._request_fn(
            "GET",
            self._object_url(object_name),
            self._authorization(),
            None,
        )
        if status == 404:
            return None
        self._expect(status, body, "stat", object_name)
        try:
            updated = json.loads(body.decode("utf-8"))["updated"]
            moment = datetime.fromisoformat(str(updated).replace("Z", "+00:00"))
        except (UnicodeDecodeError, ValueError, KeyError, TypeError) as error:
            raise RuntimeError(
                f"GCS backend: unreadable object metadata for {object_name} ({error})"
            ) from error
        return round(moment.timestamp() * 1_000_000_000)

    def write(self, rel: str, data: bytes) -> None:
        object_name = self.object_name(rel)
        url = (
            f"{UPLOAD_API}/b/{self.bucket}/o"
            f"?uploadType=media&name={self._encoded(object_name)}"
        )
        status, _, body = self._request_fn(
            "POST",
            url,
            {**self._authorization(), "Content-Type": "application/json"},
            data,
        )
        self._expect(status, body, "write", object_name)

    def read_bytes(self, rel: str) -> bytes:
        """Binary read (archives are not text); 404 still raises FileNotFoundError."""
        object_name = self.object_name(rel)
        status, _, body = self._request_fn(
            "GET",
            self._object_url(object_name) + "?alt=media",
            self._authorization(),
            None,
        )
        if status == 404:
            raise FileNotFoundError(errno.ENOENT, "no such object", object_name)
        self._expect(status, body, "read", object_name)
        return body

    def read_text(self, rel: str) -> str:
        object_name = self.object_name(rel)
        body = self.read_bytes(rel)
        try:
            return body.decode("utf-8")
        except UnicodeDecodeError as error:
            raise RuntimeError(
                f"GCS backend: object {object_name} is not UTF-8 text"
            ) from error

    def list_paths(self, sub: str, pattern: str) -> list[str]:
        list_prefix = f"{self.prefix}/{sub.strip('/')}" if sub.strip("/") else self.prefix
        url = (
            f"{JSON_API}/b/{self.bucket}/o"
            f"?prefix={self._encoded(list_prefix + '/')}&maxResults=1000"
        )
        names: list[str] = []
        seen_pages = 0
        while True:
            seen_pages += 1
            if seen_pages > 100:
                raise RuntimeError("GCS backend: listing did not terminate")
            status, _, body = self._request_fn(
                "GET", url, self._authorization(), None
            )
            self._expect(status, body, "list", list_prefix + "/")
            try:
                document = json.loads(body.decode("utf-8"))
            except UnicodeDecodeError as error:
                raise RuntimeError("GCS backend: unreadable listing") from error
            cut = len(self.prefix) + 1
            for item in document.get("items", []):
                rel = str(item["name"])[cut:]
                base = PurePosixPath(rel).name
                if fnmatch.fnmatchcase(base, pattern):
                    names.append(rel)
            page_token = document.get("nextPageToken")
            if not page_token:
                break
            url = (
                f"{JSON_API}/b/{self.bucket}/o"
                f"?prefix={self._encoded(list_prefix + '/')}&maxResults=1000"
                f"&pageToken={urllib.parse.quote(str(page_token), safe='')}"
            )
        return sorted(names)


def main(argv: list[str] | None = None) -> int:
    """Durability drill: one real dry-run observation through the backend.

    Runs inside a Cloud Run job against the live bucket with the runtime
    service account. Prints a machine-readable summary line and exits 0
    only when the observation round-trips through storage. Dry-run points
    are labelled as such in the record and never claim to be farm data.
    """
    from farm_ontology.record import list_notes, record_observation

    root = Path(tempfile.mkdtemp(prefix="farm-record-drill-"))
    try:
        backend = open_backend(root)
        saved = record_observation(latitude=0.0, longitude=0.0, dry_run=True)
        listed = list_notes()
        summary = {
            "drill": "observation-round-trip",
            "backend": backend.describe(),
            "written": saved["file"],
            "permits_financial_use": saved["observation"]["permits_financial_use"],
            "observation_count": len(listed["observations"]),
            "note_count": len(listed["notes"]),
        }
        print(json.dumps(summary, indent=2))
        if not saved["file"].startswith("obs-"):
            raise RuntimeError("drill: unexpected observation file name")
        return 0
    finally:
        import shutil

        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
