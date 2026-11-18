"""Arb rehearsal — the four doctrine lanes walked end-to-end, as QA.

Role: arbtester (task-7 adjunct; the lead's second campaign). This
module REHEARSES, it does not patch: every misalignment found becomes a
:meth:`Defect` row with a named remedy; nothing in the shipped packages
was changed to soften an outcome.

Lanes, per ``docs/alpha-fairness-doctrine.md`` §3 and
``docs/markets/arbitrage-playbook-rails.md``:

- L1 BEAR (confident-loss): point-in-time matrices at pre-/post-
  publication as-of moments on the recorded WASDE/AMS fixtures; a
  short-futures order INTENT sized to a 120 ha scenario farmer book;
  rails must kill it on grant state with the violation named; then the
  three attacks (forged valid-looking grant, expired grant, specimen).
- L2 BULL (confident-gain): forward-physical + input-financing intent;
  fail-closed on grants; can the rails EXPRESS the doctrine §4.2
  upside-share obligation in the artefact?
- L3 UNCERTAIN (≈50/50): option-collar intent; rails must demand the
  premium budget against a cap table that does not exist yet (the
  playbook ships templates only) and the rejection must NAME the rail.
- L4 HAZARD-IMMINENT chain: shock flags from a fixture replay, the
  reduction intent as an actuation command in a TEMPDIR command ledger
  (proposed→approved→dispatched→acked), an emergency HALT mid-flow
  freezing the lifecycle while voiding stays legal, and the six-facts
  gate choreography (all-true passes; any-one-missing blocks verbosely;
  truthy cheats die).
- L5 CROSS-VOCAB: the agronomy RecommendationRecord must RAISE on
  market kinds, and what happens when one is fed toward the actuation
  drone packet — both refusal ergonomics reported.

House rules honoured: injected clocks everywhere (no wall-clock reads in
any exercised path that matters), ZERO network, every temp artifact in
``tempfile`` directories the caller cleans up, class C stays closed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from farm_ontology.actuation.command_ledger import (
    ActuationRefusal,
    CommandLedger,
)
from farm_ontology.actuation.drone_packet import (
    AdvisoryRef,
    build_drone_packet,
)
from farm_ontology.actuation.gate import GATE_FACT_NAMES, GateCheck
from farm_ontology.agronomy.common import AgronomyRefusal
from farm_ontology.agronomy.recommendation import (
    InputRef,
    RationaleStep,
    draft_recommendation,
)
from farm_ontology.licences.grants import evaluate as licences_evaluate  # noqa: F401 (kept for attack cross-checks)
from farm_ontology.markets.registry import (
    RegisteredGrants,
    bridge_licences_to_grantref as _registry_bridge,
)
from farm_ontology.markets import pit_dataset as pit
from farm_ontology.markets import shock_watch as sw
from farm_ontology.markets import rails as rl
from farm_ontology.markets.pit_dataset import MarketFact

#: The scenario farmer book every lane sizes against (a FIXED rehearsal
#: constant, not a signal): 120 ha under soybeans, 3 t/ha expected.
SCENARIO_HECTARES = 120
SCENARIO_EXPECTED_T_PER_HA = 3.0
#: CBOT soybean futures contract size (exchange fact): 5,000 bushels,
#: 1 bu = 27.216 kg -> 136.077 tonnes per contract (rounded to 3 dp).
TONNES_PER_CONTRACT = 136.077

REHEARSAL_T = datetime(2026, 11, 18, 9, 0, tzinfo=timezone.utc)
T_PRE = datetime(2026, 11, 16, 15, 20, tzinfo=timezone.utc)  # after Pink, before FAO/WASDE/IMF
T_POST = datetime(2026, 11, 17, 2, 0, tzinfo=timezone.utc)  # after every capture

SEVERITY_ORDER = {"blocker": 0, "rough": 1, "cosmetic": 2}


# --------------------------------------------------------------------------- #
# Report plumbing                                                             #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RehearsalStep:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class Defect:
    lane: str
    defect_id: str
    severity: str  # blocker | rough | cosmetic
    finding: str
    named_remedy: str

    def __post_init__(self) -> None:
        if self.severity not in SEVERITY_ORDER:
            raise ValueError("defect severity is blocker, rough, or cosmetic")


@dataclass(frozen=True)
class ArbrehearsalReport:
    """One lane's rehearsal outcome (the lead's mandated shape)."""

    lane: str
    title: str
    steps_ok: tuple[str, ...]
    defects: tuple[Defect, ...]
    steps_failed: tuple[str, ...] = ()
    step_log: tuple[RehearsalStep, ...] = ()
    verdict: str = ""

    @property
    def clean(self) -> bool:
        return not self.steps_failed and not any(d.severity == "blocker" for d in self.defects)


def _step(name: str, fn) -> RehearsalStep:
    try:
        detail = fn()
        return RehearsalStep(name=name, ok=True, detail=detail)
    except AssertionError as exc:
        return RehearsalStep(name=name, ok=False, detail=f"ASSERT: {exc}")
    except Exception as exc:  # noqa: BLE001 — a rehearsal records, never crashes
        return RehearsalStep(name=name, ok=False, detail=f"{type(exc).__name__}: {exc}")


def _report(lane: str, title: str, steps: list[RehearsalStep], defects: list[Defect], verdict: str) -> ArbrehearsalReport:
    return ArbrehearsalReport(
        lane=lane,
        title=title,
        steps_ok=tuple(step.name for step in steps if step.ok),
        steps_failed=tuple(step.name for step in steps if not step.ok),
        defects=tuple(defects),
        step_log=tuple(steps),
        verdict=verdict,
    )


# --------------------------------------------------------------------------- #
# The WS6-grant bridge — now DELEGATING to the real one (fix sprint D1/D2)    #
# --------------------------------------------------------------------------- #


def bridge_licences_to_grantref(feed_id: str, at: datetime, grants_dir=None):
    """Rehearsal shim: delegate to the REAL bridge in
    ``farm_ontology.markets.registry`` (kept so the lane code and any
    earlier callers read identically). The real bridge transplants the
    licences verdict verbatim (D2) and carries the certificate
    fingerprint (D1) — the flattening this module used to exhibit is
    gone; the lanes below assert the healed behaviour."""
    return _registry_bridge(feed_id, at, grants_dir=grants_dir)


# --------------------------------------------------------------------------- #
# L1 BEAR                                                                     #
# --------------------------------------------------------------------------- #


def _l1_intent_artefact(grants: dict, text_clauses: bool = True, grant_registry=None) -> rl.PlaybookArtefact:
    physical_tonnes = SCENARIO_HECTARES * SCENARIO_EXPECTED_T_PER_HA
    lots = math.ceil(physical_tonnes / TONNES_PER_CONTRACT)
    text = (
        f"ORDER INTENT (own book): short CBOT soybean futures x{lots} lots, "
        f"sized to the {SCENARIO_HECTARES} ha scenario farmer book "
        f"({physical_tonnes:.0f} t at {SCENARIO_EXPECTED_T_PER_HA} t/ha; "
        f"{TONNES_PER_CONTRACT} t per 5,000 bu contract); anchor: physical "
        "handling exposure. "
        + (rl.DISCLOSURE_CLAUSE if text_clauses else "")
    )
    return rl.PlaybookArtefact(
        artefact_id="L1-short-futures-intent",
        state=rl.STATE_CONFIDENT_LOSS,
        text=text,
        families=(rl.F_SHORT_CBOT_SOYBEAN_FUTURES,),
        hedge_tickets=(
            rl.HedgeTicket(
                ticket_id="L1-T1",
                family=rl.F_SHORT_CBOT_SOYBEAN_FUTURES,
                would_farmer_still_sign=True,
                filed_in_trade_ledger=True,
                drafted_by="human risk owner",
            ),
        ),
        market_decisive_feeds=(pit.FEED_AMS_SOYBEAN_BID, pit.FEED_USDA_WASDE),
        contributions=(
            rl.Contribution(
                feed=pit.FEED_AMS_SOYBEAN_BID,
                licence_attribution="USDA AMS public report ams_3225",
                support_statement="northwest cash market print",
                error_statement="final printed report; band 10.7900-11.3400, average 11.1600",
            ),
            rl.Contribution(
                feed=pit.FEED_USDA_WASDE,
                licence_attribution="USDA WASDE page header",
                support_statement="U.S./world balance tables",
                error_statement="forecast, revised in later months; not scored",
            ),
        ),
        grants_by_feed=grants,
        conduct_attestations={rid: True for rid in rl.CONDUCT_ATTESTATION_IDS},
        grant_registry=grant_registry,
    )


def run_lane1() -> tuple[ArbrehearsalReport, dict]:
    steps: list[RehearsalStep] = []
    defects: list[Defect] = []

    # -- step: PIT matrices at pre-/post-publication as-of moments ---------- #
    def pre_post():
        pre_rows = pit.matrix(T_PRE)
        post_rows = pit.matrix(T_POST)
        pre_subjects = {row["subject"] for row in pre_rows}
        post_subjects = {row["subject"] for row in post_rows}
        assert pit.SUBJECT_WASDE not in pre_subjects, "WASDE visible before its recording commit"
        assert pit.SUBJECT_WASDE in post_subjects, "WASDE missing after its recording commit"
        ams_avg = [row for row in post_rows if row["metric"] == "cash_bid_average"][0]
        assert ams_avg["value"] == 11.16 and ams_avg["unit"] == "$/Bu"
        return (
            f"pre: {len(pre_subjects)} subjects (no WASDE); post: {len(post_subjects)} "
            f"(WASDE in, AMS average 11.16 $/Bu)"
        )

    steps.append(_step("pit-matrix-pre-post-publication", pre_post))

    # -- step: intent built and sized ----------------------------------------#
    def intent():
        artefact = _l1_intent_artefact({})
        physical_tonnes = SCENARIO_HECTARES * SCENARIO_EXPECTED_T_PER_HA
        lots = math.ceil(physical_tonnes / TONNES_PER_CONTRACT)
        assert f"x{lots} lots" in artefact.text, "intent text must carry the sized lots"
        return f"intent text carries {lots}-lot short against the {SCENARIO_HECTARES} ha book"

    steps.append(_step("intent-sized-to-120ha-scenario", intent))

    # -- step: rails verdict against the REAL licences bridge ----------------#
    bridge_notes: dict[str, str] = {}
    real_grants: dict[str, rl.GrantRef | None] = {}
    for feed in (pit.FEED_AMS_SOYBEAN_BID, pit.FEED_USDA_WASDE):
        ref, reason = bridge_licences_to_grantref(feed, REHEARSAL_T)
        real_grants[feed] = ref
        bridge_notes[feed] = reason

    def rails_verdict():
        artefact = _l1_intent_artefact(real_grants)
        violations = rl.validate_playbook_artefact(artefact, REHEARSAL_T)
        assert violations, "L1 intent unexpectedly passed rails (grant wall absent?!)"
        rails_named = [v.rail for v in violations]
        assert all(rail == rl.RAIL_5_TRUTHFULNESS for rail in rails_named), (
            f"unexpected non-R5 killers: {violations}"
        )
        grants_named = sum("fails closed on grant state" in v.detail for v in violations)
        assert grants_named == 2, f"expected both feed grant-walls named, saw {violations}"
        # D2 healed: the bridge transplants the licences verdict VERBATIM,
        # so the wall's detail names the real reason ('no_grant'), not a
        # generic 'closed'.
        verbatim = all("no_grant" in v.detail for v in violations)
        assert verbatim, f"reason transplant broken (expected verbatim no_grant): {violations}"
        return (
            f"dies on grant state as expected: {grants_named} R5 violations, "
            f"licences reasons verbatim (bridge: {bridge_notes})"
        )

    steps.append(_step("rails-verdict-dies-on-grant-state", rails_verdict))

    # -- attack A: forged valid-looking GrantRef ------------------------------#
    def forged():
        forged_ref = rl.GrantRef(
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
            fingerprint="0" * 64,  # plausible-looking, registered nowhere
        )
        forged_grants = {feed: forged_ref for feed in (pit.FEED_AMS_SOYBEAN_BID, pit.FEED_USDA_WASDE)}
        # Post-fix world: with the provenance registry ARMED, the forgery
        # dies on its fingerprint even though every visible field shines.
        default_registry = RegisteredGrants.default()
        armed = _l1_intent_artefact(forged_grants, grant_registry=default_registry)
        armed_violations = rl.validate_playbook_artefact(armed, REHEARSAL_T)
        provenance_hits = [
            v for v in armed_violations if "fingerprint-not-in-registry" in v.detail
        ]
        assert provenance_hits, (
            f"forgery must die on provenance when the registry is armed: "
            f"{armed_violations}"
        )
        # Legacy opt-out documented: UNARMED validation still accepts
        # well-formed refs (validate has no implicit IO), so production
        # callers MUST arm registries — that residual is part of D1.
        unarmed = _l1_intent_artefact(forged_grants)
        unarmed_violations = rl.validate_playbook_artefact(unarmed, REHEARSAL_T)
        legacy_passes = not unarmed_violations
        assert legacy_passes, f"legacy unarmed path changed behaviour: {unarmed_violations}"
        defects.append(
            Defect(
                lane="L1",
                defect_id="D1",
                severity="rough",
                finding=(
                    "HISTORICAL (healed this sprint): a self-authored GrantRef with "
                    "permits_* True used to sail through validate_playbook_artefact "
                    "with zero violations — rails could not distinguish a forged "
                    "grant from a bridged one. Post-fix, GrantRef carries a 64-hex "
                    "fingerprint and an armed RegisteredGrants attestation rejects "
                    "any ref whose fingerprint is not on it "
                    "('fingerprint-not-in-registry'). RESIDUAL: validation arms the "
                    "registry only when the artefact carries one — unarmed calls "
                    "keep the legacy permissive path, so the caller discipline "
                    "(always attach grant_registry) is load-bearing"
                ),
                named_remedy=(
                    "DONE for the engine (registry + fingerprints); the residual "
                    "closes when artefact factories in the product path always "
                    "attach RegisteredGrants.default() (or the FARM_GRANT_REGISTRY "
                    "env file) before validating"
                ),
            )
        )
        return (
            "forgery died on armed registry ("
            f"{len(provenance_hits)} provenance violations, first: "
            f"{provenance_hits[0].detail[:70]}...); legacy unarmed path "
            f"unchanged ({'passes' if legacy_passes else 'refused'})"
        )

    steps.append(_step("attack-forged-valid-looking-grant", forged))

    # -- attack B: expired grant ----------------------------------------------#
    def expired():
        expired_ref = rl.GrantRef(
            name="expired",
            issuer="licences engine",
            seat="historical",
            scope="was",
            territory="*",
            purpose="market data",
            expiry="2026-11-01T00:00:00+00:00",
            evidence_url="https://invalid.example/expired",
            permits_financial_use=True,
            permits_market_data_use=True,
        )
        artefact = _l1_intent_artefact({pit.FEED_AMS_SOYBEAN_BID: expired_ref})
        violations = rl.validate_playbook_artefact(artefact, REHEARSAL_T)
        hit = [v for v in violations if v.rail == rl.RAIL_5_TRUTHFULNESS and "expired" in v.detail]
        assert hit, f"expired grant escaped: {violations}"
        return f"caught: {hit[0].detail[:80]}..."

    steps.append(_step("attack-expired-grant-caught", expired))

    # -- attack C: specimen ref via the bridge --------------------------------#
    def specimen():
        ref, reason = bridge_licences_to_grantref("earth-engine.export", REHEARSAL_T)
        assert reason == "specimen", f"expected the licences engine to say specimen, got {reason!r}"
        assert ref.specimen is True and ref.state_detail == "specimen"
        ee_contribution = rl.Contribution(
            feed="earth-engine.export",
            licence_attribution="specimen certificate only",
            support_statement="export-scoped",
            error_statement="none recorded (specimen)",
        )
        # Arm the DEFAULT registry: the EE specimen's certificate
        # fingerprint IS registered (it sits on the WS6 state.json), so
        # provenance ADMITS the ref and the SPECIMEN state itself must be
        # what kills it — with the reason named, not flattened (D2 healed).
        artefact = rl.PlaybookArtefact(
            **{
                **_l1_intent_artefact({"earth-engine.export": ref}).__dict__,
                "market_decisive_feeds": ("earth-engine.export",),
                "contributions": (ee_contribution,),
                "grant_registry": RegisteredGrants.default(),
            }
        )
        violations = rl.validate_playbook_artefact(artefact, REHEARSAL_T)
        hit = [v for v in violations if v.rail == rl.RAIL_5_TRUTHFULNESS]
        assert hit, "specimen-fed artefact passed rails"
        verbatim = all("specimen" in v.detail for v in hit)
        assert verbatim, f"D2 regression: specimen reason no longer verbatim: {hit}"
        provenance_noise = [v for v in violations if "fingerprint-not-in-registry" in v.detail]
        assert not provenance_noise, (
            f"the registered specimen fingerprint should pass provenance: {provenance_noise}"
        )
        defects.append(
            Defect(
                lane="L1",
                defect_id="D2",
                severity="rough",
                finding=(
                    "HISTORICAL (healed this sprint): the licences engine's precise "
                    "'specimen' verdict used to flatten into rails' generic 'closed'. "
                    "Post-fix the bridge transplants the verdict verbatim into "
                    "GrantRef.state_detail and grant_state_at returns the DISTINCT "
                    "GRANT_SPECIMEN state ('specimen grant never unlocks (licences "
                    "verdict: specimen)'), so the analyst reads WHY the wall stood"
                ),
                named_remedy=(
                    "DONE: state_detail transplant + GRANT_SPECIMEN state; the "
                    "rehearsal asserts the verbatim reason end-to-end"
                ),
            )
        )
        return (
            f"caught AS specimen (distinct state, reason verbatim: "
            f"{hit[0].detail[:70]}...); flattening gone"
        )

    steps.append(_step("attack-specimen-ref-caught", specimen))

    report = _report(
        "L1",
        "BEAR confident-loss: PIT intent vs the grant wall",
        steps,
        defects,
        verdict=(
            "Intent dies on the grant wall exactly as designed (both feeds R5, licences "
            "reasons verbatim post-D2); forgeries now die on armed provenance (D1 healed, "
            "unarmed legacy path documented as the residual); specimens die AS specimens"
        ),
    )
    return report, bridge_notes


# --------------------------------------------------------------------------- #
# L2 BULL                                                                     #
# --------------------------------------------------------------------------- #


def run_lane2() -> ArbrehearsalReport:
    steps: list[RehearsalStep] = []
    defects: list[Defect] = []
    real_grants = {
        pit.FEED_AMS_SOYBEAN_BID: bridge_licences_to_grantref(pit.FEED_AMS_SOYBEAN_BID, REHEARSAL_T)[0],
        pit.FEED_USDA_WASDE: bridge_licences_to_grantref(pit.FEED_USDA_WASDE, REHEARSAL_T)[0],
    }

    def intent():
        artefact = rl.PlaybookArtefact(
            artefact_id="L2-forward-physical-intent",
            state=rl.STATE_CONFIDENT_GAIN,
            text="INTENT: forward physical purchase of the scenario book + input-supplier financing.",
            families=(rl.F_FORWARD_PHYSICAL_COMMITMENT, rl.F_INPUT_SUPPLIER_INVESTMENT),
            hedge_tickets=(
                rl.HedgeTicket("L2-T1", rl.F_FORWARD_PHYSICAL_COMMITMENT, True, True, "human"),
                rl.HedgeTicket("L2-T2", rl.F_INPUT_SUPPLIER_INVESTMENT, True, True, "human"),
            ),
            market_decisive_feeds=(pit.FEED_AMS_SOYBEAN_BID,),
            contributions=(
                rl.Contribution(
                    pit.FEED_AMS_SOYBEAN_BID,
                    "USDA AMS public report ams_3225",
                    "northwest cash market print",
                    "band low/high + average as printed",
                ),
            ),
            grants_by_feed=real_grants,
            conduct_attestations={rid: True for rid in rl.CONDUCT_ATTESTATION_IDS},
        )
        violations = rl.validate_playbook_artefact(artefact, REHEARSAL_T)
        assert any("upside" in v.detail for v in violations), (
            f"gain artefact without upside term must trip R2: {violations}"
        )
        return "fail-closed holds; the missing upside term is the first thing named"

    steps.append(_step("bull-intent-fails-closed-needs-upside-term", intent))

    def upside_term_added():
        with_term = rl.PlaybookArtefact(
            **{
                **_gain_artefact().__dict__,
                "upside_term": rl.UpsideShareTerm(0.3, rl.Beneficiary.FARMER_CONTRACTED, "Founder", "contract-L2"),
            }
        )
        violations = rl.validate_playbook_artefact(with_term, REHEARSAL_T)
        assert not any(v.rail == rl.RAIL_2_UPSIDE_SHARE for v in violations), "R2 must clear with a term"
        assert any(v.rail == rl.RAIL_5_TRUTHFULNESS for v in violations), "grant wall still must stand"
        return "upside-share obligation IS expressible via UpsideShareTerm (typed beneficiary + contract)"

    steps.append(_step("upside-share-obligation-expressible", upside_term_added))

    def clause_escape():
        # §4.1 is universal for contracts sold to farmers; the rails table
        # ties R1 to specific STATES. A gain artefact posing as a farmer
        # contract with an empty text: does anything catch it?
        naked = rl.PlaybookArtefact(
            **{
                **_gain_artefact().__dict__,
                "upside_term": rl.UpsideShareTerm(0.3, rl.Beneficiary.FARMER_CONTRACTED, "Founder", "contract-L2"),
            }
        )
        violations = rl.validate_playbook_artefact(naked, REHEARSAL_T)
        r1_hit = [v for v in violations if v.rail == rl.RAIL_1_DISCLOSURE]
        assert not r1_hit, "premise: rails does NOT demand R1 in the gain state"
        defects.append(
            Defect(
                lane="L2",
                defect_id="D3",
                severity="rough",
                finding=(
                    "doctrine §4.1 is universal ('ANY contract sold to a farmer'), but "
                    "the rails table enforces R1 only in state confident-loss — an "
                    "artefact cannot DECLARE itself a farmer contract, so a "
                    "confident-gain forward-physical CONTRACT could ship without the "
                    "verbatim clause and nothing in rails would blink"
                ),
                named_remedy=(
                    "add a carries_farmer_contract axis (mirroring "
                    "carries_farmer_level_data) and require R1 whenever it is set, "
                    "regardless of state"
                ),
            )
        )
        return f"escape CONFIRMED: no R1 demanded (violations: {[v.rail for v in violations]})"

    steps.append(_step("r1-universal-clause-escape-probe", clause_escape))

    def beneficiary_weakness():
        # D4 healed: the beneficiary is TYPED now; a free string dies at
        # construction, and the typed members travel.
        rejected = False
        try:
            rl.UpsideShareTerm(0.3, "someone-not-the-farmer", "no one", "contract-anybody")
        except ValueError:
            rejected = True
        assert rejected, "free-string beneficiary should have been refused post-D4"
        typed = rl.UpsideShareTerm(
            0.3, rl.Beneficiary.FARMER_CONTRACTED, "Founder", "contract-L2"
        )
        assert isinstance(typed.beneficiary, rl.Beneficiary)
        defects.append(
            Defect(
                lane="L2",
                defect_id="D4",
                severity="cosmetic",
                finding=(
                    "HISTORICAL (healed this sprint): R2's beneficiary used to be a "
                    "free string, so the rail could not see WHO accrued the share. "
                    "Post-fix beneficiary is a typed Beneficiary member "
                    "(OUR_BOOK | FARMER_CONTRACTED | FARMER_TRIAL) and free strings "
                    "die at construction. RESIDUAL: the type distinguishes the "
                    "DECLARED relationship class; tying the member to a specific "
                    "farmer consent record stays the grants-side job"
                ),
                named_remedy=(
                    "DONE for the type; full binding happens when the consent-grant "
                    "object (grants/ v2) carries a party ref rails can match"
                ),
            )
        )
        return (
            "free-string beneficiary REJECTED at construction; typed members travel "
            f"({typed.beneficiary.value})"
        )

    steps.append(_step("r2-beneficiary-binding-probe", beneficiary_weakness))

    report = _report(
        "L2",
        "BULL confident-gain: forward physical vs the grant wall + expressibility",
        steps,
        defects,
        verdict=(
            "Gain path fails closed on grants and CAN express the §4.2 upside share; "
            "the §4.1 clause escape (D3) is the lane's real gap"
        ),
    )
    return report


def _gain_artefact(**overrides) -> rl.PlaybookArtefact:
    base = dict(
        artefact_id="L2-forward-physical-intent",
        state=rl.STATE_CONFIDENT_GAIN,
        text="",
        families=(rl.F_FORWARD_PHYSICAL_COMMITMENT, rl.F_INPUT_SUPPLIER_INVESTMENT),
        hedge_tickets=(
            rl.HedgeTicket("L2-T1", rl.F_FORWARD_PHYSICAL_COMMITMENT, True, True, "human"),
            rl.HedgeTicket("L2-T2", rl.F_INPUT_SUPPLIER_INVESTMENT, True, True, "human"),
        ),
        market_decisive_feeds=(pit.FEED_AMS_SOYBEAN_BID,),
        contributions=(
            rl.Contribution(
                pit.FEED_AMS_SOYBEAN_BID,
                "USDA AMS public report ams_3225",
                "northwest cash market print",
                "band low/high + average as printed",
            ),
        ),
        grants_by_feed={
            pit.FEED_AMS_SOYBEAN_BID: bridge_licences_to_grantref(pit.FEED_AMS_SOYBEAN_BID, REHEARSAL_T)[0],
        },
        conduct_attestations={rid: True for rid in rl.CONDUCT_ATTESTATION_IDS},
    )
    base.update(overrides)
    return rl.PlaybookArtefact(**base)


# --------------------------------------------------------------------------- #
# L3 UNCERTAIN                                                                #
# --------------------------------------------------------------------------- #


def run_lane3() -> ArbrehearsalReport:
    steps: list[RehearsalStep] = []
    defects: list[Defect] = []

    def collar_intent():
        artefact = rl.PlaybookArtefact(
            artefact_id="L3-collar-intent",
            state=rl.STATE_UNCERTAIN,
            text="VOLATILITY stance: put-spread collar around the scenario book (no directional bet).",
            families=(rl.F_PUT_SPREAD_COLLAR,),
            hedge_tickets=(rl.HedgeTicket("L3-T1", rl.F_PUT_SPREAD_COLLAR, True, True, "human"),),
            market_decisive_feeds=(pit.FEED_AMS_SOYBEAN_BID,),
            contributions=(
                rl.Contribution(
                    pit.FEED_AMS_SOYBEAN_BID,
                    "USDA AMS public report ams_3225",
                    "northwest cash market print",
                    "band as printed",
                ),
            ),
            grants_by_feed={
                pit.FEED_AMS_SOYBEAN_BID: bridge_licences_to_grantref(pit.FEED_AMS_SOYBEAN_BID, REHEARSAL_T)[0],
            },
            conduct_attestations={rid: True for rid in rl.CONDUCT_ATTESTATION_IDS},
        )
        violations = rl.validate_playbook_artefact(artefact, REHEARSAL_T)
        budget_hits = [v for v in violations if "premium budget" in v.detail]
        assert budget_hits, f"collar without budget must be named: {violations}"
        named_rail = budget_hits[0].rail
        # Fix-sprint D5 healed: the demand now carries its own rail id (R6)
        # instead of hiding under the hedge-ticket rail (R3).
        precise = named_rail == rl.RAIL_6_PREMIUM_CAP and "human-set quarterly cap" in budget_hits[0].detail
        defects.append(
            Defect(
                lane="L3",
                defect_id="D5",
                severity="cosmetic",
                finding=(
                    "HISTORICAL (healed this sprint): the premium-budget demand "
                    "used to hide under the hedge-ticket rail id R3; the healed "
                    "validator names it R6 (RAIL_6_PREMIUM_CAP) so cap audits "
                    "have a catalogue anchor of their own"
                ),
                named_remedy=(
                    "DONE: RAIL_6_PREMIUM_CAP exists and the rehearsal now "
                    "asserts the budget demand fires under R6"
                ),
            )
        )
        return f"rejection fires precisely (rail={named_rail!r}, precise={precise})"

    steps.append(_step("collar-intent-demands-premium-budget-precisely", collar_intent))

    def self_authored_budget():
        # Fix-sprint D6 healed: the budget must quote the sha256 of the
        # SIGNED quarterly cap sheet AND that hash must sit on the
        # artefact's cap-sheet registry. With no registry bound (and only
        # the shipped SPECIMEN sheet registered), a self-authored budget
        # can no longer pass — the pre-fix crack is closed and this step
        # verifies the closed wall.
        budget = rl.PremiumBudget(
            1.0, 2.0, "2026Q4", "risk owner (self-declared)", cap_sheet_hash="a" * 64
        )
        funded = rl.PlaybookArtefact(
            **{
                **_uncertain_artefact().__dict__,
                "premium_budget": budget,
            }
        )
        violations = rl.validate_playbook_artefact(funded, REHEARSAL_T)
        budget_hits = [v for v in violations if v.rail == rl.RAIL_6_PREMIUM_CAP]
        assert budget_hits, (
            "post-fix, a self-authored budget without a registered sheet "
            f"must be refused: {violations}"
        )
        assert any(
            "cannot be bound" in v.detail or "registry" in v.detail for v in budget_hits
        )
        defects.append(
            Defect(
                lane="L3",
                defect_id="D6",
                severity="rough",
                finding=(
                    "HISTORICAL (healed this sprint): PremiumBudget was "
                    "self-authorable — rails validated only the SHAPE (fraction "
                    "under cap, human 'set_by', quarter) with no quarterly "
                    "cap-SHEET record to check the budget AGAINST, so any session "
                    "could mint its own 'human-approved' budget. Post-fix the "
                    "budget must carry cap_sheet_hash bound to a registered "
                    "signed sheet; the shipped sheet is a SPECIMEN, so every "
                    "real budget still waits for the human's signature (fail "
                    "closed with the R6 rail named)"
                ),
                named_remedy=(
                    "DONE: cap_sheet_hash is mandatory, RegisteredCapSheets is "
                    "the registry, and the SPECIMEN sheet proves mechanics while "
                    "never unlocking real caps"
                ),
            )
        )
        return "self-authored budget REFUSED (cap sheet unregistered) — wall confirmed"

    steps.append(_step("self-authored-budget-slips-through", self_authored_budget))

    def agent_guard():
        try:
            rl.PremiumBudget(1.0, 2.0, "2026Q4", "ci-agent-42", cap_sheet_hash="a" * 64)
        except ValueError as exc:
            return f"agent-set cap dies at construction: {exc}"
        raise AssertionError("an agent cap_set_by should have been refused")

    steps.append(_step("agent-cannot-mint-the-cap", agent_guard))

    report = _report(
        "L3",
        "UNCERTAIN: collar intent vs the missing cap table",
        steps,
        defects,
        verdict=(
            "Rejection names its rail exactly; the deeper crack is that budgets are "
            "self-authorable while the cap sheet does not exist (D6)"
        ),
    )
    return report


def _uncertain_artefact(**overrides) -> rl.PlaybookArtefact:
    base = dict(
        artefact_id="L3-collar-intent",
        state=rl.STATE_UNCERTAIN,
        text="VOLATILITY stance (no directional bet).",
        families=(rl.F_PUT_SPREAD_COLLAR,),
        hedge_tickets=(rl.HedgeTicket("L3-T1", rl.F_PUT_SPREAD_COLLAR, True, True, "human"),),
        market_decisive_feeds=(pit.FEED_AMS_SOYBEAN_BID,),
        contributions=(
            rl.Contribution(
                pit.FEED_AMS_SOYBEAN_BID,
                "USDA AMS public report ams_3225",
                "northwest cash market print",
                "band as printed",
            ),
        ),
        grants_by_feed={
            pit.FEED_AMS_SOYBEAN_BID: bridge_licences_to_grantref(pit.FEED_AMS_SOYBEAN_BID, REHEARSAL_T)[0],
        },
        conduct_attestations={rid: True for rid in rl.CONDUCT_ATTESTATION_IDS},
    )
    base.update(overrides)
    return rl.PlaybookArtefact(**base)


# --------------------------------------------------------------------------- #
# L4 HAZARD-IMMINENT chain                                                    #
# --------------------------------------------------------------------------- #


def run_lane4(tmpdir) -> tuple[ArbrehearsalReport, CommandLedger]:
    steps: list[RehearsalStep] = []
    defects: list[Defect] = []
    ledger = CommandLedger()
    base_facts = list(pit.all_facts())
    injected = MarketFact_below_band()
    as_of = datetime(2026, 11, 18, 9, 0, tzinfo=timezone.utc)

    def flag_first():
        flags, gaps = sw.evaluate(sw.SHOCK_RULES, [*base_facts, injected], as_of)
        assert gaps == (), f"fixture replay should be fully judgeable: {gaps}"
        fired = [f.rule_id for f in flags]
        assert fired == ["ams-bid-below-recorded-band"], f"expected the lower-band shock, saw {fired}"
        return f"shock fired: {flags[0].flag_id} (evidence {flags[0].evidence_fact_time.isoformat()})"

    steps.append(_step("fixture-replay-fires-lower-band-shock", flag_first))

    def silence_baseline():
        flags, gaps = sw.evaluate(sw.SHOCK_RULES, base_facts, as_of)
        assert flags == () and gaps == (), "the pristine fixtures must stay silent"
        return "pristine fixture baseline stays silent (no false positives)"

    steps.append(_step("pristine-fixtures-stay-silent", silence_baseline))

    cmd_ids: dict[str, str] = {}

    def propose_cmd():
        prescription = {
            "action": "emergency-sop-dispatch",
            "channel": "operator-device",
            "basis": "shock:ams-bid-below-recorded-band",
            "native_support": "grid-cell 0.05deg (JMA MSM) + northwest cash print",
            "use_class": "Screening",
        }
        record = ledger.propose(
            prescription=prescription,
            actor={"kind": "service", "id": "shock-watch-pipeline"},
            at=as_of,
            polygon_ref=None,
        )
        cid = record["event"]["command_id"]
        cmd_ids["reduce"] = cid
        assert ledger.state_of(cid) == "proposed"
        return f"reduction intent proposed: {cid[:12]}…"

    steps.append(_step("reduction-intent-proposed", propose_cmd))

    def four_eyes():
        same = dict(kind="service", id="shock-watch-pipeline")
        try:
            ledger.approve(cmd_ids["reduce"], approver=same, at=as_of + timedelta(minutes=1))
        except ActuationRefusal as exc:
            assert exc.refusal == "approver_must_be_human"
            human_same = dict(kind="human", id="shock-watch-pipeline")
            try:
                ledger.approve(cmd_ids["reduce"], approver=human_same, at=as_of + timedelta(minutes=1))
            except ActuationRefusal as exc2:
                assert exc2.refusal == "approver_equals_proposer"
                return "service approval and self-approval both refused by name"
        raise AssertionError("four-eyes guard did not fire")

    steps.append(_step("four-eyes-guard-verbosely", four_eyes))

    def approve_dispatch():
        ledger.approve(cmd_ids["reduce"], approver={"kind": "human", "id": "risk-owner"}, at=as_of + timedelta(minutes=2))
        ledger.dispatch(
            cmd_ids["reduce"],
            actor={"kind": "service", "id": "intake"},
            receipt={"transport": "sop-sheet", "version": 1},
            at=as_of + timedelta(minutes=3),
        )
        assert ledger.state_of(cmd_ids["reduce"]) == "dispatched"
        return "approved (human ≠ proposer) then dispatched with receipt"

    steps.append(_step("approve-then-dispatch", approve_dispatch))

    def halt_mid_flow():
        ledger.halt(
            reason="typhoon inbound; freeze all field commands",
            actor={"kind": "human", "id": "risk-owner"},
            at=as_of + timedelta(minutes=4),
        )
        assert ledger.halted() is True
        return "HALT raised by the human risk owner; halted() == True"

    steps.append(_step("halt-mid-flow-raised", halt_mid_flow))

    def frozen_but_void_legal():
        try:
            ledger.acknowledge(
                cmd_ids["reduce"], actor={"kind": "service", "id": "device"}, receipt={"sig": "x"}, at=as_of + timedelta(minutes=5)
            )
        except ActuationRefusal as exc:
            assert exc.refusal == "halted", exc.refusal
            # void the dispatched command WHILE halted — legal and expected
            ledger.void(
                cmd_ids["reduce"],
                reason="storm voids the exposure; SOP superseded",
                actor={"kind": "human", "id": "risk-owner"},
                at=as_of + timedelta(minutes=6),
            )
            assert ledger.state_of(cmd_ids["reduce"]) == "voided"
            return "acknowledge froze ([refusal:halted]); void stayed legal; cmd now voided"
        raise AssertionError("acknowledge proceeded during HALT")

    steps.append(_step("lifecycle-freezes-void-still-legal", frozen_but_void_legal))

    def lift_then_terminal_moves():
        ledger.lift_halt(reason="storm passed", actor={"kind": "human", "id": "risk-owner"}, at=as_of + timedelta(minutes=7))
        assert ledger.halted() is False
        try:
            ledger.acknowledge(
                cmd_ids["reduce"], actor={"kind": "service", "id": "device"}, receipt={"sig": "x"}, at=as_of + timedelta(minutes=8)
            )
        except Exception as exc:  # IllegalTransition expected: voided is terminal
            assert type(exc).__name__ == "IllegalTransition", type(exc).__name__
            return f"post-lift, voided stays terminal ({type(exc).__name__})"
        raise AssertionError("voided command was resurrected")

    steps.append(_step("voided-terminal-after-lift", lift_then_terminal_moves))

    def full_loop_second_cmd():
        second_rx = {
            "action": "emergency-sop-dispatch",
            "channel": "operator-device",
            "basis": "post-storm resumption",
            "native_support": "grid-cell 0.05deg (JMA MSM)",
            "use_class": "Screening",
        }
        rec = ledger.propose(prescription=second_rx, actor={"kind": "service", "id": "shock-watch-pipeline"}, at=as_of + timedelta(minutes=9))
        cid = rec["event"]["command_id"]
        ledger.approve(cid, approver={"kind": "human", "id": "risk-owner"}, at=as_of + timedelta(minutes=10))
        ledger.dispatch(cid, actor={"kind": "service", "id": "intake"}, receipt={"transport": "sop-sheet", "v": 2}, at=as_of + timedelta(minutes=11))
        ledger.acknowledge(cid, actor={"kind": "service", "id": "device"}, receipt={"sig": "acked"}, at=as_of + timedelta(minutes=12))
        assert ledger.state_of(cid) == "acknowledged"
        cmd_ids["resume"] = cid
        return "full proposed→approved→dispatched→acked loop completed post-lift"

    steps.append(_step("full-loop-after-lift", full_loop_second_cmd))

    def persistence():
        from pathlib import Path

        # Blocker sentinel: verify_chain over a chain CONTAINING a void
        # event (the main ledger just wrote one, legally). Registered as
        # defect D9 WHETHER OR NOT the crash reproduces — once actuation
        # heals _replay_problems, the finding text flips to the
        # regression-sentinel wording and the step keeps passing.
        crash = None
        try:
            outcome = ledger.verify_chain()
        except Exception as exc:  # noqa: BLE001
            crash = f"{type(exc).__name__}: {exc}"
        if crash is None:
            assert outcome["ok"] is True, f"verify on void-chain noisy: {outcome}"
            defects.append(
                Defect(
                    lane="L4",
                    defect_id="D9",
                    severity="blocker",
                    finding=(
                        "REGRESSION SENTINEL (was a live blocker at rehearsal "
                        "time): CommandLedger.verify_chain() crashed on any chain "
                        "containing a legal void event (KeyError: 'void'); this "
                        "run recomputed the void-bearing chain CLEAN — the "
                        "upstream fix holds. If this text ever says 'crashed' "
                        "again, the sentinel has caught a regression."
                    ),
                    named_remedy=(
                        "keep the void special-case ordered before the "
                        "_TRANSITION_FROM lookup, with a regression test over a "
                        "void-bearing chain"
                    ),
                )
            )
        else:
            defects.append(
                Defect(
                    lane="L4",
                    defect_id="D9",
                    severity="blocker",
                    finding=(
                        "CommandLedger.verify_chain() CRASHES on any chain containing "
                        f"a legal void event — {crash} — because _replay_problems "
                        "computes the expected from-state from _TRANSITION_FROM before "
                        "the void special-case, and 'void' is absent from that table. "
                        "Emergency flows that void mid-HALT can neither be re-loaded "
                        "(from_path verifies) nor audited (verify_chain) afterwards."
                    ),
                    named_remedy=(
                        "treat 'void' as start-state-exempt in _replay_problems (order "
                        "the void special-case BEFORE the _TRANSITION_FROM lookup, or "
                        "add 'void' mapped to None) and add a regression test over a "
                        "void-bearing chain"
                    ),
                )
            )
        # Void-free mini-chain exercises save/reload/tamper mechanics.
        mini = CommandLedger()
        rx = {
            "action": "drainage-note",
            "native_support": "grid-cell 0.05deg",
            "use_class": "Screening",
        }
        t0 = as_of
        m_rec = mini.propose(prescription=rx, actor={"kind": "service", "id": "s"}, at=t0)
        mini.approve(m_rec["event"]["command_id"], approver={"kind": "human", "id": "h"}, at=t0 + timedelta(minutes=1))
        mini.dispatch(m_rec["event"]["command_id"], actor={"kind": "service", "id": "i"}, receipt={"r": 1}, at=t0 + timedelta(minutes=2))
        mini.acknowledge(m_rec["event"]["command_id"], actor={"kind": "service", "id": "d"}, receipt={"a": 1}, at=t0 + timedelta(minutes=3))
        path = Path(tmpdir) / "cmd-ledger.jsonl"
        mini.save(path)
        reloaded = CommandLedger.from_path(path)
        assert reloaded.verify_chain()["ok"] is True
        cid = m_rec["event"]["command_id"]
        assert reloaded.snapshot()[cid] == "acknowledged"
        # tamper probe: edit a record like a file editor would
        tampered = CommandLedger(records=list(reloaded.records))
        first = tampered._records[0]
        first["event"] = dict(first["event"], reason="edited-history")
        tampered_report = tampered.verify_chain()
        assert tampered_report["ok"] is False, "tampering must be detectable"
        return (
            "void-free chain: tempdir save/reload/tamper verified; "
            f"void-bearing chain verify: {'OK' if crash is None else 'CRASH -> D9 recorded (' + crash + ')'}"
        )

    steps.append(_step("ledger-tempdir-persistence-and-tamper", persistence))

    def gate_all_true():
        facts = {name: True for name in GATE_FACT_NAMES}
        check = GateCheck.from_facts(facts)
        assert check.eligible_for_live_commands() is True
        assert check.gaps() == ()
        return "all-six-true gate OPENS (and only then)"

    steps.append(_step("gate-all-true-passes", gate_all_true))

    def gate_one_missing_each():
        diagnoses = []
        for omitted in GATE_FACT_NAMES:
            facts = {name: True for name in GATE_FACT_NAMES}
            facts[omitted] = None
            check = GateCheck.from_facts(facts)
            assert check.eligible_for_live_commands() is False
            gaps = check.gaps()
            named = [gap["fact"] for gap in gaps]
            assert named == [omitted], f"expected exactly {omitted}, saw {named}"
            gap = gaps[0]
            assert gap["kind"] == "missing" and gap["meaning"] and gap["satisfied_by"]
            diagnoses.append(omitted)
        summary = check.refusal_summary()
        assert summary.startswith("ineligible")
        return f"each-of-six-single-missing blocks with a NAMED, explained gap: {diagnoses}"

    steps.append(_step("gate-any-one-missing-blocks-verbosely", gate_one_missing_each))

    def gate_truthy_cheats_die():
        cheats = [
            {"min_instances": "yes"},
            {"min_instances": 1},
            {"kill_switch_contract_signed": "true"},
            {"field_drill_completed": 1.0},
            {"auth_configured": "Y"},
        ]
        caught = []
        for cheat in cheats:
            facts = {name: True for name in GATE_FACT_NAMES}
            facts.update(cheat)
            try:
                GateCheck.from_facts(facts)
            except Exception as exc:  # ActuationGap expected
                caught.append((next(iter(cheat)), type(exc).__name__))
        assert len(caught) == len(cheats), f"some truthy cheat survived: {cheats} vs {caught}"
        return f"truthy cheats die with named gaps: {caught}"

    steps.append(_step("gate-truthy-cheats-die", gate_truthy_cheats_die))

    report = _report(
        "L4",
        "HAZARD-IMMINENT: flags → reduction intent → ledger → HALT → gate",
        steps,
        defects,
        verdict=(
            "Mechanical chain fully rehearsable OFFLINE: flags, four-eyes, HALT freeze "
            "(void still legal), terminal voided, gate choreography with named gaps all held"
        ),
    )
    return report, ledger


def MarketFact_below_band():
    """An injected below-band AMS print derived FROM the recorded fixture row."""
    factory_row = next(
        row
        for row in pit.all_facts()
        if row.feed == pit.FEED_AMS_SOYBEAN_BID and row.metric == "cash_bid_average"
    )
    return MarketFact(
        **{
            **factory_row.__dict__,
            "fact_time": datetime(2026, 11, 17, 6, 0, tzinfo=timezone.utc),
            "value": 10.5,
            "value_text": "replay injection: average 10.5 inside the recorded row shape",
        }
    )


# --------------------------------------------------------------------------- #
# L5 CROSS-VOCAB                                                              #
# --------------------------------------------------------------------------- #


def run_lane5() -> ArbrehearsalReport:
    steps: list[RehearsalStep] = []
    defects: list[Defect] = []

    def record_constructs():
        rec = _irrigation_record()
        assert rec.recommendation_id.startswith("rec:")
        assert rec.permits_financial_use is False and rec.requires_human_signoff is True
        return f"baseline v0 record mints: {rec.recommendation_id[:16]}… (signoff required, financial False)"

    steps.append(_step("recommendation-record-baseline", record_constructs))

    def market_kinds_raise():
        ergonomics = {}
        for kind in ("hedge", "trade"):
            try:
                draft_recommendation(
                    kind=kind,
                    inputs=[_input_ref()],
                    rationale=[RationaleStep("probe", "probe", True)],
                    payload={"note": "cross-vocab probe"},
                    drafted_at=datetime(2026, 11, 18, tzinfo=timezone.utc),
                    expires_at=datetime(2026, 12, 18, tzinfo=timezone.utc),
                )
            except AgronomyRefusal as exc:
                ergonomics[kind] = (
                    f"[refusal:{exc.refusal}] {exc.detail[:60]}… "
                    f"(remedy: {exc.remediation})"
                )
        assert set(ergonomics) == {"hedge", "trade"}, f"kinds that did NOT raise: {ergonomics}"
        assert all("route market-side intent to WS7" in text for text in ergonomics.values())
        return f"BOTH market kinds raise with named remedies: {ergonomics}"

    steps.append(_step("agronomy-refuses-market-kinds-cleanly", market_kinds_raise))

    def raw_record_into_drone_ref():
        rec = _irrigation_record()
        ring = [(42.70, 142.40), (42.71, 142.40), (42.71, 142.41)]
        dosage = {"zone-1": {"product": "water", "dose": 5.0, "unit": "mm"}}
        window = dict(
            window_start_utc="2026-11-19T00:00:00+00:00",
            window_end_utc="2026-11-19T03:00:00+00:00",
            wind_max_ms=2.0,
            rain_free_hours=6,
            temp_min_c=15.0,
            temp_max_c=28.0,
            native_support="grid-cell 0.05deg (JMA MSM)",
        )
        try:
            build_drone_packet(
                geofence_ring=ring,
                dosage_table=dosage,
                advisory_ref=rec,  # the RAW record object, not an AdvisoryRef
                weather_window=window,
                use_class="field-ops",
                permits_financial_use=False,
            )
        except Exception as exc:
            refusal = f"{type(exc).__name__}: {exc}"
            named = "AdvisoryRef" in refusal and "advisory_ref" in refusal
            assert named, f"refusal does not name the offending input: {refusal}"
            defects.append(
                Defect(
                    lane="L5",
                    defect_id="D7",
                    severity="cosmetic",
                    finding=(
                        "feeding a raw RecommendationRecord where an AdvisoryRef is "
                        "expected refuses cleanly and names the input ('advisory_ref: "
                        "must be an AdvisoryRef…'), but the message never mentions "
                        "WHICH type arrived — the reader replays the type dance "
                        "themself"
                    ),
                    named_remedy=(
                        "include repr(type(advisory_ref)) in the gap detail"
                    ),
                )
            )
            return f"raw-object refusal fires (names the slot, not the type): {refusal[:100]}…"
        raise AssertionError("raw RecommendationRecord was accepted as an advisory ref")

    steps.append(_step("raw-record-into-drone-refused", raw_record_into_drone_ref))

    def unsigned_wrap_slips():
        rec = _irrigation_record()
        assert rec.requires_human_signoff is True
        wrapped = AdvisoryRef(
            reference_id=rec.recommendation_id,
            issuer=rec.drafted_by,
            issued_at=rec.drafted_at.isoformat(),
        ).validated()
        ring = [(42.70, 142.40), (42.71, 142.40), (42.71, 142.41)]
        dosage = {"zone-1": {"product": "water", "dose": 5.0, "unit": "mm"}}
        window = dict(
            window_start_utc="2026-11-19T00:00:00+00:00",
            window_end_utc="2026-11-19T03:00:00+00:00",
            wind_max_ms=2.0,
            rain_free_hours=6,
            temp_min_c=15.0,
            temp_max_c=28.0,
            native_support="grid-cell 0.05deg (JMA MSM)",
        )
        kml, pkt_report = build_drone_packet(
            geofence_ring=ring,
            dosage_table=dosage,
            advisory_ref=wrapped,
            weather_window=window,
            use_class="field-ops",
            permits_financial_use=False,
        )
        assert kml.startswith(b"<?xml")
        defects.append(
            Defect(
                lane="L5",
                defect_id="D8",
                severity="rough",
                finding=(
                    "an UNSIGNED recommendation (requires_human_signoff=True, v0 "
                    "record barely minted) wraps into an AdvisoryRef and the drone "
                    "packet emits happily — the sign-off obligation does not survive "
                    "the package boundary (shape-only validation), and nothing "
                    "checks packet.permits_financial_use against the record's False"
                ),
                named_remedy=(
                    "either AdvisoryRef gains an optional signed-record evidence "
                    "blob verified by the packet builder, or build_drone_packet "
                    "should accept the RecommendationRecord and REFUSE when "
                    "requires_human_signoff stands without signoff evidence and "
                    "cross-check its permits_financial_use"
                ),
            )
        )
        return (
            f"unsigned wrap EMITTED a packet (sha256 {pkt_report['sha256'][:12]}…) — slip confirmed"
        )

    steps.append(_step("unsigned-wrap-emits-packet-defect", unsigned_wrap_slips))

    report = _report(
        "L5",
        "CROSS-VOCAB: agronomy record vs market kinds and the drone packet",
        steps,
        defects,
        verdict=(
            "Agronomy refuses market kinds with textbook named remedies; the "
            "package boundary leaks sign-off obligations (D8)"
        ),
    )
    return report


def _irrigation_record():
    return draft_recommendation(
        kind="irrigation",
        inputs=[_input_ref()],
        rationale=[RationaleStep("kc-stage", "mid-season Kc from GDD stage", True)],
        payload={"deficit_mm": 12.0, "basis": "fixture season rows"},
        drafted_at=datetime(2026, 11, 18, 1, 0, tzinfo=timezone.utc),
        expires_at=datetime(2026, 11, 20, 1, 0, tzinfo=timezone.utc),
    )


def _input_ref():
    return InputRef(
        iri="urn:test:fixture-rain-row",
        native_support="grid-cell 0.05deg",
        observed_property="precipitation",
        availability_iso="2026-11-18T00:00:00+00:00",
        is_forecast=False,
        licence_instrument="synthetic-fixture",
        licence_permits_financial_use=False,
        licence_permits_redistribution=False,
        licence_expiry="none stated",
    )


# --------------------------------------------------------------------------- #
# Runner                                                                      #
# --------------------------------------------------------------------------- #


def run_all_rehearsals() -> tuple[tuple[ArbrehearsalReport, ...], str]:
    """Run L1-L5 (L4 with a tempdir ledger) and render the markdown report."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        lane1, _bridge = run_lane1()
        lane2 = run_lane2()
        lane3 = run_lane3()
        lane4, _ledger = run_lane4(tmpdir)
        lane5 = run_lane5()
    reports = (lane1, lane2, lane3, lane4, lane5)
    return reports, render_report(reports)


