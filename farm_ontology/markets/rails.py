"""Executable rails from the alpha-and-fairness doctrine.

Implements sections 3, 4, and 5 of ``docs/alpha-fairness-doctrine.md``
(the Lead-owned doctrine) as validators that FAIL CLOSED:

- section 3, the scenario table: which instrument families are
  permitted in which signal state, and which rails a playbook artefact
  must carry in each state;
- section 4, the five fairness rails: the verbatim concurrent-position
  disclosure clause, upside sharing, the hedge-ticket test, consent-first
  upward data flow, and truthfulness gates that cite licence, support,
  and error of every contributing observation and fail closed when any
  contributing feed lost its grant;
- section 5, the lawful-conduct boundaries: mandatory attestations
  covering own-account positioning, the advice gate, manipulation
  prohibitions, the public-synthesis limit, and embargo clocks.

Fail closed on grant expiry, by design: every rail that depends on a
feed grant treats a missing, unparseable, or expired grant as CLOSED,
and a validator invoked after expiry returns violations — it never
silently passes because a cached answer used to be true.

Grant objects here are a minimal local shape (``GrantRef``) aligned with
the WS6 ``LicenceGrant`` v2 fields named on shared-board task-6 (issuer,
seat/scope, territories, purpose, expiry, evidence URL). The grants
SPEC and the punch-list belong to the licences workstream; this module
consumes them as data, adapts, and does not redefine ownership. When
``farm_ontology/licences`` lands, feed its grant objects through
:func:`grant_ref_from_v2_like` rather than widening this type.

Everything here validates. Nothing executes, trades, prices, or
advises. No autonomous order exists on any path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Mapping, Sequence

from farm_ontology.timeutil import ensure_utc, parse_time

# ---------------------------------------------------------------------- #
# Doctrine section 4.1 — the mandated clause, VERBATIM.                   #
# Do not alter punctuation, capitalisation, em dashes, or capitalised     #
# pronouns; the audit test pins this string against the doctrine text.    #
# ---------------------------------------------------------------------- #

DISCLOSURE_CLAUSE = (
    "The Company maintains proprietary positions in agricultural "
    "commodities. When its data indicates materially adverse or "
    "favourable conditions for Your fields, the Company shall disclose "
    "the existence — never the size — of related positions in its "
    "periodic decision-support report, before the affected transaction "
    "dates."
)

# ---------------------------- scenarios (§3) --------------------------- #

STATE_CONFIDENT_LOSS = "confident-loss"
STATE_CONFIDENT_GAIN = "confident-gain"
STATE_UNCERTAIN = "uncertain"
STATE_HAZARD_IMMINENT = "hazard-imminent"

SCENARIO_STATES = (
    STATE_CONFIDENT_LOSS,
    STATE_CONFIDENT_GAIN,
    STATE_UNCERTAIN,
    STATE_HAZARD_IMMINENT,
)

F_SHORT_CBOT_SOYBEAN_FUTURES = "short-cbot-soybean-futures"
F_BOUGHT_PUTS = "bought-puts"
F_FORWARD_PHYSICAL_COMMITMENT = "forward-physical-commitment"
F_INPUT_SUPPLIER_INVESTMENT = "input-supplier-investment"
F_COST_CAPPED_STRADDLE = "cost-capped-straddle"
F_PUT_SPREAD_COLLAR = "put-spread-collar"
F_REDUCE_OPEN_RISK = "reduce-open-risk"

PERMITTED_FAMILIES = (
    F_SHORT_CBOT_SOYBEAN_FUTURES,
    F_BOUGHT_PUTS,
    F_FORWARD_PHYSICAL_COMMITMENT,
    F_INPUT_SUPPLIER_INVESTMENT,
    F_COST_CAPPED_STRADDLE,
    F_PUT_SPREAD_COLLAR,
    F_REDUCE_OPEN_RISK,
)

RAIL_1_DISCLOSURE = "R1"
RAIL_2_UPSIDE_SHARE = "R2"
RAIL_3_TICKET = "R3"
RAIL_4_CONSENT_FLOW = "R4"
RAIL_5_TRUTHFULNESS = "R5"

RAIL_IDS = (RAIL_1_DISCLOSURE, RAIL_2_UPSIDE_SHARE, RAIL_3_TICKET, RAIL_4_CONSENT_FLOW, RAIL_5_TRUTHFULNESS)

@dataclass(frozen=True)
class Scenario:
    """One row of the doctrine's section-3 table, encoded."""

    state: str
    own_book_families: tuple[str, ...]
    farmer_relationship: str
    rails_required: tuple[str, ...]
    premium_budget_required: bool
    conduct_attestations_required: bool


