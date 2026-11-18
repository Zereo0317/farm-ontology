"""Stdlib-threads load driver — the always-available fallback (task-12 X7).

k6 is preferred (``perf/load-test.js``); when k6 is not installed (or on
a machine where winget is forbidden), THIS script drives the same ramp
with plain ``threading`` + ``urllib`` and emits the SAME honest-bar
summary shape (p50/p95/p99, error rate, per-route table), so the numbers
matter more than the tool — the card's own wording.

Offline discipline: this module is a DRIVER — running it performs real
HTTP against ``--base`` (default the prod service). Importing it costs
nothing; the offline unit test only exercises the pure summariser
(:func:`summarise_samples`) and the ramp-plan calculator.

Usage::

    python perf/load_test.py                       # 50 VU / 5 min prod ramp
    python perf/load_test.py --vu 10 --seconds 60  # quick check
    python perf/load_test.py --base http://127.0.0.1:8080 --seconds 20
"""

from __future__ import annotations

import argparse
import json
import math
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_BASE = "https://farm-seges-ai-451400509859.asia-east1.run.app"
ROUTES = ("/livez", "/farm/ingest-status", "/farm/weather")
#: Visits per iteration cycle: livez 6, ingest-status 3, weather 1 — keeps
#: the third-party-calling route the rarest, same weighting as the k6 file.
ROUTE_CYCLE = ("/livez",) * 6 + ("/farm/ingest-status",) * 3 + ("/farm/weather",)
USER_AGENT = "farm-ontology perf/load_test.py (task-12 Sprint-E)"
THINK_S = 0.15  # small think time between requests


