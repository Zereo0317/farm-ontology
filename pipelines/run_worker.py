"""Named-job dispatch for ``pipelines/run_worker.py``.

The four scheduled WS2 jobs, their runner functions, and the time-zone
contracts the Cloud Scheduler expresses (see deploy/scheduler-setup.md).
Adding a fifth job means adding an entry here and nothing else: the
dispatcher, run logging, strikes, and alerts are generic.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# The worker may run as a bare script inside the container (python
# pipelines/run_worker.py) where the repo root is not on sys.path.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from farm_ontology import ingest_core  # noqa: E402
from farm_ontology.pipelines import hazards  # noqa: E402

WORKER_JOBS = (
    "weather-hourly",
    "planet-nightly",
    "hazard-daily",
    "ndvi-weekly",
)

SCHEDULER_CRONS_JST = (
    ("weather-hourly", "20 * * * *"),
    ("planet-nightly", "0 22 * * *"),
    ("hazard-daily", "30 7 * * *"),
    ("ndvi-weekly", "0 6 * * MON"),
)


def run_job(job: str, backend, *, now: datetime, **overrides):
    """Dispatch one named job; unknown names are a loud refusal.

    Extra keyword arguments flow into the named job's runner untouched
    (``live_document=`` for weather/planet injections, ``transport=``,
    ``force=`` ...); runners validate their own inputs.
    """
    if job == "weather-hourly":
        from farm_ontology.ingest_weather import run_weather_job

        return run_weather_job(backend, now=now, **overrides)
    if job == "planet-nightly":
        from farm_ontology.ingest_planet import run_planet_job

        return run_planet_job(backend, now=now, **overrides)
    if job == "hazard-daily":
        return hazards.run_hazard_job(backend, now=now, **overrides)
    if job == "ndvi-weekly":
        from farm_ontology.ingest_ndvi import run_ndvi_job
        from farm_ontology.http_service import FARM

        overrides.setdefault("latitude", FARM["latitude"])
        overrides.setdefault("longitude", FARM["longitude"])
        return run_ndvi_job(backend, now=now, **overrides)
    raise ValueError(f"unknown worker job {job!r}; known: {', '.join(WORKER_JOBS)}")


def _injected_clock_text(value: str) -> datetime:
    from farm_ontology.timeutil import parse_time

    return parse_time(value)


def main(argv: list[str] | None = None) -> int:
    """Worker entry: ``python -m pipelines.run_worker <job> [options]``.

    Local runs default to a scratch/local backend rooted at ``~/.farm-
    ontology`` (override ``FARM_PIPE_ROOT``); in the Cloud Run worker
    image ``FARM_RECORD_BACKEND=gcs`` routes everything to the durable
    bucket, matching the services. ``--now`` injects the run timestamp
    (ISO-8601, offset REQUIRED); without it the wall clock is used, but
    tests never do that.
    """
    parser = argparse.ArgumentParser(
        prog="pipelines.run_worker", description="Run one WS2 ingest job."
    )
    parser.add_argument("job", choices=WORKER_JOBS)
    parser.add_argument(
        "--now", help="injected run time, ISO-8601 with offset (tests/dev)"
    )
    parser.add_argument(
        "--local-root",
        help="force a local backend at this path (dev; env FARM_PIPE_ROOT otherwise)",
    )
    parser.add_argument(
        "--document",
        help=(
            "path to a JSON file injecting the fetch result (weather: the "
            "live adapter document; planet: the quick-search document). "
            "Tests/dev/offline drills use this; scheduled runs omit it."
        ),
    )
    args = parser.parse_args(argv)
    now = _injected_clock_text(args.now) if args.now else datetime.now(timezone.utc)
    if args.local_root:
        backend = ingest_core.local_pipe_backend(Path(args.local_root))
    else:
        backend = ingest_core.open_pipe_backend()
    document = None
    if args.document:
        document = json.loads(Path(args.document).read_text(encoding="utf-8"))
    if document is not None and args.job == "planet-nightly":
        overrides = {"search_document": document}
    elif document is not None:
        overrides = {"live_document": document}
    else:
        overrides = {}
    result = run_job(args.job, backend, now=now, **overrides)
    printable = dict(result)
    printable.pop("run_log", None)
    print(json.dumps(printable, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