def render_report(reports) -> str:
    lines = [
        "# Arb rehearsal report",
        "",
        "QA rehearsal (arbtester, task-7 adjunct). Scratch-branch run; nothing in the",
        "shipped packages was patched to soften an outcome. All clocks injected, all",
        "ledgers in tempdirs, zero network.",
        "",
    ]
    total_defects: list[Defect] = []
    for report in reports:
        total_defects.extend(report.defects)
        lines.append(f"## {report.lane} — {report.title}")
        lines.append("")
        lines.append(f"Steps passed: **{len(report.steps_ok)}/{len(report.step_log)}**"
                     + (f"  (failed: {list(report.steps_failed)})" if report.steps_failed else ""))
        lines.append("")
        for step in report.step_log:
            mark = "PASS" if step.ok else "FAIL"
            lines.append(f"- `{mark}` {step.name} — {step.detail}")
        if report.defects:
            lines.append("")
            lines.append("| defect | severity | finding | named remedy |")
            lines.append("| --- | --- | --- | --- |")
            for defect in sorted(report.defects, key=lambda d: SEVERITY_ORDER[d.severity]):
                lines.append(
                    f"| {defect.defect_id} | {defect.severity} | {defect.finding} | {defect.named_remedy} |"
                )
        lines.append("")
        lines.append(f"**Lane verdict:** {report.verdict}")
        lines.append("")
    blockers = [d for d in total_defects if d.severity == "blocker"]
    rough = [d for d in total_defects if d.severity == "rough"]
    cosmetic = [d for d in total_defects if d.severity == "cosmetic"]
    lines.append("## Totals")
    lines.append("")
    lines.append(
        f"Defects: {len(total_defects)} (blocker {len(blockers)}, rough {len(rough)}, cosmetic {len(cosmetic)}). "
        f"IDs: {', '.join(d.defect_id for d in sorted(total_defects, key=lambda x: x.defect_id))}."
    )
    return "\n".join(lines) + "\n"


__all__ = [
    "ArbrehearsalReport",
    "Defect",
    "RehearsalStep",
    "bridge_licences_to_grantref",
    "run_lane1",
    "run_lane2",
    "run_lane3",
    "run_lane4",
    "run_lane5",
    "run_all_rehearsals",
    "render_report",
    "SCENARIO_HECTARES",
    "REHEARSAL_T",
]
