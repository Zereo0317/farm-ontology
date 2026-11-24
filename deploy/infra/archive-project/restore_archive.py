"""Safely restore one manifested farm snapshot to the isolated drill bucket.

This tool uses the authenticated ``gcloud storage`` CLI and the Python
standard library only. It never writes to the production record bucket.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


def _run_gcloud(*args: str) -> str:
    result = subprocess.run(
        ["gcloud", *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode:
        raise RuntimeError(f"gcloud {' '.join(args[:3])} failed with exit code {result.returncode}")
    return result.stdout


def _safe_member_name(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or any(part in ("", ".", "..") for part in path.parts):
        raise ValueError(f"unsafe archive member path: {name!r}")
    if "\\" in name or "\x00" in name:
        raise ValueError(f"unsafe archive member path: {name!r}")
    return path


def _download(bucket: str, object_name: str, destination: Path) -> None:
    if not object_name.startswith("field-archive/") or ".." in PurePosixPath(object_name).parts:
        raise ValueError("manifest and archive objects must stay under field-archive/")
    _run_gcloud("storage", "cp", f"gs://{bucket}/{object_name}", str(destination))


def restore(manifest_bucket: str, manifest_object: str, target_bucket: str) -> dict:
    if not (
        manifest_bucket == "farm-seges-ai-records"
        or manifest_bucket.startswith("farm-seges-ai-records-archive")
    ):
        raise ValueError("restore source must be the farm records or records-archive bucket")
    if not target_bucket.startswith("farm-seges-ai-archive-restore"):
        raise ValueError("restore target must use the dedicated farm archive-restore bucket prefix")
    if manifest_bucket == target_bucket or target_bucket == "farm-seges-ai-records":
        raise ValueError("restore target must be separate from the archive and production record buckets")
    if not manifest_object.startswith("field-archive/manifest/") or not manifest_object.endswith(".json"):
        raise ValueError("provide one per-snapshot JSON manifest path under field-archive/manifest/")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + uuid.uuid4().hex[:8]
    target_prefix = f"restore-drills/{run_id}"
    with tempfile.TemporaryDirectory(prefix="farm-archive-restore-") as temporary:
        root = Path(temporary)
        manifest_path = root / "manifest.json"
        _download(manifest_bucket, manifest_object, manifest_path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        archive_relative_object = str(manifest.get("archive_object", ""))
        expected_digest = str(manifest.get("sha256", ""))
        expected_members = manifest.get("members")
        expected_bytes = manifest.get("bytes")
        if not re.fullmatch(r"[0-9a-f]{64}", expected_digest):
            raise ValueError("manifest digest is missing or malformed")
        if not isinstance(expected_members, int) or expected_members <= 0:
            raise ValueError("manifest member count is missing or invalid")
        if not isinstance(expected_bytes, int) or expected_bytes <= 0:
            raise ValueError("manifest byte count is missing or invalid")
        relative_archive_path = PurePosixPath(archive_relative_object)
        if (
            relative_archive_path.is_absolute()
            or not relative_archive_path.parts
            or ".." in relative_archive_path.parts
            or "\\" in archive_relative_object
            or not archive_relative_object.endswith(".tar.gz")
        ):
            raise ValueError("manifest archive object is not a safe relative archive path")
        archive_object = f"field-archive/{archive_relative_object}"

        archive_path = root / "snapshot.tar.gz"
        _download(manifest_bucket, archive_object, archive_path)
        if archive_path.stat().st_size != expected_bytes:
            raise ValueError("downloaded archive byte count does not match its manifest")
        with archive_path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != expected_digest:
            raise ValueError("downloaded archive digest does not match its manifest")

        extracted = root / "field-notes"
        extracted.mkdir()
        written = 0
        expected_files: dict[str, str] = {}
        with tarfile.open(archive_path, mode="r:gz") as archive:
            members = archive.getmembers()
            if len(members) != expected_members:
                raise ValueError("archive member count does not match its manifest")
            for member in members:
                relative = _safe_member_name(member.name)
                if not member.isfile() or relative.suffix.lower() != ".json":
                    raise ValueError("archive contains a non-regular member; restore refused")
                destination = extracted.joinpath(*relative.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    raise ValueError("archive member could not be read")
                with source, destination.open("xb") as output:
                    shutil.copyfileobj(source, output)
                if destination.suffix.lower() == ".json":
                    json.loads(destination.read_text(encoding="utf-8"))
                with destination.open("rb") as stream:
                    expected_files[relative.as_posix()] = hashlib.file_digest(
                        stream, "sha256"
                    ).hexdigest()
                written += 1

        target = f"gs://{target_bucket}/{target_prefix}/field-notes"
        _run_gcloud("storage", "rsync", "--recursive", str(extracted), target)
        target_listing = f"{target}/"
        listing = _run_gcloud("storage", "ls", "--recursive", target_listing).splitlines()
        restored_objects = [line.strip() for line in listing if line.strip()]
        actual_names = {
            line.removeprefix(target_listing).replace("\\", "/")
            for line in restored_objects
            if line.startswith(target_listing)
        }
        if actual_names != set(expected_files):
            raise ValueError("isolated GCS restore member paths do not match the source archive")
        for relative_name, expected_file_digest in expected_files.items():
            restored_path = root / "restored" / Path(*PurePosixPath(relative_name).parts)
            restored_path.parent.mkdir(parents=True, exist_ok=True)
            _run_gcloud(
                "storage", "cp", f"{target}/{relative_name}", str(restored_path)
            )
            with restored_path.open("rb") as stream:
                restored_digest = hashlib.file_digest(stream, "sha256").hexdigest()
            if restored_digest != expected_file_digest:
                raise ValueError(f"restored object digest mismatch: {relative_name}")

    return {
        "ok": True,
        "manifest_object": manifest_object,
        "archive_object": archive_relative_object,
        "sha256": expected_digest,
        "members": written,
        "restore_target": f"gs://{target_bucket}/{target_prefix}/field-notes/",
        "restored_objects": len(restored_objects),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "production_bucket_written": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-bucket", required=True)
    parser.add_argument("--manifest-object", required=True)
    parser.add_argument("--target-bucket", required=True, help="Separate farm restore-drill bucket")
    args = parser.parse_args(argv)
    try:
        receipt = restore(args.archive_bucket, args.manifest_object, args.target_bucket)
    except Exception as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
