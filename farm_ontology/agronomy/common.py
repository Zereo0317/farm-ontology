"""Shared vocabulary for the agronomy decision engine (WS3).

Mirrors the ``farm_ontology.actuation`` gap/refusal split: a *gap* means an
input was missing or ill-formed and the system refuses rather than guesses;
a *refusal* means the inputs were usable but the answer is still NO by
policy (for example proposing a hedge — a class-C-shaped use — from an
agronomy advisory).

Canonical JSON and deterministic hashing follow the one serialisation used
across the decision infrastructure (``farm_ontology.actuation.command_ledger.
canonical_json`` and the ontolaw DecisionLedger pattern): sorted keys, no
ASCII escaping, no whitespace. Reimplemented here rather than imported so
the agronomy package does not depend on the actuation package's lifecycle
semantics.

Timestamps are always injected by the caller. No module in this package
reads a clock, opens a socket, or imports anything beyond the standard
library and ``farm_ontology`` model/build/timeutil.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Sequence

#: Version of the engine's compiled configuration (rule tables + constants).
#: Every recommendation carries it so a replayed decision can be tied to the
#: exact rule set that produced it. Bump on ANY rule/threshold change.
CONFIG_VERSION = "agronomy-engine-v0-config-1"

#: Issuer of every draft recommendation (WS3.5 issuance chain).
DRAFTED_BY = "agronomy-engine"

#: v0 hard-wires this to False everywhere. Unlocking it is a written licence
#: grant recorded in WS6, never an engine decision.
PERMITS_FINANCIAL_USE_V0 = False

#: use_class of every v0 advisory: operator-facing field operations support.
USE_CLASS_FIELD_OPS = "field-ops"


class AgronomyError(Exception):
    """Base class for every deliberate failure the engine produces."""


class AgronomyGap(AgronomyError):
    """An input is missing or ill-formed; refuse, never guess.

    ``missing`` enumerates WHAT was missing so the caller (and the human
    reading the gap) can close it exactly, and ``remediation`` names how.
    """

    def __init__(
        self,
        gap: str,
        detail: str,
        *,
        missing: Sequence[str] = (),
        remediation: str = "",
    ) -> None:
        message = f"[gap:{gap}] {detail}"
        if missing:
            message += f" (missing: {', '.join(missing)})"
        if remediation:
            message += f" (remedy: {remediation})"
        super().__init__(message)
        self.gap = gap
        self.detail = detail
        self.missing = tuple(missing)
        self.remediation = remediation

    def as_gap(self) -> "Gap":
        """A first-class gap record (for staging into payloads)."""
        return Gap(
            name=self.gap,
            detail=self.detail,
            missing=self.missing,
            remediation=self.remediation,
        )


class AgronomyRefusal(AgronomyError):
    """A policy refusal: inputs were usable, the answer is still NO."""

    def __init__(self, refusal: str, detail: str, remediation: str = "") -> None:
        message = f"[refusal:{refusal}] {detail}"
        if remediation:
            message += f" (remedy: {remediation})"
        super().__init__(message)
        self.refusal = refusal
        self.detail = detail
        self.remediation = remediation


@dataclass(frozen=True)
class Gap:
    """A named, published gap. Gaps are values too; they are staged, not hidden."""

    name: str
    detail: str
    missing: tuple[str, ...] = ()
    remediation: str = ""

    def to_payload(self) -> dict:
        payload: dict = {
            "gap": self.name,
            "detail": self.detail,
            "missing": list(self.missing),
        }
        if self.remediation:
            payload["remediation"] = self.remediation
        return payload


@dataclass(frozen=True)
class SupportDeclaration:
    """The native-support ladder, rendered as an always-carryable stamp.

    ``base`` is the unconditionally-true lowest rung (the gridded weather
    support). ``extras`` are stricter, narrower claims earned by evidence
    (a calibrated probe's footprint). ``areas`` is EMPTY unless a sensor
    ITSELF declared an area — the engine never converts a point to hectares
    on the sensor's behalf.
    """

    base: str
    extras: tuple[str, ...] = ()
    areas: tuple[str, ...] = ()
    use_class: str = USE_CLASS_FIELD_OPS
    notes: tuple[str, ...] = field(default=tuple())

    def render(self) -> str:
        parts = [self.base, *self.extras, *self.areas]
        text = "; ".join(parts)
        if self.notes:
            text += " [" + "; ".join(self.notes) + "]"
        return text

    def to_payload(self) -> dict:
        return {
            "base": self.base,
            "extras": list(self.extras),
            "areas": list(self.areas),
            "use_class": self.use_class,
            "rendered": self.render(),
        }


def canonical_json(obj) -> bytes:
    """Canonical JSON bytes: sorted keys, no ASCII escaping, no whitespace.

    The one serialisation used for every deterministic id in this package,
    mirroring ``farm_ontology.actuation.command_ledger.canonical_json``.
    """
    return json.dumps(
        obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def deterministic_id(namespace: str, identity: dict) -> str:
    """A content-bound id: ``<namespace>:<sha256-prefix>``.

    Deterministic across processes and replays; timestamps are excluded
    from ``identity`` BY THE CALLER (replaying the same decision on a
    fresh day yields the same id).
    """
    digest = hashlib.sha256(canonical_json(identity)).hexdigest()
    return f"{namespace}:{digest[:32]}"


__all__ = [
    "CONFIG_VERSION",
    "DRAFTED_BY",
    "PERMITS_FINANCIAL_USE_V0",
    "USE_CLASS_FIELD_OPS",
    "AgronomyError",
    "AgronomyGap",
    "AgronomyRefusal",
    "Gap",
    "SupportDeclaration",
    "canonical_json",
    "deterministic_id",
]
