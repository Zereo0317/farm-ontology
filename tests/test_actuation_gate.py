"""Tests for the Phase-4 gate (WS5.4) — the clerk that says NO."""

import unittest

from farm_ontology.actuation.command_ledger import ActuationGap
from farm_ontology.actuation.gate import (
    GATE_FACT_MEANINGS,
    GATE_FACT_NAMES,
    SATISFYING_EVIDENCE,
    GateCheck,
)

_ALL_TRUE = {name: True for name in GATE_FACT_NAMES}


class VerdictTests(unittest.TestCase):
    def test_default_gate_is_shut_with_all_six_gaps(self):
        gate = GateCheck()
        self.assertFalse(gate.eligible_for_live_commands())
        report = gate.assessment()
        self.assertEqual(len(report["gaps"]), 6)
        self.assertTrue(all(gap["kind"] == "missing" for gap in report["gaps"]))
        self.assertIn("no live machine command", report["note"])

    def test_all_true_is_the_only_way_open(self):
        gate = GateCheck(**_ALL_TRUE)
        self.assertTrue(gate.eligible_for_live_commands())
        self.assertEqual(gate.gaps(), ())
        self.assertEqual(gate.refusal_summary(), "")

    def test_five_true_one_false_stays_shut_and_names_it(self):
        facts = dict(_ALL_TRUE)
        facts["audit_quarter_clean"] = False
        gate = GateCheck(**facts)
        self.assertFalse(gate.eligible_for_live_commands())
        gaps = gate.gaps()
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["fact"], "audit_quarter_clean")
        self.assertEqual(gaps[0]["kind"], "failed")

    def test_each_single_false_is_individually_named(self):
        for missing in GATE_FACT_NAMES:
            with self.subTest(fact=missing):
                facts = dict(_ALL_TRUE)
                facts[missing] = False
                gate = GateCheck(**facts)
                named = [g["fact"] for g in gate.gaps()]
                self.assertEqual(named, [missing])

    def test_every_gap_is_verbose(self):
        gate = GateCheck()  # everything unassessed
        for gap in gate.gaps():
            self.assertIn("meaning", gap)
            self.assertIn("satisfied_by", gap)
            self.assertGreater(len(gap["meaning"]), 30)
            self.assertGreater(len(gap["satisfied_by"]), 30)
            self.assertEqual(gap["meaning"], GATE_FACT_MEANINGS[gap["fact"]])
            self.assertEqual(gap["satisfied_by"], SATISFYING_EVIDENCE[gap["fact"]])

    def test_refusal_summary_lists_all_open_facts(self):
        gate = GateCheck(min_instances=True)
        summary = gate.refusal_summary()
        self.assertIn("ineligible", summary)
        self.assertIn("auth_configured", summary)
        self.assertIn("audit_quarter_clean", summary)
        self.assertNotIn("min_instances,", summary.split(":", 1)[1].split("-")[0])


class InputHygieneTests(unittest.TestCase):
    def test_none_vs_false_distinction(self):
        assessed = GateCheck(min_instances=False)
        unassessed = GateCheck()
        kinds = {g["fact"]: g["kind"] for g in assessed.gaps()}
        self.assertEqual(kinds["min_instances"], "failed")
        self.assertEqual(
            {g["fact"]: g["kind"] for g in unassessed.gaps()}["min_instances"],
            "missing",
        )

    def test_truthy_coercion_refused(self):
        for bad in ("yes", 1, "true", [], {}):
            with self.subTest(value=bad):
                with self.assertRaises(ActuationGap) as ctx:
                    GateCheck(min_instances=bad)
                self.assertEqual(ctx.exception.gap, "gate_fact_not_boolean")

    def test_from_facts_maps_and_refuses_unknown(self):
        gate = GateCheck.from_facts({**_ALL_TRUE, "min_instances": False})
        self.assertFalse(gate.eligible_for_live_commands())
        with self.assertRaises(ActuationGap) as ctx:
            GateCheck.from_facts({"auto_pilot_enabled": True})
        self.assertEqual(ctx.exception.gap, "gate_fact_unknown")

    def test_from_facts_non_mapping_refused(self):
        with self.assertRaises(ActuationGap) as ctx:
            GateCheck.from_facts(["min_instances"])
        self.assertEqual(ctx.exception.gap, "gate_facts_ill_formed")

    def test_partial_facts_means_unassessed_rest(self):
        gate = GateCheck.from_facts({"min_instances": True})
        self.assertFalse(gate.eligible_for_live_commands())
        self.assertEqual(len(gate.gaps()), 5)


class VocabularyContractTests(unittest.TestCase):
    def test_exact_gate_fact_names(self):
        self.assertEqual(
            set(GATE_FACT_NAMES),
            {
                "min_instances",
                "auth_configured",
                "watchdog_defined",
                "kill_switch_contract_signed",
                "field_drill_completed",
                "audit_quarter_clean",
            },
        )

    def test_meanings_carry_doctrine_anchors(self):
        self.assertIn("HALT", GATE_FACT_MEANINGS["watchdog_defined"])
        self.assertIn("risk owner", GATE_FACT_MEANINGS["kill_switch_contract_signed"])
        loop = "proposed->approved->dispatched->acknowledged"
        squashed = SATISFYING_EVIDENCE["field_drill_completed"].replace(" ", "")
        self.assertIn(loop, squashed)


if __name__ == "__main__":
    unittest.main()
