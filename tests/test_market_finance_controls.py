from __future__ import annotations

import unittest
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from farm_ontology.markets import rails
from farm_ontology.markets.finance_controls import (
    ApprovalBundle,
    ApprovalRole,
    EventType,
    EvidencePurpose,
    HedgeIntentLedger,
    HedgeOrderIntent,
    IntentEvent,
    IntentState,
    PaperReconciliationJournal,
    SignedEvidence,
    evaluate_manual_approval,
)
from farm_ontology.markets.paper_ledger import FillUnit, PaperFill, PaperLedger, Side


AT = datetime(2026, 11, 25, 12, tzinfo=timezone.utc)
SIG_PLACEHOLDER = "0" * 128


def fake_signature(issuer: str, payload: bytes) -> str:
    """Deterministic test signature; production must inject a real verifier."""
    import hashlib

    return hashlib.sha512(issuer.encode("utf-8") + b":" + payload).hexdigest()


def verifier(issuer: str, payload: bytes, signature: str) -> bool:
    return signature == fake_signature(issuer, payload)


def evidence(purpose, subject, issuer, claims, *, start=AT - timedelta(hours=1), end=AT + timedelta(days=1)):
    unsigned = SignedEvidence(
        purpose=purpose,
        subject_sha256=subject,
        issuer=issuer,
        issued_at=start,
        expires_at=end,
        claims=tuple(sorted(claims.items())),
        signature_hex=SIG_PLACEHOLDER,
    )
    return replace(unsigned, signature_hex=fake_signature(issuer, unsigned.signing_payload()))


def intent(**changes):
    values = dict(
        intent_id="intent-001",
        artifact_sha256="a" * 64,
        instrument_family=rails.F_SHORT_CBOT_SOYBEAN_FUTURES,
        side="sell",
        quantity=Decimal("2"),
        quantity_unit="contracts",
        cap_sheet_sha256="b" * 64,
        rights_bundle_sha256="c" * 64,
        scope="public-feed-only",
        feeds=("exchange-settlement",),
        territory="JP-Hokkaido",
        uses_farmer_data=False,
        farmer_consent_grant_fingerprints=(),
        created_at=AT - timedelta(minutes=5),
        expires_at=AT + timedelta(hours=1),
    )
    values.update(changes)
    return HedgeOrderIntent(**values)


def approval_evidence(value):
    cap = evidence(
        EvidencePurpose.RISK_CAP_SHEET,
        value.cap_sheet_sha256,
        "risk-alice",
        {
            "role": ApprovalRole.RISK_OWNER.value,
            "specimen": "false",
            "quarter": "2026Q4",
            "instrument_family": value.instrument_family,
            "quantity_unit": value.quantity_unit,
            "max_order_quantity": "3",
            "period_start": (AT - timedelta(days=20)).isoformat(),
            "period_end": (AT + timedelta(days=70)).isoformat(),
        },
    )
    rights = evidence(
        EvidencePurpose.SOURCE_RIGHTS,
        value.rights_bundle_sha256,
        "licence-registry",
        {
            "status": "active", "purpose": "hedge", "scope": value.scope,
            "feeds": json.dumps(value.feeds, separators=(",", ":")), "territory": value.territory,
            "uses_farmer_data": "true" if value.uses_farmer_data else "false",
            "instrument_family": value.instrument_family,
            "farmer_consent_grant_fingerprints": json.dumps(
                value.farmer_consent_grant_fingerprints, separators=(",", ":"),
            ),
        },
    )
    kill = evidence(
        EvidencePurpose.KILL_SWITCH,
        value.fingerprint,
        "independent-watchdog",
        {"halt_raised": "false"},
        start=AT - timedelta(seconds=30),
    )
    approvals = ApprovalBundle(
        risk_owner=evidence(
            EvidencePurpose.INTENT_APPROVAL,
            value.fingerprint,
            "risk-alice",
            {"role": ApprovalRole.RISK_OWNER.value, "decision": "approve"},
        ),
        independent_reviewer=evidence(
            EvidencePurpose.INTENT_APPROVAL,
            value.fingerprint,
            "reviewer-bob",
            {"role": ApprovalRole.INDEPENDENT_REVIEWER.value, "decision": "approve"},
            start=AT - timedelta(minutes=59),
        ),
    )
    return cap, rights, kill, approvals


