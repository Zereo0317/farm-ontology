"""Optional watchdog runner; --deliver requires an explicitly configured HTTPS receiver."""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from farm_ontology.ingest_core import open_pipe_backend
from farm_ontology.ingest_watchdog import evaluate


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_receiver(receiver: str) -> None:
    parsed = urllib.parse.urlsplit(receiver)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("a configured HTTPS receiver without credentials or fragment is required")


def send_report(report: dict, receiver: str, *, opener=None) -> None:
    validate_receiver(receiver)
    request = urllib.request.Request(receiver, data=json.dumps(report).encode("utf-8"),
                                     headers={"Content-Type": "application/json"}, method="POST")
    transport = opener or urllib.request.build_opener(_NoRedirect()).open
    with transport(request, timeout=10) as response:
        if not 200 <= response.status < 300:
            raise RuntimeError("watchdog receiver did not return 2xx")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deliver", action="store_true", help="send unhealthy result to configured FARM_WATCHDOG_RECEIVER")
    args = parser.parse_args(argv)
    receiver = os.environ.get("FARM_WATCHDOG_RECEIVER", "").strip()
    if args.deliver:
        try:
            validate_receiver(receiver)
        except ValueError:
            print(json.dumps({"healthy": False, "error": "valid FARM_WATCHDOG_RECEIVER is required for delivery"}))
            return 2
    try:
        report = evaluate(open_pipe_backend(), now=datetime.now(timezone.utc))
    except Exception as error:
        # Do not leak bucket names, credentials, or receiver URLs into logs.
        report = {"healthy": False, "error": "watchdog could not evaluate run history", "error_type": type(error).__name__}
    print(json.dumps(report))
    if args.deliver and not report["healthy"]:
        try:
            send_report(report, receiver)
        except Exception as error:
            print(json.dumps({"delivery": "failed", "error_type": type(error).__name__}), file=sys.stderr)
            return 2
    return 0 if report["healthy"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
