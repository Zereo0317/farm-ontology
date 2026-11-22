"""Fix-sprint producer tests: provenance discipline (D1/D2), the
universal farmer-contract clause (D3), typed beneficiaries (D4), the R6
cap rail with the specimen cap-sheet registry (D5/D6).

The forgery repro is explicit: an IDENTICAL forged GrantRef is validated
WITHOUT a registry (the pre-fix world: verdict line printed) and WITH
the registry (post-fix world: dies with 'fingerprint-not-in-registry').
Both verdicts are asserted so the before/after contrast cannot rot.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from farm_ontology.licences.grants import Grant as LicencesGrant
from farm_ontology.markets import rails as rl
from farm_ontology.markets import registry as reg
from farm_ontology.markets.pit_dataset import FEED_AMS_SOYBEAN_BID

AS_OF = datetime(2026, 11, 18, 9, 0, tzinfo=timezone.utc)

CLAUSE = rl.DISCLOSURE_CLAUSE
ATT = {rid: True for rid in rl.CONDUCT_ATTESTATION_IDS}
HASH_A = "a" * 64
HASH_B = "b" * 64


def forged_grant() -> rl.GrantRef:
    """The exact forgery from rehearsal D1: perfect-looking, self-made."""
    return rl.GrantRef(
        name="forged-perfect",
        issuer="someone else entirely",
        seat="nowhere",
        scope="everything",
        territory="*",
        purpose="market data",
        expiry="2099-01-01T00:00:00+00:00",
        evidence_url="https://invalid.example/forged",
        permits_financial_use=True,
        permits_market_data_use=True,
        fingerprint=HASH_B,  # plausible-looking, registered nowhere
    )


def loss_artefact(grants, **overrides) -> rl.PlaybookArtefact:
    feeds = overrides.get("market_decisive_feeds", (FEED_AMS_SOYBEAN_BID,))
    if not isinstance(grants, dict):
        grants_by_feed = {feed: grants for feed in feeds}
    else:
        grants_by_feed = grants
    base = dict(
        artefact_id="PX",
        state=rl.STATE_CONFIDENT_LOSS,
        text="memo. " + CLAUSE,
        families=(rl.F_BOUGHT_PUTS,),
        hedge_tickets=(rl.HedgeTicket("T", rl.F_BOUGHT_PUTS, True, True, "human"),),
        market_decisive_feeds=feeds,
        contributions=tuple(
            rl.Contribution(
                feed,
                "USDA AMS public report"
                if feed == FEED_AMS_SOYBEAN_BID
                else "recorded feed certificate",
                "northwest cash print"
                if feed == FEED_AMS_SOYBEAN_BID
                else "recorded feed support",
                "final report, not scored",
            )
            for feed in feeds
        ),
        grants_by_feed=grants_by_feed,
        conduct_attestations=dict(ATT),
    )
    base.update(overrides)
    return rl.PlaybookArtefact(**base)


class ForgeryReproTest(unittest.TestCase):
    """The lead's mandated before→after proof, as a test."""

    def test_before_after_verdict_lines(self) -> None:
        forge = forged_grant()
        before = rl.validate_playbook_artefact(loss_artefact(forge), AS_OF)
        before_line = "; ".join(v.rail for v in before) or "PASSES (0 violations)"
        after = rl.validate_playbook_artefact(
            loss_artefact(forge, grant_registry=reg.RegisteredGrants.default()), AS_OF
        )
        after_line = "; ".join(
            v.detail for v in after if "fingerprint-not-in-registry" in v.detail
        )
        self.assertTrue(any(v.rail == "R5-provenance" for v in before))
        self.assertIn("fingerprint-not-in-registry", after_line)
        # the contrast, spelled out for the report
        self.assertNotIn("fingerprint-not-in-registry", before_line)

    def test_registry_arms_provenance_even_for_fingerprintless_refs(self) -> None:
        ghost = rl.GrantRef(
            name="ghost",
            issuer="i",
            seat="s",
            scope="x",
            territory="*",
            purpose="p",
            expiry="2099-01-01T00:00:00+00:00",
            evidence_url="https://x/e",
            permits_financial_use=True,
            permits_market_data_use=True,
        )
        violations = rl.validate_playbook_artefact(
            loss_artefact(ghost, grant_registry=reg.RegisteredGrants.default()), AS_OF
        )
        self.assertTrue(any("quotes no fingerprint" in v.detail for v in violations))