SCENARIOS: dict[str, Scenario] = {
    STATE_CONFIDENT_LOSS: Scenario(
        state=STATE_CONFIDENT_LOSS,
        own_book_families=(F_SHORT_CBOT_SOYBEAN_FUTURES, F_BOUGHT_PUTS),
        farmer_relationship=(
            "deliver decision-support that limits the loss; disclose the "
            "hedge per the clause; the contract PRE-agrees the disclosure "
            "duty — never silently positioned against the grower"
        ),
        rails_required=(RAIL_1_DISCLOSURE, RAIL_3_TICKET, RAIL_5_TRUTHFULNESS),
        premium_budget_required=False,
        conduct_attestations_required=True,
    ),
    STATE_CONFIDENT_GAIN: Scenario(
        state=STATE_CONFIDENT_GAIN,
        own_book_families=(F_FORWARD_PHYSICAL_COMMITMENT, F_INPUT_SUPPLIER_INVESTMENT),
        farmer_relationship=(
            "offer the farmer the gain: input financing against "
            "contracted tons, revenue share; our leverage funds THEIR "
            "upside — alignment by design"
        ),
        rails_required=(RAIL_2_UPSIDE_SHARE, RAIL_3_TICKET, RAIL_5_TRUTHFULNESS),
        premium_budget_required=False,
        conduct_attestations_required=True,
    ),
    STATE_UNCERTAIN: Scenario(
        state=STATE_UNCERTAIN,
        own_book_families=(F_COST_CAPPED_STRADDLE, F_PUT_SPREAD_COLLAR),
        farmer_relationship=(
            "sell nothing; provide the probability map and both "
            "branches' preparations"
        ),
        rails_required=(RAIL_3_TICKET, RAIL_5_TRUTHFULNESS),
        premium_budget_required=True,
        conduct_attestations_required=True,
    ),
    STATE_HAZARD_IMMINENT: Scenario(
        state=STATE_HAZARD_IMMINENT,
        own_book_families=(F_REDUCE_OPEN_RISK,),
        farmer_relationship=(
            "trigger the emergency SOP; farmer protection outranks book "
            "pips in every tie"
        ),
        rails_required=(RAIL_5_TRUTHFULNESS,),
        premium_budget_required=False,
        conduct_attestations_required=True,
    ),
}


def scenario_for(state: str) -> Scenario:
    try:
        return SCENARIOS[state]
    except KeyError:
        raise ValueError("scenario_for is called on an unknown state") from None


# ----------------------------- grants ---------------------------------- #


@dataclass(frozen=True)
class GrantRef:
    """Minimal grant data consumed from the licences workstream (WS6).

    Field names follow the task-6 ``LicenceGrant`` v2 roster: issuer,
    seat, scope, territory, purpose, expiry, evidence. ``permits_…``
    booleans default to False and only a recorded written grant sets
    them true. Expiry is an ISO-8601 string with an offset; an
    unparseable expiry fails closed (:func:`grant_state_at`).
    """

    name: str
    issuer: str
    seat: str
    scope: str
    territory: str
    purpose: str
    expiry: str
    evidence_url: str
    permits_financial_use: bool = False
    permits_market_data_use: bool = False

    def __post_init__(self) -> None:
        if not self.name or not self.issuer or not self.evidence_url:
            raise ValueError("a grant names itself, its issuer, and its evidence")

    @property
    def state(self) -> str:
        state, _detail = grant_state_at(self, None)
        return state


GRANT_VALID = "valid"
GRANT_EXPIRED = "expired"
GRANT_UNPARSEABLE = "unparseable-expiry"
GRANT_CLOSED = "closed"


