"""Fail-closed checks for promotion of the exact staging revision."""
import argparse
import json
import re
from pathlib import Path


def verified_image(service, revision, runs, sha):
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("expected an exact full commit SHA")
    traffic = service.get("status", {}).get("traffic", [])
    serving = [row for row in traffic if row.get("percent", 0) > 0]
    name = revision.get("metadata", {}).get("name")
    if len(serving) != 1 or serving[0].get("percent") != 100 or serving[0].get("revisionName") != name:
        raise ValueError("staging must serve the verified revision at 100 percent")
    conditions = revision.get("status", {}).get("conditions", [])
    if not any(c.get("type") == "Ready" and c.get("status") == "True" for c in conditions):
        raise ValueError("staging revision is not ready")
    containers = revision.get("spec", {}).get("containers", [])
    if len(containers) != 1:
        raise ValueError("staging must have exactly one container")
    env = {item.get("name"): item.get("value") for item in containers[0].get("env", [])}
    if env.get("FARM_RELEASE_COMMIT") != sha:
        raise ValueError("staging release commit does not match requested commit")
    image = revision.get("status", {}).get("imageDigest", "")
    if not re.fullmatch(r"[a-z0-9.\-/]+@sha256:[0-9a-f]{64}", image):
        raise ValueError("staging revision has no immutable image digest")
    if not any(r.get("head_sha") == sha and r.get("event") == "push" and
               r.get("head_branch") == "main" and r.get("status") == "completed" and
               r.get("conclusion") == "success" for r in runs.get("workflow_runs", [])):
        raise ValueError("no successful main-push test workflow for requested commit")
    return image


def verify_production_config(service):
    containers = service.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
    if len(containers) != 1:
        raise ValueError("production must have exactly one container")
    env = {e.get("name"): e for e in containers[0].get("env", [])}
    for name, expected in {"GCP_PROJECT": "seges-ai", "EE_PROJECT": "seges-ai", "FARM_RECORD_BACKEND": "gcs", "FARM_RECORD_BUCKET": "farm-seges-ai-records"}.items():
        if env.get(name, {}).get("value") != expected:
            raise ValueError(f"production config {name} is missing or incorrect")
    for name, secret in {"PLANET_API_KEY": "Planet-labs", "WEB_ACCESS_TOKEN": "web-access-token"}.items():
        if env.get(name, {}).get("valueFrom", {}).get("secretKeyRef", {}).get("name") != secret:
            raise ValueError(f"production secret {name} is missing or incorrect")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--runs", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--production", required=True)
    args = parser.parse_args()
    def read(path):
        return json.loads(Path(path).read_text(encoding="utf-8"))
    verify_production_config(read(args.production))
    print(verified_image(read(args.service), read(args.revision), read(args.runs), args.sha))


if __name__ == "__main__":
    main()
