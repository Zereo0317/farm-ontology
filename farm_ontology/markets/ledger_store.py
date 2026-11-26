"""Independently protected persistence for the finance-controls chain (G2/G5).

``farm_ontology.markets.finance_controls`` is a pure model: it records the
hedge-intent lifecycle in memory and its module contract demands that callers
persist the exported event sequence "in an independently protected ledger
before treating it as an operational record".  Until this adapter existed
that demand was unanswered (audit gap G2), and ``HedgeIntentLedger._replay``
could therefore only re-accept PROPOSED events: approvals, cancellations and
halts replay as bare digests with no persisted signature material (G5).

This module closes both gaps with one seam used by two backends:

- :class:`JsonFileLedgerStore` — append-only JSONL per ledger kind, fsync'd
  on every append, holding an in-memory index of the last hash per stream.
- :class:`GcsLedgerStore` — the same interface over the
  ``farm_ontology.record_store`` GCS seam: one create-only object per entry
  (``write_once`` ⇒ ``ifGenerationMatch=0``), so server-side generation
  preconditioning makes every entry immutable; a racing writer is refused,
  never silently merged.

Interface (both backends, and what any third backend must provide)::

    append(kind, event, *, intent_payload=None, witness=None) -> (sequence, entry_hash)
    replay(kind, from_seq=1) -> iterator of StoredLedgerEntry
    last_hash(kind) -> str

Stored shape — one JSON object per entry::

    {
      "version": 1,
      "kind": "hedge-intent",
      "sequence": N,                  # store/model sequence, kept aligned
      "previous_entry_hash": "...",   # entry-level chain (genesis "0"*64)
      "event_type": "proposed|approved-manual|cancelled|halted",
      "event": {...IntentEvent payload + event_sha256...},   # model chain
      "intent_payload": {...}|None,   # PROPOSED only: rebuilds HedgeOrderIntent
      "witness": {...}|None,          # non-PROPOSED: the SIGNING PAYLOAD of
                                      # every SignedEvidence behind the event,
                                      # including each detached signature_hex
      "entry_hash": "..."             # canonical sha256 of the entry above
    }

Two tamper barriers, layered:

1. **Bytes** — ``entry_hash`` recomputes canonically and every entry links to
   the previous one; any mutation of stored bytes breaks the chain.  A
   partial ``replay(from_seq=k)`` still walks the whole stream first, so
   tamper before ``k`` is a refusal too (fail closed).
2. **Meaning** — on model replay (:func:`collect_store_history` feeding
   ``HedgeIntentLedger``) the persisted witness is rebuilt into
   ``SignedEvidence`` records, each record's surviving ``signing_payload``
   bytes are compared with the rebuilt payload, purpose/subject/time-window
   bindings are re-checked at the event moment, and the recomputed evidence
   digest must reproduce the event's ``evidence_sha256``.  With an optional
   ``verifier`` every persisted signature is re-verified.  Hash chains catch
   accidental corruption; the persisted signing payloads are what make an
   authenticated full-lifecycle replay possible at all (G5).

Scope honesty, stated up front: a store hash chain is recomputable by an
attacker who rewrites history wholesale.  What such a rewrite cannot produce
are valid Ed25519-shaped signatures for new payloads; passing a trusted
``verifier`` into replay is what separates "internally consistent" from
"authored by the recorded issuers".  The pure model still documents that a
hash chain alone detects accidental corruption, not a forged reviewer.

House rules: stdlib only; no wall-clock reads (every timestamp rides the
model's injected aware ``at``); a failed append leaves the stream untouched
and raises (never a half-written entry presented as durable); kinds are
validated identifiers so streams cannot traverse paths; exactly one writer
per stream per process — two writers colliding on ``write_once`` is a loud
refusal, not a lost update.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Iterator, Mapping, Protocol

from farm_ontology.markets import finance_controls
from farm_ontology.markets.finance_controls import (
    DEFAULT_HEDGE_LEDGER_KIND,
    EventType,
    HedgeIntentLedger,
    HedgeOrderIntent,
    IntentEvent,
    SignatureVerifier,
    SignedEvidence,
    canonical_digest,
    expected_witness_roles,
)
from farm_ontology.record_store import GcsBackend

#: Hash of the imaginary entry before the first one of a stream.
GENESIS_ENTRY_HASH = "0" * 64

#: Stored-entry schema version; a foreign version is a refusal, not a guess.
LEDGER_ENTRY_VERSION = 1

#: GCS object prefix when the adapter builds its own record-store backend.
FINANCE_LEDGER_GCS_PREFIX = "finance-ledgers"

_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_KIND = re.compile(r"^[a-z0-9][a-z0-9._-]{0,62}$")
_SEQUENCE_NAME = re.compile(r"^[0-9]{8}$")

_ENTRY_KEYS = frozenset({
    "version", "kind", "sequence", "previous_entry_hash", "event_type",
    "event", "intent_payload", "witness", "entry_hash",
})
_INTENT_EVENT_KEYS = frozenset({
    "sequence", "intent_id", "intent_sha256", "event_type", "at", "actor",
    "evidence_sha256", "previous_sha256",
})
_EVENT_RECORD_KEYS = _INTENT_EVENT_KEYS | {"event_sha256"}


__all__ = [
    "DEFAULT_HEDGE_LEDGER_KIND",
    "FINANCE_LEDGER_GCS_PREFIX",
    "GENESIS_ENTRY_HASH",
    "GcsLedgerStore",
    "JsonFileLedgerStore",
    "LEDGER_ENTRY_VERSION",
    "LedgerStore",
    "StoredLedgerEntry",
    "StoreBackedHedgeIntentLedger",
    "collect_store_history",
    "decode_entry",
    "encode_entry",
    "promote_intent",
    "replay_intent_ledger",
    "record_intent_proposal",
]


class LedgerStore(Protocol):
    """The seam both backends satisfy (documented, duck-typed at runtime)."""

    def append(self, kind: str, event: IntentEvent, *,
               intent_payload: dict | None = None,
               witness: dict | None = None) -> tuple[int, str]:
        """Persist one lifecycle event; return its (sequence, entry_hash)."""
        ...

    def replay(self, kind: str, from_seq: int = 1) -> Iterator["StoredLedgerEntry"]:
        """Yield stored entries from ``from_seq`` after validating the chain."""
        ...

    def last_hash(self, kind: str) -> str:
        """Last entry hash of a stream; GENESIS_ENTRY_HASH when empty."""
        ...


def _valid_kind(kind: object) -> str:
    if not isinstance(kind, str) or not _KIND.fullmatch(kind) or ".." in kind:
        raise ValueError("ledger kind must be a short dotted/dashed lowercase identifier")
    return kind


def _valid_hash(value: object, name: str) -> str:
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        raise ValueError(f"ledger entry {name} must be a lowercase SHA-256 hex digest")
    return value


def _valid_sequence(value: object, name: str) -> int:
    if type(value) is not int or value < 1:
        raise ValueError(f"ledger {name} must be a positive integer")
    return value


@dataclass(frozen=True)
class StoredLedgerEntry:
    """One decoded, internally validated store entry."""

    sequence: int
    entry_hash: str
    previous_entry_hash: str
    event: IntentEvent
    intent_payload: dict | None
    witness: dict | None


# ----------------------------------------------------------------------
# entry codec: stored JSON <-> validated model objects
# ----------------------------------------------------------------------


def encode_entry(
    kind: str,
    sequence: int,
    previous_entry_hash: str,
    event: IntentEvent,
    intent_payload: dict | None,
    witness: dict | None,
) -> tuple[dict, str]:
    """Build the stored entry document and its canonical hash."""
    kind = _valid_kind(kind)
    sequence = _valid_sequence(sequence, "sequence")
    _valid_hash(previous_entry_hash, "previous_entry_hash")
    if not isinstance(event, IntentEvent):
        raise ValueError("ledger store records IntentEvent events")
    body = {
        "version": LEDGER_ENTRY_VERSION,
        "kind": kind,
        "sequence": sequence,
        "previous_entry_hash": previous_entry_hash,
        "event_type": event.event_type.value,
        "event": {**event.payload(), "event_sha256": event.event_sha256},
        "intent_payload": intent_payload,
        "witness": witness,
    }
    entry_hash = canonical_digest(body)
    return {**body, "entry_hash": entry_hash}, entry_hash


def _entry_document_hash(document: Mapping[str, object]) -> str:
    body = {key: value for key, value in document.items() if key != "entry_hash"}
    return canonical_digest(body)


def decode_entry(raw: Mapping[str, object]) -> StoredLedgerEntry:
    """Strictly decode one stored entry; refuse anything unexpected.

    Validates the entry shape, rebuilds the ``IntentEvent``, re-derives both
    the event hash and the entry hash, and binds the store chain link to the
    model chain link.  Raise ``ValueError`` on any mismatch.
    """
    if not isinstance(raw, Mapping) or frozenset(raw) != _ENTRY_KEYS:
        raise ValueError("stored ledger entry has an unexpected shape")
    if raw["version"] != LEDGER_ENTRY_VERSION or type(raw["version"]) is not int:
        raise ValueError(f"unsupported stored ledger entry version: {raw['version']!r}")
    kind = _valid_kind(raw["kind"])
    sequence = _valid_sequence(raw["sequence"], "sequence")
    previous_entry_hash = _valid_hash(raw["previous_entry_hash"], "previous_entry_hash")
    entry_hash = _valid_hash(raw["entry_hash"], "entry_hash")
    event_type = raw["event_type"]
    if event_type not in {member.value for member in EventType}:
        raise ValueError(f"stored ledger entry has an unknown event type: {event_type!r}")
    event = raw["event"]
    if not isinstance(event, Mapping) or frozenset(event) != _EVENT_RECORD_KEYS:
        raise ValueError("stored ledger event record has an unexpected shape")
    if event["event_type"] != event_type or event["sequence"] != sequence:
        raise ValueError("stored ledger entry disagrees with its embedded event")
    if event["event_sha256"] != canonical_digest(
        {key: value for key, value in event.items() if key != "event_sha256"}
    ):
        raise ValueError(f"{kind}: stored event #{sequence} hash does not match its content")
    # NOTE: previous_entry_hash (store-entry chain) and event.previous_sha256
    # (model event chain) are two DIFFERENT hash domains; they coincide only
    # at the genesis entry.  The model chain is validated by
    # HedgeIntentLedger._replay; the entry chain by each backend's walk.
    intent_payload = raw["intent_payload"]
    if intent_payload is not None and not isinstance(intent_payload, Mapping):
        raise ValueError("stored intent payload must be an object or null")
    witness = raw["witness"]
    if witness is not None and not isinstance(witness, Mapping):
        raise ValueError("stored witness must be an object or null")
    if entry_hash != _entry_document_hash(raw):
        raise ValueError(f"{kind}: stored ledger entry #{sequence} hash does not match its content")
    rebuilt = IntentEvent(
        sequence=event["sequence"],
        intent_id=event["intent_id"],
        intent_sha256=event["intent_sha256"],
        event_type=EventType(event["event_type"]),
        at=datetime.fromisoformat(str(event["at"])),
        actor=event["actor"],
        evidence_sha256=event["evidence_sha256"],
        previous_sha256=event["previous_sha256"],
        event_sha256=event["event_sha256"],
    )
    return StoredLedgerEntry(
        sequence=sequence,
        entry_hash=entry_hash,
        previous_entry_hash=previous_entry_hash,
        event=rebuilt,
        intent_payload=dict(intent_payload) if intent_payload is not None else None,
        witness=dict(witness) if witness is not None else None,
    )


def _advance_chain(kind: str, previous: str, expected: int, entry: StoredLedgerEntry) -> str:
    """Chain guard shared by both backends; returns the next previous hash."""
    if entry.sequence != expected:
        raise ValueError(
            f"{kind}: ledger sequence break: expected {expected}, found {entry.sequence}"
        )
    if entry.previous_entry_hash != previous:
        raise ValueError(
            f"{kind}: ledger entry #{entry.sequence} does not continue the previous entry hash"
        )
    return entry.entry_hash


def _prepare_append(
    kind: object,
    event: IntentEvent,
    intent_payload: dict | None,
    witness: dict | None,
) -> str:
    """Shared append-side checks; returns the validated kind.

    A proposal must persist its intent payload (it carries no witness — its
    evidence IS the artifact digest); every other lifecycle event must
    persist the witness of what was signed.  The intent payload is rebuilt
    eagerly so a payload that would not reproduce the recorded fingerprint
    can never become durable.
    """
    kind = _valid_kind(kind)
    if not isinstance(event, IntentEvent):
        raise ValueError("ledger store records IntentEvent events")
    if event.event_type is EventType.PROPOSED:
        if witness not in (None, {}):
            raise ValueError("a proposal carries no witness; its evidence is the artifact digest")
        if intent_payload is None:
            raise ValueError("a proposal must persist its intent payload for full-lifecycle replay")
    else:
        if intent_payload is not None:
            raise ValueError("only a proposal persists an intent payload")
        if not witness:
            raise ValueError("a non-proposed lifecycle event must persist its signing evidence")
        if frozenset(witness) != frozenset(expected_witness_roles(event.event_type)):
            raise ValueError("witness roles do not match the lifecycle event type")
    if intent_payload is not None:
        rebuilt = HedgeOrderIntent.from_payload(dict(intent_payload))
        if rebuilt.fingerprint != event.intent_sha256:
            raise ValueError("persisted intent payload does not reproduce the recorded fingerprint")
    return kind


# ----------------------------------------------------------------------
# backend 1: fsync'd append-only JSONL
# ----------------------------------------------------------------------


class _StreamState:
    """In-memory index of one stream: entry count and last entry hash."""

    __slots__ = ("count", "last_hash", "invalid")

    def __init__(self) -> None:
        self.count = 0
        self.last_hash = GENESIS_ENTRY_HASH
        # Poisoned-stream flag (F3): set when an append's readback detects a
        # race; every further append refuses until the stream is repaired.
        self.invalid = False


class JsonFileLedgerStore:
    """Append-only JSONL per ledger kind, fsync'd on every append.

    Layout: ``<root>/ledgers/<kind>.jsonl``, one JSON entry object per line,
    lines never rewritten or deleted.  The index of the last hash per stream
    is kept in memory, rebuilt by a full validated scan the first time a
    kind is touched in this process, and treated as a cache only — the JSONL
    itself is the source of truth, so a reader always re-walks the file (and
    thereby the whole chain) before trusting it.  Single-writer per stream
    per process; a torn or duplicated line from a crashed or racing writer
    is a loud refusal on the next read, never a guessed repair.
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._states: dict[str, _StreamState] = {}
        # Serialises read-last/append/fsync/index-update within one process
        # (the documented single-writer contract, now enforced for the
        # shared-instance case; cross-process racing still refused by the
        # post-write readback below — loudly, not silently).
        import threading

        self._lock = threading.Lock()

    def describe(self) -> dict:
        return {"backend": "jsonl", "root": str(self.root)}

    # ---- internals -----------------------------------------------------

    def _kind_path(self, kind: str) -> Path:
        return self.root / "ledgers" / f"{kind}.jsonl"

    def _scan(self, kind: str) -> Iterator[StoredLedgerEntry]:
        """Fully validate a stream and yield its entries in order."""
        path = self._kind_path(kind)
        if not path.is_file():
            return
        previous = GENESIS_ENTRY_HASH
        expected = 1
        with open(path, "rb") as handle:
            for number, raw_line in enumerate(handle, 1):
                if not raw_line.endswith(b"\n"):
                    raise ValueError(
                        f"{kind}: ledger line {number} is truncated; the stream needs repair before replay"
                    )
                line = raw_line.strip()
                if not line:
                    raise ValueError(f"{kind}: blank ledger line {number}")
                try:
                    raw = json.loads(line.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as error:
                    raise ValueError(f"{kind}: unreadable ledger line {number} ({error})") from error
                entry = decode_entry(raw)
                previous = _advance_chain(kind, previous, expected, entry)
                expected += 1
                yield entry

    def _state(self, kind: str) -> _StreamState:
        state = self._states.get(kind)
        if state is None:
            state = _StreamState()
            for entry in self._scan(kind):
                state.count, state.last_hash = entry.sequence, entry.entry_hash
            self._states[kind] = state
        return state

    # ---- the seam ------------------------------------------------------

    def append(self, kind: str, event: IntentEvent, *,
               intent_payload: dict | None = None,
               witness: dict | None = None) -> tuple[int, str]:
        kind = _prepare_append(kind, event, intent_payload, witness)
        # F1 (round-2 audit): the WHOLE logical claim — index read, sequence
        # check, encoding, write, readback and index update — happens under
        # one lock. The round-1 fix locked only the physical write, letting
        # two writers both "own" sequence N and durably duplicate it with
        # zero exceptions.
        with self._lock:
            state = self._state(kind)
            if getattr(state, "invalid", False):
                raise RuntimeError(
                    f"ledger stream {kind!r} is poisoned by a detected "
                    "append race — repair the stream (replay + truncate to "
                    "the last valid entry) before appending again"
                )
            sequence = state.count + 1
            if event.sequence != sequence:
                raise ValueError(
                    f"ledger stream {kind!r} expects sequence {sequence}, got {event.sequence}"
                )
            document, _ = encode_entry(
                kind, sequence, state.last_hash, event, intent_payload, witness
            )
            line = json.dumps(
                document, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8") + b"\n"
            path = self._kind_path(kind)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "ab") as stream:
                stream.write(line)
                stream.flush()
                import os

                os.fsync(stream.fileno())
            # F2 race guard: verify OUR line really is the file's last line;
            # a mismatch poisons the stream (F3) — the next append refuses
            # until a human/tool repairs it — exactly what this error
            # message has promised since round 1.
            size = os.path.getsize(path)
            with open(path, "rb") as check:
                if size > len(line):
                    check.seek(size - len(line))
                tail = check.read()
            if tail != line:
                state.invalid = True
                raise RuntimeError(
                    f"ledger append raced on {kind!r}: our entry #{sequence} "
                    "is not the file's last line — the stream is now marked "
                    "invalid and further appends refuse until repair"
                )
            state.count, state.last_hash = sequence, document["entry_hash"]
            return sequence, document["entry_hash"]

    def replay(self, kind: str, from_seq: int = 1) -> Iterator[StoredLedgerEntry]:
        from_seq = _valid_sequence(from_seq, "from_seq")
        kind = _valid_kind(kind)
        for entry in self._scan(kind):
            if entry.sequence >= from_seq:
                yield entry

    def last_hash(self, kind: str) -> str:
        return self._state(_valid_kind(kind)).last_hash


# ----------------------------------------------------------------------
# backend 2: create-only GCS objects over the record-store seam
# ----------------------------------------------------------------------


class GcsLedgerStore:
    """The same seam, one create-only object per entry, via ``record_store``.

    Entries live at ``<prefix>/kinds/<kind>/entries/NNNNNNNN.json`` and are
    written with ``GcsBackend.write_once`` — the JSON API precondition
    ``ifGenerationMatch=0`` makes every entry create-only, so a losing
    writer raises instead of replacing history.  Appends derive the next
    sequence from a listing (zero-padded names sort numerically) and parse
    the current last entry for its hash; like the JSONL store the index is
    an in-memory view of immutable truth below it.  Reads never trust a
    cached count: every operation lists first.
    """

    def __init__(self, bucket: str, prefix: str = FINANCE_LEDGER_GCS_PREFIX,
                 *, backend: GcsBackend | None = None) -> None:
        if backend is None:
            if not bucket or not str(bucket).strip():
                raise ValueError("GcsLedgerStore requires a bucket name")
            backend = GcsBackend(str(bucket), prefix)
        self._backend = backend
        self._states: dict[str, _StreamState] = {}

    def describe(self) -> dict:
        return {**self._backend.describe(), "store": "gcs-ledger"}

    # ---- internals -----------------------------------------------------

    def _entries_rel(self, kind: str) -> str:
        return f"kinds/{kind}/entries"

    def _entry_rel(self, kind: str, sequence: int) -> str:
        return f"kinds/{kind}/entries/{sequence:08d}.json"

    def _sequences(self, kind: str) -> list[int]:
        """Listing-derived sequence numbers; gaps and duplicates are refusals."""
        rels = self._backend.list_paths(self._entries_rel(kind), "*.json")
        found: list[int] = []
        for index, rel in enumerate(rels, 1):
            name = PurePosixPath(rel).name
            if not name.endswith(".json") or not _SEQUENCE_NAME.fullmatch(name[:-5]):
                raise ValueError(f"{kind}: unexpected ledger object name {name!r}")
            sequence = int(name[:-5])
            if sequence != index:
                raise ValueError(f"{kind}: ledger object numbering gap at {name!r}")
            found.append(sequence)
        return found

    def _read_entry(self, kind: str, sequence: int) -> StoredLedgerEntry:
        data = self._backend.read_bytes(self._entry_rel(kind, sequence))
        try:
            raw = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"{kind}: unreadable ledger object #{sequence} ({error})") from error
        entry = decode_entry(raw)
        if entry.sequence != sequence:
            raise ValueError(
                f"{kind}: ledger object #{sequence} carries sequence {entry.sequence}"
            )
        return entry

    def _walk(self, kind: str) -> Iterator[StoredLedgerEntry]:
        previous = GENESIS_ENTRY_HASH
        expected = 1
        for sequence in self._sequences(kind):
            entry = self._read_entry(kind, sequence)
            previous = _advance_chain(kind, previous, expected, entry)
            expected += 1
            yield entry

    # ---- the seam ------------------------------------------------------

    def append(self, kind: str, event: IntentEvent, *,
               intent_payload: dict | None = None,
               witness: dict | None = None) -> tuple[int, str]:
        kind = _prepare_append(kind, event, intent_payload, witness)
        sequences = self._sequences(kind)
        sequence = len(sequences) + 1
        if event.sequence != sequence:
            raise ValueError(
                f"ledger stream {kind!r} expects sequence {sequence}, got {event.sequence}"
            )
        if sequences:
            previous = self._read_entry(kind, sequences[-1]).entry_hash
        else:
            previous = GENESIS_ENTRY_HASH
        document, _ = encode_entry(
            kind, sequence, previous, event, intent_payload, witness
        )
        payload = json.dumps(
            document, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        try:
            self._backend.write_once(self._entry_rel(kind, sequence), payload)
        except FileExistsError as error:
            raise FileExistsError(
                f"ledger stream {kind!r}: another writer appended entry #{sequence}; refusing to co-write"
            ) from error
        state = self._states.setdefault(kind, _StreamState())
        state.count, state.last_hash = sequence, document["entry_hash"]
        return sequence, document["entry_hash"]

    def replay(self, kind: str, from_seq: int = 1) -> Iterator[StoredLedgerEntry]:
        from_seq = _valid_sequence(from_seq, "from_seq")
        kind = _valid_kind(kind)
        for entry in self._walk(kind):
            if entry.sequence >= from_seq:
                yield entry

    def last_hash(self, kind: str) -> str:
        kind = _valid_kind(kind)
        state = self._states.setdefault(kind, _StreamState())
        sequences = self._sequences(kind)
        if not sequences:
            state.count, state.last_hash = 0, GENESIS_ENTRY_HASH
            return state.last_hash
        entry = self._read_entry(kind, sequences[-1])
        state.count, state.last_hash = entry.sequence, entry.entry_hash
        return entry.entry_hash


# ----------------------------------------------------------------------
# glue: hydration, persistence, and the promote transition
# ----------------------------------------------------------------------


def collect_store_history(store, kind: str = DEFAULT_HEDGE_LEDGER_KIND,
                          ) -> tuple[tuple[IntentEvent, ...], tuple[HedgeOrderIntent, ...], dict]:
    """Read a fully validated (events, intents, witnesses) history.

    The store chain is verified first (byte barrier); the meaning barrier —
    witness authentication of the recorded decisions — happens inside
    ``HedgeIntentLedger`` when these inputs are replayed into it.
    """
    kind = _valid_kind(kind)
    events: list[IntentEvent] = []
    intents: list[HedgeOrderIntent] = []
    witnesses: dict[int, dict] = {}
    for entry in store.replay(kind):
        events.append(entry.event)
        if entry.intent_payload is not None:
            intents.append(HedgeOrderIntent.from_payload(dict(entry.intent_payload)))
        if entry.witness:
            witnesses[entry.event.sequence] = entry.witness
    return tuple(events), tuple(intents), witnesses


class StoreBackedHedgeIntentLedger(HedgeIntentLedger):
    """A hedge-intent ledger hydrated from, and persisting to, a store.

    History replay — including witness authentication of approvals,
    cancellations and halts (the G5 close) — happens once at construction;
    afterwards every mutation is validated by the inherited pure-model
    methods and then appended to the store together with its intent payload
    or signing witness.  If the store refuses the write, the in-memory
    mutation rolls back (``attach_persistence`` contract), so the model can
    never outrun the independently protected ledger.
    """

    def __init__(self, store, kind: str = DEFAULT_HEDGE_LEDGER_KIND, *,
                 verifier: SignatureVerifier | None = None) -> None:
        events, intents, witnesses = collect_store_history(store, kind)
        super().__init__(events, intents, witnesses=witnesses, verifier=verifier)
        self._store = store
        self._kind = _valid_kind(kind)
        super().attach_persistence(self._persist_event, capture_signing_witness=True)

    @classmethod
    def replay_from_store(cls, store, kind: str = DEFAULT_HEDGE_LEDGER_KIND, *,
                          verifier: SignatureVerifier | None = None,
                          ) -> "StoreBackedHedgeIntentLedger":
        """Reconstruct the FULL lifecycle from a LedgerStore (gap G5)."""
        return cls(store, kind, verifier=verifier)

    @property
    def store(self):
        return self._store

    @property
    def kind(self) -> str:
        return self._kind

    def _persist_event(self, event: IntentEvent, intent: HedgeOrderIntent,
                       witness: dict | None) -> None:
        self._store.append(
            self._kind, event,
            intent_payload=(
                intent.payload() if event.event_type is EventType.PROPOSED else None
            ),
            witness=witness,
        )


def replay_intent_ledger(store, kind: str = DEFAULT_HEDGE_LEDGER_KIND, *,
                         verifier: SignatureVerifier | None = None,
                         ) -> StoreBackedHedgeIntentLedger:
    """Functional spelling of the store-backed replay."""
    return StoreBackedHedgeIntentLedger(store, kind, verifier=verifier)


def record_intent_proposal(intent: HedgeOrderIntent, store, *,
                           at: datetime, actor: str,
                           kind: str = DEFAULT_HEDGE_LEDGER_KIND) -> IntentEvent:
    """Append and durably record the PROPOSED event of a hedge intent."""
    ledger = StoreBackedHedgeIntentLedger(store, kind)
    return ledger.propose(intent, at=at, actor=actor)


def promote_intent(
    intent_id: str,
    approvals,
    store,
    *,
    intent: HedgeOrderIntent,
    cap_sheet: SignedEvidence | None = None,
    source_rights: SignedEvidence | None = None,
    kill_switch: SignedEvidence | None = None,
    at: datetime,
    actor: str,
    verifier: SignatureVerifier | None = None,
    kind: str = DEFAULT_HEDGE_LEDGER_KIND,
) -> IntentEvent:
    """Promote a PROPOSED hedge intent to APPROVED_MANUAL (gap G1).

    Three conditions, all enforced:

    1. The deployment-wide Class C switch must read ``open``
       (``finance_controls.CLASS_C_POLICY``).  While it is closed — the
       current production reality — this function refuses before anything
       is written, with the authoritative gate code
       ``class-c-policy-closed``.  Opening the switch belongs to the human
       gate, never to this call.
    2. The store must already hold a PROPOSED event binding exactly this
       intent fingerprint.
    3. The manual-approval gate must pass at ``at``: fresh, trusted,
       correctly-pledged cap sheet, source rights, kill-switch evidence and
       the two distinct human approvals (risk owner first), per
       ``evaluate_manual_approval``.

    On success the signed approval event — with the full signing witness of
    all five evidence records — is appended to the store and returned.
    """
    # Authoritative prod stance: the Class C switch wins before any evidence
    # is even looked at, and a refusal writes nothing.
    if finance_controls.CLASS_C_POLICY != "open":
        raise PermissionError(
            "class-c-policy-closed: Class C promotion is refused while the "
            "deployment switch (fd:classCPolicy) is closed; hedge intents stay "
            "PROPOSED and only the human gate may open the switch."
        )
    ledger = StoreBackedHedgeIntentLedger(store, kind, verifier=verifier)
    known = ledger.intent(intent_id)
    if known is None or known.fingerprint != intent.fingerprint:
        raise ValueError("promoted intent does not bind the proposed immutable content")
    if ledger.state(intent_id, at=at) is not finance_controls.IntentState.PROPOSED:
        raise ValueError("only a proposed intent can be promoted")
    return ledger.approve_for_manual_review(
        intent_id, at=at, actor=actor, cap_sheet=cap_sheet,
        source_rights=source_rights, kill_switch=kill_switch,
        approvals=approvals, verifier=verifier,
    )
