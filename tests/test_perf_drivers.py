"""Offline tests for the perf drivers (task-12, Sprint-E).

No network, no gcloud: these pin the PURE halves of the load driver and
tie the shipped report/JSON artifacts together, so the runbook's quoted
numbers cannot drift from the recorded evidence files.
"""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_driver():
    spec = importlib.util.spec_from_file_location(
        "perf_load_test", ROOT / "perf" / "load_test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DRIVER = _load_driver()


class RampPlanTest(unittest.TestCase):
    def test_plan_ends_drained(self) -> None:
        plan = DRIVER.ramp_plan(4, 12)
        self.assertEqual(plan[-1][0], 0)
        self.assertEqual(sum(dwell for _level, dwell in plan), 12.0)

    def test_plan_never_exceeds_vu(self) -> None:
        for _level, _dwell in DRIVER.ramp_plan(50, 300):
            self.assertLessEqual(_level, 50)

    def test_hold_dominates(self) -> None:
        plan = DRIVER.ramp_plan(50, 300)
        hold_level, hold_dwell = plan[-2]
        self.assertEqual(hold_level, 50)
        ramp_total = sum(dwell for level, dwell in plan[:-2] if level < 50)
        self.assertGreater(hold_dwell, ramp_total)


class SummariserTest(unittest.TestCase):
    def samples(self):
        samples = []
        for i in range(60):
            samples.append(
                {"route": "/livez", "status": 200, "elapsed_ms": 100 + i, "error": None}
            )
        for i in range(30):
            samples.append(
                {
                    "route": "/farm/weather",
                    "status": 200,
                    "elapsed_ms": 300 + i * 2,
                    "error": None,
                }
            )
        samples.append(
            {"route": "/livez", "status": 500, "elapsed_ms": 55.0, "error": "HTTP 500"}
        )
        return samples

    def test_percentiles_and_error_rate(self) -> None:
        summary = DRIVER.summarise_samples(
            self.samples(), vu=5, seconds=30, base="http://test"
        )
        self.assertEqual(summary["requests"], 91)
        self.assertEqual(summary["errors"], 1)
        self.assertAlmostEqual(summary["error_rate_pct"], 1.099, places=2)
        self.assertGreaterEqual(summary["p95_ms"], summary["p50_ms"])
        self.assertGreaterEqual(summary["p99_ms"], summary["p95_ms"])

    def test_within_bar_verdict(self) -> None:
        clean = [s for s in self.samples() if s["error"] is None]
        summary = DRIVER.summarise_samples(clean, vu=5, seconds=30, base="http://test")
        self.assertFalse(summary["honest_bar"]["breaching"])
        self.assertTrue(summary["honest_bar"]["p95_lt_400ms"])

    def test_latency_breach_is_recorded_not_smoothed(self) -> None:
        hot = [{**s, "elapsed_ms": 900} for s in self.samples()]
        summary = DRIVER.summarise_samples(hot, vu=5, seconds=30, base="http://test")
        self.assertTrue(summary["honest_bar"]["breaching"])
        self.assertEqual(summary["p95_ms"], 900)
        rendered = DRIVER.render_summary(summary)
        self.assertIn("BREACHED", rendered)

    def test_error_breach_recorded(self) -> None:
        flaky = [
            {**s, "error": f"boom {i}"} if i % 3 == 0 else s
            for i, s in enumerate(self.samples())
        ]
        summary = DRIVER.summarise_samples(flaky, vu=5, seconds=30, base="http://test")
        self.assertTrue(summary["honest_bar"]["breaching"])
        self.assertTrue(summary["first_errors"])

    def test_empty_samples_refused(self) -> None:
        with self.assertRaises(ValueError):
            DRIVER.summarise_samples([], vu=1, seconds=1, base="http://test")

    def test_per_route_table_built(self) -> None:
        summary = DRIVER.summarise_samples(
            self.samples(), vu=5, seconds=30, base="http://test"
        )
        self.assertIn("/livez", summary["per_route"])
        self.assertIn("/farm/weather", summary["per_route"])
        livez = summary["per_route"]["/livez"]
        self.assertEqual(livez["count"], 61)  # 60 clean + 1 error sample
        self.assertGreater(livez["error_pct"], 0)


class ArtifactConsistencyTest(unittest.TestCase):
    """The report must quote the SAME numbers the recorded JSONs carry."""

    def test_verdict_file_carries_the_honest_bar(self) -> None:
        verdict = json.loads((ROOT / "perf" / "verdict-k6.json").read_text(encoding="utf-8"))
        for key in ("p50_ms", "p95_ms", "p99_ms", "error_rate_pct", "honest_bar", "per_route"):
            self.assertIn(key, verdict)
        self.assertTrue(verdict["honest_bar"]["breaching"], "this run recorded a breach")
        self.assertEqual(
            verdict["base_url"], "https://farm-seges-ai-451400509859.asia-east1.run.app"
        )

    def test_native_dump_agrees_with_the_verdict(self) -> None:
        verdict = json.loads((ROOT / "perf" / "verdict-k6.json").read_text(encoding="utf-8"))
        metrics = json.loads((ROOT / "perf" / "k6-metrics-full.json").read_text(encoding="utf-8"))
        duration = metrics["metrics"]["http_req_duration"]
        self.assertEqual(verdict["p95_ms"], round(duration["p(95)"]))
        self.assertEqual(verdict["p50_ms"], round(duration["med"]))
        livez = metrics["metrics"]["http_req_duration{name:livez}"]
        self.assertEqual(verdict["per_route"]["livez"]["p50_ms"], round(livez["med"]))

    def test_report_quotes_the_recorded_breach(self) -> None:
        report = (ROOT / "perf" / "RESILIENCE-REPORT.md").read_text(encoding="utf-8")
        verdict = json.loads((ROOT / "perf" / "verdict-k6.json").read_text(encoding="utf-8"))
        self.assertIn(f"p95 = **{verdict['p95_ms']} ms**", report)
        self.assertIn("BREACHED", report)
        self.assertIn("recorded verbatim", report.lower())

    def test_drill_results_show_full_lifecycle(self) -> None:
        results = json.loads(
            (ROOT / "perf" / "chaos-20261118T120905Z" / "RESULTS.json").read_text(encoding="utf-8")
        )
        self.assertTrue(results["verdict"]["drill_ok"])
        snapshot = results["verdict"]["restored_snapshot"]
        self.assertEqual(list(snapshot.values())[0], "acknowledged")
        cold = results["verdict"]["cold_start_measured"]
        self.assertGreater(cold[0], cold[1], "cold hit must be slower than the first warm hit")

    def test_chaos_script_is_staging_bound(self) -> None:
        text = (ROOT / "perf" / "chaos-drill.ps1").read_text(encoding="utf-8")
        self.assertIn("farm-seges-ai-staging", text)
        self.assertIn("STAGING ONLY", text.upper())
        # no prod service name in a MUTATING gcloud verb line
        for line in text.splitlines():
            if "farm-seges-ai " in line and ("run services update" in line or "run deploy" in line):
                self.fail(f"prod mutating line found: {line}")

    def test_drill_ledger_on_bucket_shape(self) -> None:
        from farm_ontology.actuation.command_ledger import CommandLedger

        ledger_path = (
            ROOT / "perf" / "chaos-20261118T120905Z" / "ledger-20261118T120905Z.jsonl"
        )
        ledger = CommandLedger.from_path(str(ledger_path))  # verifies the chain
        report = ledger.verify_chain()
        self.assertTrue(report["ok"])
        self.assertEqual(list(ledger.snapshot().values())[-1], "acknowledged")


class DisciplineTest(unittest.TestCase):
    def test_stdlib_driver_has_no_import_time_side_effects(self) -> None:
        # importing the module performed no requests (it defines, not drives)
        self.assertTrue(callable(DRIVER.run_load))
        self.assertTrue(callable(DRIVER.summarise_samples))
        self.assertEqual(DRIVER.DEFAULT_BASE.count("run.app"), 1)

    def test_gate_guard_matches_house_pattern(self) -> None:
        # the live capture guard in the markets sources stays coherent with
        # the perf discipline: same env var, same truthy set
        from farm_ontology.markets.sources import capture_online
        from farm_ontology.testing import ONLINE_ENV

        import os

        old = os.environ.pop(ONLINE_ENV, None)
        try:
            with self.assertRaises(PermissionError):
                capture_online("zs.f", "d", "2026-01-01", "2026-02-01", ".")
        finally:
            if old is not None:
                os.environ[ONLINE_ENV] = old


if __name__ == "__main__":
    unittest.main()
