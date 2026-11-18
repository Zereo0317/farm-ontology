"""Command ledger — hash-chained machine-command records (WS5.3, spec-first).

A command is a record too (``decision-infra-roadmap.md`` WS5). Every lifecycle
event on a command appends one hash-chained record::

    record = {seq, type, ts, prev, event, hash}
    hash   = sha256(prev.encode("ascii") + canonical_json({type, ts, event}))

Mechanics mirror the ontolaw DecisionLedger pattern
(``ontolaw/src/ontolaw/ledger.py``: canonical JSON with sorted keys, genesis
``"0" * 64``, whole-chain recompute on verify, seq continuity check). The
record type is OURS — command lifecycle — not theirs; no ontolaw domain rule
is imported or assumed. This module is the completeness layer only; there is
no transport and no machine connection anywhere in ``farm_ontology.actuation``.

State machine (docs/actuation-interface-spec.md §3)::

    proposed ──approve──▶ approved ──dispatch──▶ dispatched ──ack──▶ acknowledged
       │                    │                     │                   │
       └────────────────────┴─────────────────────┴───────────────────┴─▶ voided

Legal transitions ONLY; anything else raises. Approval requires a human
approver distinct from the proposer (four-eyes; the doctrine's "engine
proposes, humans dispose"). An emergency HALT record (doctrine §6) freezes
propose/approve/dispatch/acknowledge until lifted; voiding stays available
during a HALT because cancelling commands only reduces risk.

Fail-closed house rules: missing/ill-formed inputs raise ``ActuationGap``
with a named gap; illegal moves raise ``IllegalTransition``; there is no
wall-clock read anywhere (every event takes an injected aware ``at`` for
replay determinism); JSONL persistence verifies the whole chain before
trusting it. ``voided`` is terminal — voiding never erases history, it only
stops the state machine.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

__all__ = [
    "COMMAND_STATES",
    "GENESIS_HASH",
    "ActuationError",
    "ActuationGap",
    "ActuationRefusal",
    "CommandLedger",
    "IllegalTransition",
    "canonical_json",
    "command_id_for",
]

#: Ordered lifecycle states of a command. ``voided`` is terminal.
COMMAND_STATES = ("proposed", "approved", "dispatched", "acknowledged", "voided")

#: Hash of the imaginary record before the first one.
GENESIS_HASH = "0" * 64

#: Prescription keys that must travel with every command payload (roadmap
#: §1: native support travels with every value; stamps are carried opaquely,
#: interpreted downstream, never rewritten here).
PRESCRIPTION_STAMP_KEYS = ("native_support", "use_class")

_ACTOR_KINDS = ("human", "service")
_LIFECYCLE_EVENTS = ("propose", "approve", "dispatch", "acknowledge", "void")

#: from-state requirement per lifecycle event (void handled separately: any
#: non-voided state may go to voided).
_TRANSITION_FROM = {
    "approve": "proposed",
    "dispatch": "approved",
    "acknowledge": "dispatched",
}


# ---------------------------------------------------------------------------
# Errors — the shared gap/refusal vocabulary of the whole actuation package.
# Catalogued in docs/actuation-interface-spec.md §6.


class ActuationError(Exception):
    """Base class for every deliberate failure this package can produce."""


class ActuationGap(ActuationError):
    """An input is missing or ill-formed; the system refuses rather than guesses."""

    def __init__(self, gap: str, detail: str, remediation: str = "") -> None:
        message = f"[gap:{gap}] {detail}"
        if remediation:
            message += f" (remedy: {remediation})"
        super().__init__(message)
        self.gap = gap
        self.detail = detail
        self.remediation = remediation


class ActuationRefusal(ActuationError):
    """A policy refusal: inputs were usable, the answer is still NO."""

    def __init__(self, refusal: str, detail: str, remediation: str = "") -> None:
        message = f"[refusal:{refusal}] {detail}"
        if remediation:
            message += f" (remedy: {remediation})"
        super().__init__(message)
        self.refusal = refusal
        self.detail = detail
        self.remediation = remediation


class IllegalTransition(ActuationRefusal):
    """A state-machine move that is not in the legal transition table."""

    def __init__(self, from_state: object, to_state: str, detail: str = "") -> None:
        message = (
            f"transition {_describe(from_state)!r} -> {to_state!r} is not a legal "
            "command transition (see docs/actuation-interface-spec.md §3)"
        )
        if detail:
            message += f": {detail}"
        super().__init__("illegal_transition", message, "follow the state machine")
        self.from_state = from_state
        self.to_state = to_state


def _describe(value: object) -> str:
    return "start" if value is None else str(value)


# ---------------------------------------------------------------------------
# Canonicalisation helpers (mirroring the ontolaw ledger mechanics).


def canonical_json(obj) -> bytes:
    """Canonical JSON bytes: sorted keys, no ASCII escaping, no whitespace.

    The one serialisation used for every hash and every deterministic id in
    this package.
    """
    return json.dumps(
        obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def _hash_body(prev_hash: str, body: dict) -> str:
    return hashlib.sha256(prev_hash.encode("ascii") + canonical_json(body)).hexdigest()


def _require_string(value, gap: str, detail: str, remediation: str = "") -> str:
    if not isinstance(value, str) or value.strip() == "":
        raise ActuationGap(gap, detail, remediation)
    return value


def _require_receipt(receipt, gap: str, what: str):
    if isinstance(receipt, str) and receipt.strip() != "":
        return receipt
    if isinstance(receipt, (dict, list)) and len(receipt) > 0:
        return copy.deepcopy(receipt)
    raise ActuationGap(
        gap, f"{what} requires a non-empty receipt blob (string or JSON object)"
    )


def _stamp_present(value) -> bool:
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (dict, list, tuple)):
        return len(value) > 0
    if isinstance(value, bool):
        return value is True
    if isinstance(value, (int, float)):
        return True
    return False


def _require_at(at) -> str:
    """Normalise an injected timestamp to a UTC ISO string; refuse naive ones."""
    if not isinstance(at, datetime) or at.tzinfo is None or at.utcoffset() is None:
        raise ActuationGap(
            "naive_timestamp",
            "every event takes an injected timezone-aware `at`; naive datetimes "
            "cannot be replayed deterministically",
            "pass e.g. datetime(2027, 1, 15, 9, 0, tzinfo=timezone.utc)",
        )
    return at.astimezone(timezone.utc).isoformat()


def _instant(iso_ts: str) -> datetime:
    return datetime.fromisoformat(iso_ts)


def _require_actor(actor, role: str) -> dict:
    if not isinstance(actor, dict):
        raise ActuationGap(
            f"{role}_missing", f"{role}: actor record {{'kind','id'}} is required"
        )
    kind = actor.get("kind")
    actor_id = actor.get("id")
    if kind not in _ACTOR_KINDS:
        raise ActuationGap(
            "actor_kind_invalid",
            f"{role}.kind must be one of {_ACTOR_KINDS}, got {kind!r}",
        )
    if not isinstance(actor_id, str) or actor_id.strip() == "":
        raise ActuationGap(
            "actor_id_missing", f"{role}.id must be a non-empty string"
        )
    return {"kind": kind, "id": actor_id.strip()}


def command_id_for(*, prescription, polygon_ref, proposer) -> str:
    """Deterministic command id from canonical identity fields.

    Identity = proposal content (prescription object, polygon_ref or None,
    proposer id). Timestamps are deliberately excluded: replaying the same
    proposal on a fresh ledger yields the same command_id, and two proposals
    of identical content are one command, not two.
    """
    identity = {
        "kind": "farm.actuation.command",
        "polygon_ref": polygon_ref,
        "prescription": copy.deepcopy(prescription),
        "proposer": proposer,
    }
    return hashlib.sha256(canonical_json(identity)).hexdigest()[:32]


# ---------------------------------------------------------------------------
# The ledger.


class CommandLedger:
    """Append-only JSON-serialisable hash chain of command lifecycle events.

    In-memory by construction; persist with :meth:`save` and reload with
    :meth:`from_path`/``from_jsonl_text`` — reloading verifies the whole chain
    and refuses a tampered file. A lifecycle event looks like::

        {"seq": 1, "type": "command_event", "ts": "...", "prev": GENESIS_HASH,
         "event": {"name": "propose", "command_id": "...", "from_state": None,
                   "to_state": "proposed", "actor": {"kind": "service",
                   "id": "agronomy-engine"}, "prescription": {...}},
         "hash": "..."}

    and a HALT record looks like::

        {"seq": 4, "type": "halt", "ts": "...", "prev": "...",
         "event": {"name": "halt", "halt_action": "raise", "actor": {...},
                   "reason": "typhoon inbound; freeze all field commands"},
         "hash": "..."}
    """

    #: Record types on this chain.
    RECORD_TYPES = ("command_event", "halt")
    HALT_ACTIONS = ("raise", "lift")

    def __init__(self, records=None) -> None:
        self._records: list[dict] = []
        for record in records or ():
            if not isinstance(record, dict):
                raise ActuationGap(
                    "ledger_record_ill_formed",
                    f"records must be dicts, got {type(record).__name__}",
                )
            self._records.append(copy.deepcopy(record))

    # -- reading ------------------------------------------------------------

    @property
    def records(self) -> tuple:
        """Defensive copies of every stored record (append-only by convention)."""
        return tuple(copy.deepcopy(record) for record in self._records)

    def tail_hash(self) -> str:
        return self._records[-1]["hash"] if self._records else GENESIS_HASH

    def state_of(self, command_id) -> str:
        """Fold the chain to the current state of one command.

        Raises ``ActuationGap("unknown_command")`` for an id never proposed.
        """
        cid = _require_string(command_id, "command_id_missing", "command_id required")
        last = None
        for record in self._records:
            event = record.get("event") or {}
            if record.get("type") == "command_event" and event.get("command_id") == cid:
                last = event
        if last is None:
            raise ActuationGap(
                "unknown_command",
                f"no lifecycle records for command {cid!r}",
                "check the id; command ids are content-derived (see command_id_for)",
            )
        return last["to_state"]

    def events_of(self, command_id) -> tuple:
        """All lifecycle records for one command, in chain order."""
        cid = _require_string(command_id, "command_id_missing", "command_id required")
        self.state_of(cid)  # unknown_command for free
        return tuple(
            copy.deepcopy(record)
            for record in self._records
            if record.get("type") == "command_event"
            and (record.get("event") or {}).get("command_id") == cid
        )

    def snapshot(self) -> dict:
        """Every known command_id mapped to its current state."""
        out: dict[str, str] = {}
        for record in self._records:
            if record.get("type") != "command_event":
                continue
            event = record.get("event") or {}
            out[event["command_id"]] = event["to_state"]
        return out

    def halted(self) -> bool:
        """True while an emergency HALT (doctrine §6) is active."""
        for record in reversed(self._records):
            if record.get("type") == "halt":
                return (record.get("event") or {}).get("halt_action") == "raise"
        return False

    # -- writing ------------------------------------------------------------

    def _append(self, record_type: str, event: dict, at) -> dict:
        ts = _require_at(at)
        body = {
            "type": record_type,
            "ts": ts,
            "event": copy.deepcopy(event),
        }
        prev = self.tail_hash()
        record = {
            "seq": len(self._records) + 1,
            "type": record_type,
            "ts": ts,
            "prev": prev,
            "event": copy.deepcopy(event),
            "hash": _hash_body(prev, body),
        }
        self._records.append(record)
        return copy.deepcopy(record)

    def _guard_not_halted(self, action: str) -> None:
        if self.halted():
            raise ActuationRefusal(
                "halted",
                f"{action} refused: an emergency HALT is active on this ledger",
                "lift the HALT with lift_halt(reason=...) (risk owner) or void "
                "the affected commands",
            )

    def _last_event(self, command_id: str) -> dict | None:
        """The full RECORD of this command's most recent lifecycle event."""
        last = None
        for record in self._records:
            event = record.get("event") or {}
            if record.get("type") == "command_event" and event.get("command_id") == command_id:
                last = record
        return last

    def _check_monotonic(self, command_id: str, at, what: str) -> None:
        last = self._last_event(command_id)
        if last is None:
            return
        incoming = _instant(_require_at(at))
        previous = _instant(last["ts"])
        if incoming < previous:
            raise ActuationGap(
                "timestamp_regression",
                f"{what} at {incoming.isoformat()} predates the command's last "
                f"recorded event at {previous.isoformat()}",
                "inject a timestamp at or after the last lifecycle event",
            )

    def propose(self, *, prescription, actor, at, polygon_ref=None) -> dict:
        """Open a new command. State becomes ``proposed``.

        Refuses while a HALT is active, on a missing/blank prescription
        stamp (``native_support``/``use_class``), a non-dict prescription,
        an ill-formed actor/polygon_ref/timestamp, or an exact-content
        duplicate of an existing command (same content = same command).
        """
        self._guard_not_halted("propose")
        actor = _require_actor(actor, "proposer")
        if polygon_ref is not None:
            _require_string(
                polygon_ref,
                "polygon_ref_ill_formed",
                "polygon_ref must be a non-empty BoundaryVersion IRI (WS4) or None "
                "while geometry is pending",
            )
        if not isinstance(prescription, dict) or not prescription:
            raise ActuationGap(
                "prescription_missing",
                "prescription payload must be a non-empty JSON object",
            )
        for key in PRESCRIPTION_STAMP_KEYS:
            if not _stamp_present(prescription.get(key)):
                raise ActuationGap(
                    f"{key}_missing",
                    f"prescription must carry a non-empty {key!r} stamp "
                    "(native support travels with every value)",
                )
        command_id = command_id_for(
            prescription=prescription, polygon_ref=polygon_ref, proposer=actor["id"]
        )
        if any(
            record.get("type") == "command_event"
            and (record.get("event") or {}).get("command_id") == command_id
            for record in self._records
        ):
            raise IllegalTransition(
                "start",
                "proposed",
                f"command {command_id!r} already exists; identical proposals are "
                "one command — change the prescription, polygon_ref or proposer",
            )
        event = {
            "name": "propose",
            "command_id": command_id,
            "from_state": None,
            "to_state": "proposed",
            "actor": actor,
            "polygon_ref": polygon_ref,
            "prescription": copy.deepcopy(prescription),
        }
        return self._append("command_event", event, at)

    def approve(self, command_id, *, approver, at) -> dict:
        """proposed -> approved. Requires a human approver ≠ the proposer."""
        self._guard_not_halted("approve")
        cid = _require_string(command_id, "command_id_missing", "command_id required")
        approver = _require_actor(approver, "approver")
        if approver["kind"] != "human":
            raise ActuationRefusal(
                "approver_must_be_human",
                "approval authority rests with the human risk owner "
                "(docs/actuation-interface-spec.md §5)",
            )
        current = self.state_of(cid)
        if current != "proposed":
            raise IllegalTransition(current, "approved")
        proposer = self._event_of_name(cid, "propose")["actor"]
        if approver["id"] == proposer["id"]:
            raise ActuationRefusal(
                "approver_equals_proposer",
                f"command {cid!r} may not be approved by its proposer "
                f"({proposer['id']!r}); four-eyes separation is mandatory",
            )
        self._check_monotonic(cid, at, "approve")
        event = {
            "name": "approve",
            "command_id": cid,
            "from_state": "proposed",
            "to_state": "approved",
            "actor": approver,
        }
        return self._append("command_event", event, at)

    def dispatch(self, command_id, *, actor, receipt, at) -> dict:
        """approved -> dispatched. Requires a non-empty dispatch receipt blob."""
        self._guard_not_halted("dispatch")
        cid = _require_string(command_id, "command_id_missing", "command_id required")
        actor = _require_actor(actor, "dispatcher")
        current = self.state_of(cid)
        if current != "approved":
            raise IllegalTransition(current, "dispatched")
        self._check_monotonic(cid, at, "dispatch")
        kept = _require_receipt(
            receipt,
            "dispatch_receipt_missing",
            "dispatch",
        )
        event = {
            "name": "dispatch",
            "command_id": cid,
            "from_state": "approved",
            "to_state": "dispatched",
            "actor": actor,
            "receipt": kept,
        }
        return self._append("command_event", event, at)

    def acknowledge(self, command_id, *, actor, receipt, at) -> dict:
        """dispatched -> acknowledged. Requires an acknowledgement receipt."""
        self._guard_not_halted("acknowledge")
        cid = _require_string(command_id, "command_id_missing", "command_id required")
        actor = _require_actor(actor, "acknowledger")
        current = self.state_of(cid)
        if current != "dispatched":
            raise IllegalTransition(current, "acknowledged")
        self._check_monotonic(cid, at, "acknowledge")
        kept = _require_receipt(receipt, "ack_receipt_missing", "acknowledgement")
        event = {
            "name": "acknowledge",
            "command_id": cid,
            "from_state": "dispatched",
            "to_state": "acknowledged",
            "actor": actor,
            "receipt": kept,
        }
        return self._append("command_event", event, at)

    def void(self, command_id, *, reason, actor, at) -> dict:
        """Any non-voided state -> voided. Reason mandatory; history is kept."""
        cid = _require_string(command_id, "command_id_missing", "command_id required")
        actor = _require_actor(actor, "voider")
        motive = _require_string(
            reason, "void_reason_missing", "voiding requires a non-empty reason"
        )
        current = self.state_of(cid)
        if current == "voided":
            raise IllegalTransition(current, "voided")
        self._check_monotonic(cid, at, "void")
        event = {
            "name": "void",
            "command_id": cid,
            "from_state": current,
            "to_state": "voided",
            "actor": actor,
            "reason": motive,
        }
        return self._append("command_event", event, at)

    # -- HALT (doctrine §6: kill switch, written by the human risk owner) ----

    def halt(self, *, reason, actor, at) -> dict:
        """Raise an emergency HALT; freezes propose/approve/dispatch/acknowledge."""
        actor = _require_actor(actor, "halter")
        if actor["kind"] != "human":
            raise ActuationRefusal(
                "halt_actor_must_be_human",
                "only the human risk owner may raise an emergency HALT (doctrine §6)",
            )
        motive = _require_string(
            reason, "halt_reason_missing", "a HALT without a reason is not auditable"
        )
        if self.halted():
            raise ActuationRefusal(
                "halt_already_active", "a HALT is already active on this ledger"
            )
        event = {
            "name": "halt",
            "halt_action": "raise",
            "actor": actor,
            "reason": motive,
        }
        return self._append("halt", event, at)

    def lift_halt(self, *, reason, actor, at) -> dict:
        """Lift an active HALT (risk owner's explicit decision, on the record)."""
        actor = _require_actor(actor, "halter")
        if actor["kind"] != "human":
            raise ActuationRefusal(
                "halt_actor_must_be_human",
                "only the human risk owner may lift an emergency HALT (doctrine §6)",
            )
        motive = _require_string(
            reason, "lift_reason_missing", "lifting a HALT requires a reason"
        )
        if not self.halted():
            raise ActuationRefusal("halt_not_active", "no HALT is currently active")
        event = {
            "name": "halt",
            "halt_action": "lift",
            "actor": actor,
            "reason": motive,
        }
        return self._append("halt", event, at)

    # -- integrity -----------------------------------------------------------

    def verify_chain(self) -> dict:
        """Recompute the whole chain; return ``{"ok", "records", "problems"}``.

        Detects: edited record bodies (entry hash mismatch), rewritten link
        hashes / reordering (prev mismatch), deleted records (seq break),
        structurally impossible events, and lifecycle histories that violate
        the state machine even when their hashes were re-forged.
        """
        problems: list[str] = []
        prev = GENESIS_HASH
        command_state: dict[str, str] = {}
        for index, record in enumerate(self._records, start=1):
            record = record if isinstance(record, dict) else {}
            if record.get("seq") != index:
                problems.append(
                    f"seq broken at record {index}: {record.get('seq')!r}"
                )
            if record.get("prev") != prev:
                problems.append(
                    f"prev hash mismatch at record {index} (chain edited or reordered)"
                )
            body = {
                "type": record.get("type"),
                "ts": record.get("ts"),
                "event": record.get("event"),
            }
            expected = _hash_body(record.get("prev", ""), body)
            if record.get("hash") != expected:
                problems.append(
                    f"entry hash mismatch at record {index} (record content was altered)"
                )
            problems.extend(self._structural_problems(index, record))
            problems.extend(
                self._replay_problems(index, record, command_state)
            )
            prev = record.get("hash", prev)
        return {"ok": not problems, "records": len(self._records), "problems": problems}

    @staticmethod
    def _structural_problems(index: int, record: dict) -> list[str]:
        if record.get("type") not in CommandLedger.RECORD_TYPES:
            return [f"unknown record type at record {index}: {record.get('type')!r}"]
        event = record.get("event")
        if not isinstance(event, dict):
            return [f"event missing at record {index}"]
        if record["type"] == "command_event":
            if event.get("name") not in _LIFECYCLE_EVENTS:
                return [f"unknown event name at record {index}: {event.get('name')!r}"]
            to_state = event.get("to_state")
            if to_state not in COMMAND_STATES:
                return [
                    f"unknown to_state at record {index}: {to_state!r}"
                ]
        elif event.get("halt_action") not in CommandLedger.HALT_ACTIONS:
            return [
                f"unknown halt_action at record {index}: "
                f"{event.get('halt_action')!r}"
            ]
        return []

    @staticmethod
    def _replay_problems(
        index: int, record: dict, command_state: dict[str, str]
    ) -> list[str]:
        if record.get("type") != "command_event":
            return []
        event = record.get("event") or {}
        cid = event.get("command_id")
        if not isinstance(cid, str) or not cid:
            return [f"command_id missing at record {index}"]
        name = event.get("name")
        current = command_state.get(cid)
        if name == "propose":
            if current is not None:
                return [
                    f"duplicate proposal at record {index}: command {cid!r} "
                    "already proposed"
                ]
            command_state[cid] = "proposed"
            return []
        if name == "void":
            # (D9 fix, ws/fix/actuation-ledger) void is decided HERE, before
            # any from-state lookup: _TRANSITION_FROM has no "void" key and
            # consulting it for a legal void event used to raise KeyError,
            # killing verify_chain on any chain that contained voiding.
            if current is None:
                return [
                    f"void for unproposed command {cid!r} at record {index} "
                    "(forged or reordered history)"
                ]
            if current == "voided":
                return [f"illegal transition at record {index}: voided -> voided"]
            command_state[cid] = "voided"
            return []
        expected_from = _TRANSITION_FROM.get(name)
        if expected_from is None:
            return [f"unknown event name at record {index}: {name!r}"]
        if current != expected_from:
            return [
                f"illegal transition at record {index}: "
                f"{current!r} -> {event['to_state']!r} for command {cid!r}"
            ]
        command_state[cid] = event["to_state"]
        return []

    # -- persistence ----------------------------------------------------------

    def to_jsonl_text(self) -> str:
        """Whole ledger as canonical JSONL (one record per line)."""
        return "".join(
            json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
            for record in self._records
        )

    def save(self, path) -> None:
        """Write JSONL to ``path``. Offline; the parent directory must exist."""
        try:
            Path(path).write_text(self.to_jsonl_text(), encoding="utf-8")
        except OSError as exc:
            raise ActuationGap(
                "ledger_write_failed",
                f"could not persist ledger to {path!r}: {exc}",
                "create the directory first; the ledger never fabricates a write",
            ) from exc

    @classmethod
    def from_jsonl_text(cls, text: str) -> "CommandLedger":
        """Load JSONL and verify the whole chain before trusting it."""
        records: list[dict] = []
        for lineno, line in enumerate(text.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ActuationGap(
                    "ledger_line_unparsable",
                    f"line {lineno}: {exc}",
                ) from exc
        ledger = cls(records)
        report = ledger.verify_chain()
        if not report["ok"]:
            raise ActuationRefusal(
                "ledger_verify_failed",
                "loaded chain failed verification: " + "; ".join(report["problems"]),
                "restore from a verified backup; a tampered chain is never "
                "silently accepted",
            )
        return ledger

    @classmethod
    def from_path(cls, path) -> "CommandLedger":
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            raise ActuationGap(
                "ledger_read_failed", f"could not read {path!r}: {exc}"
            ) from exc
        return cls.from_jsonl_text(text)

    # -- misc -----------------------------------------------------------------

    def _event_of_name(self, command_id: str, name: str) -> dict:
        for record in self._records:
            event = record.get("event") or {}
            if (
                record.get("type") == "command_event"
                and event.get("command_id") == command_id
                and event.get("name") == name
            ):
                return event
        raise ActuationGap(
            "unknown_command",
            f"no {name!r} event found for command {command_id!r}",
        )