def grant_state_at(
    grant: GrantRef | None, as_of: datetime | None
) -> tuple[str, str]:
    """Judge one grant at ``as_of``. Anything unsure is CLOSED.

    ``as_of=None`` judges against the current clock. States:
    ``GRANT_VALID`` only when every condition provably holds; expiry
    parity means already expired (a grant is not valid at the instant
    it dies); a missing grant object is ``GRANT_CLOSED`` outright.
    """
    if grant is None:
        return GRANT_CLOSED, "no grant object is recorded"
    if not grant.permits_financial_use or not grant.permits_market_data_use:
        return GRANT_CLOSED, "the recorded grant does not permit this use"
    try:
        expiry = parse_time(grant.expiry)
    except (TypeError, ValueError):
        return GRANT_UNPARSEABLE, "the grant expiry is not an ISO-8601 instant with an offset"
    if as_of is None:
        as_of = datetime.now(timezone.utc)
    moment = ensure_utc(as_of, "as_of")
    if expiry <= moment:
        return GRANT_EXPIRED, f"the grant expired at {expiry.isoformat()}"
    return GRANT_VALID, "permit provably alive"


def grant_ref_from_v2_like(**fields) -> GrantRef:
    """Adapter shim for WS6 grant objects once they land.

    Accepted keys are the intersection used here; unknown extra fields
    are ignored, missing essentials raise via ``GrantRef``. This keeps
    task-7 forward-compatible with the licences module without owning
    its spec.
    """
    known = {
        key: fields[key]
        for key in (
            "name",
            "issuer",
            "seat",
            "scope",
            "territory",
            "purpose",
            "expiry",
            "evidence_url",
            "permits_financial_use",
            "permits_market_data_use",
        )
        if key in fields
    }
    return GrantRef(**known)


# ----------------------- doctrine section 4 rails ---------------------- #


@dataclass(frozen=True)
class RailViolation:
    """One failed rail check. Returned, never swallowed."""

    rail: str
    detail: str


@dataclass(frozen=True)
class UpsideShareTerm:
    """Rail 2: the negotiated upside-sharing term on a gain artefact."""

    agreed_share_fraction: float
    beneficiary: str
    negotiated_by: str
    contract_reference: str

    def __post_init__(self) -> None:
        if not (0.0 < float(self.agreed_share_fraction) < 1.0):
            raise ValueError(
                "the negotiated share is a fraction in (0, 1); the "
                "doctrine rejects pure asymmetry and 100-percent giving"
            )
        if not self.beneficiary or not self.negotiated_by or not self.contract_reference:
            raise ValueError(
                "an upside term names the beneficiary, the negotiator, "
                "and the contract"
            )


@dataclass(frozen=True)
class HedgeTicket:
    """Rail 3: the hedge ticket that must be filed before conduct.

    ``farmer_would_still_sign`` is the doctrine's own question: would
    the farmer still sign if they saw this hedge ticket? It is answered
    by a human, in the ticket, and a ticket filed nowhere is a lie.
    """

    ticket_id: str
    family: str
    would_farmer_still_sign: bool
    filed_in_trade_ledger: bool
    drafted_by: str

    def __post_init__(self) -> None:
        if not self.ticket_id or not self.family:
            raise ValueError("a hedge ticket has an id and a family")
        if not self.drafted_by:
            raise ValueError("a hedge ticket names its human drafter")


@dataclass(frozen=True)
class PremiumBudget:
    """The uncertainty-state premium budget, human-set quarterly.

    The doctrine sets the CAP quarterly by a human; the engine only
    checks the term is recorded and respected.
    """

    premium_percent_of_notional: float
    cap_percent_of_notional: float
    quarter: str
    cap_set_by: str

    def __post_init__(self) -> None:
        if not self.quarter:
            raise ValueError("a premium budget names its quarter")
        if "agent" in self.cap_set_by.strip().lower() or not self.cap_set_by.strip():
            raise ValueError(
                "the premium cap is set quarterly by a human, not by an agent"
            )
        if self.cap_percent_of_notional <= 0:
            raise ValueError("the premium cap is a positive percent")
        if self.premium_percent_of_notional >= self.cap_percent_of_notional:
            raise ValueError(
                "the planned premium must sit strictly under the human-set cap"
            )


@dataclass(frozen=True)
class ConsentGrant:
    """Rail 4: the farmer's written consent for upward data flow.

    Mirrors the grants/ v2 idea for FARMER-side data: purpose, scope,
    expiry, and the written evidence. Owned by the licences workstream's
    consent spec; consumed here as data.
    """

    farmer_ref: str
    purpose: str
    scope: str
    expiry: str
    written_grant_url: str

    def __post_init__(self) -> None:
        if not self.farmer_ref or not self.written_grant_url:
            raise ValueError("a consent grant names the farmer and the written grant")
        parse_time(self.expiry)  # unparseable consent fails fast here too


