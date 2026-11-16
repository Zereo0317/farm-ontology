"""Write one soybean field observation as JSON.

No network and no cloud. Crop Ontology CO_336 was resolved on
cropontology.org on 2026-11-16: the term page is titled Soybean Ontology
and the RDF URL returned HTTP 200. This command does not look the id up
again, so it still runs in a field with no signal.

GPS accuracy stays unknown unless the caller types metres. The weather
slot is the Open-Meteo JMA MSM grid at 0.05 degrees. It is not a plant
measurement and it is not a trade signal.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

SOYBEAN_ID = "CO_336"
SOYBEAN_TITLE = "Soybean Ontology"
SOYBEAN_TERM = "https://cropontology.org/term/CO_336:ROOT"
SOYBEAN_RDF = "https://cropontology.org/ontology/CO_336/rdf"
GRID_DEG = 0.05
DRY_LATITUDE = 0.0
DRY_LONGITUDE = 0.0
DRY_NOTE = "dry-run synthetic point at 0 N, 0 E. Not a farm."


def build_observation(
    *,
    latitude: float,
    longitude: float,
    note: str,
    at: datetime,
    dry_run: bool,
    metres: float | None = None,
    sample_id: str | None = None,
    photo_path: str | None = None,
    harvest_unit: str | None = None,
    moisture: float | None = None,
) -> dict:
    if at.tzinfo is None or at.tzinfo.utcoffset(at) is None:
        raise ValueError("phenomenon time must be timezone-aware")
    if not -90.0 <= latitude <= 90.0 or not -180.0 <= longitude <= 180.0:
        raise ValueError("latitude or longitude is out of range")
    accuracy = "unknown" if metres is None else "stated-metres"
    return {
        "record_type": "field-observation",
        "dry_run": dry_run,
        "labeled_as_farm": False if dry_run else None,
        "crop": "soybean",
        "crop_stage": "harvest",
        "crop_ontology_id": SOYBEAN_ID,
        "crop_ontology_title": SOYBEAN_TITLE,
        "crop_ontology_term": SOYBEAN_TERM,
        "crop_ontology_rdf": SOYBEAN_RDF,
        "crop_ontology_resolved": True,
        "phenomenon_time": at.astimezone(timezone.utc).isoformat(),
        "latitude": latitude,
        "longitude": longitude,
        "gps_accuracy_m": metres,
        "gps_accuracy": accuracy,
        "note": note,
        "row_or_sample_id": sample_id,
        "photo_path": photo_path,
        "harvest_unit": harvest_unit,
        "moisture": moisture,
        "yield": None,
        "futures_price": None,
        "weather": {
            "source": "open-meteo",
            "model": "jma_msm",
            "native_resolution_deg": GRID_DEG,
            "spatial_support": "grid-cell",
            "shrunk_to_plant": False,
            "value": None,
        },
        "use_class": "Screening",
        "class_c_policy": CLASS_C_POLICY,
        "permits_financial_use": False,
        "trade_signal": False,
    }


def write_observation(document: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write one soybean field observation.")
    parser.add_argument("--lat", type=float)
    parser.add_argument("--lon", type=float)
    parser.add_argument("--note", default="")
    parser.add_argument("--metres", type=float)
    parser.add_argument("--sample-id", default=None)
    parser.add_argument("--photo", default=None)
    parser.add_argument("--harvest-unit", default=None)
    parser.add_argument("--moisture", type=float)
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write the synthetic 0 N, 0 E point. It is not a farm.",
    )
    args = parser.parse_args(argv)
    if args.dry_run:
        latitude = DRY_LATITUDE
        longitude = DRY_LONGITUDE
        note = DRY_NOTE
    else:
        if args.lat is None or args.lon is None:
            parser.error("--lat and --lon are required unless --dry-run")
        latitude = args.lat
        longitude = args.lon
        note = args.note
    document = build_observation(
        latitude=latitude,
        longitude=longitude,
        note=note,
        at=datetime.now(timezone.utc),
        dry_run=args.dry_run,
        metres=None if args.dry_run else args.metres,
        sample_id=None if args.dry_run else args.sample_id,
        photo_path=None if args.dry_run else args.photo,
        harvest_unit=None if args.dry_run else args.harvest_unit,
        moisture=None if args.dry_run else args.moisture,
    )
    write_observation(document, Path(args.out))
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
