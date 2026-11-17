"""Offline tests for the doctrine rails (alpha-fairness §3-§5).

Includes the FAIL-CLOSED proof the lead mandated: any grant that
expires flips validation to violations; a frozen success answer is
impossible. Also proves the mandated clause stays VERBATIM by reading
it out of the doctrine document itself.
"""

from __future__ import annotations

import re
import unittest
from datetime import datetime, timezone
from pathlib import Path

from farm_ontology.markets import rails as rl
from farm_ontology.markets.pit_dataset import SUBJECT_AMS_BID

ROOT = Path(__file__).resolve().parents[1]
DOCTRINE = ROOT / "docs" / "alpha-fairness-doctrine.md"

GOOD_GRANT = dict(
    name="earth-engine-commercial",
    issuer="vendor",
    seat="somewhere",
    scope="history exports",
    territory="worldwide",
    purpose="market data",
    expiry="2027-06-30T00:00:00+00:00",
    evidence_url="https://example.com/grant.pdf",
    permits_financial_use=True,
    permits_market_data_use=True,
)

ATT = {rid: True for rid in rl.CONDUCT_ATTESTATION_IDS}

CONTRIB = (
    rl.Contribution(
        feed=SUBJECT_AMS_BID,
        licence_attribution="USDA AMS, public report",
        support_statement="northwest cash market print",
        error_statement="final printed report; not scored",
    ),
)

AS_OF = datetime(2026, 11, 18, tzinfo=timezone.utc)


def grant(**overrides):
    return rl.GrantRef(**{**GOOD_GRANT, **overrides})


def artefact(**overrides) -> rl.PlaybookArtefact:
    base = dict(
        artefact_id="ART-1",
        state=rl.STATE_CONFIDENT_LOSS,
        text="analyst memo. " + rl.DISCLOSURE_CLAUSE,
        families=(rl.F_BOUGHT_PUTS,),
        hedge_tickets=(
            rl.HedgeTicket(
                ticket_id="T-1",
                family=rl.F_BOUGHT_PUTS,
                would_farmer_still_sign=True,
                filed_in_trade_ledger=True,
                drafted_by="human",
            ),
        ),
        market_decisive_feeds=(SUBJECT_AMS_BID,),
        contributions=CONTRIB,
        grants_by_feed={SUBJECT_AMS_BID: grant()},
        conduct_attestations=dict(ATT),
    )
    base.update(overrides)
    return rl.PlaybookArtefact(**base)


class VerbatimClauseTest(unittest.TestCase):
    def _doctrine_quotes(self) -> list[str]:
        doctrine_text = DOCTRINE.read_text(encoding="utf-8")
        matches = re.findall(r"\"The Company maintains[^\"]+\"", doctrine_text)
        self.assertTrue(matches, "the doctrine no longer quotes the clause")
        return matches

    def test_clause_matches_doctrine_document(self) -> None:
        clause = " ".join(self._doctrine_quotes()[0].strip('"').split())
        self.assertEqual(clause, rl.DISCLOSURE_CLAUSE)

    def test_clause_wrapping_normalises_to_the_pinned_string(self) -> None:
        unwrapped = " ".join(self._doctrine_quotes()[0].split())
        self.assertEqual(unwrapped.strip('"'), rl.DISCLOSURE_CLAUSE)


class ScenarioEncodingTest(unittest.TestCase):
    def test_states_and_families_match_the_doctrine_table(self) -> None:
        self.assertEqual(
            {scenario.state for scenario in rl.SCENARIOS.values()},
            {rl.STATE_CONFIDENT_LOSS, rl.STATE_CONFIDENT_GAIN, rl.STATE_UNCERTAIN, rl.STATE_HAZARD_IMMINENT},
        )
        self.assertEqual(
            rl.scenario_for(rl.STATE_CONFIDENT_LOSS).own_book_families,
            (rl.F_SHORT_CBOT_SOYBEAN_FUTURES, rl.F_BOUGHT_PUTS),
        )
        self.assertEqual(
            rl.scenario_for(rl.STATE_CONFIDENT_GAIN).own_book_families,
            (rl.F_FORWARD_PHYSICAL_COMMITMENT, rl.F_INPUT_SUPPLIER_INVESTMENT),
        )
        self.assertEqual(
            rl.scenario_for(rl.STATE_UNCERTAIN).own_book_families,
            (rl.F_COST_CAPPED_STRADDLE, rl.F_PUT_SPREAD_COLLAR),
        )
        self.assertEqual(rl.scenario_for(rl.STATE_HAZARD_IMMINENT).own_book_families, (rl.F_REDUCE_OPEN_RISK,))

    def test_uncertain_demands_premium_budget_familywise(self) -> None:
        self.assertTrue(rl.scenario_for(rl.STATE_UNCERTAIN).premium_budget_required)
        for state in (rl.STATE_CONFIDENT_LOSS, rl.STATE_CONFIDENT_GAIN, rl.STATE_HAZARD_IMMINENT):
            self.assertFalse(rl.scenario_for(state).premium_budget_required)


