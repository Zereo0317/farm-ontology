"""WS2 ingestion plumbing: durable pipes, run-log rows, strike alerts.

Every scheduled worker (``pipelines/run_worker.py``) funnels through THIS
module. The rules:

1. Storage goes through the existing record-store seam
   (``farm_ontology.record_store``: local directory or the GCS bucket
   ``farm-seges-ai-records``). Pipeline artefacts are siblings of the
   field record, never new storage infrastructure::

       <backend root>/pipelines/run-log/YYYYMMDD-<job>.json
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

4. Idempotence. Job re-runs overwrite their own dated artefacts with
   byte-identical content when inputs repeat (fixed day stamps, no wall
   clock outside the injected ``now``) and dedupe rules (weather
   equal-value rows, Planet scene-id deltas, hazard warning signatures)
   prevent duplicate data rows. Running a job twice writes nothing new
   the second time unless the underlying feed changed.
"""

from __future__ import annotations

import json
import os
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

    ``FARM_RECORD_BACKEND=gcs`` reuses the durable record bucket with the
    dedicated ``pipelines`` prefix, so run rows and alerts enjoy the same
    durability as observations. Local default root: ``~/.farm-ontology``
    with the ``pipelines`` subtree; rel paths are IDENTICAL under both
    backends (``run-log/...``, ``alerts/...``, ``state/...``).
    """
    name = os.environ.get("FARM_RECORD_BACKEND", "").strip().lower() or "local"
    if name == "local":
        root = os.environ.get("FARM_PIPE_ROOT", "").strip()
        base = Path(root) if root else Path.home() / ".farm-ontology"
        return LocalBackend(base / PIPE_SEGMENT)
    if name == "gcs":
        bucket = os.environ.get("FARM_RECORD_BUCKET", "").strip()
        if not bucket:
            raise ValueError("FARM_RECORD_BACKEND=gcs requires FARM_RECORD_BUCKET")
        return GcsBackend(bucket, PIPE_SEGMENT)
    raise ValueError(f"FARM_RECORD_BACKEND must be local or gcs, got {name!r}")


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
    backend.write(rel, (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    return rel


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
    """Append (dated-overwrite = one row per job per UTC day) a run row.

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
    return write_json(backend, log_rel(day_stamp(now), job), document)


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
    """Failed rows since the newest success (date-order scan)."""
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
    threshold, carrying the evidence trail. Idempotent: the same failed
    day rewritten produces the same alert.
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
    "open_pipe_backend",
    "describe_backend",
    "read_json",
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
    "iso",
    "day_stamp",
    "run_stamp",
    "safe_name",
    "rel_name",
]
