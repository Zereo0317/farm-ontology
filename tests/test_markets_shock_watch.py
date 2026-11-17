"""Offline tests for the shock-watch threshold engine.

Runs against the recorded fixture facts only. No network, no scheduler,
no persistence: the engine emits records and the tests check them.
"""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone

from farm_ontology.markets import pit_dataset as pit
from farm_ontology.markets import shock_watch as sw
from farm_ontology.markets.pit_dataset import MarketFact
from farm_ontology.markets.shock_watch import (
    MarketRule,
    ShockFlag,
    ShockGap,
    evaluate,
    flag_payload,
    gaps_payload,
)

AS_OF = datetime(2026, 11, 18, tzinfo=timezone.utc)
LATE = datetime(2027, 6, 1, tzinfo=timezone.utc)


def ams_override(value: float, fact_time: datetime) -> MarketFact:
    """A newer AMS cash-bid fact with a replaced printed average."""
    factory_row = next(
        row
        for row in pit.all_facts()
        if row.feed == pit.FEED_AMS_SOYBEAN_BID and row.metric == "cash_bid_average"
    )
    return MarketFact(
        **{
            **factory_row.__dict__,
            "fact_time": fact_time,
            "value": value,
        }
    )


class SeededRulesTest(unittest.TestCase):
    def test_seed_count_and_kinds(self) -> None:
        self.assertEqual(len(sw.SHOCK_RULES), 8)
        kinds = {rule.rule_kind for rule in sw.SHOCK_RULES}
        self.assertEqual(kinds, {"threshold", "text-change", "presence"})

    def test_seed_descriptions_record_provenance(self) -> None:
        for rule in sw.SHOCK_RULES:
            self.assertTrue(rule.description, rule.rule_id)
            self.assertIn("recorded fixture", rule.description)


class EvaluateSilenceTest(unittest.TestCase):
    """The recorded fixture sits inside its own bands: total silence."""

    def test_recorded_facts_fire_nothing(self) -> None:
        flags, gaps = evaluate(sw.SHOCK_RULES, pit.all_facts(), AS_OF)
        self.assertEqual(flags, ())
        self.assertEqual(gaps, ())


class ThresholdCasesTest(unittest.TestCase):
    def test_below_band_fires_lower_rule_only(self) -> None:
        facts = list(pit.all_facts()) + [ams_override(10.5, datetime(2026, 11, 17, 6, 0, tzinfo=timezone.utc))]
        flags, gaps = evaluate(sw.SHOCK_RULES, facts, AS_OF)
        self.assertEqual(gaps, ())
        fired = [flag.rule_id for flag in flags]
        self.assertEqual(fired, ["ams-bid-below-recorded-band"])
        self.assertEqual(flags[0].observed_value, 10.5)
        self.assertLessEqual(flags[0].evidence_fact_time, flags[0].fired_at)

    def test_above_band_fires_upper_rule_only(self) -> None:
        facts = list(pit.all_facts()) + [ams_override(12.0, datetime(2026, 11, 17, 6, 0, tzinfo=timezone.utc))]
        flags, gaps = evaluate(sw.SHOCK_RULES, facts, AS_OF)
        self.assertEqual(gaps, ())
        self.assertEqual([flag.rule_id for flag in flags], ["ams-bid-above-recorded-band"])

    def test_flag_id_is_deterministic(self) -> None:
        facts = list(pit.all_facts()) + [ams_override(10.5, datetime(2026, 11, 17, 6, 0, tzinfo=timezone.utc))]
        flags_a, _ = evaluate(sw.SHOCK_RULES, facts, AS_OF)
        flags_b, _ = evaluate(sw.SHOCK_RULES, facts, AS_OF)
        self.assertEqual([flag.flag_id for flag in flags_a], [flag.flag_id for flag in flags_b])