class GrantStateTest(unittest.TestCase):
    def test_states_cover_happy_and_every_failure(self) -> None:
        self.assertEqual(rl.grant_state_at(grant(), AS_OF), (rl.GRANT_VALID, "permit provably alive"))
        self.assertEqual(rl.grant_state_at(grant(expiry="2026-11-01T00:00:00+00:00"), AS_OF)[0], rl.GRANT_EXPIRED)
        self.assertEqual(rl.grant_state_at(grant(expiry="next quarter"), AS_OF)[0], rl.GRANT_UNPARSEABLE)
        self.assertEqual(rl.grant_state_at(None, AS_OF)[0], rl.GRANT_CLOSED)
        self.assertEqual(
            rl.grant_state_at(grant(permits_financial_use=False), AS_OF)[0],
            rl.GRANT_CLOSED,
        )

    def test_expiry_parity_counts_as_expired(self) -> None:
        moment = datetime(2026, 11, 18, tzinfo=timezone.utc)
        self.assertEqual(rl.grant_state_at(grant(expiry="2026-11-18T00:00:00+00:00"), moment)[0], rl.GRANT_EXPIRED)


class FailClosedTest(unittest.TestCase):
    def test_expired_grant_flips_validation_to_violations(self) -> None:
        healthy = rl.validate_playbook_artefact(artefact(), AS_OF)
        self.assertEqual(healthy, ())
        broken = artefact(grants_by_feed={SUBJECT_AMS_BID: grant(expiry="2026-11-01T00:00:00+00:00")})
        violations = rl.validate_playbook_artefact(broken, AS_OF)
        self.assertTrue(any(v.rail == rl.RAIL_5_TRUTHFULNESS and "expired" in v.detail for v in violations))

    def test_removed_grant_object_fails_closed(self) -> None:
        broken = artefact(grants_by_feed={SUBJECT_AMS_BID: None})
        violations = rl.validate_playbook_artefact(broken, AS_OF)
        self.assertTrue(any("'closed'" in v.detail for v in violations))

    def test_unrecorded_grant_key_fails_closed(self) -> None:
        broken = artefact(grants_by_feed={})
        violations = rl.validate_playbook_artefact(broken, AS_OF)
        self.assertTrue(any(v.rail == rl.RAIL_5_TRUTHFULNESS for v in violations))

    def test_contributed_but_stale_answer_never_persists(self) -> None:
        # the SAME artefact validated later, after expiry, must flip
        g = grant(expiry="2026-12-31T00:00:00+00:00")
        a = artefact(grants_by_feed={SUBJECT_AMS_BID: g})
        self.assertEqual(rl.validate_playbook_artefact(a, AS_OF), ())
        later = datetime(2027, 1, 5, tzinfo=timezone.utc)
        self.assertTrue(rl.validate_playbook_artefact(a, later))