@dataclass(frozen=True)
class Contribution:
    """Rail 5: the licence/support/error triple for one cited feed."""

    feed: str
    licence_attribution: str
    support_statement: str
    error_statement: str


@dataclass(frozen=True)
class PlaybookArtefact:
    """Any artefact a playbook state produces, before it ships.

    Carries everything its state's rails judge: the rendered text, the
    own-book families invoked, the upside term and tickets, the premium
    budget, the contributing feeds and their grants, whether farmer-level
    data reached the artefact and under which consent, and the conduct
    attestations.
    """

    artefact_id: str
    state: str
    text: str
    families: tuple[str, ...] = ()
    upside_term: UpsideShareTerm | None = None
    hedge_tickets: tuple[HedgeTicket, ...] = ()
    premium_budget: PremiumBudget | None = None
    market_decisive_feeds: tuple[str, ...] = ()
    contributions: tuple[Contribution, ...] = ()
    grants_by_feed: Mapping[str, GrantRef | None] = field(default_factory=dict)
    carries_farmer_level_data: bool = False
    consent: ConsentGrant | None = None
    conduct_attestations: Mapping[str, bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.artefact_id:
            raise ValueError("a playbook artefact carries its id")
        if self.state not in SCENARIO_STATES:
            raise ValueError("a playbook artefact names a doctrine state")
        for family in self.families:
            if family not in PERMITTED_FAMILIES:
                raise ValueError("a playbook artefact uses a declared family")


# ---- rail validators (each returns violations; empty list = pass) ----- #


def rail_1_concurrent_position_disclosure(text: str) -> list[RailViolation]:
    """Rail 1: the verbatim clause must appear in the artefact."""
    if DISCLOSURE_CLAUSE in (text or ""):
        return []
    return [
        RailViolation(
            RAIL_1_DISCLOSURE,
            "the concurrent-position disclosure clause is missing or "
            "altered; the doctrine mandates it verbatim",
        )
    ]


def rail_2_upside_share(
    state: str, term: UpsideShareTerm | None
) -> list[RailViolation]:
    """Rail 2: gain-state artefacts share realised upside with the farmer."""
    if state != STATE_CONFIDENT_GAIN:
        return []
    if term is None:
        return [
            RailViolation(
                RAIL_2_UPSIDE_SHARE,
                "a confident-gain artefact must carry the negotiated "
                "upside-share term; the doctrine rejects pure asymmetry",
            )
        ]
    if not 0.0 < term.agreed_share_fraction < 1.0:
        return [
            RailViolation(
                RAIL_2_UPSIDE_SHARE,
                "the agreed share is not a real fraction in (0, 1)",
            )
        ]
    return []


def rail_3_hedge_ticket_filed(
    artefact: PlaybookArtefact,
) -> list[RailViolation]:
    """Rail 3: every own-book action files a ticket with the human answer."""
    violations: list[RailViolation] = []
    if artefact.families and not artefact.hedge_tickets:
        return [
            RailViolation(
                RAIL_3_TICKET,
                "own-book families are invoked but no hedge ticket is "
                "filed; audit beats convenience",
            )
        ]
    seen_families: set[str] = set()
    for ticket in artefact.hedge_tickets:
        if ticket.family not in PERMITTED_FAMILIES:
            violations.append(
                RailViolation(RAIL_3_TICKET, f"ticket {ticket.ticket_id} names an undeclared family")
            )
        if not ticket.would_farmer_still_sign:
            violations.append(
                RailViolation(
                    RAIL_3_TICKET,
                    f"ticket {ticket.ticket_id} fails the doctrine question: "
                    "would the farmer still sign if they saw this hedge ticket?",
                )
            )
        if not ticket.filed_in_trade_ledger:
            violations.append(
                RailViolation(
                    RAIL_3_TICKET,
                    f"ticket {ticket.ticket_id} is not filed in the trade ledger",
                )
            )
        seen_families.add(ticket.family)
    uncovered = set(artefact.families) - seen_families
    for family in sorted(uncovered):
        violations.append(
            RailViolation(
                RAIL_3_TICKET,
                f"family {family} is invoked with no hedge ticket filed",
            )
        )
    return violations


def rail_4_consent_first_upward_flow(
    artefact: PlaybookArtefact, as_of: datetime
) -> list[RailViolation]:
    """Rail 4: farmer-level data reaches market artefacts only on consent.

    Fail closed: consent missing, unparseable, or expired leaves the
    aggregated/anonymised path as the only lawful route.
    """
    if not artefact.carries_farmer_level_data:
        return []
    consent = artefact.consent
    if consent is None:
        return [
            RailViolation(
                RAIL_4_CONSENT_FLOW,
                "farmer-level data on a market-facing artefact with no "
                "written consent grant; the aggregation must stay "
                "anonymised",
            )
        ]
    try:
        expiry = parse_time(consent.expiry)
    except (TypeError, ValueError):
        return [
            RailViolation(
                RAIL_4_CONSENT_FLOW,
                "the consent expiry is unparseable; consent is presumed void",
            )
        ]
    moment = ensure_utc(as_of, "as_of")
    if expiry <= moment:
        return [
            RailViolation(
                RAIL_4_CONSENT_FLOW,
                f"the consent expired at {expiry.isoformat()}; farmer-level "
                "data may not ride this artefact",
            )
        ]
    if not consent.purpose.strip() or not consent.scope.strip():
        return [
            RailViolation(
                RAIL_4_CONSENT_FLOW,
                "the consent grant carries no purpose or no scope",
            )
        ]
    return []


def rail_5_truthfulness_gate(
    artefact: PlaybookArtefact, as_of: datetime
) -> list[RailViolation]:
    """Rail 5: signals cite licence, support, error — and grants hold.

    Every market-decisive feed the artefact leans on must have a
    contribution citing licence, support, and error, AND a grant that is
    provably valid at ``as_of``. No contribution, expired grant,
    unparseable expiry, or unrecorded grant each fail closed. This is
    the lead's explicit invariant: expiry flips the verdict, it does not
    freeze the last good answer.
    """
    violations: list[RailViolation] = []
    cited = set(artefact.market_decisive_feeds)
    contributed: dict[str, Contribution] = {}
    for contribution in artefact.contributions:
        contributed[contribution.feed] = contribution
    for feed in sorted(cited):
        contribution = contributed.get(feed)
        if contribution is None:
            violations.append(
                RailViolation(
                    RAIL_5_TRUTHFULNESS,
                    f"feed {feed} is market-decisive but cites no "
                    "licence/support/error triple",
                )
            )
            continue
        missing = [
            label
            for label, text in (
                ("licence attribution", contribution.licence_attribution),
                ("support statement", contribution.support_statement),
                ("error statement", contribution.error_statement),
            )
            if not (text or "").strip()
        ]
        if missing:
            violations.append(
                RailViolation(
                    RAIL_5_TRUTHFULNESS,
                    f"feed {feed} lacks {', '.join(missing)}",
                )
            )
        state, detail = grant_state_at(artefact.grants_by_feed.get(feed), as_of)
        if state != GRANT_VALID:
            violations.append(
                RailViolation(
                    RAIL_5_TRUTHFULNESS,
                    f"feed {feed} fails closed on grant state '{state}': {detail}",
                )
            )
    return violations


# ------------- doctrine section 5: lawful-conduct checks --------------- #

CONDUCT_OWN_ACCOUNT = "conduct/own-account-prop-trading"
CONDUCT_ADVICE_GATE = "conduct/advice-gate-off"
CONDUCT_NO_MANIPULATION = "conduct/no-manipulation"
CONDUCT_PUBLIC_SYNTHESIS = "conduct/public-synthesis-only"
CONDUCT_EMBARGO_CLOCKS = "conduct/embargo-clocks-honoured"

CONDUCT_ATTESTATION_IDS = (
    CONDUCT_OWN_ACCOUNT,
    CONDUCT_ADVICE_GATE,
    CONDUCT_NO_MANIPULATION,
    CONDUCT_PUBLIC_SYNTHESIS,
    CONDUCT_EMBARGO_CLOCKS,
)

CONDUCT_ATTESTATION_MEANINGS = {
    CONDUCT_OWN_ACCOUNT: (
        "proprietary trading on own account with own risk capital is "
        "outside FIEA investment-advice licensing; the moment we advise "
        "(personalised, for reward), we license or stop"
    ),
    CONDUCT_ADVICE_GATE: (
        "no artefact routes personalised trade calls to investors; the "
        "product ships decision-support to operators"
    ),
    CONDUCT_NO_MANIPULATION: (
        "no spoofing, wash trading, squeezes, or trading to create an "
        "artificial price; reducing ahead of a disaster is lawful "
        "information reaction, and so attested"
    ),
    CONDUCT_PUBLIC_SYNTHESIS: (
        "signals synthesise public data recorded in the repo; nothing "
        "rides a privileged government pre-release window"
    ),
    CONDUCT_EMBARGO_CLOCKS: (
        "embargo clocks are recorded facts and honoured mechanically; "
        "no dissemination before the clock releases"
    ),
}


def conduct_checks(
    attestations: Mapping[str, bool],
) -> list[RailViolation]:
    """Section 5 attestations. A missing or False attestation fails."""
    violations: list[RailViolation] = []
    for attestation_id in CONDUCT_ATTESTATION_IDS:
        value = attestations.get(attestation_id)
        if value is not True:
            meaning = CONDUCT_ATTESTATION_MEANINGS[attestation_id]
            violations.append(
                RailViolation(
                    "R5-conduct",
                    f"attestation {attestation_id} is not affirmatively "
                    f"true ({meaning})",
                )
            )
    for extra in sorted(set(attestations) - set(CONDUCT_ATTESTATION_IDS)):
        violations.append(
            RailViolation("R5-conduct", f"unknown attestation {extra}")
        )
    return violations


def premium_budget_check(artefact: PlaybookArtefact) -> list[RailViolation]:
    """Uncertainty-state artefacts carry a written premium budget."""
    scenario = SCENARIOS[artefact.state]
    if not scenario.premium_budget_required:
        return []
    if artefact.premium_budget is None:
        return [
            RailViolation(
                RAIL_3_TICKET,
                "an uncertainty artefact must carry the written premium "
                "budget with the human-set quarterly cap",
            )
        ]
    return []


# --------------------- the artefact validator -------------------------- #


def validate_playbook_artefact(
    artefact: PlaybookArtefact, as_of: datetime
) -> tuple[RailViolation, ...]:
    """Judge one artefact under its scenario's required rails.

    Order is deterministic. The conduct attestations are demanded
    whenever the scenario involves own-book posture (all four states
    do). Fail closed is the contract with the caller: violations come
    back; nothing raises that would mask a judgement.
    """
    scenario = SCENARIOS[artefact.state]
    unknown = [family for family in artefact.families if family not in scenario.own_book_families]
    violations: list[RailViolation] = []
    for family in unknown:
        violations.append(
            RailViolation(
                "S3-family",
                f"family {family} is not a permitted own-book family in "
                f"state {artefact.state}",
            )
        )
    required = set(scenario.rails_required)
    if RAIL_1_DISCLOSURE in required:
        violations.extend(rail_1_concurrent_position_disclosure(artefact.text))
    if RAIL_2_UPSIDE_SHARE in required:
        violations.extend(rail_2_upside_share(artefact.state, artefact.upside_term))
    if RAIL_3_TICKET in required:
        violations.extend(rail_3_hedge_ticket_filed(artefact))
        violations.extend(premium_budget_check(artefact))
    if RAIL_4_CONSENT_FLOW in required or artefact.carries_farmer_level_data:
        violations.extend(rail_4_consent_first_upward_flow(artefact, as_of))
    if RAIL_5_TRUTHFULNESS in required:
        violations.extend(rail_5_truthfulness_gate(artefact, as_of))
    if scenario.conduct_attestations_required:
        violations.extend(conduct_checks(artefact.conduct_attestations))
    return tuple(sorted(violations, key=lambda item: (item.rail, item.detail)))


__all__ = [
    "DISCLOSURE_CLAUSE",
    "SCENARIO_STATES",
    "SCENARIOS",
    "PERMITTED_FAMILIES",
    "RAIL_IDS",
    "GRANT_VALID",
    "GRANT_EXPIRED",
    "GRANT_UNPARSEABLE",
    "GRANT_CLOSED",
    "CONDUCT_ATTESTATION_IDS",
    "CONDUCT_ATTESTATION_MEANINGS",
    "Scenario",
    "GrantRef",
    "RailViolation",
    "UpsideShareTerm",
    "HedgeTicket",
    "PremiumBudget",
    "ConsentGrant",
    "Contribution",
    "PlaybookArtefact",
    "grant_state_at",
    "grant_ref_from_v2_like",
    "rail_1_concurrent_position_disclosure",
    "rail_2_upside_share",
    "rail_3_hedge_ticket_filed",
    "rail_4_consent_first_upward_flow",
    "rail_5_truthfulness_gate",
    "conduct_checks",
    "premium_budget_check",
    "validate_playbook_artefact",
]
