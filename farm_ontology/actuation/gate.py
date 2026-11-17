"""The Phase-4 gate, as code (WS5.4) — the clerk that says NO.

``decision-infra-roadmap.md`` WS5.4: "Closed-loop gate definition —
min-instances=1 + authN + watchdog + kill-switch contract — written down as
the Phase-4 entry exam." This module IS that exam. It evaluates deployment
FACTS handed to it (never inspects a live deployment itself — no network, no
process probes, stdlib only) and answers one question: may production
commands flow to real machines?

Doctrine §6 rows this module implements:
- Farm-side actions flow recommendation → human approve → TaskSet/drone
  packet; the command ledger (``farm_ontology.actuation.command_ledger``)
  records every step;
- the kill switch is an emergency HALT record written by the human risk
  owner, PROPAGATED BY THE RUNTIME WATCHDOG — hence ``watchdog_defined`` and
  ``kill_switch_contract_signed`` are gate inputs, not decorations.

House rules: every input that is ``None`` (unassessed) or ``False`` makes
the gate ineligible and NAMES the gap verbosely — what the fact means and
what would satisfy it. Non-boolean facts are refused (no truthy coercion:
``"yes"`` is not a deployment fact). Passing only achievable facts can never
flip the gate; only all-six-true does. There is no override knob on purpose.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

from farm_ontology.actuation.command_ledger import ActuationGap

__all__ = [
    "GATE_FACT_MEANINGS",
    "GATE_FACT_NAMES",
    "GateCheck",
    "SATISFYING_EVIDENCE",
]


#: What each gate fact MEANS (the Phase-4 entry exam, in words).
GATE_FACT_MEANINGS = {
    "min_instances": (
        "the command-intake deployment holds at least one warm instance "
        "(Cloud Run min-instances=1 or equivalent) so a dispatched command is "
        "never lost to a cold start"
    ),
    "auth_configured": (
        "every mutating actuation endpoint demands an authenticated, "
        "authorised principal; unauthenticated invokers may read, never command"
    ),
    "watchdog_defined": (
        "a runtime watchdog owns HALT propagation: an emergency HALT record "
        "reaches intake/freezes command dispatch within one poll interval, "
        "and watchdog liveness is itself alerted on"
    ),
    "kill_switch_contract_signed": (
        "the human risk owner has SIGNED the kill-switch contract — who may "
        "halt, maximum acknowledge latency, and the drill procedure "
        "(doctrine §6)"
    ),
    "field_drill_completed": (
        "a successful closed-loop field drill ran on the real equipment: a "
        "command traveled proposed -> approved -> dispatched -> acknowledged "
        "with an exported TaskSet/drone packet under supervision"
    ),
    "audit_quarter_clean": (
        "the most recent full quarter of command-ledger operation closed with "
        "zero unresolved verify_chain() or audit findings"
    ),
}

#: Ordered gate fact names (stable; public vocabulary).
GATE_FACT_NAMES = tuple(GATE_FACT_MEANINGS)

#: What evidence satisfies each fact (the "how to pass" half of verbosity).
SATISFYING_EVIDENCE = {
    "min_instances": (
        "deployment config diff showing min-instances=1 (or the equivalent "
        "warm-floor) on the command-intake service, attached to the gate review"
    ),
    "auth_configured": (
        "endpoint test evidence: unauthenticated mutating request -> 401/403, "
        " authorised command -> ledger event; plus the auth-config reference"
    ),
    "watchdog_defined": (
        "watchdog spec naming the HALT poll interval, the freeze behaviour, "
        "and the liveness alert channel (reserved per doctrine §7 for "
        "'HALT raised' events)"
    ),
    "kill_switch_contract_signed": (
        "the signed kill-switch contract document with risk-owner signature "
        "and date"
    ),
    "field_drill_completed": (
        "the drill's command_ledger export showing the proposed->approved->"
        "dispatched->acknowledged loop with verify_chain() ok"
    ),
    "audit_quarter_clean": (
        "the quarterly audit memo: verify_chain() runs green over the whole "
        "quarter, no unresolved findings"
    ),
}


@dataclass(frozen=True)
class GateCheck:
    """Six deployment facts, honestly ``None`` until each is evidenced.

    Construct with keyword booleans; ``None`` (the default) means "not yet
    assessed". The gate never performs the assessment itself — facts arrive
    from deployment evidence, keeping this module offline and pure.
    """

    min_instances: bool | None = None
    auth_configured: bool | None = None
    watchdog_defined: bool | None = None
    kill_switch_contract_signed: bool | None = None
    field_drill_completed: bool | None = None
    audit_quarter_clean: bool | None = None

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if value is not None and not isinstance(value, bool):
                raise ActuationGap(
                    "gate_fact_not_boolean",
                    f"gate fact {field.name!r} must be True, False or None "
                    f"(unassessed); got {value!r} — the gate never coerces "
                    "'yes'/1/truthy strings into facts",
                    "pass real booleans from deployment evidence",
                )

    @classmethod
    def from_facts(cls, facts) -> "GateCheck":
        """Build from a ``{name: bool|None}`` mapping; unknown keys refused."""
        if not isinstance(facts, dict):
            raise ActuationGap(
                "gate_facts_ill_formed",
                "from_facts expects a {fact_name: bool|None} mapping",
            )
        unknown = sorted(set(facts) - set(GATE_FACT_NAMES))
        if unknown:
            raise ActuationGap(
                "gate_fact_unknown",
                f"unknown gate fact(s): {unknown}; known facts are "
                f"{list(GATE_FACT_NAMES)}",
            )
        kwargs = {}
        for name in GATE_FACT_NAMES:
            if name in facts:
                value = facts[name]
                if value is not None and not isinstance(value, bool):
                    raise ActuationGap(
                        "gate_fact_not_boolean",
                        f"gate fact {name!r} must be True, False or None; got "
                        f"{value!r}",
                    )
                kwargs[name] = value
        return cls(**kwargs)

    # -- the clerk ------------------------------------------------------------

    def gaps(self) -> tuple[dict, ...]:
        """Verbose, NAMED reasons the gate is shut, ordered by fact name.

        Each gap carries ``fact`` (name), ``kind`` (``missing`` for an
        unassessed ``None``, ``failed`` for an evidenced ``False``), the
        fact's meaning, and the evidence that would satisfy it.
        """
        out: list[dict] = []
        for name in GATE_FACT_NAMES:
            value = getattr(self, name)
            if value is True:
                continue
            out.append(
                {
                    "fact": name,
                    "kind": "missing" if value is None else "failed",
                    "meaning": GATE_FACT_MEANINGS[name],
                    "satisfied_by": SATISFYING_EVIDENCE[name],
                }
            )
        return tuple(out)

    def eligible_for_live_commands(self) -> bool:
        """TRUE only when all six facts are evidenced True. Default: NO."""
        return all(getattr(self, name) is True for name in GATE_FACT_NAMES)

    def assessment(self) -> dict:
        """The full clerk's report: verdict, verbose gaps, and fact states."""
        return {
            "eligible_for_live_commands": self.eligible_for_live_commands(),
            "gaps": [dict(gap) for gap in self.gaps()],
            "facts": {name: getattr(self, name) for name in GATE_FACT_NAMES},
            "note": (
                "no live machine command may flow while any gap stands "
                "(roadmap WS5.4, doctrine §6)"
            ),
        }

    def refusal_summary(self) -> str:
        """One-line verbose refusal for logs; '' when eligible."""
        if self.eligible_for_live_commands():
            return ""
        named = ", ".join(gap["fact"] for gap in self.gaps())
        return (
            "ineligible for live commands: "
            + named
            + " — see docs/actuation-interface-spec.md §8"
        )
