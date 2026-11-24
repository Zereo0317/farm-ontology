"""Human-reviewed, non-executing finance intent controls.

This module records immutable, versioned hedge intents and their human review
events.  It deliberately has no broker, submit, or live-execution interface.
Moving an intent to ``approved-manual`` means a human may consider an
independent, out-of-band action; it does not assert that an order was placed.

Every approval path requires a caller-supplied signature verifier.  The
verifier must check signatures against a separately managed trusted-key and
revocation registry.  No verifier is configured by default, so missing trust
configuration fails closed.  This module is a pure model and does not persist
records; callers must persist its exported event sequence in an independently
protected ledger before treating it as an operational record.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Callable, Iterable, Mapping

from farm_ontology.markets.rails import PERMITTED_FAMILIES
from farm_ontology.policy import CLASS_C_POLICY

_HASH = re.compile(r"^[0-9a-f]{64}$")
_SIGNATURE = re.compile(r"^[0-9a-f]{128}$")
# Operational evidence freshness bounds.  They constrain evidence age, not
# trading limits or strategy values.  The cap's own signed period is also
# checked; a short period cannot be extended by this module.
MAX_CAP_SHEET_PERIOD = timedelta(days=100)
MAX_KILL_SWITCH_AGE = timedelta(minutes=5)


def _utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _hash(value: str, name: str) -> str:
    if not isinstance(value, str) or not _HASH.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")
    return value


def _actor(value: str, name: str = "actor") -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be nonempty and unpadded")
    return value


def _canonical(value: object) -> bytes:
    def jsonable(item: object) -> object:
        if isinstance(item, Decimal):
            return str(item)
        if isinstance(item, datetime):
            return _utc(item, "datetime").isoformat()
        if isinstance(item, Enum):
            return item.value
        if isinstance(item, Mapping):
            if any(not isinstance(key, str) for key in item):
                raise TypeError("canonical mapping keys must be strings")
            return {key: jsonable(val) for key, val in item.items()}
        if isinstance(item, (tuple, list)):
            return [jsonable(val) for val in item]
        if item is None or isinstance(item, (str, int, float, bool)):
            return item
        raise TypeError(f"unsupported canonical evidence value: {type(item).__name__}")

    return json.dumps(
        jsonable(value), sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _claim_list(values: tuple[str, ...]) -> str:
    """Unambiguous string encoding for list-valued signed evidence claims."""
    return _canonical(values).decode("utf-8")


class EvidencePurpose(str, Enum):
    RISK_CAP_SHEET = "risk-cap-sheet"
    SOURCE_RIGHTS = "source-rights"
    KILL_SWITCH = "kill-switch"
    INTENT_APPROVAL = "intent-approval"
    INTENT_CANCEL = "intent-cancel"


class ApprovalRole(str, Enum):
    RISK_OWNER = "risk-owner"
    INDEPENDENT_REVIEWER = "independent-reviewer"


class IntentState(str, Enum):
    PROPOSED = "proposed"
    APPROVED_MANUAL = "approved-manual"
    CANCELLED = "cancelled"
    HALTED = "halted"
    EXPIRED = "expired"


class EventType(str, Enum):
    PROPOSED = "proposed"
    APPROVED_MANUAL = "approved-manual"
    CANCELLED = "cancelled"
    HALTED = "halted"


SignatureVerifier = Callable[[str, bytes, str], bool]


@dataclass(frozen=True)
class SignedEvidence:
    """Detached Ed25519-shaped evidence verified by a trusted host adapter.

    ``claims`` is covered by ``signing_payload``.  A 64-byte signature shape
    check prevents accidental empty or malformed evidence; only the injected
    verifier establishes signer identity and cryptographic validity.
    """

    purpose: EvidencePurpose
    subject_sha256: str
    issuer: str
    issued_at: datetime
    expires_at: datetime
    claims: tuple[tuple[str, str], ...]
    signature_hex: str

    def __post_init__(self) -> None:
        if not isinstance(self.purpose, EvidencePurpose):
            raise ValueError("evidence purpose must be an explicit EvidencePurpose")
        _hash(self.subject_sha256, "subject_sha256")
        _actor(self.issuer, "evidence issuer")
        start, end = _utc(self.issued_at, "issued_at"), _utc(self.expires_at, "expires_at")
        if end <= start:
            raise ValueError("evidence expiry must follow issue time")
        if not isinstance(self.claims, tuple) or any(
            not isinstance(claim, tuple) or len(claim) != 2
            or not isinstance(claim[0], str) or not isinstance(claim[1], str)
            for claim in self.claims
        ):
            raise ValueError("evidence claims must be a tuple of string key/value pairs")
        if tuple(sorted(self.claims)) != self.claims:
            raise ValueError("evidence claims must be sorted for canonical signing")
        if len({key for key, _ in self.claims}) != len(self.claims):
            raise ValueError("evidence claims cannot contain duplicate keys")
        if any(not key or key != key.strip() for key, _value in self.claims):
            raise ValueError("evidence claim keys must be nonempty and unpadded")
        if not isinstance(self.signature_hex, str) or not _SIGNATURE.fullmatch(self.signature_hex):
            raise ValueError("evidence signature must be 64-byte lowercase hex")

    def signing_payload(self) -> bytes:
        return _canonical({
            "version": 1,
            "purpose": self.purpose.value,
            "subject_sha256": self.subject_sha256,
            "issuer": self.issuer,
            "issued_at": _utc(self.issued_at, "issued_at").isoformat(),
            "expires_at": _utc(self.expires_at, "expires_at").isoformat(),
            "claims": dict(self.claims),
        })

    @property
    def fingerprint(self) -> str:
        return _digest({
            "payload": self.signing_payload().decode("utf-8"),
            "signature_hex": self.signature_hex,
        })


def _verified(
    evidence: SignedEvidence,
    *,
    purpose: EvidencePurpose,
    subject_sha256: str,
    at: datetime,
    verifier: SignatureVerifier | None,
) -> bool:
    if not isinstance(evidence, SignedEvidence):
        return False
    moment = _utc(at, "at")
    if evidence.purpose is not purpose or evidence.subject_sha256 != subject_sha256:
        return False
    if moment < _utc(evidence.issued_at, "issued_at") or moment >= _utc(evidence.expires_at, "expires_at"):
        return False
    if verifier is None:
        return False
    try:
        return verifier(evidence.issuer, evidence.signing_payload(), evidence.signature_hex) is True
    except Exception:
        return False


@dataclass(frozen=True)
class HedgeOrderIntent:
    """Versioned proposal bound to market, rights, and human-set risk evidence."""

    intent_id: str
    artifact_sha256: str
    instrument_family: str
    side: str
    quantity: Decimal
    quantity_unit: str
    cap_sheet_sha256: str
    rights_bundle_sha256: str
    scope: str
    feeds: tuple[str, ...]
    territory: str
    uses_farmer_data: bool
    farmer_consent_grant_fingerprints: tuple[str, ...]
    created_at: datetime
    expires_at: datetime
    class_c_policy: str = "closed"
    version: int = 1

    def __post_init__(self) -> None:
        _actor(self.intent_id, "intent_id")
        if type(self.version) is not int or self.version != 1:
            raise ValueError("unsupported hedge intent version")
        _hash(self.artifact_sha256, "artifact_sha256")
        _hash(self.cap_sheet_sha256, "cap_sheet_sha256")
        _hash(self.rights_bundle_sha256, "rights_bundle_sha256")
        _actor(self.instrument_family, "instrument_family")
        _actor(self.side, "intent side")
        _actor(self.scope, "intent scope")
        if not isinstance(self.feeds, (tuple, list)):
            raise ValueError("intent feeds must be an explicit tuple or list of feed identifiers")
        if any(not isinstance(feed, str) for feed in self.feeds):
            raise ValueError("intent feed identifiers must be strings")
        # Store immutable canonical content even when a caller supplies a list.
        object.__setattr__(self, "feeds", tuple(self.feeds))
        if not self.feeds or tuple(sorted(set(self.feeds))) != self.feeds:
            raise ValueError("intent feeds must be nonempty, sorted, and unique")
        if any(not feed or feed != feed.strip() for feed in self.feeds):
            raise ValueError("intent feed identifiers must be nonempty and unpadded")
        _actor(self.territory, "intent territory")
        if not isinstance(self.uses_farmer_data, bool):
            raise ValueError("intent uses_farmer_data must be explicit boolean")
        if not isinstance(self.farmer_consent_grant_fingerprints, (tuple, list)) or any(
            not isinstance(value, str) for value in self.farmer_consent_grant_fingerprints
        ):
            raise ValueError("farmer consent fingerprints must be an explicit tuple or list of strings")
        object.__setattr__(self, "farmer_consent_grant_fingerprints", tuple(self.farmer_consent_grant_fingerprints))
        if tuple(sorted(set(self.farmer_consent_grant_fingerprints))) != self.farmer_consent_grant_fingerprints:
            raise ValueError("farmer consent fingerprints must be sorted and unique")
        for fingerprint in self.farmer_consent_grant_fingerprints:
            _hash(fingerprint, "farmer consent grant fingerprint")
        if self.uses_farmer_data and not self.farmer_consent_grant_fingerprints:
            raise ValueError("farmer-derived scope requires consent grant fingerprints")
        if self.instrument_family not in PERMITTED_FAMILIES:
            if self.instrument_family.strip().lower() in {
                "settlement", "hedge", "trigger", "nature-unit",
            }:
                raise ValueError("Class C finance uses remain closed")
            raise ValueError("intent instrument family is not on the doctrine allow-list")
        if self.side not in {"buy", "sell", "reduce"}:
            raise ValueError("intent side must be buy, sell, or reduce")
        if not isinstance(self.quantity, Decimal) or not self.quantity.is_finite() or self.quantity <= 0:
            raise ValueError("intent quantity must be a finite positive Decimal")
        _actor(self.quantity_unit, "intent quantity_unit")
        if not isinstance(self.class_c_policy, str) or self.class_c_policy != "closed":
            raise ValueError("Class C must remain closed")
        created, expires = _utc(self.created_at, "created_at"), _utc(self.expires_at, "expires_at")
        if expires <= created:
            raise ValueError("intent expiry must follow creation")

    def payload(self) -> dict:
        quantity = format(self.quantity, "f")
        if "." in quantity:
            quantity = quantity.rstrip("0").rstrip(".")
        return {
            "version": self.version,
            "intent_id": self.intent_id,
            "artifact_sha256": self.artifact_sha256,
            "instrument_family": self.instrument_family,
            "side": self.side,
            "quantity": quantity,
            "quantity_unit": self.quantity_unit,
            "cap_sheet_sha256": self.cap_sheet_sha256,
            "rights_bundle_sha256": self.rights_bundle_sha256,
            "scope": self.scope,
            "feeds": list(self.feeds),
            "territory": self.territory,
            "uses_farmer_data": self.uses_farmer_data,
            "farmer_consent_grant_fingerprints": list(self.farmer_consent_grant_fingerprints),
            "created_at": _utc(self.created_at, "created_at").isoformat(),
            "expires_at": _utc(self.expires_at, "expires_at").isoformat(),
            "class_c_policy": self.class_c_policy,
        }

    @property
    def fingerprint(self) -> str:
        return _digest(self.payload())


@dataclass(frozen=True)
class ApprovalBundle:
    risk_owner: SignedEvidence
    independent_reviewer: SignedEvidence

    def __post_init__(self) -> None:
        if not isinstance(self.risk_owner, SignedEvidence) or not isinstance(
            self.independent_reviewer, SignedEvidence
        ):
            raise ValueError("approval bundle must contain two signed evidence records")


@dataclass(frozen=True)
class GateDecision:
    approved_for_manual_review: bool
    violations: tuple[str, ...]
    independent_reviewer: str = ""
    evidence_sha256: str = ""


def evaluate_manual_approval(
    intent: HedgeOrderIntent,
    *,
    at: datetime,
    cap_sheet: SignedEvidence | None,
    source_rights: SignedEvidence | None,
    kill_switch: SignedEvidence | None,
    approvals: ApprovalBundle | None,
    verifier: SignatureVerifier | None,
) -> GateDecision:
    """Return whether an intent may be marked human-approved, never executed.

    All external evidence is bound to the exact intent or content digest and
    must be valid at ``at``.  Missing signature infrastructure is a refusal.
    """
    moment = _utc(at, "at")
    violations: list[str] = []
    # The authoritative global switch wins over caller-provided intent data.
    if CLASS_C_POLICY != "open":
        violations.append("class-c-policy-closed")
    if moment < _utc(intent.created_at, "created_at") or moment >= _utc(intent.expires_at, "expires_at"):
        violations.append("intent-expired-or-not-yet-valid")
    if cap_sheet is None or not _verified(
        cap_sheet, purpose=EvidencePurpose.RISK_CAP_SHEET,
        subject_sha256=intent.cap_sheet_sha256, at=moment, verifier=verifier,
    ):
        violations.append("risk-cap-sheet-missing-invalid-expired-or-untrusted")
    else:
        cap_claims = dict(cap_sheet.claims)
        try:
            cap_period_start = datetime.fromisoformat(cap_claims["period_start"])
            cap_period_end = datetime.fromisoformat(cap_claims["period_end"])
            if (cap_period_start.tzinfo is None or cap_period_end.tzinfo is None
                    or not _utc(cap_period_start, "cap period start") <= moment < _utc(cap_period_end, "cap period end")
                    or not _utc(cap_period_start, "cap period start") <= _utc(cap_sheet.issued_at, "cap issue time") < _utc(cap_period_end, "cap period end")
                    or _utc(cap_period_end, "cap period end") - _utc(cap_period_start, "cap period start") > MAX_CAP_SHEET_PERIOD):
                raise ValueError
        except (KeyError, ValueError):
            violations.append("risk-cap-sheet-period-missing-invalid-or-stale")
        if cap_claims.get("specimen") != "false":
            violations.append("risk-cap-sheet-is-specimen")
        if cap_claims.get("role") != ApprovalRole.RISK_OWNER.value:
            violations.append("risk-cap-sheet-does-not-name-risk-owner-role")
        if "agent" in cap_sheet.issuer.lower():
            violations.append("risk-cap-sheet-cannot-be-issued-by-agent")
        if cap_claims.get("instrument_family") != intent.instrument_family:
            violations.append("risk-cap-sheet-does-not-cover-instrument-family")
        if cap_claims.get("quantity_unit") != intent.quantity_unit:
            violations.append("risk-cap-sheet-quantity-unit-does-not-match-intent")
        try:
            maximum = Decimal(cap_claims.get("max_order_quantity", ""))
            if not maximum.is_finite() or maximum <= 0:
                raise ValueError
            if intent.quantity > maximum:
                violations.append("intent-exceeds-signed-order-quantity-cap")
        except (ValueError, ArithmeticError):
            violations.append("risk-cap-sheet-lacks-valid-order-quantity-cap")
    if source_rights is None or not _verified(
        source_rights, purpose=EvidencePurpose.SOURCE_RIGHTS,
        subject_sha256=intent.rights_bundle_sha256, at=moment, verifier=verifier,
    ):
        violations.append("source-rights-missing-invalid-expired-or-untrusted")
    else:
        rights_claims = dict(source_rights.claims)
        if rights_claims.get("status") != "active" or rights_claims.get("purpose") != "hedge":
            violations.append("source-rights-not-active-for-hedge-purpose")
        expected_rights = {
            "scope": intent.scope,
            "feeds": _claim_list(intent.feeds),
            "territory": intent.territory,
            "uses_farmer_data": "true" if intent.uses_farmer_data else "false",
            "instrument_family": intent.instrument_family,
            "farmer_consent_grant_fingerprints": _claim_list(intent.farmer_consent_grant_fingerprints),
        }
        if any(rights_claims.get(key) != value for key, value in expected_rights.items()):
            violations.append("source-rights-do-not-cover-explicit-intent-scope")
        if intent.uses_farmer_data and not intent.farmer_consent_grant_fingerprints:
            violations.append("farmer-derived-scope-requires-consent-grant-fingerprints")
    if kill_switch is None or not _verified(
        kill_switch, purpose=EvidencePurpose.KILL_SWITCH,
        subject_sha256=intent.fingerprint, at=moment, verifier=verifier,
    ):
        violations.append("independent-kill-switch-evidence-missing-invalid-or-expired")
    elif dict(kill_switch.claims).get("halt_raised") != "false":
        violations.append("kill-switch-halt-raised-or-unknown")
    elif moment - _utc(kill_switch.issued_at, "kill-switch issue time") > MAX_KILL_SWITCH_AGE:
        violations.append("kill-switch-evidence-is-stale")
    if approvals is None:
        violations.append("risk-owner-and-independent-approval-missing")
    else:
        pair = (
            (approvals.risk_owner, ApprovalRole.RISK_OWNER),
            (approvals.independent_reviewer, ApprovalRole.INDEPENDENT_REVIEWER),
        )
        verified_ids: list[str] = []
        for evidence, role in pair:
            claims = dict(evidence.claims)
            if not _verified(
                evidence, purpose=EvidencePurpose.INTENT_APPROVAL,
                subject_sha256=intent.fingerprint, at=moment, verifier=verifier,
            ):
                violations.append(f"{role.value}-approval-missing-invalid-or-expired")
                continue
            if claims.get("role") != role.value or claims.get("decision") != "approve":
                violations.append(f"{role.value}-approval-claims-invalid")
            else:
                verified_ids.append(evidence.issuer)
        if len(verified_ids) == 2 and verified_ids[0] == verified_ids[1]:
            violations.append("risk-owner-and-independent-reviewer-must-be-distinct")
        if _utc(approvals.risk_owner.issued_at, "risk owner approval time") >= _utc(
            approvals.independent_reviewer.issued_at, "independent review time"
        ):
            violations.append("risk-owner-approval-must-precede-independent-review")
        if approvals.risk_owner.issuer != (cap_sheet.issuer if cap_sheet else ""):
            violations.append("risk-cap-sheet-signer-must-match-risk-owner")
        if kill_switch is not None and kill_switch.issuer in verified_ids:
            violations.append("kill-switch-evidence-must-be-independent-of-approvers")
    verified_reviewer = (
        approvals.independent_reviewer.issuer if approvals is not None else ""
    )
    evidence_hash = _digest({
        "cap": cap_sheet.fingerprint if cap_sheet else None,
        "rights": source_rights.fingerprint if source_rights else None,
        "kill_switch": kill_switch.fingerprint if kill_switch else None,
        "risk_owner_approval": approvals.risk_owner.fingerprint if approvals else None,
        "independent_approval": approvals.independent_reviewer.fingerprint if approvals else None,
    })
    return GateDecision(
        not violations, tuple(sorted(set(violations))), verified_reviewer, evidence_hash
    )


@dataclass(frozen=True)
class IntentEvent:
    sequence: int
    intent_id: str
    intent_sha256: str
    event_type: EventType
    at: datetime
    actor: str
    evidence_sha256: str
    previous_sha256: str
    event_sha256: str

    def __post_init__(self) -> None:
        if type(self.sequence) is not int or self.sequence < 1:
            raise ValueError("intent event sequence must be a positive integer")
        _actor(self.intent_id, "event intent_id")
        if not isinstance(self.event_type, EventType):
            raise ValueError("intent event type must be an explicit EventType")
        _actor(self.actor, "event actor")
        for name in ("intent_sha256", "evidence_sha256", "previous_sha256", "event_sha256"):
            _hash(getattr(self, name), f"event {name}")
        _utc(self.at, "event at")

    def payload(self) -> dict:
        return {
            "sequence": self.sequence,
            "intent_id": self.intent_id,
            "intent_sha256": self.intent_sha256,
            "event_type": self.event_type.value,
            "at": _utc(self.at, "at").isoformat(),
            "actor": self.actor,
            "evidence_sha256": self.evidence_sha256,
            "previous_sha256": self.previous_sha256,
        }


class HedgeIntentLedger:
    """Append-only, hash-chained in-memory lifecycle; intentionally no submit API."""

    def __init__(self, events: Iterable[IntentEvent] = (),
                 intents: Iterable[HedgeOrderIntent] = ()) -> None:
        self._events: list[IntentEvent] = []
        self._intents: dict[str, HedgeOrderIntent] = {}
        self._states: dict[str, IntentState] = {}
        for intent in intents:
            if not isinstance(intent, HedgeOrderIntent):
                raise ValueError("intent replay inputs must be HedgeOrderIntent records")
            if intent.intent_id in self._intents:
                raise ValueError("duplicate immutable intent id in replay input")
            self._intents[intent.intent_id] = intent
        self._replay(tuple(events))

    @property
    def events(self) -> tuple[IntentEvent, ...]:
        return tuple(self._events)

    @property
    def intents(self) -> tuple[HedgeOrderIntent, ...]:
        return tuple(self._intents.values())

    def state(self, intent_id: str, *, at: datetime) -> IntentState | None:
        """Return time-derived state; an approved proposal expires at intent expiry."""
        state = self._states.get(intent_id)
        intent = self._intents.get(intent_id)
        if state in {IntentState.PROPOSED, IntentState.APPROVED_MANUAL} and intent is not None:
            moment = _utc(at, "at")
            if moment < _utc(intent.created_at, "created_at") or moment >= _utc(intent.expires_at, "expires_at"):
                return IntentState.EXPIRED
        return state

    def _append(self, intent: HedgeOrderIntent, event_type: EventType,
                at: datetime, actor: str, evidence_sha256: str) -> IntentEvent:
        _actor(actor)
        _hash(evidence_sha256, "event evidence_sha256")
        moment = _utc(at, "at")
        if self._events and moment < _utc(self._events[-1].at, "previous event at"):
            raise ValueError("intent events must be time ordered")
        previous = self._events[-1].event_sha256 if self._events else "0" * 64
        provisional = IntentEvent(
            sequence=len(self._events) + 1, intent_id=intent.intent_id,
            intent_sha256=intent.fingerprint, event_type=event_type,
            at=moment, actor=actor, evidence_sha256=evidence_sha256,
            previous_sha256=previous, event_sha256="0" * 64,
        )
        event = IntentEvent(**{**provisional.__dict__, "event_sha256": _digest(provisional.payload())})
        self._events.append(event)
        self._states[intent.intent_id] = IntentState(event_type.value)
        return event

    def propose(self, intent: HedgeOrderIntent, *, at: datetime, actor: str) -> IntentEvent:
        _actor(actor, "proposer identity")
        existing = self._intents.get(intent.intent_id)
        if existing:
            if existing.fingerprint != intent.fingerprint:
                raise ValueError("intent_id already binds different immutable content")
            return next(event for event in self._events if event.intent_id == intent.intent_id)
        if _utc(at, "at") < _utc(intent.created_at, "created_at") or _utc(at, "at") >= _utc(intent.expires_at, "expires_at"):
            raise ValueError("proposal is outside its validity window")
        self._intents[intent.intent_id] = intent
        return self._append(intent, EventType.PROPOSED, at, actor, intent.artifact_sha256)

    def approve_for_manual_review(self, intent_id: str, *, at: datetime,
                                  actor: str, cap_sheet: SignedEvidence | None,
                                  source_rights: SignedEvidence | None,
                                  kill_switch: SignedEvidence | None,
                                  approvals: ApprovalBundle | None,
                                  verifier: SignatureVerifier | None) -> IntentEvent:
        intent = self._intents.get(intent_id)
        if intent is None or self._states.get(intent_id) is not IntentState.PROPOSED:
            raise ValueError("only a proposed intent can be approved")
        decision = evaluate_manual_approval(
            intent, at=at, cap_sheet=cap_sheet, source_rights=source_rights,
            kill_switch=kill_switch, approvals=approvals, verifier=verifier,
        )
        if not decision.approved_for_manual_review or decision.violations:
            raise ValueError("finance approval gates did not pass")
        if actor != decision.independent_reviewer:
            raise ValueError("the independent reviewer must record the approval event")
        return self._append(intent, EventType.APPROVED_MANUAL, at, actor, decision.evidence_sha256)

    def cancel(self, intent_id: str, *, at: datetime, actor: str,
               signed_cancel_evidence: SignedEvidence,
               verifier: SignatureVerifier | None) -> IntentEvent:
        intent = self._intents.get(intent_id)
        if intent is None or self._states.get(intent_id) not in {IntentState.PROPOSED, IntentState.APPROVED_MANUAL}:
            raise ValueError("only an open intent can be cancelled")
        if not _verified(
            signed_cancel_evidence, purpose=EvidencePurpose.INTENT_CANCEL,
            subject_sha256=intent.fingerprint, at=at, verifier=verifier,
        ) or dict(signed_cancel_evidence.claims).get("decision") != "cancel":
            raise ValueError("cancellation requires trusted, current signed evidence")
        if actor != signed_cancel_evidence.issuer:
            raise ValueError("cancellation event actor must match signed issuer")
        return self._append(intent, EventType.CANCELLED, at, actor, signed_cancel_evidence.fingerprint)

    def halt(self, intent_id: str, *, at: datetime, actor: str,
             kill_switch: SignedEvidence,
             verifier: SignatureVerifier | None) -> IntentEvent:
        intent = self._intents.get(intent_id)
        if intent is None or self._states.get(intent_id) not in {IntentState.PROPOSED, IntentState.APPROVED_MANUAL}:
            raise ValueError("only an open intent can be halted")
        if not _verified(
            kill_switch, purpose=EvidencePurpose.KILL_SWITCH,
            subject_sha256=intent.fingerprint, at=at, verifier=verifier,
        ) or dict(kill_switch.claims).get("halt_raised") != "true":
            raise ValueError("HALT requires trusted, current signed kill-switch evidence")
        if actor != kill_switch.issuer:
            raise ValueError("HALT event actor must match signed issuer")
        return self._append(intent, EventType.HALTED, at, actor, kill_switch.fingerprint)

    def _replay(self, events: tuple[IntentEvent, ...]) -> None:
        previous = "0" * 64
        last_at: datetime | None = None
        for index, event in enumerate(events, 1):
            if not isinstance(event, IntentEvent):
                raise ValueError("intent event replay inputs must be IntentEvent records")
            if event.sequence != index or event.previous_sha256 != previous:
                raise ValueError("intent event sequence or previous hash is invalid")
            if event.event_sha256 != _digest(event.payload()):
                raise ValueError("intent event hash does not match its content")
            # Hash chains detect accidental corruption, not a forged reviewer.
            # There is no persisted signature-verification contract in this
            # model, so only unsigned proposal records can be replayed.
            if event.event_type is not EventType.PROPOSED:
                raise ValueError("replayed lifecycle event lacks cryptographic authentication")
            _actor(event.actor, "event actor")
            _hash(event.intent_sha256, "event intent_sha256")
            _hash(event.evidence_sha256, "event evidence_sha256")
            moment = _utc(event.at, "event at")
            if last_at is not None and moment < last_at:
                raise ValueError("intent events must be time ordered")
            state = self._states.get(event.intent_id)
            intent = self._intents.get(event.intent_id)
            if intent is None or intent.fingerprint != event.intent_sha256:
                raise ValueError("intent event does not bind to matching immutable content")
            if event.event_type is EventType.PROPOSED:
                if state is not None:
                    raise ValueError("intent may be proposed only once")
                if not _utc(intent.created_at, "intent created_at") <= moment < _utc(
                    intent.expires_at, "intent expires_at"
                ):
                    raise ValueError("replayed proposal is outside its validity window")
                if event.evidence_sha256 != intent.artifact_sha256:
                    raise ValueError("replayed proposal evidence does not match the intent artifact digest")
                self._states[event.intent_id] = IntentState.PROPOSED
            elif event.event_type is EventType.APPROVED_MANUAL and state is IntentState.PROPOSED:
                self._states[event.intent_id] = IntentState.APPROVED_MANUAL
            elif event.event_type is EventType.CANCELLED and state in {IntentState.PROPOSED, IntentState.APPROVED_MANUAL}:
                self._states[event.intent_id] = IntentState.CANCELLED
            elif event.event_type is EventType.HALTED and state in {IntentState.PROPOSED, IntentState.APPROVED_MANUAL}:
                self._states[event.intent_id] = IntentState.HALTED
            else:
                raise ValueError("intent event violates lifecycle order")
            self._events.append(event)
            previous, last_at = event.event_sha256, moment


@dataclass(frozen=True)
class ReconciliationEntry:
    reconciliation_id: str
    statement_sha256: str
    unverified_result_sha256: str
    recorded_at: datetime
    previous_sha256: str
    entry_sha256: str

    def __post_init__(self) -> None:
        _actor(self.reconciliation_id, "reconciliation_id")
        for name in ("statement_sha256", "unverified_result_sha256", "previous_sha256", "entry_sha256"):
            _hash(getattr(self, name), f"reconciliation {name}")
        _utc(self.recorded_at, "recorded_at")

    def payload(self) -> dict:
        return {
            "reconciliation_id": self.reconciliation_id,
            "statement_sha256": self.statement_sha256,
            "unverified_result_sha256": self.unverified_result_sha256,
            "recorded_at": _utc(self.recorded_at, "recorded_at").isoformat(),
            "previous_sha256": self.previous_sha256,
        }


class PaperReconciliationJournal:
    """Journal caller-supplied comparisons as explicitly unverified evidence.

    The result digest only identifies caller-provided bytes. It does not prove
    that the arithmetic was correct or that the statement is authoritative.
    """

    def __init__(self, entries: Iterable[ReconciliationEntry] = ()) -> None:
        self._entries: list[ReconciliationEntry] = []
        self._by_id: dict[str, ReconciliationEntry] = {}
        self._by_statement: dict[str, ReconciliationEntry] = {}
        self._replay(tuple(entries))

    @property
    def entries(self) -> tuple[ReconciliationEntry, ...]:
        return tuple(self._entries)

    def record(self, reconciliation_id: str, *, statement: Mapping[str, object],
               result: Mapping[str, object], recorded_at: datetime) -> ReconciliationEntry:
        _actor(reconciliation_id, "reconciliation_id")
        if not isinstance(statement, Mapping) or not isinstance(result, Mapping):
            raise ValueError("reconciliation statement and result must be mappings")
        statement_hash, result_hash = _digest(statement), _digest(result)
        old = self._by_id.get(reconciliation_id)
        if old:
            if (old.statement_sha256, old.unverified_result_sha256) != (statement_hash, result_hash):
                raise ValueError("reconciliation_id replay has different content")
            return old
        duplicate_statement = self._by_statement.get(statement_hash)
        if duplicate_statement is not None:
            raise ValueError("statement was already reconciled under another id")
        previous = self._entries[-1].entry_sha256 if self._entries else "0" * 64
        provisional = ReconciliationEntry(
            reconciliation_id, statement_hash, result_hash,
            _utc(recorded_at, "recorded_at"), previous, "0" * 64,
        )
        entry = ReconciliationEntry(**{**provisional.__dict__, "entry_sha256": _digest(provisional.payload())})
        self._entries.append(entry)
        self._by_id[reconciliation_id] = entry
        self._by_statement[statement_hash] = entry
        return entry

    def _replay(self, entries: tuple[ReconciliationEntry, ...]) -> None:
        previous = "0" * 64
        last_at: datetime | None = None
        for entry in entries:
            if not isinstance(entry, ReconciliationEntry):
                raise ValueError("reconciliation replay inputs must be ReconciliationEntry records")
            moment = _utc(entry.recorded_at, "recorded_at")
            if not entry.reconciliation_id or not _HASH.fullmatch(entry.statement_sha256) or not _HASH.fullmatch(entry.unverified_result_sha256):
                raise ValueError("reconciliation entry has invalid identity or digest")
            if entry.reconciliation_id in self._by_id:
                raise ValueError("reconciliation journal contains duplicate IDs")
            if entry.statement_sha256 in self._by_statement:
                raise ValueError("reconciliation journal contains duplicate statements")
            if entry.previous_sha256 != previous or entry.entry_sha256 != _digest(entry.payload()):
                raise ValueError("reconciliation journal hash chain is invalid")
            if last_at is not None and moment < last_at:
                raise ValueError("reconciliation entries must be time ordered")
            self._entries.append(entry)
            self._by_id[entry.reconciliation_id] = entry
            self._by_statement[entry.statement_sha256] = entry
            previous, last_at = entry.entry_sha256, moment


__all__ = [
    "ApprovalBundle", "ApprovalRole", "EvidencePurpose", "EventType",
    "GateDecision", "HedgeIntentLedger", "HedgeOrderIntent", "IntentEvent",
    "IntentState", "PaperReconciliationJournal", "ReconciliationEntry",
    "SignatureVerifier", "SignedEvidence", "evaluate_manual_approval",
]