def ramp_plan(vus: int, seconds: int) -> list[tuple[int, float]]:
    """``(level, dwell_seconds)`` steps mirroring the k6 stages: linear
    ramp-up over the first quarter, hold half, drain the last quarter."""
    ramp_up = max(1, seconds // 4)
    hold = max(1, seconds // 2)
    drain = max(1, seconds - ramp_up - hold)
    plan: list[tuple[int, float]] = []
    for tick in range(ramp_up):
        level = max(1, min(vus, round((tick + 1) * vus / ramp_up)))
        plan.append((level, 1.0))
    plan.append((vus, float(hold)))
    plan.append((0, float(drain)))
    return plan


def summarise_samples(samples: list[dict], *, vu: int, seconds: int, base: str) -> dict:
    """The honest-bar summary over raw per-request samples.

    Pure function; the offline test exercises THIS, never the network.
    A sample: {route, status, elapsed_ms, error (str|None)}.
    Errors <0.5% and p95 <400ms = within bar; anything else is a breach
    that must be reported verbatim, not smoothed.
    """
    if not samples:
        raise ValueError("no samples collected; the driver found nothing to summarise")
    latencies = sorted(sample["elapsed_ms"] for sample in samples)
    percentile_map = {0.50: "p50_ms", 0.95: "p95_ms", 0.99: "p99_ms"}

    def pct(fraction: float) -> int:
        index = min(len(latencies) - 1, math.ceil(fraction * len(latencies)) - 1)
        return int(round(latencies[max(0, index)]))

    errors = [sample for sample in samples if sample["error"] is not None]
    error_rate_pct = round(100.0 * len(errors) / len(samples), 3)
    p95 = pct(0.95)
    per_route: dict[str, dict] = {}
    for route in ROUTES:
        route_lat = sorted(
            sample["elapsed_ms"] for sample in samples if sample["route"] == route
        )
        if route_lat:
            per_route[route] = {
                "count": len(route_lat),
                "p50_ms": int(round(route_lat[len(route_lat) // 2])),
                "p95_ms": int(round(route_lat[min(len(route_lat) - 1, math.ceil(0.95 * len(route_lat)) - 1)])),
                "p99_ms": int(round(route_lat[min(len(route_lat) - 1, math.ceil(0.99 * len(route_lat)) - 1)])),
                "error_pct": round(
                    100.0
                    * sum(
                        1
                        for sample in samples
                        if sample["route"] == route and sample["error"] is not None
                    )
                    / len(route_lat),
                    3,
                ),
            }
    return {
        "driver": "python-stdlib-threads",
        "base_url": base,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "vu": vu,
        "seconds": seconds,
        "requests": len(samples),
        "errors": len(errors),
        "error_rate_pct": error_rate_pct,
        "p50_ms": pct(0.50),
        "p95_ms": p95,
        "p99_ms": pct(0.99),
        "per_route": per_route,
        "honest_bar": {
            "p95_lt_400ms": p95 < 400,
            "errors_lt_05pct": error_rate_pct < 0.5,
            "breaching": p95 >= 400 or error_rate_pct >= 0.5,
        },
        "first_errors": [sample["error"] for sample in errors[:5]],
    }


def render_summary(summary: dict) -> str:
    bar = summary["honest_bar"]
    lines = [
        "HONEST BAR SUMMARY (stdlib driver)",
        f"  base_url: {summary['base_url']}",
        f"  vu: {summary['vu']}  seconds: {summary['seconds']}  requests: {summary['requests']}",
        f"  p50/p95/p99 (ms): {summary['p50_ms']} / {summary['p95_ms']} / {summary['p99_ms']}",
        f"  error rate: {summary['error_rate_pct']}%",
        f"  bar p95<400ms: {bar['p95_lt_400ms']}  bar errors<0.5%: {bar['errors_lt_05pct']}",
        f"  VERDICT: {'BREACHED (recorded verbatim)' if bar['breaching'] else 'WITHIN BAR'}",
    ]
    for route, stats in summary["per_route"].items():
        lines.append(
            f"  {route}: n={stats['count']} p50={stats['p50_ms']} "
            f"p95={stats['p95_ms']} p99={stats['p99_ms']} err={stats['error_pct']}%"
        )
    return "\n".join(lines) + "\n"


def _worker(stop: threading.Event, base: str, samples: list, lock: threading.Lock) -> None:
    cycle_len = len(ROUTE_CYCLE)
    cursor = 0
    while not stop.is_set():
        route = ROUTE_CYCLE[cursor % cycle_len]
        cursor += 1
        started = time.perf_counter()
        status, error = 0, None
        try:
            request = urllib.request.Request(
                base + route, headers={"User-Agent": USER_AGENT, "Connection": "close"}
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                response.read()
                status = response.status
        except urllib.error.HTTPError as exc:
            status, error = exc.code, f"HTTP {exc.code} on {route}: {exc.reason}"
        except Exception as exc:  # noqa: BLE001 — a sample, not a crash
            error = f"{type(exc).__name__} on {route}: {exc}"
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        with lock:
            samples.append(
                {"route": route, "status": status, "elapsed_ms": elapsed_ms, "error": error}
            )
        if stop.wait(THINK_S):
            return


def run_load(base: str, vu: int, seconds: int) -> dict:
    """Drive the ramp; returns the honest-bar summary dict.

    Thread pool only ever RAMPS UP during the run (a shrunk pool under a
    shared stop event is all-or-nothing); the drain stops everything at
    the end, which is the semantics that matters for a bar measurement.
    """
    samples: list[dict] = []
    lock = threading.Lock()
    stop = threading.Event()
    plan = ramp_plan(vu, seconds)
    threads: list[threading.Thread] = []
    started = time.monotonic()
    for level, dwell in plan:
        if time.monotonic() - started > seconds:
            break
        while len(threads) < level:
            thread = threading.Thread(
                target=_worker, args=(stop, base, samples, lock), daemon=True
            )
            thread.start()
            threads.append(thread)
        time.sleep(dwell)
    stop.set()
    for thread in threads:
        thread.join(timeout=5)
    return summarise_samples(samples, vu=vu, seconds=seconds, base=base)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--vu", type=int, default=50)
    parser.add_argument("--seconds", type=int, default=300)
    parser.add_argument("--out", default="perf/results-stdlib.json")
    args = parser.parse_args(argv)
    summary = run_load(args.base, args.vu, args.seconds)
    print(render_summary(summary))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