class RailViolationsTest(unittest.TestCase):
    def test_r1_missing_clause(self) -> None:
        broken = artefact(text="no clause here")
        self.assertTrue(any(v.rail == rl.RAIL_1_DISCLOSURE for v in rl.validate_playbook_artefact(broken, AS_OF)))

    def test_r2_gain_needs_upside_share(self) -> None:
        gain = artefact(
            state=rl.STATE_CONFIDENT_GAIN,
            families=(rl.F_FORWARD_PHYSICAL_COMMITMENT,),
            hedge_tickets=(
                rl.HedgeTicket("T", rl.F_FORWARD_PHYSICAL_COMMITMENT, True, True, "human"),
            ),
        )
        violations = rl.validate_playbook_artefact(gain, AS_OF)
        self.assertTrue(any(v.rail == rl.RAIL_2_UPSIDE_SHARE for v in violations))
        fixed = artefact(
            state=rl.STATE_CONFIDENT_GAIN,
            families=(rl.F_FORWARD_PHYSICAL_COMMITMENT,),
            hedge_tickets=(
                rl.HedgeTicket("T", rl.F_FORWARD_PHYSICAL_COMMITMENT, True, True, "human"),
            ),
            upside_term=rl.UpsideShareTerm(0.3, "farmer", "Founder", "contract-2027-01"),
        )
        self.assertEqual(
            [v for v in rl.validate_playbook_artefact(fixed, AS_OF) if v.rail == rl.RAIL_2_UPSIDE_SHARE],
            [],
        )

    def test_r3_unsigned_or_unfiled_tickets_fail(self) -> None:
        unsigned = artefact(
            hedge_tickets=(rl.HedgeTicket("T", rl.F_BOUGHT_PUTS, False, True, "human"),)
        )
        self.assertTrue(
            any("still sign" in v.detail for v in rl.validate_playbook_artefact(unsigned, AS_OF))
        )
        unfiled = artefact(hedge_tickets=(rl.HedgeTicket("T", rl.F_BOUGHT_PUTS, True, False, "human"),))
        self.assertTrue(
            any("not filed" in v.detail for v in rl.validate_playbook_artefact(unfiled, AS_OF))
        )
        uncovered = artefact(
            families=(rl.F_BOUGHT_PUTS, rl.F_SHORT_CBOT_SOYBEAN_FUTURES),
            hedge_tickets=(rl.HedgeTicket("T", rl.F_BOUGHT_PUTS, True, True, "human"),),
        )
        self.assertTrue(
            any("no hedge ticket" in v.detail for v in rl.validate_playbook_artefact(uncovered, AS_OF))
        )

    def test_r3_uncertainty_requires_human_set_budget(self) -> None:
        unc = artefact(
            state=rl.STATE_UNCERTAIN,
            families=(rl.F_COST_CAPPED_STRADDLE,),
            hedge_tickets=(rl.HedgeTicket("T", rl.F_COST_CAPPED_STRADDLE, True, True, "human"),),
        )
        self.assertTrue(any("premium budget" in v.detail for v in rl.validate_playbook_artefact(unc, AS_OF)))
        funded = artefact(
            state=rl.STATE_UNCERTAIN,
            families=(rl.F_COST_CAPPED_STRADDLE,),
            hedge_tickets=(rl.HedgeTicket("T", rl.F_COST_CAPPED_STRADDLE, True, True, "human"),),
            premium_budget=rl.PremiumBudget(1.0, 2.0, "2026Q4", "risk owner"),
        )
        budget_violations = [
            v for v in rl.validate_playbook_artefact(funded, AS_OF) if "premium budget" in v.detail
        ]
        self.assertEqual(budget_violations, [])

    def test_agent_cannot_set_the_cap(self) -> None:
        with self.assertRaises(ValueError):
            rl.PremiumBudget(1.0, 2.0, "2026Q4", "ci-agent-42")

    def test_r4_consent_failures(self) -> None:
        carrying = artefact(carries_farmer_level_data=True)
        self.assertTrue(any(v.rail == rl.RAIL_4_CONSENT_FLOW for v in rl.validate_playbook_artefact(carrying, AS_OF)))
        expired_consent = artefact(
            carries_farmer_level_data=True,
            consent=rl.ConsentGrant("farmer-A", "market synthesis", "parcel yields", "2026-11-01T00:00:00+00:00", "url"),
        )
        self.assertTrue(
            any("expired" in v.detail for v in rl.validate_playbook_artefact(expired_consent, AS_OF))
        )
        # an unparseable consent fails FAST at construction (house style:
        # bad times are refused, not absorbed)
        with self.assertRaises(ValueError):
            rl.ConsentGrant("farmer-A", "market synthesis", "parcel yields", "soon", "url")
        valid_consent = artefact(
            carries_farmer_level_data=True,
            consent=rl.ConsentGrant("farmer-A", "market synthesis", "parcel yields", "2027-11-01T00:00:00+00:00", "url"),
        )
        self.assertEqual(
            [v for v in rl.validate_playbook_artefact(valid_consent, AS_OF) if v.rail == rl.RAIL_4_CONSENT_FLOW],
            [],
        )

    def test_r5_missing_contribution_triple(self) -> None:
        hollow = artefact(contributions=())
        self.assertTrue(
            any("cites no" in v.detail for v in rl.validate_playbook_artefact(hollow, AS_OF))
        )
        incomplete = artefact(
            contributions=(rl.Contribution(SUBJECT_AMS_BID, "attrib", "", "err"),)
        )
        self.assertTrue(any("support statement" in v.detail for v in rl.validate_playbook_artefact(incomplete, AS_OF)))


