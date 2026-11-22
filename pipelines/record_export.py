"""Nightly record export: compose the field record into one archive object.

Pipelines companion to the durable record store. Each run:

1. reads every JSON object of the FIELD RECORD (``field-notes/...`` through the
   same backend the record seam chose),
2. composes them deterministically into one gzipped tar
   (``field-archive/YYYYMMDD/record-snapshot-<RUNSTAMP>-<SHA256>.tar.gz``),
3. creates an immutable per-snapshot manifest row under
   ``field-archive/manifest/YYYYMMDD/`` and
4. records its run in the shared WS2 run log (``job="record-export"``),
   inheriting the 3-strike alert machinery of
   ``farm_ontology.ingest_core`` for free.

Design rules respected:

- Retention/pruning is a WRITTEN POLICY ONLY (deploy/record-retention-
  policy.md); this module never deletes anything, not even old
  snapshots. Pruning is approval-gated infra work.
- Idempotence: the same clock and snapshot content reproduce the same
  names and bytes. Existing different content at a chosen name is refused.
  A retry using a different clock is a separate snapshot. Failures are logged.
- Honesty: the manifest row carries the archive's sha256 and the member
  count so a restore can verify completeness without trusting the tar
  reader. All members are read back once after composition.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from farm_ontology.ingest_core import (  # noqa: E402
    append_run,
    day_stamp,
    describe_backend,
    iso,
    on_run_finished,
    open_pipe_backend,
    run_stamp,
)
from farm_ontology.record_store import GcsBackend, LocalBackend, open_backend  # noqa: E402

ARCHIVE_PREFIX = "field-archive"
MANIFEST_DIR = "manifest"
SNAPSHOT_JOB = "record-export"


def record_backend():
    """The FIELD RECORD backend exactly as the record seam sees it."""
    from farm_ontology.record import record_dir

    return open_backend(record_dir())


def archive_backend():
    """Backend of the ARCHIVE prefix, mirroring record/pipes composition.

    Local: ``<record root>/field-archive`` (not an independent failure domain).
    GCS: a separately configured bucket with ``field-archive`` prefix. Rel paths are identical
    under both, like every other house subtrees.
    """
    from farm_ontology.record import record_dir

    name = os.environ.get("FARM_RECORD_BACKEND", "").strip().lower() or "local"
    if name == "local":
        root = os.environ.get("FARM_RECORD_DIR", "").strip()
        base = Path(root) if root else _REPO_ROOT / "field-notes"
        return LocalBackend(base.parent / ARCHIVE_PREFIX)
    if name == "gcs":
        source_bucket = os.environ.get("FARM_RECORD_BUCKET", "").strip()
        bucket = os.environ.get("FARM_ARCHIVE_BUCKET", "").strip()
        if not source_bucket:
            raise ValueError("FARM_RECORD_BACKEND=gcs requires FARM_RECORD_BUCKET")
        if not bucket or bucket == source_bucket:
            raise ValueError("FARM_ARCHIVE_BUCKET must name a separate archive bucket")
        return GcsBackend(bucket, ARCHIVE_PREFIX)
    raise ValueError(f"FARM_RECORD_BACKEND must be local or gcs, got {name!r}")


def _gather_members(backend) -> list[tuple[str, bytes]]:
    """Every record object as (rel name, bytes); unreadable = loud error.

    De-duplicated on the rel name: the GCS listing under the record
    prefix is recursive while the local glob is not, so both sources
    merge into one sorted set before reading. The result must be
    identical on either backend (tests assert it).
    """
    names: set[str] = set()
    # GCS listing is recursive by prefix; pathlib requires a recursive glob.
    pattern = "**/*.json" if isinstance(backend, LocalBackend) else "*.json"
    names.update(backend.list_paths("", pattern))
    members = []
    for name in sorted(names):
        members.append((name, backend.read_text(name).encode("utf-8")))
    if not members:
        raise ValueError("record export: the record store is empty; refusing to snapshot emptiness")
    return members


def _compose_tar(members: list[tuple[str, bytes]], *, now_epoch: int) -> bytes:
    """Deterministic gzipped tar: sorted members, fixed clock, uid/gid 0."""
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for name, payload in sorted(members):
            info = tarfile.TarInfo(name=name)
            info.size = len(payload)
            info.mtime = now_epoch
            info.uid = 0
            info.gid = 0
            info.mode = 0o644
            info.type = tarfile.REGTYPE
            tar.addfile(info, io.BytesIO(payload))
    packed = io.BytesIO()
    with gzip.GzipFile(fileobj=packed, mode="wb", compresslevel=9, mtime=now_epoch) as gz:
        gz.write(raw.getvalue())
    return packed.getvalue()


def _manifest_rel(day: str) -> str:
    return f"{MANIFEST_DIR}/{day}.ndjson"


def _read_manifest_lines(backend, day: str) -> list[dict]:
    """Read historical daily NDJSON and new immutable per-snapshot rows."""
    rows = []
    try:
        text = backend.read_text(_manifest_rel(day))
    except FileNotFoundError:
        text = ""
    for line in text.splitlines():
        if line.strip():
            rows.append(json.loads(line))
    for rel in backend.list_paths(f"{MANIFEST_DIR}/{day}", "*.json"):
        rows.append(json.loads(backend.read_text(rel)))
    return rows


def _write_once_or_verify(backend, rel: str, body: bytes) -> None:
    """Identical retries succeed; a conflicting existing object is refused."""
    try:
        backend.write_once(rel, body)
    except FileExistsError:
        if backend.read_bytes(rel) != body:
            raise RuntimeError(f"record export: immutable object conflict: {rel}")


def run_export(backend, archive, *, now: datetime, verify_readback: bool = True) -> dict:
    """One export round: snapshot, manifest row, run row, strike upkeep."""
    started = now
    members = _gather_members(backend)
    payload = _compose_tar(members, now_epoch=int(now.timestamp()))
    digest = hashlib.sha256(payload).hexdigest()
    object_name = f"{day_stamp(now)}/record-snapshot-{run_stamp(now)}-{digest}.tar.gz"

    _write_once_or_verify(archive, object_name, payload)
    if verify_readback:
        raw = archive.read_bytes(object_name)
        if hashlib.sha256(raw).hexdigest() != digest:
            raise RuntimeError(
                f"record export: readback of {object_name} does not match the composed bytes"
            )
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tar:
            archived_names = sorted(tar.getnames())
        if archived_names != sorted(name for name, _ in members):
            raise RuntimeError(
                "record export: archived member names differ from the record store listing"
            )

    day = day_stamp(now)
    row = {
        "archive_object": object_name,
        "sha256": digest,
        "members": len(members),
        "bytes": len(payload),
        "backend": describe_backend(backend),
        "written_at": iso(now.replace(microsecond=0)),
        "manifest_note": "one row per snapshot object; snapshots are additive, pruning is policy-gated (deploy/record-retention-policy.md)",
    }
    manifest = f"{MANIFEST_DIR}/{day}/{run_stamp(now)}-{digest}.json"
    _write_once_or_verify(archive, manifest, (json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))
    finished = now

    run = {
        "job": SNAPSHOT_JOB,
        "started": iso(started),
        "finished": iso(finished),
        "ok": True,
        "row_count": len(members),
        "error": None,
    }
    log_rel = append_run(
        open_pipe_backend(),
        job=SNAPSHOT_JOB,
        now=now,
        started=started,
        finished=finished,
        ok=True,
        row_count=len(members),
        archive_object=object_name,
        sha256=digest,
    )
    strikes = on_run_finished(open_pipe_backend(), job=SNAPSHOT_JOB, now=now, run=run)
    return {
        "ok": True,
        "archive_object": object_name,
        "sha256": digest,
        "members": len(members),
        "bytes": len(payload),
        "manifest": manifest,
        "run_log": log_rel,
        "strikes": strikes,
    }


def _record_failure(pipe_backend, *, started: datetime, moment: datetime, error: BaseException) -> None:
    """The failure still owes its run row (house rule) and strike bookkeeping."""
    document = {
        "job": SNAPSHOT_JOB,
        "started": iso(started),
        "finished": iso(moment),
        "ok": False,
        "row_count": 0,
        "error": str(error),
    }
    append_run(
        pipe_backend,
        job=SNAPSHOT_JOB,
        now=moment,
        started=started,
        finished=moment,
        ok=False,
        row_count=0,
        error=str(error),
    )
    on_run_finished(pipe_backend, job=SNAPSHOT_JOB, now=moment, run=document)


def main(argv: list[str] | None = None) -> int:
    """Job entry: ``python -m pipelines.record_export [--now ISO]``.

    The Cloud Scheduler binds 03:30 JST nightly (see
    deploy/nightly-export.md). ``--now`` (ISO-8601, offset REQUIRED)
    injects the run clock for tests and offline drills.
    """
    parser = argparse.ArgumentParser(
        prog="pipelines.record_export", description="Compose the field record into one archive snapshot."
    )
    parser.add_argument("--now", help="injected run time, ISO-8601 with offset (tests/dev)")
    args = parser.parse_args(argv)
    now = (
        datetime.fromisoformat(args.now).astimezone(timezone.utc)
        if args.now
        else datetime.now(timezone.utc)
    )
    pipes = open_pipe_backend()
    try:
        result = run_export(record_backend(), archive_backend(), now=now)
    except Exception as error:  # the failure still owes its run row
        _record_failure(pipes, started=now, moment=datetime.now(timezone.utc), error=error)
        print(json.dumps({"ok": False, "error": str(error)}, indent=2))
        return 1
    printable = dict(result)
    printable.pop("run_log", None)
    print(json.dumps(printable, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
