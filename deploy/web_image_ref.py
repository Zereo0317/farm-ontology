"""Validate an immutable digest for the farm web image line."""
import re
import sys

BASE = "asia-east1-docker.pkg.dev/seges-ai/cloud-run-source-deploy/farm-seges-ai-web"


def normalize(value):
    value = value.strip()
    if value.startswith(BASE + "@"):
        value = value[len(BASE) + 1:]
    if re.fullmatch(r"[a-f0-9]{64}", value):
        value = "sha256:" + value
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", value):
        raise ValueError("expected the farm web image's sha256 digest")
    return BASE + "@" + value


if __name__ == "__main__":
    print(normalize(sys.argv[1]))