class ConductAttestationTest(unittest.TestCase):
    def test_missing_attestation_fails(self) -> None:
        partial = {k: True for k in list(ATT)[:4]}
        violations = rl.conduct_checks(partial)
        self.assertTrue(any("not affirmatively" in v.detail for v in violations))

    def test_false_attestation_fails(self) -> None:
        flipped = dict(ATT)
        flipped[rl.CONDUCT_NO_MANIPULATION] = False
        violations = rl.conduct_checks(flipped)
        self.assertEqual(len(violations), 1)
        self.assertIn(rl.CONDUCT_NO_MANIPULATION, violations[0].detail)

    def test_unknown_attestation_is_a_violation(self) -> None:
        padded = dict(ATT)
        padded["conduct/extra"] = True
        self.assertTrue(any("unknown attestation" in v.detail for v in rl.conduct_checks(padded)))


class StructuralGuardsTest(unittest.TestCase):
    def test_wrong_state_family_rejected_by_validator(self) -> None:
        wrong = artefact(state=rl.STATE_UNCERTAIN)  # bear families under uncertainty
        violations = rl.validate_playbook_artefact(wrong, AS_OF)
        self.assertTrue(any(v.rail == "S3-family" for v in violations))

    def test_unknown_scenario_state_rejected(self) -> None:
        with self.assertRaises(ValueError):
            artefact(state="moonshot")

    def test_upside_share_bounds(self) -> None:
        with self.assertRaises(ValueError):
            rl.UpsideShareTerm(0.0, "f", "h", "c")
        with self.assertRaises(ValueError):
            rl.UpsideShareTerm(1.0, "f", "h", "c")

    def test_adapter_shim_ignores_unknown_fields(self) -> None:
        adapted = rl.grant_ref_from_v2_like(**GOOD_GRANT, extra_field="ignored")
        self.assertEqual(adapted.evidence_url, GOOD_GRANT["evidence_url"])

    def test_validation_is_deterministic(self) -> None:
        messy = artefact(text="", grants_by_feed={}, contributions=(), conduct_attestations={})
        first = rl.validate_playbook_artefact(messy, AS_OF)
        second = rl.validate_playbook_artefact(messy, AS_OF)
        self.assertEqual(first, second)
        self.assertTrue(first)


if __name__ == "__main__":
    unittest.main()


# ---- Lead integration seam tests (2026-11-18) ----

class Ws6GrantSeamTests(unittest.TestCase):
    """The Lead-added bridge: a real WS6 Grant through grant_ref_from_ws6_grant."""

    def _ws6(self, *, expiry, specimen=False):
        from farm_ontology.licences.grants import Grant

        return Grant(
            grant_id="GR-TEST-001",
            issuer="Planet Labs PBC",
            grantee_seat="zereo0317@gmail.com",
            feeds=("planet.psscene",),
            uses=("screening", "settlement"),
            territory="JP",
            purpose="testing",
            expiry_utc=expiry,
            evidence_url="https://example.com/quote.pdf",
            specimen=specimen,
        )

    def test_specimen_grant_is_closed_with_no_ref(self):
        from datetime import datetime, timezone

        from farm_ontology.markets.rails import grant_ref_from_ws6_grant

        state, ref = grant_ref_from_ws6_grant(
            self._ws6(expiry="2099-01-01T00:00:00+00:00", specimen=True),
            at=datetime(2026, 11, 18, tzinfo=timezone.utc),
        )
        self.assertEqual(state, "closed")
        self.assertIsNone(ref)

    def test_live_non_specimen_grant_adapts_with_financial_true(self):
        from datetime import datetime, timezone

        from farm_ontology.markets.rails import GRANT_VALID, grant_ref_from_ws6_grant

        grant = self._ws6(expiry="2099-01-01T00:00:00+00:00")
        state, ref = grant_ref_from_ws6_grant(grant, at=datetime(2026, 11, 18, tzinfo=timezone.utc))
        self.assertEqual(state, GRANT_VALID)
        self.assertIsNotNone(ref)
        self.assertTrue(ref.permits_financial_use)
        self.assertTrue(ref.permits_market_data_use)
        self.assertIn("planet.psscene", ref.scope)
        self.assertEqual(ref.expiry, "2099-01-01T00:00:00+00:00")

    def test_expired_grant_reads_expired(self):
        from datetime import datetime, timezone

        from farm_ontology.markets.rails import grant_ref_from_ws6_grant

        state, ref = grant_ref_from_ws6_grant(
            self._ws6(expiry="2020-01-01T00:00:00+00:00"),
            at=datetime(2026, 11, 18, tzinfo=timezone.utc),
        )
        self.assertEqual(state, "expired")
        self.assertIsNone(ref)