class TextChangeCasesTest(unittest.TestCase):
    def test_changed_cycle_text_fires(self) -> None:
        wasde = next(
            row
            for row in pit.all_facts()
            if row.feed == pit.FEED_USDA_WASDE and row.metric == "issue_cycle"
        )
        moved = MarketFact(
            **{
                **wasde.__dict__,
                "fact_time": datetime(2026, 12, 10, tzinfo=timezone.utc),
                "value_text": "December 2026 report linked from the page",
            }
        )
        facts = [*pit.all_facts(), moved]
        flags, gaps = evaluate(sw.SHOCK_RULES, facts, datetime(2026, 12, 11, tzinfo=timezone.utc))
        self.assertEqual(gaps, ())
        fired = {flag.rule_id for flag in flags}
        self.assertIn("wasde-issue-cycle-moved", fired)
        self.assertIn("November 2026 report linked from the page", [f.expected_text for f in flags if f.rule_id == "wasde-issue-cycle-moved"])


class GapSemanticsTest(unittest.TestCase):
    def test_stale_series_is_a_gap_not_a_flag(self) -> None:
        flags, gaps = evaluate(sw.SHOCK_RULES, pit.all_facts(), LATE)
        self.assertEqual(flags, ())
        self.assertEqual(len(gaps), len(sw.SHOCK_RULES))
        reasons = {gap.reason for gap in gaps}
        self.assertIn("no fact for the metric inside the lookback window", reasons)

    def test_presence_rule_gaps_when_metric_stores_no_value(self) -> None:
        rule = MarketRule(
            rule_id="probe-presence-value",
            rule_kind="presence",
            subject=pit.SUBJECT_WASDE,
            metric="storage_scope",
            description="probe",
        )
        flags, gaps = evaluate([rule], pit.all_facts(), AS_OF)
        self.assertEqual(flags, ())
        self.assertEqual(gaps[0].reason, "the metric is known but stores no value")


class ValidationTest(unittest.TestCase):
    def test_mixed_kind_rules_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            MarketRule(
                rule_id="x",
                rule_kind="threshold",
                subject=pit.SUBJECT_AMS_BID,
                metric="cash_bid_average",
                description="x",
                comparator="<",
                level=1.0,
                expected_text="should not be here",
            )
        with self.assertRaises(ValueError):
            MarketRule(
                rule_id="y",
                rule_kind="text-change",
                subject=pit.SUBJECT_AMS_BID,
                metric="cash_bid_average",
                description="y",
                level=1.0,
            )
        with self.assertRaises(ValueError):
            MarketRule(
                rule_id="z",
                rule_kind="presence",
                subject=pit.SUBJECT_AMS_BID,
                metric="cash_bid_average",
                description="z",
                level=1.0,
            )

    def test_bogus_comparator_rejected(self) -> None:
        with self.assertRaises(ValueError):
            MarketRule(
                rule_id="c",
                rule_kind="threshold",
                subject=pit.SUBJECT_AMS_BID,
                metric="cash_bid_average",
                description="c",
                comparator="!=",
                level=1.0,
            )


class PayloadTest(unittest.TestCase):
    def test_flag_payload_json_round_trip(self) -> None:
        facts = list(pit.all_facts()) + [ams_override(10.5, datetime(2026, 11, 17, 6, 0, tzinfo=timezone.utc))]
        flags, _ = evaluate(sw.SHOCK_RULES, facts, AS_OF)
        payload = flag_payload(flags[0])
        rebuilt = json.loads(json.dumps(payload))
        self.assertEqual(rebuilt, payload)
        for key in (
            "flag_id",
            "rule_id",
            "rule_kind",
            "subject",
            "metric",
            "fired_at",
            "evidence_fact_time",
            "description",
            "observed_value",
        ):
            self.assertIn(key, rebuilt)

    def test_gaps_payload_shape(self) -> None:
        flags, gaps = evaluate(sw.SHOCK_RULES, pit.all_facts(), LATE)
        payloads = gaps_payload(gaps)
        self.assertEqual(len(payloads), len(gaps))
        self.assertTrue(all(set(item) == {"rule_id", "subject", "metric", "reason"} for item in payloads))

    def test_real_datatypes_used(self) -> None:
        probe = ShockFlag(
            rule_id="r",
            rule_kind=sw.RULE_PRESENCE,
            subject="s",
            metric="m",
            fired_at=AS_OF,
            evidence_fact_time=AS_OF,
            description="d",
        )
        self.assertTrue(probe.flag_id.startswith("shock:r@"))
        gap = ShockGap(rule_id="r", subject="s", metric="m", reason="why")
        self.assertEqual(gap.reason, "why")


if __name__ == "__main__":
    unittest.main()
