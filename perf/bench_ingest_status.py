"""Offline micro-benchmark for the ingest-status compose (task-15).

Deterministic, NO NETWORK: a fully-real-shaped GCS transport sleeps an
injected artificial latency per HTTP ask (an RTT stand-in), and the
benchmark times three paths over the SAME seeded store:

- ``legacy``  the Sprint-E deep composer (per-job list + full serial reads);
- ``fast``    the task-15 composer (two concurrent listings + parallel
              minimal GETs through the singleflight row cache);
- ``fast-warm`` a second compose with everything row-cached.

Run: ``python perf/bench_ingest_status.py [--rtt-ms 25] [--iterations 12]``
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from farm_ontology import ingest_core  # noqa: E402
from farm_ontology.ingest_status import WATCHED_JOBS, compose_status, summarize_job  # noqa: E402
from farm_ontology.record_store import GcsBackend  # noqa: E402

BUCKET = "farm-seges-ai-records"


class DelayedRealShapedGcs:
    """Real-metadata GCS JSON API fixture with a per-ask delay (RTT)."""

    def __init__(self, rtt_s: float):
        self.rtt = rtt_s
        self.objects: dict[str, bytes] = {}
        self.requests = 0

    def __call__(self, method, url, headers, body):
        self.requests += 1
        time.sleep(self.rtt)
        parsed = urllib.parse.urlsplit(url)
        query = urllib.parse.parse_qs(parsed.query)
        if method == "POST" and parsed.path == f"/upload/storage/v1/b/{BUCKET}/o":
            self.objects[query["name"][0]] = body
            return 200, {}, json.dumps({"name": query["name"][0]}).encode("utf-8")
        if method == "GET" and parsed.path == f"/storage/v1/b/{BUCKET}/o":
            prefix = query["prefix"][0]
            items = [
                {"name": n, "bucket": BUCKET, "generation": "1763341200000000",
                 "metageneration": "1", "contentType": "application/json",
                 "storageClass": "STANDARD", "size": str(len(self.objects[n])),
                 "md5Hash": "rL0Y20zC+Fzt72VPzMSk2A==", "crc32c": "vVSosQ==",
                 "etag": "CKaI4rDVuPECEAM=",
                 "timeCreated": "2026-11-18T02:00:00.123Z",
                 "updated": "2026-11-18T02:00:00.456Z"}
                for n in sorted(self.objects) if n.startswith(prefix)
            ]
            document = {"kind": "storage#objects", "totalSize": len(items)}
            if items:
                document["items"] = items
            return 200, {}, json.dumps(document).encode("utf-8")
        if method == "GET" and parsed.path.startswith(f"/storage/v1/b/{BUCKET}/o/"):
            name = urllib.parse.unquote(parsed.path.split("/o/", 1)[1])
            if name not in self.objects:
                return 404, {}, json.dumps({"error": {"code": 404, "message": "no"}}).encode("utf-8")
            if query.get("alt", [None])[0] == "media":
                return 200, {}, self.objects[name]
            return 200, {}, json.dumps({"name": name, "updated": "2026-11-18T02:00:00.456Z"}).encode("utf-8")
        return 400, {}, json.dumps({"error": {"code": 400, "message": "unexpected"}}).encode("utf-8")


def pctl(values: list[float], fraction: float) -> int:
    ordered = sorted(values)
    index = min(len(ordered) - 1, math.ceil(fraction * len(ordered)) - 1)
    return int(round(ordered[max(0, index)]))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rtt-ms", type=float, default=25.0)
    parser.add_argument("--iterations", type=int, default=12)
    parser.add_argument("--rows-per-job", type=int, default=50)
    args = parser.parse_args(argv)

    transport = DelayedRealShapedGcs(args.rtt_ms / 1000.0)
    backend = GcsBackend(BUCKET, "pipelines", request_fn=transport, token_fn=lambda: ("tok", 3600))
    base = datetime(2026, 11, 1, 2, 0, tzinfo=timezone.utc)
    now = base + timedelta(days=args.rows_per_job + 1)
    for job in WATCHED_JOBS:
        for index in range(args.rows_per_job):
            moment = base + timedelta(days=index)
            ingest_core.append_run(
                backend, job=job, now=moment, started=moment,
                finished=moment + timedelta(seconds=1), ok=True, row_count=1,
            )

    legacy_times = []
    for _ in range(max(1, args.iterations // 3)):  # the legacy path is SLOW
        started = time.perf_counter()
        for job in WATCHED_JOBS:
            summarize_job(backend, job, now=now)
        legacy_times.append((time.perf_counter() - started) * 1000.0)

    ingest_core.clear_row_caches()
    fast_times = []
    for _ in range(args.iterations):
        ingest_core.clear_row_caches()
        started = time.perf_counter()
        compose_status(backend, now=now)
        fast_times.append((time.perf_counter() - started) * 1000.0)

    warm_times = []
    for _ in range(args.iterations):
        started = time.perf_counter()
        compose_status(backend, now=now)
        warm_times.append((time.perf_counter() - started) * 1000.0)

    report = {
        "bench": "ingest-status compose",
        "rtt_ms_per_ask": args.rtt_ms,
        "iterations": args.iterations,
        "rows_per_job": args.rows_per_job,
        "storage_asks_total": transport.requests,
        "legacy": {
            "p50_ms": pctl(legacy_times, 0.50),
            "p95_ms": pctl(legacy_times, 0.95),
        },
        "fast": {
            "p50_ms": pctl(fast_times, 0.50),
            "p95_ms": pctl(fast_times, 0.95),
        },
        "fast_warm": {
            "p50_ms": pctl(warm_times, 0.50),
            "p95_ms": pctl(warm_times, 0.95),
        },
        "speedup_p50_vs_legacy": round(
            pctl(legacy_times, 0.50) / max(0.001, pctl(fast_times, 0.50)), 1
        ),
    }
    print(json.dumps(report, indent=2))
    Path("perf/bench-ingest-status.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
