"""WS2 ingestion plumbing: durable pipes, run-log rows, strike alerts.

Every scheduled worker (``pipelines/run_worker.py``) funnels through THIS
module. The rules:

1. Storage goes through the existing record-store seam
   (``farm_ontology.record_store``: local directory or the GCS bucket
   ``farm-seges-ai-records``). Pipeline artefacts are siblings of the
   field record, never new storage infrastructure::

       <backend root>/pipelines/run-log/<timestamp>-<id>-<job>.json
       <backend root>/pipelines/alerts/YYYYMMDD-<job>-ALERT.json
       <backend root>/pipelines/state/planet-last.json
       <backend root>/pipelines/state/hazard-seen-warnings.json
       <backend root>/pipelines/<kind>/<row>.json

   With ``FARM_RECORD_BACKEND=gcs`` those live in the durable bucket and
   survive instance recycle exactly like the field record. Locally the
   default root is ``~/.farm-ontology`` (override with
   ``FARM_PIPE_ROOT``); tests inject a ``LocalBackend(tmp)`` directly.

2. Every run of every job appends one ingest-run row with the fixed
   evidence schema: ``job, started, finished, ok, row_count, error``.
   A failure never skips its row: the row IS the audit trail.

3. Three consecutive failed runs of one job write
   ``alerts/<day>-<job>-ALERT.json``. THE ALERT ROW IS THE TRIGGER
   ARTIFACT. Notification delivery (email, webhook, the infra HALT
   policy of deploy/GCP_SETUP.md) intentionally does NOT live here: this
   module has no credentials, sends nothing, and fetches nothing. The
   infra watchdog can watch the ``alerts/`` prefix later and translate a
   standing alert into whatever channel policy chooses.

4. Data deduplication. Weather equal-value rows, Planet scene-id deltas,
   and hazard warning signatures prevent duplicate data rows. Every execution
   is retained in the run log, including retries of identical data.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from farm_ontology.record_store import GcsBackend, LocalBackend

PIPE_SEGMENT = "pipelines"
RUN_LOG = "run-log"
ALERTS = "alerts"
STATE = "state"

CONSECUTIVE_FAILURE_ALERT_AT = 3
#: How much of the failure window rides inside an ALERT row.
ALERT_EVIDENCE_WINDOW = 5

#: Identity of the durable pipeline store, echoed into run rows.
OWNER_PROJECT = "seges-ai"
OWNER_BUCKET = "farm-seges-ai-records"

#: Upper bound of the process-wide row cache (singleflight); cleared
#: wholesale when exceeded — rows are cheap to re-read on demand.
_ROW_READ_CACHE_LIMIT = 512

#: The status fast-path reads rows concurrently (I/O-bound waits, no
#: GIL contention): a modest pool per compose call.
ROW_READ_WORKERS = 8


# ---------------------------------------------------------------- clocks


def utc_now_stub() -> datetime:
    """Injected-clock default; production callers pass ``now`` explicitly."""
    raise ValueError(
        "workers must pass an injected now; this default exists only so the"
        " signature is explicit"
    )


def iso(at: datetime) -> str:
    return at.astimezone(timezone.utc).isoformat()


def day_stamp(at: datetime) -> str:
    return at.astimezone(timezone.utc).strftime("%Y%m%d")


def run_stamp(at: datetime) -> str:
    return at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def rel_name(rel: str) -> str:
    """Final filename of a backend-relative POSIX path."""
    return rel.replace("\\", "/").rsplit("/", 1)[-1]


def safe_name(text: str) -> str:
    """Filenames carry only POSIX-safe characters; the rest collapses."""
    cleaned = "".join(
        character if character.isalnum() or character in "._-" else "-"
        for character in str(text)
    )
    return cleaned.strip("-.") or "unnamed"


# --------------------------------------------------------------- backend


def open_pipe_backend():
    """Pipeline backend from the environment, mirroring record_store.

    Resolution order (task-9 lesson: a HALF-configured env must not
    silently read an empty shadow store — that is exactly how prod
    revision 00054 reported every job as ``no ingest-run row exists``
    while the workers were correctly filling the bucket):

    - ``FARM_RECORD_BACKEND=gcs`` → GCS bucket ``FARM_RECORD_BUCKET``
      (required) under the ``pipelines`` prefix;
    - ``FARM_RECORD_BACKEND=local`` WITH ``FARM_RECORD_BUCKET`` set →
      REFUSED loudly: the env declares a durable bucket but asks for a
      local store, and the resulting blindness (empty local read) is the
      failure mode this module exists to prevent — unset one of the two;
    - ``FARM_RECORD_BACKEND=local`` alone → local, root preference:
      ``FARM_PIPE_ROOT`` → ``FARM_RECORD_DIR/pipelines`` (ride the same
      record-directory seam the services and Dockerfile configure;
      Dockerfile sets ``FARM_RECORD_DIR=/tmp/farm-records``, which beats
      the useless ``/nonexistent`` home of the container's system user);
    - backend UNSET but ``FARM_RECORD_BUCKET`` set → GCS: the bucket var
      IS the durability declaration;
    - both unset → local at ``~/.farm-ontology/pipelines`` (laptop).

    Rel paths are IDENTICAL under both backends (``run-log/...``,
    ``alerts/...``, ``state/...``).
    """
    backend_name = os.environ.get("FARM_RECORD_BACKEND", "").strip().lower()
    bucket = os.environ.get("FARM_RECORD_BUCKET", "").strip()
    if backend_name == "gcs":
        if not bucket:
            raise ValueError("FARM_RECORD_BACKEND=gcs requires FARM_RECORD_BUCKET")
        return GcsBackend(bucket, PIPE_SEGMENT)
    if backend_name == "local":
        if bucket:
            raise ValueError(
                "FARM_RECORD_BACKEND=local contradicts FARM_RECORD_BUCKET="
                f"{bucket}: the env declares a durable record bucket, so a "
                "local pipeline store would silently read empty. Unset "
                "FARM_RECORD_BUCKET or set FARM_RECORD_BACKEND=gcs."
            )
        return LocalBackend(_local_pipe_root())
    if backend_name == "":
        if bucket:
            return GcsBackend(bucket, PIPE_SEGMENT)
        return LocalBackend(_local_pipe_root())
    raise ValueError(f"FARM_RECORD_BACKEND must be local or gcs, got {backend_name!r}")


def _local_pipe_root() -> Path:
    """Where the local pipelines subtree lives: FARM_PIPE_ROOT, else the
    record dir seam (FARM_RECORD_DIR), else home."""
    explicit = os.environ.get("FARM_PIPE_ROOT", "").strip()
    if explicit:
        return Path(explicit) / PIPE_SEGMENT
    record_dir = os.environ.get("FARM_RECORD_DIR", "").strip()
    if record_dir:
        return Path(record_dir) / PIPE_SEGMENT
    return Path.home() / ".farm-ontology" / PIPE_SEGMENT


def local_pipe_backend(root: Path) -> LocalBackend:
    """A local backend whose rel paths mirror the GCS layout exactly.

    ``run-log/...``, ``alerts/...``, ``state/...`` are relative to the
    pipelines subtree; the env backend and this helper place that subtree
    identically (``root/pipelines/...`` on disk). Tests use this helper,
    never bare LocalBackend, so layouts cannot drift between dev and
    production.
    """
    return LocalBackend(Path(root) / PIPE_SEGMENT)


def describe_backend(backend) -> dict:
    try:
        described = backend.describe()
    except AttributeError:
        described = {"backend": "unknown"}
    return described


# ------------------------------------------------------------------ i/o


def read_json(backend, rel: str) -> dict | None:
    """One JSON document, or None when absent. Corrupt content raises."""
    try:
        return json.loads(backend.read_text(rel))
    except FileNotFoundError:
        return None


def write_json(backend, rel: str, document: dict) -> str:
    """Write one document; ANY write through this seam invalidates the
    process-wide ingest-status response cache (task-15 contract: operators
    never see strikes/runs older than the write that changed them)."""
    written = rel
    backend.write(rel, (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    invalidate_ingest_status_cache(reason=f"write:{rel}")
    return written


# ------------------------------------------- row cache (singleflight+TTLish)


_ROW_CACHE: dict[str, dict | None] = {}


def clear_row_caches() -> None:
    """Flush the row cache (tests, ops tooling; identical-identity stores
    reseeded in-process must not inherit prior rows)."""
    _ROW_CACHE.clear()


def _row_cache_key(backend, name: str) -> str:
    try:
        ident = json.dumps(backend.describe(), sort_keys=True, default=str)
    except Exception:  # noqa: BLE001 - identity is best-effort
        ident = "unknown-backend"
    return f"{ident}|{name}"


def read_row_once(backend, name: str) -> dict | None:
    """Read one row document, deduplicating repeated reads process-wide.

    The same run-log row is asked for by strikes, evidence windows, and
    every status compose; without this cache each asker pays its own GET.
    Corrupt content raises (read_json discipline); FileNotFoundError
    caches the absence too.
    """
    key = _row_cache_key(backend, name)
    if key in _ROW_CACHE:
        return _ROW_CACHE[key]
    row = read_json(backend, name)
    if len(_ROW_CACHE) >= _ROW_READ_CACHE_LIMIT:
        _ROW_CACHE.clear()
    _ROW_CACHE[key] = row
    return row


def read_rows_parallel(backend, names: list[str]) -> dict[str, dict | None]:
    """Several row GETs concurrently; one storage GET per name (warm rows
    are answered from :func:`read_row_once` and cost no round trip)."""
    if not names:
        return {}
    wanted = {name: _row_cache_key(backend, name) for name in names}
    unresolved = [name for name, key in wanted.items() if key not in _ROW_CACHE]
    resolved: dict[str, dict | None] = {
        name: _ROW_CACHE[wanted[name]] for name in wanted if name not in unresolved
    }
    if unresolved:
        with ThreadPoolExecutor(max_workers=max(1, min(ROW_READ_WORKERS, len(unresolved)))) as pool:
            fetched = list(pool.map(lambda name: read_json(backend, name), unresolved))
        for name, row in zip(unresolved, fetched):
            if len(_ROW_CACHE) >= _ROW_READ_CACHE_LIMIT:
                _ROW_CACHE.clear()
            _ROW_CACHE[wanted[name]] = row
            resolved[name] = row
    return resolved


# ------------------------------------------------------------------ rows


def job_rows(backend, kind: str, prefix: str) -> list[dict]:
    """Existing rows of one kind (sorted, decode failures surface)."""
    rows = []
    for name in backend.list_paths(kind, prefix + "*.json"):
        document = read_json(backend, name)
        if document is not None:
            rows.append({"file": name, **document})
    return rows


def already_equal_value_row(rows: list[dict], incoming: dict, keys: tuple[str, ...]) -> bool:
    """True when an existing row equals the incoming one on every key."""
    wanted = tuple(incoming.get(key) for key in keys)
    for row in rows:
        if tuple(row.get(key) for key in keys) == wanted:
            return True
    return False


def _attach_run_meta(document: dict, *, job: str, now: datetime) -> dict:
    return {
        **document,
        "job": job,
        "written_at": iso(now),
        "permits_financial_use": False,
        "use_class": "Screening",
        "record_owner": OWNER_PROJECT,
    }


def write_data_row(backend, kind: str, name: str, row: dict, *, job: str, now: datetime) -> str:
    return write_json(backend, f"{kind}/{name}", _attach_run_meta(row, job=job, now=now))


# ------------------------------------------------- status response cache


#: Owned HERE because every writer in this module must be able to
#: invalidate it; composed/consumed by ``farm_ontology.ingest_status``.
#: Slots are KEYED BY BACKEND IDENTITY so concurrent distinct stores
#: (tests, tooling pointing at tmp dirs) never see each other's rows.
STATUS_CACHE_TTL_S = 60.0
_STATUS_CACHE: dict[str, dict] = {}
#: Slot upper bound (test/tmp backends accumulate); wholesale clear beyond.
_STATUS_CACHE_SLOT_LIMIT = 64
#: Process-wide invalidation counter (mutable cell; tests may observe it).
_CACHE_GENERATION = [0]

#: Monotonic clock indirection: tests inject to jump the TTL.
status_clock = time.monotonic


def _cache_slot_key(backend) -> str:
    try:
        return json.dumps(backend.describe(), sort_keys=True, default=str)
    except Exception:  # noqa: BLE001 - identity is best-effort
        return "unknown-backend"


def invalidate_ingest_status_cache(reason: str = "unspecified") -> None:
    """Drop ALL cached /farm/ingest-status payloads (any writer may call;
    a writer cannot know which backend identity a reader holds, so the
    conservative whole-flush guarantees the operator-visibility contract)."""
    for slot in _STATUS_CACHE.values():
        slot["payload"] = None
        slot["invalidated_by"] = reason
    _CACHE_GENERATION[0] += 1


def status_cache_generation() -> int:
    return _CACHE_GENERATION[0]


def cached_status_payload(backend):
    """(payload, age_seconds, hit) from the TTL cache, or (None, .., False)."""
    slot = _STATUS_CACHE.get(_cache_slot_key(backend))
    if not slot or slot["payload"] is None:
        return None, 0.0, False
    age = status_clock() - slot["built_at_mono"]
    if age >= STATUS_CACHE_TTL_S:
        return None, age, False
    return slot["payload"], age, True


def store_status_payload(backend, payload: dict) -> None:
    if len(_STATUS_CACHE) >= _STATUS_CACHE_SLOT_LIMIT:
        _STATUS_CACHE.clear()
    key = _cache_slot_key(backend)
    previous_builds = _STATUS_CACHE.get(key, {}).get("builds", 0)
    _STATUS_CACHE[key] = {
        "payload": payload,
        "built_at_mono": status_clock(),
        "invalidated_by": None,
        "builds": previous_builds + 1,
    }


# --------------------------------------------------------------- run log


def log_rel(day: str, job: str) -> str:
    return f"{RUN_LOG}/{day}-{job}.json"


def append_run(
    backend,
    *,
    job: str,
    now: datetime,
    started: datetime,
    finished: datetime,
    ok: bool,
    row_count: int,
    error: str | None = None,
    **extra,
) -> str:
    """Append an immutable run row, including repeated same-day executions.

    Fixed schema first, evidence extras after. This row is written even
    when the job raised; it is the durable success/failure audit trail
    demanded by roadmap WS2.5.
    """
    document = {
        "job": job,
        "started": iso(started),
        "finished": iso(finished),
        "ok": bool(ok),
        "row_count": int(row_count),
        "error": (str(error)[:400] if error else None),
        **extra,
    }
    # Include time and a unique id; keep the job suffix for legacy readers.
    stamp = now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    identity = f"{time.time_ns():020d}-{uuid.uuid4().hex}"
    written = f"{RUN_LOG}/{stamp}-{identity}-{safe_name(job)}.json"
    backend.write_once(written, (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    invalidate_ingest_status_cache(reason=f"append_run:{job}")
    return written


def run_rows(backend, job: str | None = None) -> list[dict]:
    """Run rows oldest-first, optionally for one job."""
    suffix = f"-{job}.json" if job else ".json"
    rows = []
    for name in backend.list_paths(RUN_LOG, "*.json"):
        if job is not None and not name.endswith(suffix):
            continue
        document = read_json(backend, name)
        if document is not None:
            rows.append({"file": rel_name(name), **document, "file_rel": name})
    rows.sort(key=lambda row: row["file_rel"])
    return rows


def consecutive_failures(backend, job: str) -> int:
    """Failed rows since the newest success (execution-order scan)."""
    streak = 0
    for row in reversed(run_rows(backend, job)):
        if row["ok"]:
            break
        streak += 1
    return streak


# ---------------------------------------------------------------- alerts


def alert_rel(day: str, job: str, suffix: str = "ALERT") -> str:
    return f"{ALERTS}/{day}-{job}-{suffix}.json"


def evidence_window(backend, job: str) -> list[dict]:
    """Most recent run rows (newest first), capped, for alert evidence."""
    return [
        {
            "file": row["file"],
            "started": row["started"],
            "finished": row["finished"],
            "ok": row["ok"],
            "row_count": row["row_count"],
            "error": row["error"],
        }
        for row in list(reversed(run_rows(backend, job)))[:ALERT_EVIDENCE_WINDOW]
    ]


def on_run_finished(
    backend, *, job: str, now: datetime, run: dict
) -> dict:
    """Strike bookkeeping after any run: success resets, failure counts.

    Fires (or refreshes, dated) the consecutive-failure ALERT at the
    threshold, carrying the evidence trail. The dated alert is refreshed
    on repeated failures; execution evidence remains append-only.
    """
    streak = consecutive_failures(backend, job)
    if run["ok"] or streak < CONSECUTIVE_FAILURE_ALERT_AT:
        return {"consecutive_failures": streak, "alert": None}
    day = day_stamp(now)
    alert = {
        "alert": "consecutive-failures",
        "job": job,
        "day": day,
        "threshold": CONSECUTIVE_FAILURE_ALERT_AT,
        "consecutive_failures": streak,
        "evidence": evidence_window(backend, job),
        "latest_error": (run.get("error") or "")[:400],
        "alert_written_at": iso(now),
        "notification_policy": (
            "artifact-only: this ALERT row is the trigger artefact. Email, "
            "webhook, or the infra HALT policy reads the alerts/ prefix; "
            "this module has no credentials and sends nothing (house rule: "
            "never fetch secrets, never call networks outside fetch seams)."
        ),
        "suggested_action": (
            "Inspect the run rows under pipelines/run-log/ named in "
            "evidence; a job still failing on its next scheduled day "
            "refreshes this alert with a new day stamp."
        ),
    }
    written = write_json(backend, alert_rel(day, job), alert)
    return {"consecutive_failures": streak, "alert": written}


def persist_flag_rows(
    backend, *, job: str, now: datetime, kind_label: str, flags: list[dict]
) -> list[str]:
    """File discovery/analyst artefacts under alerts/ (dated, idempotent).

    Shapes accepted: anything JSON-serialisable with stable identity in
    ``flag_id``/``id``. This is the generic sink the market shock-watch
    ``flag_payload`` rows and new-warning/new-acquisition artefacts share;
    delivery remains the infra watchdog's concern (see on_run_finished).
    """
    written = []
    day = day_stamp(now)
    for flag in flags:
        ident = safe_name(flag.get("flag_id") or flag.get("id") or "flag")
        name = f"{day}-{job}-{kind_label}-{ident}.json"
        document = {
            **flag,
            "alert": kind_label,
            "job": job,
            "day": day,
            "alert_written_at": iso(now),
        }
        written.append(write_json(backend, alert_rel_persistent(name), document))
    return written


def alert_rel_persistent(name: str) -> str:
    return f"{ALERTS}/{name}"


def standing_alerts(backend, job: str | None = None) -> list[str]:
    names = []
    for name in backend.list_paths(ALERTS, "*.json"):
        if job is not None and f"-{job}-" not in name:
            continue
        names.append(name)
    return sorted(names)


__all__ = [
    "PIPE_SEGMENT",
    "RUN_LOG",
    "ALERTS",
    "STATE",
    "CONSECUTIVE_FAILURE_ALERT_AT",
    "ALERT_EVIDENCE_WINDOW",
    "ROW_READ_WORKERS",
    "STATUS_CACHE_TTL_S",
    "open_pipe_backend",
    "describe_backend",
    "read_json",
    "read_row_once",
    "read_rows_parallel",
    "clear_row_caches",
    "write_json",
    "job_rows",
    "already_equal_value_row",
    "write_data_row",
    "log_rel",
    "append_run",
    "run_rows",
    "consecutive_failures",
    "alert_rel",
    "evidence_window",
    "on_run_finished",
    "persist_flag_rows",
    "standing_alerts",
    "invalidate_ingest_status_cache",
    "status_cache_generation",
    "cached_status_payload",
    "store_status_payload",
    "status_clock",
    "iso",
    "day_stamp",
    "run_stamp",
    "safe_name",
    "rel_name",
]