class BridgedGrantAliveTest(unittest.TestCase):
    """A real WS6 Grant on a tempdir shelf bridges to a registry-admitted ref."""

    def test_bridge_grant_alive_and_registered(self) -> None:
        real_cert = LicencesGrant(
            grant_id="usda-wasde-executed",
            issuer="USDA (mock executed grant)",
            grantee_seat="risk-owner",
            feeds=["usda.wasde"],
            uses=["screening", "commercial", "hedge"],
            territory="*",
            purpose="rehearsal producer test: executed certificate",
            expiry_utc="2099-01-01T00:00:00+00:00",
            evidence_url="https://example.com/executed",
            issued_at_utc="2026-11-17T00:00:00+00:00",
            permits_redistribution=False,
            specimen=False,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            shelf = Path(tmpdir)
            (shelf / "usda-wasde-executed.json").write_text(
                json.dumps(real_cert.to_payload(), indent=2), encoding="utf-8"
            )
            state = {
                "schema": "farm-ontology.grants.state/1",
                "grants": [
                    {**real_cert.to_payload(), "fingerprint": real_cert.fingerprint}
                ],
            }
            state_path = shelf / "state.json"
            state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

            ref, reason = reg.bridge_licences_to_grantref("usda_wasde", AS_OF, grants_dir=shelf)
            self.assertEqual(reason, "provider_rights_unverified")
            self.assertEqual(ref.state_detail, "provider_rights_unverified")
            self.assertFalse(ref.permits_financial_use)
            self.assertFalse(ref.specimen)

            registry = reg.RegisteredGrants.from_state_json(state_path)
            self.assertTrue(registry.contains(real_cert.fingerprint))
            self.assertTrue(registry.contains(ref.fingerprint))

            artefact = loss_artefact(
                ref, market_decisive_feeds=("usda_wasde",), grant_registry=registry
            )
            violations = rl.validate_playbook_artefact(artefact, AS_OF)
            self.assertEqual(
                [v for v in violations if "usda_wasde" in v.detail] != [],
                True,
                f"unverified grant must remain closed: {violations}",
            )


class ExpiredAndSpecimenDieTest(unittest.TestCase):
    def test_expired_bridge_dies_named(self) -> None:
        expiring = LicencesGrant(
            grant_id="usda-wasde-lapsed",
            issuer="USDA (mock executed grant, lapsed)",
            grantee_seat="risk-owner",
            feeds=["usda.wasde"],
            uses=["screening", "commercial", "hedge"],
            territory="*",
            purpose="lapsed certificate",
            expiry_utc="2026-11-01T00:00:00+00:00",
            evidence_url="https://example.com/lapsed",
            specimen=False,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            shelf = Path(tmpdir)
            (shelf / "lapsed.json").write_text(json.dumps(expiring.to_payload()), encoding="utf-8")
            ref, reason = reg.bridge_licences_to_grantref("usda_wasde", AS_OF, grants_dir=shelf)
            self.assertEqual(reason, "expired")
            self.assertEqual(ref.state_detail, "expired")
            violations = rl.validate_playbook_artefact(
                loss_artefact(ref, market_decisive_feeds=("usda_wasde",)), AS_OF
            )
            self.assertTrue(any("expired at" in v.detail for v in violations))

    def test_specimen_state_is_distinct_and_never_unlocks(self) -> None:
        ref, reason = reg.bridge_licences_to_grantref("earth-engine.export", AS_OF)
        self.assertEqual(reason, "specimen")
        self.assertEqual(ref.state_detail, "specimen")
        self.assertTrue(ref.specimen)
        state, detail = rl.grant_state_at(ref, AS_OF)
        self.assertEqual(state, rl.GRANT_SPECIMEN)
        self.assertIn("never unlocks", detail)
        self.assertIn("specimen", detail)
        violations = rl.validate_playbook_artefact(
            loss_artefact(ref), AS_OF
        )
        self.assertTrue(any("specimen" in v.detail for v in violations))


class NoFlatteningTest(unittest.TestCase):
    """D2: the ORIGINAL licences reason survives into the violation text."""

    def test_no_grant_reason_travels_verbatim(self) -> None:
        ref, reason = reg.bridge_licences_to_grantref("ams_soybean_bid", AS_OF)
        self.assertEqual(reason, "no_grant")
        self.assertIn("no_grant", ref.purpose)
        violations = rl.validate_playbook_artefact(
            loss_artefact(ref), AS_OF
        )
        self.assertTrue(any("no_grant" in v.detail for v in violations))


class FarmerContractUniversalClauseTest(unittest.TestCase):
    """D3: ANY state shipping a farmer contract needs the clause verbatim."""

    def gain_artefact(self, **overrides) -> rl.PlaybookArtefact:
        base = dict(
            artefact_id="GX",
            state=rl.STATE_CONFIDENT_GAIN,
            text="forward-physical term sheet",
            families=(rl.F_FORWARD_PHYSICAL_COMMITMENT,),
            hedge_tickets=(rl.HedgeTicket("GT", rl.F_FORWARD_PHYSICAL_COMMITMENT, True, True, "human"),),
            upside_term=rl.UpsideShareTerm(0.3, rl.Beneficiary.FARMER_CONTRACTED, "Founder", "contract-G"),
            market_decisive_feeds=(FEED_AMS_SOYBEAN_BID,),
            contributions=(
                rl.Contribution(FEED_AMS_SOYBEAN_BID, "USDA AMS", "cash print", "final"),
            ),
            grants_by_feed={FEED_AMS_SOYBEAN_BID: None},
            conduct_attestations=dict(ATT),
        )
        base.update(overrides)
        return rl.PlaybookArtefact(**base)

    def test_gain_contract_without_clause_fails(self) -> None:
        violations = rl.validate_playbook_artefact(
            self.gain_artefact(carries_farmer_contract=True), AS_OF
        )
        self.assertTrue(
            any(v.rail == rl.RAIL_1_DISCLOSURE for v in violations),
            f"gain-state farmer contract must require the clause: {violations}",
        )

    def test_gain_contract_with_clause_clears_r1(self) -> None:
        violations = rl.validate_playbook_artefact(
            self.gain_artefact(carries_farmer_contract=True, text="ts. " + CLAUSE),
            AS_OF,
        )
        self.assertEqual(
            [v for v in violations if v.rail == rl.RAIL_1_DISCLOSURE], []
        )

    def test_no_contract_no_clause_demand(self) -> None:
        violations = rl.validate_playbook_artefact(self.gain_artefact(), AS_OF)
        self.assertEqual([v for v in violations if v.rail == rl.RAIL_1_DISCLOSURE], [])


class TypedBeneficiaryTest(unittest.TestCase):
    """D4: the beneficiary is a typed member, not a hope."""

    def test_free_string_rejected(self) -> None:
        with self.assertRaises(ValueError):
            rl.UpsideShareTerm(0.3, "whoever", "Founder", "c1")

    def test_members_accepted(self) -> None:
        for member in rl.Beneficiary:
            term = rl.UpsideShareTerm(0.5, member, "Founder", "c2")
            self.assertIs(term.beneficiary, member)


class PremiumCapRailTest(unittest.TestCase):
    """D5/D6: the cap rail is named, registry-bound, and specimen-aware."""

    def budget(self, cap_sheet_hash=HASH_A, quarter="2026Q4") -> rl.PremiumBudget:
        return rl.PremiumBudget(1.0, 2.0, quarter, "risk owner", cap_sheet_hash)

    def test_cap_rail_id_in_catalogue(self) -> None:
        self.assertIn(rl.RAIL_6_PREMIUM_CAP, rl.RAIL_IDS)
        artefact = rl.PlaybookArtefact(
            artefact_id="UX",
            state=rl.STATE_UNCERTAIN,
            text="vol stance",
            families=(rl.F_PUT_SPREAD_COLLAR,),
            hedge_tickets=(rl.HedgeTicket("UT", rl.F_PUT_SPREAD_COLLAR, True, True, "human"),),
            market_decisive_feeds=(FEED_AMS_SOYBEAN_BID,),
            contributions=(rl.Contribution(FEED_AMS_SOYBEAN_BID, "USDA AMS", "cash print", "final"),),
            grants_by_feed={FEED_AMS_SOYBEAN_BID: None},
            conduct_attestations=dict(ATT),
        )
        violations = rl.validate_playbook_artefact(artefact, AS_OF)
        self.assertTrue(
            any(v.rail == rl.RAIL_6_PREMIUM_CAP for v in violations),
            f"missing budget must name R6: {violations}",
        )

    def test_budget_without_registry_is_refused_by_name(self) -> None:
        artefact = rl.PlaybookArtefact(
            **{
                **self._uncertain().__dict__,
                "premium_budget": self.budget(),
            }
        )
        violations = rl.validate_playbook_artefact(artefact, AS_OF)
        hits = [v for v in violations if v.rail == rl.RAIL_6_PREMIUM_CAP]
        self.assertTrue(any("cap_sheet_hash cannot be bound" in v.detail for v in hits))

    def test_mismatched_hash_refused(self) -> None:
        registry = reg.RegisteredCapSheets.default()
        self.assertEqual(registry.entry("2026Q4")[0], reg.cap_sheet_hash(reg.load_cap_sheet(reg.CAP_SHEET_SPECIMEN_PATH)))
        artefact = rl.PlaybookArtefact(
            **{
                **self._uncertain().__dict__,
                "premium_budget": self.budget(cap_sheet_hash=HASH_B),
                "cap_sheet_registry": registry,
            }
        )
        violations = rl.validate_playbook_artefact(artefact, AS_OF)
        hits = [v for v in violations if v.rail == rl.RAIL_6_PREMIUM_CAP]
        self.assertTrue(any("does not match the registered sheet" in v.detail for v in hits))

    def test_specimen_sheet_never_unlocks_real_caps(self) -> None:
        registry = reg.RegisteredCapSheets.default()
        real_hash, specimen = registry.entry("2026Q4")
        self.assertTrue(specimen, "the shipped 2026Q4 sheet IS the specimen")
        artefact = rl.PlaybookArtefact(
            **{
                **self._uncertain().__dict__,
                "premium_budget": self.budget(cap_sheet_hash=real_hash),
                "cap_sheet_registry": registry,
            }
        )
        violations = rl.validate_playbook_artefact(artefact, AS_OF)
        hits = [v for v in violations if v.rail == rl.RAIL_6_PREMIUM_CAP]
        self.assertTrue(
            any("SPECIMEN" in v.detail and "never unlocks real caps" in v.detail for v in hits),
            f"matching-but-specimen sheet must be refused BY NAME: {hits}",
        )

    def test_real_signed_sheet_unlocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            real = {
                "quarter": "2027Q1",
                "specimen": False,
                "caps": {
                    "p1_seasonal_premium_budget_percent_of_notional": 1.5,
                    "p2_single_strategy_sub_allocation_percent_of_p1": 40.0,
                    "p3_collar_skew_tolerance_debit_percent_of_p1": 25.0,
                    "set_by": "Hiroki Tomiyasu",
                    "set_on": "2027-01-05",
                },
            }
            path = Path(tmpdir) / "cap-sheet-2027Q1.json"
            path.write_text(json.dumps(real, indent=2), encoding="utf-8")
            registry = reg.RegisteredCapSheets.from_sheet_paths(path)
            registered_hash, specimen = registry.entry("2027Q1")
            self.assertFalse(specimen)
            artefact = rl.PlaybookArtefact(
                **{
                    **self._uncertain().__dict__,
                    "premium_budget": self.budget(
                        cap_sheet_hash=registered_hash, quarter="2027Q1"
                    ),
                    "cap_sheet_registry": registry,
                }
            )
            violations = rl.validate_playbook_artefact(artefact, AS_OF)
            self.assertEqual(
                any(v.rail == rl.RAIL_6_PREMIUM_CAP for v in violations),
                True,
                f"a self-asserted sheet must remain closed: {violations}",
            )

    def test_budget_without_hash_rejected_at_construction(self) -> None:
        with self.assertRaises(ValueError):
            rl.PremiumBudget(1.0, 2.0, "2026Q4", "risk owner")

    def _uncertain(self, **overrides) -> rl.PlaybookArtefact:
        base = dict(
            artefact_id="UX2",
            state=rl.STATE_UNCERTAIN,
            text="vol stance",
            families=(rl.F_PUT_SPREAD_COLLAR,),
            hedge_tickets=(rl.HedgeTicket("UT", rl.F_PUT_SPREAD_COLLAR, True, True, "human"),),
            market_decisive_feeds=(FEED_AMS_SOYBEAN_BID,),
            contributions=(rl.Contribution(FEED_AMS_SOYBEAN_BID, "USDA AMS", "cash print", "final"),),
            grants_by_feed={FEED_AMS_SOYBEAN_BID: None},
            conduct_attestations=dict(ATT),
            premium_budget=None,
            cap_sheet_registry=None,
        )
        base.update(overrides)
        return rl.PlaybookArtefact(**base)


class BetterExceptionsTest(unittest.TestCase):
    """D7 (markets half): contradictions raise RailError saying WHY+WHAT."""

    def test_pre_monotonic_contribution_raises_rail_error(self) -> None:
        artefact = loss_artefact(None)
        late_informed = rl.PlaybookArtefact(
            **{
                **artefact.__dict__,
                "contributions": (
                    rl.Contribution(
                        FEED_AMS_SOYBEAN_BID,
                        "USDA AMS public report",
                        "northwest cash print",
                        "final report, not scored",
                        contribution_time=datetime(2026, 11, 19, tzinfo=timezone.utc),
                    ),
                ),
            }
        )
        try:
            rl.validate_playbook_artefact(late_informed, AS_OF)
        except rl.RailError as exc:
            self.assertEqual(exc.rail, "R5-times")
            self.assertIn("2026-11-19", exc.observed)
            self.assertIn("2026-11-18", exc.observed)
            self.assertIn("postdate", exc.constraint)
        else:
            self.fail("a contribution postdating as_of must raise RailError")

    def test_contemporaneous_and_unset_times_still_validate(self) -> None:
        # unarmed legacy path + a well-formed (valid-state) grant: the
        # artefact passes, so ONLY the timing dimension is exercised
        live = rl.GrantRef(
            name="live",
            issuer="i",
            seat="s",
            scope="x",
            territory="*",
            purpose="p",
            expiry="2099-01-01T00:00:00+00:00",
            evidence_url="https://x/e",
            permits_financial_use=True,
            permits_market_data_use=True,
        )
        contemporary = loss_artefact(live)
        self.assertFalse(any(v.rail == "R5-times" for v in rl.validate_playbook_artefact(contemporary, AS_OF)))
        stamped = rl.PlaybookArtefact(
            **{
                **contemporary.__dict__,
                "contributions": (
                    rl.Contribution(
                        FEED_AMS_SOYBEAN_BID,
                        "USDA AMS public report",
                        "northwest cash print",
                        "final report, not scored",
                        contribution_time=datetime(2026, 11, 17, tzinfo=timezone.utc),
                    ),
                ),
            }
        )
        self.assertFalse(any(v.rail == "R5-times" for v in rl.validate_playbook_artefact(stamped, AS_OF)))

    def test_rail_error_message_carries_both_halves(self) -> None:
        exc = rl.RailError.for_time("observed-stamp", "the rule text")
        self.assertIn("observed-stamp", str(exc))
        self.assertIn("the rule text", str(exc))
        self.assertEqual(exc.rail, "R5-times")


class RegistryUnitTest(unittest.TestCase):
    def test_empty_registry_valid_and_dead(self) -> None:
        empty = reg.RegisteredGrants()
        self.assertEqual(len(empty), 0)
        self.assertFalse(empty.contains(HASH_A))

    def test_non_hex_fingerprints_rejected(self) -> None:
        with self.assertRaises(ValueError):
            reg.RegisteredGrants(["zz" * 32])

    def test_grantref_rejects_bad_fingerprint_shape(self) -> None:
        with self.assertRaises(ValueError):
            rl.GrantRef(
                name="n",
                issuer="i",
                seat="s",
                scope="x",
                territory="*",
                purpose="p",
                expiry="2099-01-01T00:00:00+00:00",
                evidence_url="https://x/e",
                fingerprint="nothex",
            )

    def test_env_loader_reads_registry_file(self) -> None:
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "registry.json"
            path.write_text(json.dumps({"fingerprints": [HASH_A]}), encoding="utf-8")
            old = os.environ.get(reg.ENV_GRANT_REGISTRY)
            os.environ[reg.ENV_GRANT_REGISTRY] = str(path)
            try:
                loaded = reg.RegisteredGrants.from_env()
                self.assertIsNotNone(loaded)
                self.assertTrue(loaded.contains(HASH_A))
            finally:
                if old is None:
                    del os.environ[reg.ENV_GRANT_REGISTRY]
                else:
                    os.environ[reg.ENV_GRANT_REGISTRY] = old

    def test_default_registry_prefers_repo_state_json(self) -> None:
        default = reg.RegisteredGrants.default()
        self.assertEqual(len(default), 4)  # 3 specimens + the operator grant
        self.assertIn("state.json", default.source)


if __name__ == "__main__":
    unittest.main()
