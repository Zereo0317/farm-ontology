"""Validate gcloud's Storage bucket JSON before Terraform adopts the state bucket."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _value(data: dict[str, Any], *paths: tuple[str, ...]) -> Any:
    for path in paths:
        value: Any = data
        for component in path:
            if not isinstance(value, dict) or component not in value:
                break
            value = value[component]
        else:
            return value
    return None


def _enabled(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("enabled")
    return value


def verify_bucket_json(data: dict[str, Any], *, bucket: str, region: str) -> None:
    actual_name = _value(data, ("name",))
    actual_region = _value(data, ("location",))
    uniform_access = _value(
        data,
        ("uniform_bucket_level_access",),
        ("uniform_bucket_level_access_enabled",),
        ("iam_configuration", "uniform_bucket_level_access", "enabled"),
        ("iam_configuration", "uniform_bucket_level_access"),
        ("iam_configuration", "bucket_policy_only", "enabled"),
    )
    public_access = _value(
        data,
        ("public_access_prevention",),
        ("iam_configuration", "public_access_prevention"),
    )
    versioning = _value(
        data,
        ("versioning_enabled",),
        ("versioning", "enabled"),
        ("versioning",),
    )

    if actual_name != bucket:
        raise ValueError(f"state bucket name mismatch: {actual_name!r}")
    if not isinstance(actual_region, str) or actual_region.casefold() != region.casefold():
        raise ValueError(f"state bucket region mismatch: {actual_region!r}")
    if _enabled(uniform_access) is not True:
        raise ValueError("state bucket must have uniform bucket-level access enabled")
    if public_access != "enforced":
        raise ValueError("state bucket must enforce public access prevention")
    if _enabled(versioning) is not True:
        raise ValueError("state bucket must have object versioning enabled")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", required=True, type=Path, help="gcloud describe JSON file")
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--region", required=True)
    args = parser.parse_args(argv)
    try:
        verify_bucket_json(
            json.loads(args.json.read_text(encoding="utf-8")),
            bucket=args.bucket,
            region=args.region,
        )
    except Exception as error:
        print(f"State bucket verification failed: {error}", file=sys.stderr)
        return 1
    print(f"Verified gs://{args.bucket} in {args.region}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
