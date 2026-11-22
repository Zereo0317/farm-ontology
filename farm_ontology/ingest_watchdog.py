"""Evaluate ingestion execution freshness; no network or clock side effects."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import isfinite

from farm_ontology import ingest_core
from farm_ontology.timeutil import parse_time

# Cadence plus tolerance, based on deploy/scheduler-setup.md. Job execution
# success is not proof that the underlying data are live, useful or fresh.
DEFAULT_MAX_AGE = {
    "weather-hourly": timedelta(hours=2),
    "planet-nightly": timedelta(hours=30),
    "hazard-daily": timedelta(hours=30),
    "ndvi-weekly": timedelta(days=8),
    "record-export": timedelta(hours=30),
}


def evaluate(backend, *, now: datetime, max_age=None, failure_threshold: int = 3) -> dict:
    """Report missing/stale successes and consecutive failed executions.

    Invalid or future timestamps are explicit monitoring gaps, never ignored.
    Historical daily rows remain readable, although overwritten events cannot
    be recovered. ``now`` must be an aware timestamp.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must have a timezone")
    if type(failure_threshold) is not int or failure_threshold < 1:
        raise ValueError("failure threshold must be a positive integer")
    limits = DEFAULT_MAX_AGE if max_age is None else max_age
    if not limits:
        raise ValueError("at least one monitored job is required")
    now = now.astimezone(timezone.utc)
    result = {}
    for job, limit in limits.items():
        if not isinstance(job, str) or not job or not isinstance(limit, timedelta) or not isfinite(limit.total_seconds()) or limit.total_seconds() <= 0:
            raise ValueError("each job needs a positive finite freshness limit")
        rows = ingest_core.run_rows(backend, job)
        valid = []
        problems = []
        for row in rows:
            try:
                if row.get("job") != job or type(row.get("ok")) is not bool:
                    raise ValueError("invalid job or outcome")
                stamp = parse_time(row["finished"])
                if stamp > now:
                    raise ValueError("finish time is in the future")
                valid.append((stamp, row))
            except (ValueError, TypeError, KeyError) as error:
                problems.append({"file": row.get("file"), "reason": str(error)})
        valid.sort(key=lambda item: (item[0], item[1].get("file", "")), reverse=True)
        last_success = next((at for at, row in valid if row["ok"]), None)
        failures = 0
        for _, row in valid:
            if row["ok"]:
                break
            failures += 1
        reasons = []
        if not rows:
            reasons.append("missing-run")
        elif last_success is None:
            reasons.append("no-success")
        elif now - last_success > limit:
            reasons.append("stale-success")
        if failures >= failure_threshold:
            reasons.append("consecutive-failures")
        if problems:
            reasons.append("invalid-run-evidence")
        result[job] = {
            "healthy": not reasons,
            "reasons": reasons,
            "last_success": last_success.isoformat() if last_success else None,
            "last_run": valid[0][0].isoformat() if valid else None,
            "consecutive_failures": failures,
            "max_age_seconds": limit.total_seconds(),
            "invalid_rows": problems,
        }
    return {"checked_at": now.isoformat(), "healthy": all(v["healthy"] for v in result.values()), "jobs": result}
