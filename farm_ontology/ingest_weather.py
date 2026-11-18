"""WS2.1 weather worker: hourly jma_msm through the existing adapters.

The fetch composes the SAME modules the live /farm/weather path exposes,
directly (module import, never HTTP-to-self):

- ``farm_ontology.http_service._open_meteo_current`` documents WHAT a live
  weather answer carries (model, current block, grid note);
- ``farm_ontology.adapters.open_meteo.fetch_live_sample`` +
  ``build_live_document`` turn it into the governed adapter document with
  issue time, availability time, and the 0.05 deg native grid.

Conversion here wraps ``build_live_document``'s output in one observation
dict with the schema this workstream owns. Dedupe rule (2.1): skip when
an equal phenomenon-hour row already exists with the SAME values — so an
unchanged feed is a no-op re-run, and a REVISED value for the same hour
earns its own evidence row (row names hash the dedupe keys). One run,
one commit, through ``ingest_core`` pipes: run-log row always, alert
after 3 consecutive failures.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from farm_ontology import ingest_core

WEATHER_JOB = "weather-hourly"

DedupeKeys = ("kind", "phenomenon_hour", "issued", "value_mm")


def weather_observation(live_document: dict, *, captured_at: datetime) -> dict:
    """The observation-dict shape persisted under pipelines/weather/.

    Composition honesty: value fields come only from
    ``build_live_document`` output; the captured-at stamp comes from the
    worker's injected clock, never from a wall read.
    """
    return {
        "kind": WEATHER_JOB,
        "source": "open-meteo",
        "model": live_document["model"],
        "issue_time": live_document["issue_time"],
        "valid_time": live_document["valid_time"],
        "phenomenon_hour": live_document["valid_time"],
        "issued": live_document["issue_time"],
        "availability_time": live_document["availability_time"],
        "value_mm": live_document["value_mm"],
        "unit": "mm",
        "grid_deg": live_document["grid_deg"],
        "spatial_support": "grid-cell",
        "feature_local": live_document["feature_local"],
        "captured_at": ingest_core.iso(captured_at),
        "captured_live": bool(live_document.get("captured_live", True)),
    }


def row_name(incoming: dict, *, day: str) -> str:
    """Stable name hashing the dedupe keys: equal values collapse."""
    keys = json.dumps(
        [incoming.get(key) for key in DedupeKeys],
        sort_keys=True,
        ensure_ascii=False,
    )
    digest = hashlib.sha256(keys.encode("utf-8")).hexdigest()[:8]
    hour = ingest_core.safe_name(incoming["phenomenon_hour"])
    return f"wx-{day}-{hour}-{digest}.json"


def maybe_write(
    backend, live_document: dict, *, job: str, now: datetime
) -> tuple[str | None, int]:
    """Persist-or-dedupe: none written when the same hour is already stored.

    Returns (written_rel_or_None, row_count_delta).
    """
    incoming = weather_observation(live_document, captured_at=now)
    existing = ingest_core.job_rows(backend, "weather", "wx-")
    if ingest_core.already_equal_value_row(existing, incoming, DedupeKeys):
        return None, 0
    name = row_name(incoming, day=ingest_core.day_stamp(now))
    written = ingest_core.write_data_row(backend, "weather", name, incoming, job=job, now=now)
    return written, 1


def run_weather_job(
    backend, *, now: datetime, live_document: dict | None = None
) -> dict:
    """One scheduled weather run against an injected backend.

    ``live_document`` overrides fetch (offline tests inject
    ``build_live_document`` output or recorded fixtures). Without it the
    real fetch composes the adapter functions exactly as the live path
    does. Worker contract: the run-log row is appended whatever happens.
    """
    started = now
    written: str | None = None
    row_delta = 0
    error: str | None = None
    try:
        if live_document is None:
            from farm_ontology.adapters.open_meteo import (
                build_live_document,
                fetch_live_sample,
            )

            live_document = build_live_document(fetch_live_sample())
        written, row_delta = maybe_write(backend, live_document, job=WEATHER_JOB, now=now)
    except (OSError, ValueError, KeyError, TypeError) as caught:
        error = f"weather-hourly failed: {caught}"
    finished = now
    row = ingest_core.append_run(
        backend,
        job=WEATHER_JOB,
        now=finished,
        started=started,
        finished=finished,
        ok=error is None,
        row_count=row_delta,
        error=error,
        dedupe_skipped=(row_delta == 0 and error is None),
        backend_desc=ingest_core.describe_backend(backend),
    )
    result = {
        "job": WEATHER_JOB,
        "ok": error is None,
        "row_count": row_delta,
        "written_row": written,
        "run_log": row,
        "error": error,
    }
    result.update(ingest_core.on_run_finished(backend, job=WEATHER_JOB, now=finished, run={
        "ok": error is None,
        "error": error,
        "row_count": row_delta,
        "started": ingest_core.iso(started),
        "finished": ingest_core.iso(finished),
        "file": "",
    }))
    return result


__all__ = [
    "WEATHER_JOB",
    "DedupeKeys",
    "weather_observation",
    "row_name",
    "maybe_write",
    "run_weather_job",
]
