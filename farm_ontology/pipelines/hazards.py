"""WS2.4 hazard watcher: daily JMA + U.S. Drought Monitor capture.

TEMPLATE SHAPES ONLY, already merged. The recorded fixture headers in
``farm_ontology.us_drought_monitor``, ``.jma_torrential``, ``.jma_snow``
and ``.jma_marine`` (their recorded printed constants) are the exact row
shapes stored here. Nothing new is fetched anywhere in this module's
code paths.

The seam
--------

``fetch_hazard(source_id, force=False, fetcher=None)`` is the ONLY way a
row enters this watcher:

- ``force=False`` (the scheduled default) replays the recorded in-repo
  fixture headers VERBATIM — zero network, deterministic, offline-test
  friendly. Replay rows carry ``fixture: True`` so recorded headers are
  never mistaken for live collections.
- ``force=True`` performs the real collection: it requires the
  ``FARM_HAZARD_FETCH_ENABLED=1`` environment flag, then retrieves the
  feed URL with the supplied ``fetcher`` (tests inject a canned one;
  production wiring may inject a urllib-based fetcher). A refused flag
  or a failing fetch RAISES — there is no silent fallback, because a
  failed honest fetch must land in the run-log as a failure, not be
  papered over with yesterday's fixture.

Real OAuth/credential prerequisites belong to later tasks; this module
holds none (house rule: never fetch secrets).

New-warning detection
---------------------

Each replayed/collected header reduces to a signature (publisher,
product, kind, period, unit). Signatures not in
``state/hazard-seen-warnings.json`` are NEW WARNINGS: flagged under
``alerts/<day>-hazard-daily-warnings-*.json`` and remembered. The first
run after adoption establishes the baseline and therefore flags every
recorded warning once; the second run with unchanged feeds is a no-op
(idempotent re-run). A changed live header later changes its signature
and fires again. Delivery of the flag artefacts stays with the infra
watchdog (artifact-only policy, see ``farm_ontology.ingest_core``).
"""

from __future__ import annotations

import os
from datetime import datetime

from farm_ontology import ingest_core
from farm_ontology import jma_marine, jma_snow, jma_torrential, us_drought_monitor

HAZARD_JOB = "hazard-daily"

SEEN_WARNINGS_REL = f"{ingest_core.STATE}/hazard-seen-warnings.json"

FETCH_ENABLED_ENV = "FARM_HAZARD_FETCH_ENABLED"

#: Header sources RECORDED in the repository. Rows are the recorded
#: printed constants exactly as the merged fixture modules store them.
HAZARD_SOURCES: tuple[dict, ...] = (
    {
        "source_id": "jma-torrential",
        "publisher": jma_torrential.PUBLISHER,
        "product": jma_torrential.PRODUCT,
        "period": jma_torrential.PERIOD,
        "unit": jma_torrential.UNIT,
        "kind": jma_torrential.KIND,
        "citation_url": jma_torrential.JMA_TORRENTIAL_URL,
        "fixture_module": "farm_ontology.jma_torrential",
    },
    {
        "source_id": "jma-snow",
        "publisher": jma_snow.PUBLISHER,
        "product": jma_snow.PRODUCT,
        "period": jma_snow.PERIOD,
        "unit": jma_snow.UNIT,
        "kind": jma_snow.KIND,
        "citation_url": jma_snow.JMA_SNOW_URL,
        "fixture_module": "farm_ontology.jma_snow",
    },
    {
        "source_id": "jma-marine",
        "publisher": jma_marine.PUBLISHER,
        "product": jma_marine.PRODUCT,
        "period": jma_marine.PERIOD,
        "kind": jma_marine.KIND,
        "administrative_area": jma_marine.ADMINISTRATIVE_AREA,
        "citation_url": jma_marine.JMA_MARINE_URL,
        "fixture_module": "farm_ontology.jma_marine",
    },
    {
        "source_id": "us-drought-monitor",
        "publisher": us_drought_monitor.PUBLISHER,
        "product": us_drought_monitor.PRODUCT,
        "period": us_drought_monitor.PERIOD,
        "unit": us_drought_monitor.UNIT,
        "kind": us_drought_monitor.KIND,
        "citation_url": us_drought_monitor.US_DROUGHT_MONITOR_URL,
        "administrative_area": us_drought_monitor.ADMINISTRATIVE_AREA,
        "fixture_module": "farm_ontology.us_drought_monitor",
    },
)


