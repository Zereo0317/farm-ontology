"""Recommendation as a first-class record (WS3.5).

Every advisory output becomes a ``RecommendationRecord``: a replayable,
deterministic-id record of WHAT was proposed, from WHICH inputs, under
WHICH licence states, with WHICH uncertainty, expiring WHEN, and — always
in v0 — requiring a human sign-off.

Issuance chain (v0)::

    drafted_by='agronomy-engine' → requires_human_signoff=True → (human)

Failed-closed properties, enforced by the constructor:

* ``permits_financial_use`` is FALSE, structurally. Passing True raises —
  the v0 engine cannot bless a financial use even by accident. Flipping
  the class happens in WS6 through a written grant, never here.
* A recommendation may not even PROPOSE a refused use: kinds 'hedge',
  'trade', 'settlement', 'trigger', 'nature-unit' raise
  :class:`AgronomyRefusal` at construction (refused uses stay refused —
  a recommendation object for them never exists to be waved around).
* ``expires_at`` must be timezone-aware and strictly after ``drafted_at``
  (a record cannot be born expired; a naive stamp cannot be replayed).
* The id is a content hash of kind + sorted input IRIs + rationale rule
  ids + payload. ``drafted_at``/``expires_at`` are deliberately OUTSIDE
  the id: re-deriving the same recommendation from the same inputs on a
  different day yields the same id (replay), while the audit trail keeps
  both stamps.

Licence states ride on every input (:class:`InputRef`, built from an
``Observation`` by :func:`input_ref_from_observation`): native support,
financial/redistribution permissions, licence instrument and expiry.
The record is honest about mixed inputs: a recommendation whose inputs
carry differing licence classes says so field by field.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Sequence

from farm_ontology.agronomy.common import (
    CONFIG_VERSION,
    DRAFTED_BY,
    PERMITS_FINANCIAL_USE_V0,
    USE_CLASS_FIELD_OPS,
    AgronomyGap,
    AgronomyRefusal,
    deterministic_id,
)
from farm_ontology.model import Observation
from farm_ontology.timeutil import ensure_utc

#: Kinds a v0 recommendation may carry.
KINDS = frozenset({"irrigation", "spray", "fertility", "phenology-query"})

#: Kinds the engine refuses to even propose (class-C-shaped and market
#: uses). Attempting one raises; the refusal is not recorded as advice.
REFUSED_KINDS = frozenset(
    {"hedge", "trade", "sell", "buy", "short", "long", "settlement", "trigger", "nature-unit"}
)

#: Namespace for deterministic ids.
_ID_NAMESPACE = "rec"


@dataclass(frozen=True)
class InputRef:
    """One input's identity and its licence state, travelling together."""

    iri: str
    native_support: str
    observed_property: str | None
    availability_iso: str | None
    is_forecast: bool
    licence_instrument: str
    licence_permits_financial_use: bool
    licence_permits_redistribution: bool
    licence_expiry: str

    def to_payload(self) -> dict:
        return {
            "iri": self.iri,
            "native_support": self.native_support,
            "observed_property": self.observed_property,
            "availability": self.availability_iso,
            "is_forecast": self.is_forecast,
            "licence": {
                "instrument": self.licence_instrument,
                "permits_financial_use": self.licence_permits_financial_use,
                "permits_redistribution": self.licence_permits_redistribution,
                "expiry": self.licence_expiry,
            },
        }


@dataclass(frozen=True)
class RationaleStep:
    """One line of the rule trace that produced the proposal."""

    rule_id: str
    detail: str
    triggered: bool
    evidence: tuple[tuple[str, object], ...] = ()

    def to_payload(self) -> dict:
        payload = {
            "rule_id": self.rule_id,
            "detail": self.detail,
            "triggered": self.triggered,
        }
        if self.evidence:
            payload["evidence"] = {key: value for key, value in self.evidence}
        return payload


def input_ref_from_observation(obs: Observation) -> InputRef:
    """Project an Observation into an InputRef with its licence state."""
    return InputRef(
        iri=obs.iri,
        native_support=obs.spatial_support,
        observed_property=obs.observed_property,
        availability_iso=(
            obs.availability_time.isoformat() if obs.availability_time else None
        ),
        is_forecast=bool(obs.is_forecast),
        licence_instrument=obs.licence.instrument,
        licence_permits_financial_use=bool(obs.licence.permits_financial_use),
        licence_permits_redistribution=bool(obs.licence.permits_redistribution),
        licence_expiry=obs.licence.expiry,
    )


