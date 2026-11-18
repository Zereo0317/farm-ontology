"""Tests for the arb rehearsal (QA lens over the doctrine lanes).

These tests RUN the rehearsals (offline, tempdir ledgers, injected
clocks) and pin the outcome invariants: every step must pass, the
defect registry must be exactly the recorded set (a silently changed
misalignment is itself a finding), and the headline behaviours — the
grant wall, the premium-budget demand, the HALT freeze, the gate
cheat-death, the cross-vocab refusals — must keep firing.
"""

from __future__ import annotations

import tempfile
import unittest

from farm_ontology.fieldtest import arb_rehearsal as ar


def _all_reports():
    reports, _markdown = ar.run_all_rehearsals()
    return {report.lane: report for report in reports}


class FullRunShapeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.reports = _all_reports()

    def test_five_lanes_present(self) -> None:
        self.assertEqual(
            sorted(self.reports), ["L1", "L2", "L3", "L4", "L5"]
        )

    def test_every_step_passed(self) -> None:
        for lane, report in self.reports.items():
            self.assertEqual(
                report.steps_failed,
                (),
                f"{lane} failed steps: {report.steps_failed}",
            )
            self.assertTrue(report.step_log, f"{lane} ran no steps")

    def test_steps_ok_matches_log(self) -> None:
        for report in self.reports.values():
            self.assertEqual(
                report.steps_ok,
                tuple(step.name for step in report.step_log if step.ok),
            )

    def test_defect_registry_is_exact(self) -> None:
        registry = {
            report.lane: [defect.defect_id for defect in report.defects]
            for report in self.reports.values()
        }
        self.assertEqual(
            registry,
            {
                "L1": ["D1", "D2"],
                "L2": ["D3", "D4"],
                "L3": ["D5", "D6"],
                "L4": ["D9"],
                "L5": ["D7", "D8"],
            },
        )
        severities = {
            defect.defect_id: defect.severity
            for report in self.reports.values()
            for defect in report.defects
        }
        self.assertEqual(severities["D9"], "blocker")
        for defect_id in ("D1", "D2", "D3", "D6", "D8"):
            self.assertEqual(severities[defect_id], "rough")
        for defect_id in ("D4", "D5", "D7"):
            self.assertEqual(severities[defect_id], "cosmetic")

    def test_defects_always_carry_a_named_remedy(self) -> None:
        for report in self.reports.values():
            for defect in report.defects:
                self.assertTrue(defect.named_remedy, defect.defect_id)


class Lane1GrantWallTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report, cls.bridge = ar.run_lane1()

    def test_wall_holds_with_named_violations(self) -> None:
        self.assertIn("rails-verdict-dies-on-grant-state", self.report.steps_ok)
        verdict_step = next(
            step for step in self.report.step_log if step.name == "rails-verdict-dies-on-grant-state"
        )
        self.assertIn("2 R5 violations", verdict_step.detail)

    def test_forged_grant_dies_on_armed_registry(self) -> None:
        step = next(step for step in self.report.step_log if step.name == "attack-forged-valid-looking-grant")
        self.assertIn("died on armed registry", step.detail)
        self.assertIn("fingerprint-not-in-registry", step.detail)
        self.assertIn("legacy unarmed path unchanged", step.detail)
        defect = next(defect for defect in self.report.defects if defect.defect_id == "D1")
        self.assertEqual(defect.severity, "rough")
        self.assertIn("HISTORICAL (healed this sprint)", defect.finding)
        self.assertIn("RESIDUAL", defect.finding)

    def test_expired_and_specimen_attacks_caught(self) -> None:
        self.assertIn("attack-expired-grant-caught", self.report.steps_ok)
        self.assertIn("attack-specimen-ref-caught", self.report.steps_ok)
        step = next(step for step in self.report.step_log if step.name == "attack-expired-grant-caught")
        self.assertIn("expired at", step.detail)

    def test_pit_chronology_asserted(self) -> None:
        step = next(step for step in self.report.step_log if step.name == "pit-matrix-pre-post-publication")
        self.assertIn("11.16", step.detail)
        self.assertIn("no WASDE", step.detail)