def source_ids() -> tuple[str, ...]:
    return tuple(source["source_id"] for source in HAZARD_SOURCES)


def _fixture_headers() -> dict[str, dict]:
    """The recorded header dicts, shaped as the fixture modules write them."""
    headers: dict[str, dict] = {}
    for source in HAZARD_SOURCES:
        header = {
            "publisher": source["publisher"],
            "product": source["product"],
            "period": source["period"],
            "citation_url": source["citation_url"],
            "kind": source["kind"],
            "permits_financial_use": False,
        }
        if source.get("unit"):
            header["unit"] = source["unit"]
        if source.get("administrative_area"):
            header["administrative_area"] = source["administrative_area"]
        headers[source["source_id"]] = header
    return headers


def _live_fetch(url: str) -> str:
    """Stdlib GET used only behind force=True + the enabled flag."""
    import urllib.request

    request = urllib.request.Request(url, headers={"Accept": "text/html,application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read(1_048_576).decode("utf-8", "replace")


def fetch_hazard(
    source_id: str,
    *,
    force: bool = False,
    fetcher=None,
) -> dict:
    """One hazard feed snapshot through the only sanctioned seam.

    force=False replays the recorded fixture header verbatim (offline,
    deterministic, ``fixture: True``). force=True demands the enabled
    flag, fetches the source URL live via ``fetcher`` (or the stdlib
    default), and fails loudly instead of fabricating. The returned dict
    always carries ``headers`` (the row payload) plus honesty fields.
    """
    source = next(
        (item for item in HAZARD_SOURCES if item["source_id"] == source_id), None
    )
    if source is None:
        raise ValueError(f"unknown hazard source {source_id!r}")
    if not force:
        return {
            "source_id": source_id,
            "headers": _fixture_headers()[source_id],
            "header_source": "recorded-template",
            "fixture": True,
            "collected_at": None,
        }
    if not os.environ.get(FETCH_ENABLED_ENV, "").strip():
        raise ValueError(
            f"{FETCH_ENABLED_ENV}=1 is required before a forced live hazard fetch"
        )
    collected = (fetcher or _live_fetch)(source["citation_url"])
    if not collected.strip():
        raise ValueError(f"hazard source {source_id} returned an empty document")
    # The header template is unchanged: no live parser exists yet (a later
    # task graduates one). The probe proves connectivity and reports the
    # payload size; it fabricates no live field values.
    return {
        "source_id": source_id,
        "headers": _fixture_headers()[source_id],
        "header_source": "recorded-template",
        "fixture": True,
        "collected_at": None,
        "live_probe": {
            "url": source["citation_url"],
            "bytes": len(collected.encode("utf-8")),
            "note": "connectivity probe only; no live parser exists yet",
        },
    }


def hazard_signature(headers: dict) -> list[str]:
    """Warning identity: the printed fields that mean the same warning."""
    keys = ("publisher", "product", "kind", "period", "unit", "administrative_area")
    return [str(headers.get(key, "")) for key in keys]


def load_seen(backend) -> dict:
    return ingest_core.read_json(backend, SEEN_WARNINGS_REL) or {"signatures": {}}


def assemble_hazard_rows(replayed: list[dict], *, day: str) -> list[dict]:
    """Observation-dict rows: one per source, header template verbatim."""
    rows = []
    for item in replayed:
        rows.append(
            {
                "kind": HAZARD_JOB,
                "source_id": item["source_id"],
                **item["headers"],
                "header_source": item.get("header_source", "recorded-template"),
                "fixture": item["fixture"],
                "observed_day": day,
                "pixels_downloaded": False,
            }
        )
    return rows


def run_hazard_job(
    backend, *, now: datetime, force: bool = False, fetcher=None
) -> dict:
    """One daily watcher run against an injected backend.

    Default (force=False) replays the recorded fixtures — the offline
    path tests exercise and the scheduled job runs until live hazard
    credentials/parsers graduate from a later task. Run-log row appended
    whatever happens; new signatures emit persistent warning artefacts.
    """
    started = now
    written: list[str] = []
    warned: list[str] = []
    error: str | None = None
    try:
        replayed = [
            fetch_hazard(source_id, force=force, fetcher=fetcher)
            for source_id in source_ids()
        ]
        day = ingest_core.day_stamp(now)
        for index, row in enumerate(assemble_hazard_rows(replayed, day=day), start=1):
            name = f"hazard-{day}-{ingest_core.safe_name(row['source_id'])}.json"
            written.append(
                ingest_core.write_data_row(backend, "hazards", name, row, job=HAZARD_JOB, now=now)
            )
        seen = load_seen(backend)
        signatures: dict[str, str] = dict(seen.get("signatures") or {})
        for item in replayed:
            signature = "|".join(hazard_signature(item["headers"]))
            if signatures.get(signature):
                continue
            signatures[signature] = day
            flag_name = (
                f"{day}-{HAZARD_JOB}-warnings-"
                f"new-{ingest_core.safe_name(item['source_id'])}.json"
            )
            ingest_core.write_json(
                backend,
                ingest_core.alert_rel_persistent(flag_name),
                {
                    "flag_id": f"hazard-new-{item['source_id']}-{day}",
                    "alert_kind": "new-hazard-warning",
                    "source_id": item["source_id"],
                    "publisher": item["headers"].get("publisher"),
                    "product": item["headers"].get("product"),
                    "kind": item["headers"].get("kind"),
                    "fixture": item["fixture"],
                    "delivery": "artifact-only; infra watchdog translates (see ingest_core)",
                    "observed_day": day,
                    "job": HAZARD_JOB,
                    "alert_written_at": ingest_core.iso(now),
                },
            )
            warned.append(item["source_id"])
        ingest_core.write_json(
            backend,
            SEEN_WARNINGS_REL,
            {"signatures": signatures, "updated": ingest_core.iso(now)},
        )
    except (OSError, ValueError, KeyError, TypeError) as caught:
        error = f"hazard-daily failed: {caught}"
    finished = now
    ingest_core.append_run(
        backend,
        job=HAZARD_JOB,
        now=finished,
        started=started,
        finished=finished,
        ok=error is None,
        row_count=len(written),
        error=error,
        new_warnings=warned,
        seen_signatures_rel=SEEN_WARNINGS_REL,
        forced_live=bool(force),
        backend_desc=ingest_core.describe_backend(backend),
    )
    result = {
        "job": HAZARD_JOB,
        "ok": error is None,
        "row_count": len(written),
        "written_rows": written,
        "new_warnings": warned,
        "error": error,
    }
    result.update(ingest_core.on_run_finished(backend, job=HAZARD_JOB, now=finished, run={
        "ok": error is None,
        "error": error,
        "row_count": len(written),
        "started": ingest_core.iso(started),
        "finished": ingest_core.iso(finished),
        "file": "",
    }))
    return result


__all__ = [
    "HAZARD_JOB",
    "SEEN_WARNINGS_REL",
    "FETCH_ENABLED_ENV",
    "HAZARD_SOURCES",
    "source_ids",
    "fetch_hazard",
    "hazard_signature",
    "load_seen",
    "assemble_hazard_rows",
    "run_hazard_job",
]
