"""JSON bridge for the Next field page.

The page calls this module. Recording never attaches weather and never
opens a map. Class C and financial use stay on the values fieldkit writes.
"""

from __future__ import annotations

import json
import sys

from farm_ontology.record import add_note, list_notes, record_observation, status


def dispatch(req: dict) -> dict:
    op = req.get("op")
    if op == "status":
        return status()
    if op == "list":
        return list_notes()
    if op == "observe":
        return record_observation(
            latitude=req.get("latitude"),
            longitude=req.get("longitude"),
            note=str(req.get("note") or ""),
            metres=req.get("metres"),
            sample_id=req.get("sample_id") or None,
            photo_path=req.get("photo") or None,
            harvest_unit=req.get("harvest_unit") or None,
            moisture=req.get("moisture"),
            dry_run=bool(req.get("dry_run")),
            attach_weather=False,
        )
    if op == "note":
        return add_note(
            kind=str(req.get("kind") or ""),
            text=str(req.get("text") or ""),
            observation_file=req.get("observation_file") or None,
        )
    raise ValueError("unknown page operation")


def main() -> int:
    try:
        req = json.loads(sys.stdin.read() or "{}")
        json.dump(dispatch(req), sys.stdout, ensure_ascii=False)
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        json.dump({"error": str(error)}, sys.stdout, ensure_ascii=False)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
