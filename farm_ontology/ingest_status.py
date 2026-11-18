"""Read side of the ingest workstream: per-job last-run summaries.

Backed ONLY by the record backend's ``pipelines/run-log/`` and
``pipelines/alerts/`` rows (WS2.5's own artefacts). A job with no run
rows is reported as a GAP, never invented as healthy: freshness claims
come from the durable audit trail or they do not exist (house honesty
rules). This module performs no network calls and no clock reads —
callers inject ``now`` so staleness is measurable and tests are
deterministic.
"""

from __future__ import annotations

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


def summarize_job(backend, job: str, *, now: datetime) -> dict:
    """Last run (chronologically newest by filename date stamp) + strikes."""
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


def ingest_status(backend, *, now: datetime) -> dict:
    """The /farm/ingest-status payload: every watched job, gaps included."""
    jobs = {}
    for job in WATCHED_JOBS:
        jobs[job] = summarize_job(backend, job, now=now)
    return {
        "watched_jobs": list(WATCHED_JOBS),
        "checked_at": ingest_core.iso(now),
        "jobs": jobs,
        "failures_at_threshold": {
            job: summary["consecutive_failures"] >= ingest_core.CONSECUTIVE_FAILURE_ALERT_AT
            for job, summary in jobs.items()
        },
        "source": "pipelines/run-log + pipelines/alerts via the record backend",
        "note": (
            "Absence of runs is a published gap; the ALERT artefact itself is "
            "the notification trigger (artifact-only policy, ingest_core doc)."
        ),
    }


__all__ = [
    "WATCHED_JOBS",
    "STALE_AFTER",
    "summarize_job",
    "ingest_status",
]
