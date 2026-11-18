"""Egress probe for the Cloud Run worker network path.

Distinguishes DNS/TLS/handshake trouble from HTTP trouble on the two
hosts the ingest workers call: the single-runs endpoint (the forecast
worker's feed) and the apex forecast endpoint (the HTTP service's live
weather). Three attempts per host with a short backoff; a 400 from
single-runs still PROVES the TLS path works (a parsed request error is
an application-level reply). Run it as a Cloud Run job when a worker
start failing with handshake timeouts:

    gcloud run jobs deploy farm-probe-egress --source . \\
        --command python --args pipelines/probe_egress.py ...

Logs are stdout/flush=True so Cloud Logging captures them verbatim.
"""

from __future__ import annotations

import time
import urllib.request

HOSTS = (
    (
        "https://single-runs-api.open-meteo.com/v1/forecast"
        "?latitude=42.7&longitude=142.4&hourly=precipitation&models=jma_msm"
    ),
    (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=42.7&longitude=142.4&current=temperature_2m"
    ),
)
ATTEMPTS = 3
TIMEOUT = 20
BACKOFF = 3


def main() -> int:
    verdicts = []
    for host in HOSTS:
        name = host.split("/")[2]
        for attempt in range(1, ATTEMPTS + 1):
            started = time.time()
            try:
                with urllib.request.urlopen(host, timeout=TIMEOUT) as response:
                    response.read(200)
                print(f"{name} try{attempt}: OK {time.time() - started:.2f}s", flush=True)
                verdicts.append((name, True))
                break
            except Exception as error:  # probe: report ANY failure mode by name
                print(
                    f"{name} try{attempt}: FAIL {type(error).__name__} {error} "
                    f"after {time.time() - started:.2f}s",
                    flush=True,
                )
                if attempt < ATTEMPTS:
                    time.sleep(BACKOFF)
                else:
                    verdicts.append((name, False))
    for name, ok in verdicts:
        print(f"VERDICT {name}: {'reachable' if ok else 'UNREACHABLE'}", flush=True)
    return 0 if all(ok for _name, ok in verdicts) else 1


if __name__ == "__main__":
    raise SystemExit(main())
