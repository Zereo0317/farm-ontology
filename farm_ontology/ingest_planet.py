"""WS2.2 Planet nightly worker: header-only delta of the quick-search feed.

The nightly cadence mirrors the live /farm/planet path. As with weather,
fetch composes ``farm_ontology.http_service._planet_search`` DIRECTLY by
module import — never HTTP-to-self — so the worker exercises the same
authentication, gap, and header-shaping code the service serves.

Delta rule (2.2): diff scene-id sets against the last snapshot
(``state/planet-last.json``). NEW scene ids append rows under
``planet/``; the snapshot is then rewritten to the current set.
Disappeared scenes stay in previously-written rows (the record is
append-only) but leave the snapshot. Headers only: no pixels travel,
matching the licence posture of the service path.

Alert hook: the roadmap demands an alert on NEW ACQUISITIONS. The
durable artefact is ``alerts/<day>-planet-nightly-acquisitions.json``
listing the new scene ids; delivery to a webhook/channel stays with the
infra watchdog, exactly like the 3-strike alerts (see ``ingest_core``).
Same-day repeats diff to an empty set and write nothing.
"""

from __future__ import annotations

from datetime import datetime

from farm_ontology import ingest_core

PLANET_JOB = "planet-nightly"

SNAPSHOT_REL = f"{ingest_core.STATE}/planet-last.json"

SCENE_KEYS = (
    "id",
    "acquired",
    "cloud_cover",
    "instrument",
    "publishing_stage",
    "quality_category",
    "strip_id",
)


def scene_row(scene: dict, *, job_day: str) -> dict:
    """One header row — exactly the fields the service path shapes."""
    return {
        "kind": PLANET_JOB,
        "scene_id": scene.get("id"),
        **{key: scene.get(key) for key in SCENE_KEYS if key != "id"},
        "source": "planet-data-api-quick-search-headers",
        "pixels_downloaded": False,
        "observed_day": job_day,
    }


def load_snapshot(backend) -> dict:
    return ingest_core.read_json(backend, SNAPSHOT_REL) or {"seen_scene_ids": [], "updated": None}


def diff_new_scenes(snapshot: dict, scenes: list[dict]) -> list[dict]:
    seen = set(map(str, snapshot.get("seen_scene_ids") or []))
    return [scene for scene in scenes if str(scene.get("id")) not in seen]


def run_planet_job(
    backend, *, now: datetime, search_document: dict | None = None
) -> dict:
    """One nightly delta run against an injected backend.

    ``search_document`` overrides the search (offline tests inject the
    recorded service answer shape). Direct-import composition is used
    otherwise. Run-log row appended whatever happens; new acquisitions
    additionally emit the persistent acquisition alert artefact.
    """
    started = now
    new_ids: list[str] = []
    written: list[str] = []
    acquisition_alert: str | None = None
    error: str | None = None
    try:
        if search_document is None:
            from farm_ontology import http_service

            search_document = http_service._planet_search(
                float(http_service.FARM["latitude"]),
                float(http_service.FARM["longitude"]),
            )
        if "gap" in search_document:
            raise ValueError(
                f"planet search returned a gap: {str(search_document['gap'])[:200]}"
            )
        scenes = list(search_document.get("scenes") or [])
        snapshot = load_snapshot(backend)
        day = ingest_core.day_stamp(now)
        incoming = [scene_row(scene, job_day=day) for scene in diff_new_scenes(snapshot, scenes)]
        for row in incoming:
            name = f"scene-{ingest_core.safe_name(row['scene_id'])}.json"
            written.append(
                ingest_core.write_data_row(backend, "planet", name, row, job=PLANET_JOB, now=now)
            )
            new_ids.append(str(row["scene_id"]))
        merged_seen = list(dict.fromkeys(
            [*(snapshot.get("seen_scene_ids") or []), *(str(scene.get("id")) for scene in scenes)]
        ))
        ingest_core.write_json(
            backend,
            SNAPSHOT_REL,
            {
                "seen_scene_ids": merged_seen,
                "matched_this_run": len(scenes),
                "new_this_run": len(new_ids),
                "updated": ingest_core.iso(now),
                "snapshot_job": PLANET_JOB,
                "headers_only": True,
            },
        )
        if new_ids:
            acquisition_alert = ingest_core.persist_flag_rows(
                backend,
                job=PLANET_JOB,
                now=now,
                kind_label="acquisitions",
                flags=[
                    {
                        "flag_id": f"planet-new-{ingest_core.safe_name(scene_id)}",
                        "alert_kind": "new-scene-acquisition",
                        "scene_id": scene_id,
                        "matched_scenes_this_run": len(scenes),
                        "delivery": "artifact-only; infra watchdog translates (see ingest_core)",
                    }
                    for scene_id in new_ids
                ],
            )[0]
    except (OSError, ValueError, KeyError, TypeError) as caught:
        error = f"planet-nightly failed: {caught}"
    finished = now
    ingest_core.append_run(
        backend,
        job=PLANET_JOB,
        now=finished,
        started=started,
        finished=finished,
        ok=error is None,
        row_count=len(written),
        error=error,
        new_scene_ids=new_ids,
        acquisition_alert=acquisition_alert,
        snapshot_rel=SNAPSHOT_REL,
        backend_desc=ingest_core.describe_backend(backend),
    )
    result = {
        "job": PLANET_JOB,
        "ok": error is None,
        "row_count": len(written),
        "written_rows": written,
        "new_scene_ids": new_ids,
        "acquisition_alert": acquisition_alert,
        "error": error,
    }
    result.update(ingest_core.on_run_finished(backend, job=PLANET_JOB, now=finished, run={
        "ok": error is None,
        "error": error,
        "row_count": len(written),
        "started": ingest_core.iso(started),
        "finished": ingest_core.iso(finished),
        "file": "",
    }))
    return result


__all__ = [
    "PLANET_JOB",
    "SNAPSHOT_REL",
    "SCENE_KEYS",
    "scene_row",
    "load_snapshot",
    "diff_new_scenes",
    "run_planet_job",
]