def recommendation_id_for(
    *,
    kind: str,
    inputs: Sequence[InputRef],
    rationale: Sequence[RationaleStep],
    payload: Mapping,
) -> str:
    """Deterministic id from kind + inputs + rule trace + payload.

    Times are excluded on purpose: same inputs on another day ⇒ same id.
    """
    identity = {
        "kind_of_record": "farm.agronomy.recommendation",
        "config_version": CONFIG_VERSION,
        "recommendation_kind": kind,
        "inputs": [ref.to_payload() for ref in inputs],
        "rationale": [step.to_payload() for step in rationale],
        "payload": dict(payload),
    }
    return deterministic_id(_ID_NAMESPACE, identity)


@dataclass(frozen=True)
class RecommendationRecord:
    """The WS3.5 record. Construct it through :func:`draft_recommendation`."""

    recommendation_id: str
    kind: str
    inputs: tuple[InputRef, ...]
    rationale: tuple[RationaleStep, ...]
    uncertainty: dict | None
    use_class: str
    permits_financial_use: bool
    drafted_by: str
    requires_human_signoff: bool
    drafted_at: datetime
    expires_at: datetime
    payload: Mapping
    config_version: str = CONFIG_VERSION

    def to_payload(self) -> dict:
        return {
            "recommendation_id": self.recommendation_id,
            "kind": self.kind,
            "inputs": [ref.to_payload() for ref in self.inputs],
            "rationale": [step.to_payload() for step in self.rationale],
            "uncertainty": self.uncertainty,
            "use_class": self.use_class,
            "permits_financial_use": self.permits_financial_use,
            "drafted_by": self.drafted_by,
            "requires_human_signoff": self.requires_human_signoff,
            "drafted_at": self.drafted_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "payload": dict(self.payload),
            "config_version": self.config_version,
        }


def draft_recommendation(
    *,
    kind: str,
    inputs: Sequence[InputRef],
    rationale: Sequence[RationaleStep],
    payload: Mapping,
    drafted_at: datetime,
    expires_at: datetime,
    uncertainty: dict | None = None,
) -> RecommendationRecord:
    """Validate, mint the deterministic id, and freeze the record.

    All house guarantees are enforced HERE, so no caller can assemble a
    record that quietly promises more than the engine may say.
    """
    drafted_at = ensure_utc(drafted_at, "drafted_at")
    expires_at = ensure_utc(expires_at, "expires_at")

    if kind in REFUSED_KINDS:
        raise AgronomyRefusal(
            "refused-use",
            f"a v0 agronomy recommendation may not even propose a "
            f"'{kind}' use; refused uses stay refused",
            remediation="route market-side intent to WS7 with its own gates",
        )
    if kind not in KINDS:
        raise AgronomyGap(
            "unknown-kind",
            f"unknown recommendation kind {kind!r}",
            missing=("kind in " + "|".join(sorted(KINDS)),),
        )
    if not inputs:
        raise AgronomyGap(
            "no-inputs",
            "a recommendation without inputs is an opinion, not a record",
            missing=("inputs",),
        )
    if not rationale:
        raise AgronomyGap(
            "no-rationale",
            "the rule trace is the record's conscience; it cannot be empty",
            missing=("rationale",),
        )
    if expires_at <= drafted_at:
        raise AgronomyRefusal(
            "born-expired",
            "expires_at must be strictly after drafted_at; a record cannot "
            "be born already dead",
        )

    ordered_inputs = tuple(inputs)
    ordered_rationale = tuple(rationale)
    record_id = recommendation_id_for(
        kind=kind,
        inputs=ordered_inputs,
        rationale=ordered_rationale,
        payload=payload,
    )
    return RecommendationRecord(
        recommendation_id=record_id,
        kind=kind,
        inputs=ordered_inputs,
        rationale=ordered_rationale,
        uncertainty=uncertainty,
        use_class=USE_CLASS_FIELD_OPS,
        permits_financial_use=PERMITS_FINANCIAL_USE_V0,
        drafted_by=DRAFTED_BY,
        requires_human_signoff=True,
        drafted_at=drafted_at,
        expires_at=expires_at,
        payload=dict(payload),
    )


__all__ = [
    "KINDS",
    "REFUSED_KINDS",
    "InputRef",
    "RationaleStep",
    "RecommendationRecord",
    "input_ref_from_observation",
    "recommendation_id_for",
    "draft_recommendation",
]