class FinanceControlTests(unittest.TestCase):
    def test_missing_trust_evidence_and_unconfigured_verifier_fail_closed(self):
        value = intent()
        decision = evaluate_manual_approval(
            value, at=AT, cap_sheet=None, source_rights=None,
            kill_switch=None, approvals=None, verifier=None,
        )
        self.assertFalse(decision.approved_for_manual_review)
        self.assertIn("risk-cap-sheet-missing-invalid-expired-or-untrusted", decision.violations)
        self.assertIn("source-rights-missing-invalid-expired-or-untrusted", decision.violations)
        self.assertIn("independent-kill-switch-evidence-missing-invalid-or-expired", decision.violations)
        cap, rights, kill, approvals = approval_evidence(value)
        untrusted = evaluate_manual_approval(
            value, at=AT, cap_sheet=cap, source_rights=rights,
            kill_switch=kill, approvals=approvals, verifier=None,
        )
        self.assertFalse(untrusted.approved_for_manual_review)
        self.assertTrue(any("untrusted" in item for item in untrusted.violations))

    def test_expired_cap_rights_kill_switch_and_approvals_refuse(self):
        value = intent()
        cap, rights, kill, approvals = approval_evidence(value)
        expired_at = AT - timedelta(seconds=1)
        items = (
            (replace(cap, expires_at=expired_at), rights, kill, approvals),
            (cap, replace(rights, expires_at=expired_at), kill, approvals),
            (cap, rights, replace(kill, expires_at=expired_at), approvals),
            (cap, rights, kill, replace(approvals, independent_reviewer=replace(
                approvals.independent_reviewer, expires_at=expired_at))),
        )
        for args in items:
            with self.subTest(item=args):
                self.assertFalse(
                    evaluate_manual_approval(
                        value, at=AT, cap_sheet=args[0], source_rights=args[1],
                        kill_switch=args[2], approvals=args[3], verifier=verifier,
                    ).approved_for_manual_review
                )

    def test_tampered_cap_hash_or_signature_does_not_unlock(self):
        value = intent()
        cap, rights, kill, approvals = approval_evidence(value)
        wrong_subject = replace(cap, subject_sha256="d" * 64)
        bad_signature = replace(cap, signature_hex="e" * 128)
        for altered in (wrong_subject, bad_signature):
            decision = evaluate_manual_approval(
                value, at=AT, cap_sheet=altered, source_rights=rights,
                kill_switch=kill, approvals=approvals, verifier=verifier,
            )
            self.assertFalse(decision.approved_for_manual_review)
            self.assertIn("risk-cap-sheet-missing-invalid-expired-or-untrusted", decision.violations)
        specimen = replace(cap, claims=tuple(sorted({**dict(cap.claims), "specimen": "true"}.items())))
        self.assertFalse(evaluate_manual_approval(
            value, at=AT, cap_sheet=specimen, source_rights=rights,
            kill_switch=kill, approvals=approvals, verifier=verifier,
        ).approved_for_manual_review)

        undersized_cap = evidence(
            EvidencePurpose.RISK_CAP_SHEET,
            value.cap_sheet_sha256,
            "risk-alice",
            {
                "role": ApprovalRole.RISK_OWNER.value,
                "specimen": "false",
                "quarter": "2026Q4",
                "instrument_family": value.instrument_family,
                "quantity_unit": value.quantity_unit,
                "max_order_quantity": "1",
            },
        )
        decision = evaluate_manual_approval(
            value, at=AT, cap_sheet=undersized_cap, source_rights=rights,
            kill_switch=kill, approvals=approvals, verifier=verifier,
        )
        self.assertFalse(decision.approved_for_manual_review)
        self.assertIn("intent-exceeds-signed-order-quantity-cap", decision.violations)

    def test_approval_roles_order_and_independence_are_enforced(self):
        value = intent()
        cap, rights, kill, approvals = approval_evidence(value)
        reversed_roles = replace(
            approvals,
            risk_owner=approvals.independent_reviewer,
            independent_reviewer=approvals.risk_owner,
        )
        decision = evaluate_manual_approval(
            value, at=AT, cap_sheet=cap, source_rights=rights,
            kill_switch=kill, approvals=reversed_roles, verifier=verifier,
        )
        self.assertFalse(decision.approved_for_manual_review)
        self.assertTrue(any("claims-invalid" in item for item in decision.violations))

        same_actor = replace(
            approvals,
            independent_reviewer=evidence(
                EvidencePurpose.INTENT_APPROVAL, value.fingerprint, "risk-alice",
                {"role": ApprovalRole.INDEPENDENT_REVIEWER.value, "decision": "approve"},
            ),
        )
        decision = evaluate_manual_approval(
            value, at=AT, cap_sheet=cap, source_rights=rights,
            kill_switch=kill, approvals=same_actor, verifier=verifier,
        )
        self.assertFalse(decision.approved_for_manual_review)
        self.assertIn("risk-owner-and-independent-reviewer-must-be-distinct", decision.violations)

        out_of_order = replace(
            approvals,
            independent_reviewer=evidence(
                EvidencePurpose.INTENT_APPROVAL,
                value.fingerprint,
                "reviewer-bob",
                {"role": ApprovalRole.INDEPENDENT_REVIEWER.value, "decision": "approve"},
                start=AT - timedelta(hours=2),
            ),
        )
        decision = evaluate_manual_approval(
            value, at=AT, cap_sheet=cap, source_rights=rights,
            kill_switch=kill, approvals=out_of_order, verifier=verifier,
        )
        self.assertFalse(decision.approved_for_manual_review)
        self.assertIn("risk-owner-approval-must-precede-independent-review", decision.violations)

    def test_global_class_c_policy_refuses_all_approval_even_when_intent_claims_closed(self):
        value = intent()
        cap, rights, kill, approvals = approval_evidence(value)
        decision = evaluate_manual_approval(
            value, at=AT, cap_sheet=cap, source_rights=rights,
            kill_switch=kill, approvals=approvals, verifier=verifier,
        )
        self.assertFalse(decision.approved_for_manual_review)
        self.assertIn("class-c-policy-closed", decision.violations)
        ledger = HedgeIntentLedger()
        proposed = ledger.propose(value, at=AT, actor="analyst-charlie")
        repeated = ledger.propose(value, at=AT, actor="analyst-charlie")
        self.assertEqual(proposed, repeated)
        with self.assertRaisesRegex(ValueError, "approval gates"):
            ledger.approve_for_manual_review(
                value.intent_id, at=AT + timedelta(minutes=1), actor="reviewer-bob",
                cap_sheet=cap, source_rights=rights, kill_switch=kill,
                approvals=approvals, verifier=verifier,
            )
        replayed = HedgeIntentLedger(ledger.events, intents=(value,))
        self.assertEqual(replayed.events, ledger.events)
        self.assertEqual(replayed.state(value.intent_id, at=AT), IntentState.PROPOSED)
        self.assertFalse(hasattr(ledger, "submit_order"))
        self.assertFalse(hasattr(ledger, "execute"))

    def test_replay_rejects_recomputed_hash_only_approval_events(self):
        import hashlib
        import json

        value = intent()
        ledger = HedgeIntentLedger()
        proposal = ledger.propose(value, at=AT, actor="analyst-charlie")
        payload = {
            "sequence": 2, "intent_id": value.intent_id,
            "intent_sha256": value.fingerprint,
            "event_type": EventType.APPROVED_MANUAL.value,
            "at": (AT + timedelta(minutes=1)).isoformat(),
            "actor": "forged-reviewer", "evidence_sha256": "f" * 64,
            "previous_sha256": proposal.event_sha256,
        }
        forged_sha = hashlib.sha256(json.dumps(
            payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        ).encode("utf-8")).hexdigest()
        forged = IntentEvent(
            sequence=2, intent_id=value.intent_id, intent_sha256=value.fingerprint,
            event_type=EventType.APPROVED_MANUAL,
            at=AT + timedelta(minutes=1), actor="forged-reviewer",
            evidence_sha256="f" * 64, previous_sha256=proposal.event_sha256,
            event_sha256=forged_sha,
        )
        with self.assertRaisesRegex(ValueError, "cryptographic authentication"):
            HedgeIntentLedger((proposal, forged), intents=(value,))

    def test_ledger_refuses_ordered_approval_bypass_and_halt_freezes_intent(self):
        value = intent()
        ledger = HedgeIntentLedger()
        ledger.propose(value, at=AT, actor="analyst-charlie")
        with self.assertRaisesRegex(ValueError, "approval gates"):
            ledger.approve_for_manual_review(
                value.intent_id, at=AT + timedelta(minutes=1), actor="reviewer-bob",
                cap_sheet=None, source_rights=None, kill_switch=None,
                approvals=None, verifier=verifier,
            )
        halt = evidence(
            EvidencePurpose.KILL_SWITCH, value.fingerprint, "independent-watchdog",
            {"halt_raised": "true"},
        )
        event = ledger.halt(
            value.intent_id, at=AT + timedelta(minutes=2), actor="independent-watchdog",
            kill_switch=halt, verifier=verifier,
        )
        self.assertEqual(event.event_type, EventType.HALTED)
        self.assertEqual(ledger.state(value.intent_id, at=AT + timedelta(minutes=2)), IntentState.HALTED)
        with self.assertRaisesRegex(ValueError, "only a proposed intent"):
            ledger.approve_for_manual_review(
                value.intent_id, at=AT + timedelta(minutes=3), actor="reviewer-bob",
                cap_sheet=None, source_rights=None, kill_switch=None,
                approvals=None, verifier=verifier,
            )

    def test_intent_id_conflict_expiry_and_class_c_opening_are_refused(self):
        ledger = HedgeIntentLedger()
        value = intent()
        ledger.propose(value, at=AT, actor="analyst-charlie")
        with self.assertRaisesRegex(ValueError, "different immutable content"):
            ledger.propose(intent(quantity=Decimal("3")), at=AT, actor="analyst-charlie")
        with self.assertRaisesRegex(ValueError, "outside its validity"):
            HedgeIntentLedger().propose(value, at=value.expires_at, actor="analyst-charlie")
        with self.assertRaisesRegex(ValueError, "Class C must remain closed"):
            intent(class_c_policy="open")
        with self.assertRaisesRegex(ValueError, "Class C"):
            intent(instrument_family="settlement")

    def test_approved_state_is_time_derived_and_expires(self):
        value = intent()
        ledger = HedgeIntentLedger()
        ledger.propose(value, at=AT, actor="analyst-charlie")
        self.assertEqual(ledger.state(value.intent_id, at=AT), IntentState.PROPOSED)
        self.assertEqual(ledger.state(value.intent_id, at=value.expires_at), IntentState.EXPIRED)
        ledger._states[value.intent_id] = IntentState.APPROVED_MANUAL
        self.assertEqual(ledger.state(value.intent_id, at=AT), IntentState.APPROVED_MANUAL)
        self.assertEqual(ledger.state(value.intent_id, at=value.expires_at), IntentState.EXPIRED)

    def test_rights_scope_feeds_territory_instrument_and_farmer_grants_are_bound(self):
        with self.assertRaisesRegex(ValueError, "consent grant fingerprints"):
            intent(scope="farmer-derived", uses_farmer_data=True)

        value = intent(scope="farmer-derived", uses_farmer_data=True,
                       farmer_consent_grant_fingerprints=("d" * 64,))
        cap, rights, kill, approvals = approval_evidence(value)
        mismatched = evidence(
            EvidencePurpose.SOURCE_RIGHTS, value.rights_bundle_sha256, "licence-registry",
            {**dict(rights.claims), "territory": "JP-Okinawa"},
        )
        result = evaluate_manual_approval(
            value, at=AT, cap_sheet=cap, source_rights=mismatched,
            kill_switch=kill, approvals=approvals, verifier=verifier,
        )
        self.assertIn("source-rights-do-not-cover-explicit-intent-scope", result.violations)

    def test_cap_period_and_kill_switch_freshness_are_bounded(self):
        value = intent()
        cap, rights, kill, approvals = approval_evidence(value)
        stale_kill = evidence(
            EvidencePurpose.KILL_SWITCH, value.fingerprint, "independent-watchdog",
            {"halt_raised": "false"}, start=AT - timedelta(minutes=6),
        )
        decision = evaluate_manual_approval(
            value, at=AT, cap_sheet=cap, source_rights=rights,
            kill_switch=stale_kill, approvals=approvals, verifier=verifier,
        )
        self.assertIn("kill-switch-evidence-is-stale", decision.violations)

        overlong_cap = evidence(
            EvidencePurpose.RISK_CAP_SHEET, value.cap_sheet_sha256, "risk-alice",
            {**dict(cap.claims), "period_start": (AT - timedelta(days=101)).isoformat(),
             "period_end": (AT + timedelta(days=1)).isoformat()},
        )
        decision = evaluate_manual_approval(
            value, at=AT, cap_sheet=overlong_cap, source_rights=rights,
            kill_switch=kill, approvals=approvals, verifier=verifier,
        )
        self.assertIn("risk-cap-sheet-period-missing-invalid-or-stale", decision.violations)

    def test_reconciliation_journal_is_idempotent_replayable_and_rejects_reversal(self):
        journal = PaperReconciliationJournal()
        statement = {"broker_statement_id": "paper-001", "cash": Decimal("90"), "qty": Decimal("2")}
        result = {"cash_difference": Decimal("0"), "position_difference": Decimal("0"), "matches": True}
        entry = journal.record("recon-001", statement=statement, result=result, recorded_at=AT)
        self.assertTrue(hasattr(entry, "unverified_result_sha256"))
        self.assertFalse(hasattr(entry, "validated_result_sha256"))
        self.assertEqual(journal.record(
            "recon-001", statement=statement, result=result,
            recorded_at=AT + timedelta(hours=1),
        ), entry)
        with self.assertRaisesRegex(ValueError, "different content"):
            journal.record(
                "recon-001", statement={**statement, "qty": Decimal("3")},
                result=result, recorded_at=AT + timedelta(hours=1),
            )
        with self.assertRaisesRegex(ValueError, "already reconciled"):
            journal.record(
                "recon-002", statement=statement, result=result,
                recorded_at=AT + timedelta(hours=1),
            )
        replayed = PaperReconciliationJournal(journal.entries)
        self.assertEqual(replayed.entries, journal.entries)
        with self.assertRaisesRegex(ValueError, "hash chain"):
            PaperReconciliationJournal((replace(entry, unverified_result_sha256="f" * 64),))

        # Existing paper accounting intentionally refuses a long-to-short
        # reversal; closing at zero and reopening long is supported.
        paper = PaperLedger(Decimal("1000"))
        first = PaperFill("buy-1", "soy-cash", Side.BUY, Decimal("10"), Decimal("10"),
                          FillUnit.USD_PER_BUSHEL, Decimal("0"), AT)
        close = PaperFill("sell-1", "soy-cash", Side.SELL, Decimal("10"), Decimal("11"),
                          FillUnit.USD_PER_BUSHEL, Decimal("0"), AT + timedelta(seconds=1))
        reopen = PaperFill("buy-2", "soy-cash", Side.BUY, Decimal("1"), Decimal("12"),
                           FillUnit.USD_PER_BUSHEL, Decimal("0"), AT + timedelta(seconds=2))
        short = PaperFill("sell-2", "soy-cash", Side.SELL, Decimal("2"), Decimal("12"),
                          FillUnit.USD_PER_BUSHEL,
                          Decimal("0"), AT + timedelta(seconds=3))
        paper.record_fill(first)
        self.assertEqual(paper.record_fill(close).positions_bushels, ())
        self.assertEqual(paper.record_fill(reopen).positions_bushels, (("soy-cash", Decimal("1")),))
        before = paper.snapshot()
        with self.assertRaisesRegex(ValueError, "short position"):
            paper.record_fill(short)
        self.assertEqual(paper.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