class Lane2ExpressibilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = ar.run_lane2()

    def test_upside_share_expressible(self) -> None:
        self.assertIn("upside-share-obligation-expressible", self.report.steps_ok)

    def test_r1_escape_recorded(self) -> None:
        defect = next(defect for defect in self.report.defects if defect.defect_id == "D3")
        self.assertIn("ANY contract sold to a farmer", defect.finding)
        self.assertIn("carries_farmer_contract", defect.named_remedy)


class Lane3PrecisionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = ar.run_lane3()

    def test_budget_demand_names_rail_precisely(self) -> None:
        step = next(
            step
            for step in self.report.step_log
            if step.name == "collar-intent-demands-premium-budget-precisely"
        )
        self.assertIn("rail='R6'", step.detail)
        self.assertIn("precise=True", step.detail)

    def test_self_authored_budget_is_the_crack(self) -> None:
        defect = next(defect for defect in self.report.defects if defect.defect_id == "D6")
        self.assertIn("self-authorable", defect.finding)

    def test_agent_cannot_mint_the_cap(self) -> None:
        self.assertIn("agent-cannot-mint-the-cap", self.report.steps_ok)


class Lane4ChainTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cls.report, _ledger = ar.run_lane4(tmpdir)

    def test_halts_freeze_while_void_stays_legal(self) -> None:
        self.assertIn("lifecycle-freezes-void-still-legal", self.report.steps_ok)
        step = next(
            step for step in self.report.step_log if step.name == "lifecycle-freezes-void-still-legal"
        )
        self.assertIn("[refusal:halted]", step.detail)
        self.assertIn("voided", step.detail)

    def test_four_eyes_and_terminality(self) -> None:
        self.assertIn("four-eyes-guard-verbosely", self.report.steps_ok)
        self.assertIn("voided-terminal-after-lift", self.report.steps_ok)

    def test_gate_cheats_die_and_single_missing_blocks(self) -> None:
        self.assertIn("gate-truthy-cheats-die", self.report.steps_ok)
        self.assertIn("gate-any-one-missing-blocks-verbosely", self.report.steps_ok)
        step = next(
            step for step in self.report.step_log if step.name == "gate-truthy-cheats-die"
        )
        self.assertIn("ActuationGap", step.detail)

    def test_verify_chain_void_sentinel_registered(self) -> None:
        defect = next(defect for defect in self.report.defects if defect.defect_id == "D9")
        self.assertEqual(defect.severity, "blocker")
        # the sentinel speaks in the crash's voice while the bug is live,
        # and in the regression-sentinel voice once actuation heals it
        self.assertTrue(
            "KeyError" in defect.finding or "REGRESSION SENTINEL" in defect.finding,
            defect.finding,
        )
        step = next(
            step
            for step in self.report.step_log
            if step.name == "ledger-tempdir-persistence-and-tamper"
        )
        self.assertTrue(
            "CRASH -> D9" in step.detail or "void-bearing chain verify: OK" in step.detail,
            step.detail,
        )


class Lane5CrossVocabTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = ar.run_lane5()

    def test_market_kinds_raise_with_remedies(self) -> None:
        step = next(
            step for step in self.report.step_log if step.name == "agronomy-refuses-market-kinds-cleanly"
        )
        self.assertIn("'hedge'", step.detail)
        self.assertIn("'trade'", step.detail)
        self.assertIn("route market-side intent to WS7", step.detail)

    def test_raw_object_refusal_names_the_slot(self) -> None:
        self.assertIn("raw-record-into-drone-refused", self.report.steps_ok)

    def test_unsigned_wrap_slip_recorded(self) -> None:
        self.assertIn("unsigned-wrap-emits-packet-defect", self.report.steps_ok)
        defect = next(defect for defect in self.report.defects if defect.defect_id == "D8")
        self.assertIn("UNSIGNED", defect.finding)
        self.assertIn("signoff evidence", defect.named_remedy)


class MarkdownRenderingTest(unittest.TestCase):
    def test_render_includes_totals_and_lanes(self) -> None:
        _reports, markdown = ar.run_all_rehearsals()
        for lane in ("L1", "L2", "L3", "L4", "L5"):
            self.assertIn(f"## {lane}", markdown)
        self.assertIn("| defect | severity | finding | named remedy |", markdown)
        self.assertIn("(blocker 1, rough 5, cosmetic 3)", markdown)
        self.assertIn("Lane verdict:", markdown)


if __name__ == "__main__":
    unittest.main()
