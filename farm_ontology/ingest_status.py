"""Read side of the ingest workstream: per-job last-run summaries.

Backed ONLY by the record backend's ``pipelines/run-log/`` and
``pipelines/alerts/`` rows (WS2.5's own artefacts). A job with no run
rows is reported as a GAP, never invented as healthy: freshness claims
come from the durable audit trail or they do not exist (house honesty
rules). Staleness is measured against the CALLER-INJECTED ``now`` —
never a wall clock — so tests are deterministic.

Hot path (task-15, Sprint-G)
----------------------------

``ingest_status(backend, now=...)`` composes in THREE storage asks,
issued as two concurrent listings (``run-log/`` + ``alerts/``) plus
parallel minimal GETs of only the rows the answer names — instead of
the legacy per-job list+read+re-list cascade (~4 listings and ~3× rows
of serial round trips per request; that cascade measured as a 988 ms
↔ 16894 ms p95 tail on prod, Sprint-E/F reports). Correctness aids:

- rows are read through ``ingest_core.read_row_once`` (singleflight,
  process-wide), so parallel workers never duplicate a GET;
- strikes stop scanning at the newest successful row (early exit),
  bounding reads to the size of the current failure streak;
- a per-backend 60 s TTL response cache fronts the whole compose
  (``ingest_core``'s clock/cache slot), invalidated by ANY write
  through ``ingest_core`` (``write_json``/``append_run``) — operators
  never see strikes or runs older than the write that changed them;
  cross-instance staleness is bounded by the TTL (documented trade).

``summarize_job``/``consecutive_failures``/``standing_alerts`` stay as
the legacy deep path: equivalence tests prove both composers agree on
identical stores.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from farm_ontology import ingest_core
from farm_ontology.ingest_ndvi import NDVI_JOB
from farm_ontology.ingest_planet import PLANET_JOB
from farm_ontology.ingest_weather import WEATHER_JOB
from farm_ontology.pipelines.hazards import HAZARD_JOB
from farm_ontology.timeutil import parse_time

WATCHED_JOBS = (WEATHER_JOB, PLANET_JOB, HAZARD_JOB, NDVI_JOB)

STALE_AFTER = {
    WEATHER_JOB: (2, "hours"),
    PLANET_JOB: (30, "hours"),
    HAZARD_JOB: (30, "hours"),
    NDVI_JOB: (8, "days"),
}

#: Descending row-read batching for the strikes early-exit walk.
STRIDES_FIRST_CHUNK = 3
STRIDES_CHUNK = 8

LISTING_WORKERS = 2


# ------------------------------------------------------------ name parsing


def job_of_row_name(filename: str) -> str | None:
    """``20261118-weather-hourly.json`` → ``weather-hourly``; None if alien."""
    base = ingest_core.rel_name(filename)
    if not base.endswith(".json"):
        return None
    stem = base[: -len(".json")]
    # Accept both legacy daily filenames and timestamped execution filenames.
    date, separator, remainder = stem.partition("-")
    if not separator or not date[:8].isdigit():
        return None
    for job in WATCHED_JOBS:
        if remainder == job or remainder.endswith("-" + job):
            return job
    return None


def summarize_entry(filename: str, row: dict) -> dict:
    return {
        "file": ingest_core.rel_name(filename),
        "ok": row["ok"],
        "started": row["started"],
        "finished": row["finished"],
        "row_count": row["row_count"],
        "error": row["error"],
    }


# ------------------------------------------------------- fast composition


def _walk_descending(backend, names_desc: list[str]) -> tuple[list[dict], int]:
    """(recent_runs ascending[:3], consecutive_failures) via parallel GETs.

    Two independent stopping needs, so the walk continues until BOTH are
    satisfied: ``recent_runs`` wants the 3 NEWEST rows whatever their
    status; ``strikes`` settles at the NEWEST SUCCESSFUL row (failures
    before it, descending, count; rows older than the settled success
    never matter). Read budget: at most first-stride (3) + enough
    failure-extension strides to settle the streak — never the history.
    """
    recent_desc: list[dict] = []
    strikes = 0
    settled = False
    index = 0
    while index < len(names_desc) and (len(recent_desc) < STRIDES_FIRST_CHUNK or not settled):
        take = STRIDES_FIRST_CHUNK if index == 0 else STRIDES_CHUNK
        batch = names_desc[index : index + take]
        rows = ingest_core.read_rows_parallel(backend, batch)
        for name in batch:
            row = rows.get(name)
            if row is None:
                continue
            entry = summarize_entry(name, row)
            if len(recent_desc) < STRIDES_FIRST_CHUNK:
                recent_desc.append(entry)
            if not settled:
                if entry["ok"]:
                    settled = True
                else:
                    strikes += 1
            if len(recent_desc) >= STRIDES_FIRST_CHUNK and settled:
                break
        index += take
    return list(reversed(recent_desc)), strikes


def compose_status(backend, *, now: datetime) -> dict:
    """The honest per-job summary from ONE run-log + ONE alerts listing."""
    with ThreadPoolExecutor(max_workers=LISTING_WORKERS) as pool:
        run_listing = pool.submit(backend.list_paths, ingest_core.RUN_LOG, "*.json")
        alert_listing = pool.submit(backend.list_paths, ingest_core.ALERTS, "*.json")
        run_names = sorted(run_listing.result())
        alert_names = sorted(alert_listing.result())

    by_job: dict[str, list[str]] = {job: [] for job in WATCHED_JOBS}
    unparsed = 0
    for name in run_names:
        job = job_of_row_name(name)
        if job is None:
            unparsed += 1
            continue
        by_job[job].append(name)

    jobs: dict[str, dict] = {}
    for job in WATCHED_JOBS:
        names_asc = by_job[job]
        standing = [
            name for name in alert_names
            if f"-{job}-" in ingest_core.rel_name(name)
        ]
        if not names_asc:
            jobs[job] = {
                "job": job,
                "last_run": None,
                "gap": "no ingest-run row exists for this job yet",
                "consecutive_failures": 0,
                "alerts_standing": standing,
            }
            continue
        names_desc = list(reversed(names_asc))
        recent, strikes = _walk_descending(backend, names_desc)
        newest = recent[-1]
        hours_old = (now - parse_time(newest["finished"])).total_seconds() / 3600.0
        count, unit = STALE_AFTER[job]
        limit_seconds = count * {"hours": 3600.0, "days": 86400.0}[unit]
        jobs[job] = {
            "job": job,
            "last_run": newest["file"],
            "last_ok": newest["ok"],
            "last_row_count": newest["row_count"],
            "last_error": newest["error"],
            "hours_since_last_run": round(max(0.0, hours_old), 2),
            "stale": hours_old * 3600.0 > limit_seconds,
            "staleness_limit": f"{count} {unit}",
            "consecutive_failures": strikes,
            "alerts_standing": standing,
            "recent_runs": recent,
        }
    return {
        "watched_jobs": list(WATCHED_JOBS),
        "checked_at": ingest_core.iso(now),
        "jobs": jobs,
        "failures_at_threshold": {
            job: summary["consecutive_failures"] >= ingest_core.CONSECUTIVE_FAILURE_ALERT_AT
            for job, summary in jobs.items()
        },
        "source": "pipelines/run-log + pipelines/alerts via the record backend",
        "compose": "fast-path: two concurrent listings + parallel minimal GETs (task-15)",
        "unparsed_runlog_names": unparsed,
        "note": (
            "Absence of runs is a published gap; the ALERT artefact itself is "
            "the notification trigger (artifact-only policy, ingest_core doc)."
        ),
    }


# --------------------------------------------------------- legacy deep path


def summarize_job(backend, job: str, *, now: datetime) -> dict:
    """LEGACY deep path (kept for equivalence/tooling): full list + reads."""
    rows = ingest_core.run_rows(backend, job)
    strikes = ingest_core.consecutive_failures(backend, job)
    summaries = []
    if not rows:
        return {
            "job": job,
            "last_run": None,
            "gap": "no ingest-run row exists for this job yet",
            "consecutive_failures": 0,
            "alerts_standing": ingest_core.standing_alerts(backend, job),
        }
    newest = rows[-1]
    for row in rows[-3:]:
        summaries.append(
            {
                "file": row["file"],
                "ok": row["ok"],
                "started": row["started"],
                "finished": row["finished"],
                "row_count": row["row_count"],
                "error": row["error"],
            }
        )
    hours_old = (now - parse_time(newest["finished"])).total_seconds() / 3600.0
    count, unit = STALE_AFTER[job]
    limit_seconds = count * {"hours": 3600.0, "days": 86400.0}[unit]
    return {
        "job": job,
        "last_run": newest["file"],
        "last_ok": newest["ok"],
        "last_row_count": newest["row_count"],
        "last_error": newest["error"],
        "hours_since_last_run": round(max(0.0, hours_old), 2),
        "stale": hours_old * 3600.0 > limit_seconds,
        "staleness_limit": f"{count} {unit}",
        "consecutive_failures": strikes,
        "alerts_standing": ingest_core.standing_alerts(backend, job),
        "recent_runs": summaries,
    }


# ----------------------------------------------------------------- facade


def ingest_status(backend, *, now: datetime) -> dict:
    """Cached facade over :func:`compose_status`.

    Fresh build on TTL expiry, backend identity change, or any write
    through ``ingest_core`` (write_json/append_run invalidate eagerly);
    hits decorate the cached payload with ``cache`` bookkeeping. Cached
    payloads are shared: CALLERS MUST NOT MUTATE (the service wrapper
    decorates shallow-copies only).
    """
    payload, age, hit = ingest_core.cached_status_payload(backend)
    if hit:
        return {**payload, "cache": {"hit": True, "age_s": round(age, 3)}}
    fresh = compose_status(backend, now=now)
    ingest_core.store_status_payload(backend, fresh)
    return {**fresh, "cache": {"hit": False, "age_s": 0.0}}


__all__ = [
    "WATCHED_JOBS",
    "STALE_AFTER",
    "STRIDES_FIRST_CHUNK",
    "STRIDES_CHUNK",
    "job_of_row_name",
    "summarize_entry",
    "compose_status",
    "summarize_job",
    "ingest_status",
]
