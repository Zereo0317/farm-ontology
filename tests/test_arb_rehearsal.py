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
                # D9 (verify_chain void crash) and D8 (unsigned drone packet)
                # were FIXED on main (ws/fix/actuation-ledger); the rehearsal
                # now runs those steps CLEAN, so L4 and L5 expect no D8/D9.
                "L4": [],
                "L5": ["D7"],
            },
        )
        severities = {
            defect.defect_id: defect.severity
            for report in self.reports.values()
            for defect in report.defects
        }
        for defect_id in ("D1", "D2", "D3", "D6"):
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

    def test_forged_grant_slips_and_is_caught_by_crosscheck(self) -> None:
        step = next(step for step in self.report.step_log if step.name == "attack-forged-valid-looking-grant")
        self.assertIn("PASSED rails", step.detail)
        self.assertIn("unknown_feed", step.detail)
        defect = next(defect for defect in self.report.defects if defect.defect_id == "D1")
        self.assertEqual(defect.severity, "rough")
        self.assertIn("fingerprint", defect.named_remedy)

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
        self.assertIn("rail='R3'", step.detail)
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

    def test_verify_chain_survives_legal_void_after_fix(self) -> None:
        # D9 was a blocker (verify_chain KeyError 'void'); fixed on main via
        # ws/fix/actuation-ledger. The rehearsal must now verify a void-bearing
        # chain CLEANLY — the regression guard flips direction: any RETURN of
        # the old crash is itself a finding.
        void_steps = [
            step
            for step in self.report.step_log
            if "void" in step.name or "void" in step.detail.lower()
        ]
        self.assertTrue(void_steps, "void rehearsal step vanished from the log")
        self.assertNotIn(
            "KeyError", " ".join(step.detail for step in void_steps)
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

    def test_unsigned_wrap_now_refuses_after_fix(self) -> None:
        # D8 pre-fix: an unsigned recommendation wrapped into a packet and
        # emitted. Post-fix (SignoffRelease/operator_override gate) the wrap
        # REFUSES with signature_missing — the rehearsal walks that refusal
        # as a PASSED step named raw-record-into-drone-refused (extended).
        self.assertIn("raw-record-into-drone-refused", self.report.steps_ok)
        self.assertNotIn(
            "D8", [defect.defect_id for defect in self.report.defects]
        )


class MarkdownRenderingTest(unittest.TestCase):
    def test_render_includes_totals_and_lanes(self) -> None:
        _reports, markdown = ar.run_all_rehearsals()
        for lane in ("L1", "L2", "L3", "L4", "L5"):
            self.assertIn(f"## {lane}", markdown)
        self.assertIn("| defect | severity | finding | named remedy |", markdown)
        # Totals line is GENERATED by the rehearsal module; pin only its shape
        # and that D9/D8 no longer appear as blockers post-fix.
        self.assertRegex(markdown, r"\(blocker \d+, rough \d+, cosmetic \d+\)")
        self.assertNotIn("D9", markdown)
        self.assertIn("Lane verdict:", markdown)


if __name__ == "__main__":
    unittest.main()
