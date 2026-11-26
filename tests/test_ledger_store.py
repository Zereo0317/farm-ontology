"""Producer tests for the independently protected finance ledger store.

These tests fail on the pre-adapter code: there was no
``farm_ontology.markets.ledger_store``, no persisted signing payloads, and no
promote transition (audit gaps G1/G2/G5).  Offline and stdlib-only: the GCS
transport is an in-memory fake in the exact shape ``record_store`` tests
record from the JSON API.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
import urllib.parse
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.markets import rails
from farm_ontology.markets.finance_controls import (
    ApprovalBundle,
    ApprovalRole,
    EventType,
    EvidencePurpose,
    GENESIS_SHA256,
    HedgeIntentLedger,
    HedgeOrderIntent,
    IntentState,
    SignedEvidence,
)
from farm_ontology.markets.ledger_store import (
    GENESIS_ENTRY_HASH,
    GcsLedgerStore,
    JsonFileLedgerStore,
    StoredLedgerEntry,
    StoreBackedHedgeIntentLedger,
    collect_store_history,
    decode_entry,
    encode_entry,
    promote_intent,
)
from farm_ontology.record_store import GcsBackend

AT = datetime(2026, 11, 25, 12, tzinfo=timezone.utc)
SIG_PLACEHOLDER = "0" * 128
BUCKET = "farm-seges-ai-records"


def fake_signature(issuer: str, payload: bytes) -> str:
    return hashlib.sha512(issuer.encode("utf-8") + b":" + payload).hexdigest()


def verifier(issuer: str, payload: bytes, signature: str) -> bool:
    return signature == fake_signature(issuer, payload)


def evidence(purpose, subject, issuer, claims, *, start=AT - timedelta(hours=1),
             end=AT + timedelta(days=1)) -> SignedEvidence:
    unsigned = SignedEvidence(
        purpose=purpose, subject_sha256=subject, issuer=issuer,
        issued_at=start, expires_at=end,
        claims=tuple(sorted(claims.items())), signature_hex=SIG_PLACEHOLDER,
    )
    return replace(unsigned, signature_hex=fake_signature(issuer, unsigned.signing_payload()))


def intent(**changes) -> HedgeOrderIntent:
    values = dict(
        intent_id="intent-001",
        artifact_sha256="a" * 64,
        instrument_family=rails.F_SHORT_CBOT_SOYBEAN_FUTURES,
        side="sell",
        quantity=Decimal("2"),
        quantity_unit="contracts",
        cap_sheet_sha256="b" * 64,
        rights_bundle_sha256="c" * 64,
        scope="public-feed-only",
        feeds=("exchange-settlement",),
        territory="JP-Hokkaido",
        uses_farmer_data=False,
        farmer_consent_grant_fingerprints=(),
        created_at=AT - timedelta(minutes=5),
        expires_at=AT + timedelta(hours=1),
    )
    values.update(changes)
    return HedgeOrderIntent(**values)


def approval_evidence(value):
    cap = evidence(
        EvidencePurpose.RISK_CAP_SHEET, value.cap_sheet_sha256, "risk-alice",
        {
            "role": ApprovalRole.RISK_OWNER.value,
            "specimen": "false",
            "quarter": "2026Q4",
            "instrument_family": value.instrument_family,
            "quantity_unit": value.quantity_unit,
            "max_order_quantity": "3",
            "period_start": (AT - timedelta(days=20)).isoformat(),
            "period_end": (AT + timedelta(days=70)).isoformat(),
        },
    )
    rights = evidence(
        EvidencePurpose.SOURCE_RIGHTS, value.rights_bundle_sha256, "licence-registry",
        {
            "status": "active", "purpose": "hedge", "scope": value.scope,
            "feeds": json.dumps(value.feeds, separators=(",", ":")),
            "territory": value.territory,
            "uses_farmer_data": "false",
            "instrument_family": value.instrument_family,
            "farmer_consent_grant_fingerprints": "[]",
        },
    )
    kill = evidence(
        EvidencePurpose.KILL_SWITCH, value.fingerprint, "independent-watchdog",
        {"halt_raised": "false"}, start=AT - timedelta(seconds=30),
    )
    approvals = ApprovalBundle(
        risk_owner=evidence(
            EvidencePurpose.INTENT_APPROVAL, value.fingerprint, "risk-alice",
            {"role": ApprovalRole.RISK_OWNER.value, "decision": "approve"},
        ),
        independent_reviewer=evidence(
            EvidencePurpose.INTENT_APPROVAL, value.fingerprint, "reviewer-bob",
            {"role": ApprovalRole.INDEPENDENT_REVIEWER.value, "decision": "approve"},
            start=AT - timedelta(minutes=59),
        ),
    )
    return cap, rights, kill, approvals


def halt_evidence(value) -> SignedEvidence:
    return evidence(
        EvidencePurpose.KILL_SWITCH, value.fingerprint, "independent-watchdog",
        {"halt_raised": "true"},
    )


AT1 = AT
AT2 = AT + timedelta(minutes=1)
AT3 = AT + timedelta(minutes=2)


class MemGcs:
    """In-memory GCS JSON API surface: list, create-only put, media read."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}
        self.token_calls = 0

    def token(self):
        self.token_calls += 1
        return "test-token", 3600

    def __call__(self, method, url, headers, body):
        parsed = urllib.parse.urlsplit(url)
        query = urllib.parse.parse_qs(parsed.query)
        if method == "POST" and parsed.path == f"/upload/storage/v1/b/{BUCKET}/o":
            name = query["name"][0]
            if query.get("ifGenerationMatch") == ["0"] and name in self.objects:
                return 412, {}, b"precondition failed"
            self.objects[name] = body
            return 200, {}, json.dumps({"name": name, "bucket": BUCKET}).encode("utf-8")
        if method == "GET" and parsed.path == f"/storage/v1/b/{BUCKET}/o":
            prefix = query["prefix"][0]
            limit = int(query.get("maxResults", ["1000"])[0])
            offset = int(query.get("pageToken", ["0"])[0])
            names = sorted(n for n in self.objects if n.startswith(prefix))
            window = names[offset:offset + limit]
            document = {"kind": "storage#objects"}
            if window:
                document["items"] = [
                    {"name": n, "bucket": BUCKET, "updated": "2026-11-25T00:00:00.000Z"}
                    for n in window
                ]
            following = offset + len(window)
            if following < len(names):
                document["nextPageToken"] = str(following)
            return 200, {}, json.dumps(document).encode("utf-8")
        match = urllib.parse.unquote(parsed.path).rsplit(f"/b/{BUCKET}/o/", 1)
        if len(match) == 2 and method == "GET":
            name = match[1]
            if name in self.objects and query.get("alt", [None])[0] == "media":
                return 200, {}, self.objects[name]
            missing = {"error": {"code": 404, "message": f"No such object: {name}"}}
            return 404, {}, json.dumps(missing).encode("utf-8")
        raise AssertionError(f"memory GCS unrouted: {method} {url}")


def gcs_store(mem: MemGcs | None = None, prefix: str = "finance-ledgers-test"):
    mem = mem or MemGcs()
    backend = GcsBackend(BUCKET, prefix, request_fn=mem, token_fn=mem.token)
    return mem, GcsLedgerStore(BUCKET, prefix, backend=backend)


class JsonStoreLifecycleTests(unittest.TestCase):
    """(a) Full-lifecycle replay from a store: propose → approve → halt."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = JsonFileLedgerStore(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _promote(self, value, approvals, cap, rights, kill):
        with patch("farm_ontology.markets.finance_controls.CLASS_C_POLICY", "open"):
            return promote_intent(
                value.intent_id, approvals, self.store, intent=value,
                cap_sheet=cap, source_rights=rights, kill_switch=kill,
                at=AT2, actor="reviewer-bob", verifier=verifier,
            )

    def test_full_lifecycle_replays_from_store_with_persisted_signatures(self):
        value = intent()
        cap, rights, kill, approvals = approval_evidence(value)
        ledger = StoreBackedHedgeIntentLedger(self.store)
        ledger.propose(value, at=AT1, actor="analyst-charlie")
        self.assertEqual(self.store.last_hash("hedge-intent") != GENESIS_ENTRY_HASH, True)

        approved = self._promote(value, approvals, cap, rights, kill)
        self.assertEqual(approved.event_type, EventType.APPROVED_MANUAL)

        halt_sig = halt_evidence(value)
        hydrated = StoreBackedHedgeIntentLedger(self.store, verifier=verifier)
        halted = hydrated.halt(
            value.intent_id, at=AT3, actor="independent-watchdog",
            kill_switch=halt_sig, verifier=verifier,
        )
        self.assertEqual(halted.event_type, EventType.HALTED)

        # Replay the FULL lifecycle from durable storage (G5 close).
        reborn = StoreBackedHedgeIntentLedger.replay_from_store(self.store, verifier=verifier)
        self.assertEqual(
            [(event.sequence, event.event_type) for event in reborn.events],
            [(1, EventType.PROPOSED), (2, EventType.APPROVED_MANUAL), (3, EventType.HALTED)],
        )
        self.assertEqual(reborn.state(value.intent_id, at=AT3), IntentState.HALTED)
        self.assertEqual(reborn.intents, (value,))
        witnesses = dict(reborn.signing_witnesses)
        self.assertEqual(sorted(witnesses), [2, 3])
        # The approval carries every signing payload, actor-verifiable:
        approval_witness = witnesses[2]
        self.assertEqual(
            sorted(approval_witness),
            ["cap-sheet", "independent-approval", "kill-switch",
             "risk-owner-approval", "source-rights"],
        )
        for role in ("risk-owner-approval", "independent-approval"):
            record = approval_witness[role]
            rebuilt = SignedEvidence(
                purpose=EvidencePurpose.INTENT_APPROVAL,
                subject_sha256=record["subject_sha256"],
                issuer=record["issuer"],
                issued_at=datetime.fromisoformat(record["issued_at"]),
                expires_at=datetime.fromisoformat(record["expires_at"]),
                claims=tuple((pair[0], pair[1]) for pair in record["claims"]),
                signature_hex=record["signature_hex"],
            )
            self.assertTrue(verifier(
                rebuilt.issuer, rebuilt.signing_payload(), rebuilt.signature_hex,
            ))
        self.assertEqual(
            {approval_witness["risk-owner-approval"]["issuer"],
             approval_witness["independent-approval"]["issuer"]},
            {"risk-alice", "reviewer-bob"},
        )
        halt_witness = witnesses[3]
        self.assertEqual(list(halt_witness), ["kill-switch"])
        self.assertEqual(halt_witness["kill-switch"]["claims"], [["halt_raised", "true"]])

        # Byte truth: the JSONL carries the archived signing payloads.
        lines = (Path(self.tmp.name) / "ledgers" / "hedge-intent.jsonl").read_text(
            encoding="utf-8",
        ).splitlines()
        self.assertEqual(len(lines), 3)
        second = json.loads(lines[1])
        self.assertEqual(second["event"]["event_type"], "approved-manual")
        self.assertIn("signing_payload_hex", second["witness"]["cap-sheet"])

    def test_store_chain_index_tracks_appended_entries(self):
        value = intent()
        StoreBackedHedgeIntentLedger(self.store).propose(value, at=AT1, actor="analyst-charlie")
        first_hash = self.store.last_hash("hedge-intent")
        value2 = intent(intent_id="intent-002", artifact_sha256="d" * 64,
                        cap_sheet_sha256="e" * 64, rights_bundle_sha256="f" * 64)
        StoreBackedHedgeIntentLedger(self.store).propose(value2, at=AT1, actor="analyst-charlie")
        second_hash = self.store.last_hash("hedge-intent")
        self.assertNotEqual(first_hash, second_hash)
        entries = list(self.store.replay("hedge-intent"))
        self.assertEqual([entry.sequence for entry in entries], [1, 2])
        self.assertEqual(entries[-1].entry_hash, second_hash)
        self.assertEqual(entries[0].previous_entry_hash, GENESIS_ENTRY_HASH)
        partial = list(self.store.replay("hedge-intent", from_seq=2))
        self.assertEqual([entry.sequence for entry in partial], [2])
        with self.assertRaises(ValueError):
            list(self.store.replay("hedge-intent", from_seq=0))
        with self.assertRaisesRegex(ValueError, "kind"):
            self.store.last_hash("../escape")
        with self.assertRaisesRegex(ValueError, "kind"):
            self.store.append("Bad_Kind", entries[0].event)

    def test_hydration_refuses_verifier_less_nonproposed_history(self):
        value = intent()
        cap, rights, kill, approvals = approval_evidence(value)
        ledger = StoreBackedHedgeIntentLedger(self.store)
        ledger.propose(value, at=AT1, actor="analyst-charlie")
        self._promote(value, approvals, cap, rights, kill)
        # Events+witnesses replayed WITHOUT trust config: fail closed.
        events, intents, witnesses = collect_store_history(self.store)
        with self.assertRaisesRegex(ValueError, "without a trusted verifier"):
            HedgeIntentLedger(events, intents, witnesses=witnesses)
        # And the old failure mode persists for bare recomputed hashes:
        proposal = events[0]
        with self.assertRaisesRegex(ValueError, "persisted signing evidence"):
            HedgeIntentLedger(
                (proposal, replace(
                    events[1], sequence=2, previous_sha256=proposal.event_sha256,
                )),
                intents=intents,
            )

    def test_rolling_back_failed_persistence_keeps_memory_consistent(self):
        value = intent()
        ledger = HedgeIntentLedger()

        def exploding_sink(event, persisted_intent, witness):
            raise RuntimeError("disk offline")

        ledger.attach_persistence(exploding_sink)
        with self.assertRaisesRegex(RuntimeError, "disk offline"):
            ledger.propose(value, at=AT1, actor="analyst-charlie")
        self.assertEqual(ledger.events, ())
        self.assertIsNone(ledger.intent(value.intent_id))
        self.assertIsNone(ledger.state(value.intent_id, at=AT1))
        # A healthy sink records witnesses for non-proposed events only.
        seen: list[tuple] = []
        healthy = HedgeIntentLedger()
        healthy.attach_persistence(lambda event, intent_, witness: seen.append(
            (event.event_type, None if witness is None else sorted(witness)),
        ))
        cap, rights, kill, approvals = approval_evidence(value)
        healthy.propose(value, at=AT1, actor="analyst-charlie")
        healthy._capture_witness = True
        from farm_ontology.markets.finance_controls import evaluate_manual_approval
        with patch("farm_ontology.markets.finance_controls.CLASS_C_POLICY", "open"):
            healthy.approve_for_manual_review(
                value.intent_id, at=AT2, actor="reviewer-bob", cap_sheet=cap,
                source_rights=rights, kill_switch=kill, approvals=approvals,
                verifier=verifier,
            )
        self.assertEqual(seen[0], (EventType.PROPOSED, None))
        self.assertEqual(seen[1][0], EventType.APPROVED_MANUAL)
        self.assertEqual(len(seen[1][1]), 5)


class TamperDetectionTests(unittest.TestCase):
    """(b) Tampered store entries are refused on replay."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "ledgers" / "hedge-intent.jsonl"
        self.store = JsonFileLedgerStore(Path(self.tmp.name))
        value = intent()
        cap, rights, kill, approvals = approval_evidence(value)
        StoreBackedHedgeIntentLedger(self.store).propose(value, at=AT1, actor="analyst-charlie")
        with patch("farm_ontology.markets.finance_controls.CLASS_C_POLICY", "open"):
            promote_intent(
                value.intent_id, approvals, self.store, intent=value,
                cap_sheet=cap, source_rights=rights, kill_switch=kill,
                at=AT2, actor="reviewer-bob", verifier=verifier,
            )
        self.lines = self.path.read_text(encoding="utf-8").splitlines()
        self.original = list(self.lines)

    def tearDown(self):
        self.tmp.cleanup()

    def _rewrite(self) -> None:
        self.path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")

    def test_tampered_event_bytes_break_the_chain(self):
        record = json.loads(self.lines[1])
        record["event"]["actor"] = "tamperer"
        self.lines[1] = json.dumps(record, sort_keys=True, separators=(",", ":"))
        self._rewrite()
        with self.assertRaisesRegex(ValueError, "#2 hash does not match its content"):
            StoreBackedHedgeIntentLedger.replay_from_store(self.store, verifier=verifier)

    def test_tampered_claim_inside_a_persisted_signature_breaks_authentication(self):
        record = json.loads(self.lines[1])
        claims = record["witness"]["independent-approval"]["claims"]
        record["witness"]["independent-approval"]["claims"] = [
            [key, "reject" if key == "decision" else value] for key, value in claims
        ]
        self.lines[1] = json.dumps(record, sort_keys=True, separators=(",", ":"))
        self._rewrite()
        with self.assertRaisesRegex(ValueError, "inconsistent|#2|authentication"):
            StoreBackedHedgeIntentLedger.replay_from_store(self.store, verifier=verifier)

    def test_swapped_wholesale_entries_still_bind_the_model_chain(self):
        # Same-entry-count reshuffle: the store-entry chain may be repaired by
        # an attacker, but the model's previous_sha256 links are derived from
        # event bytes and cannot absorb an order swap.
        self.lines[1], self.lines[0] = self.lines[0], self.lines[1]
        self._rewrite()
        with self.assertRaisesRegex(ValueError, "sequence break|does not continue"):
            StoreBackedHedgeIntentLedger.replay_from_store(self.store, verifier=verifier)

    def test_truncated_tail_line_is_a_refusal_not_a_guess(self):
        # Crash mid-append: the final newline never reached the disk.
        self.path.write_bytes(self.path.read_bytes()[:-1])
        with self.assertRaisesRegex(ValueError, "truncated"):
            list(self.store.replay("hedge-intent"))
        self.assertFalse(self.path.read_bytes().endswith(b"\n"))

    def test_tampered_intent_payload_changes_the_immutable_content(self):
        value = intent()
        event = StoreBackedHedgeIntentLedger(self.store, verifier=verifier).propose(
            value, at=AT1, actor="analyst-charlie",
        )
        stream = list(self.store.replay("hedge-intent"))
        self.assertEqual(stream[0].event, event)
        # Persisted payload drift is caught when the history is collected.
        _, intents, _ = collect_store_history(self.store)
        self.assertEqual(intents, (value,))
        with self.assertRaisesRegex(ValueError, "unexpected shape"):
            decode_entry({"version": 1})
    def test_append_refuses_payload_that_does_not_reproduce_the_fingerprint(self):
        value = intent()
        ledger = StoreBackedHedgeIntentLedger(self.store, verifier=verifier)
        ledger.propose(value, at=AT1, actor="analyst-charlie")
        proposal = ledger.events[0]
        forged_payload = {**value.payload(), "side": "buy"}
        store = JsonFileLedgerStore(Path(self.tmp.name) / "second")
        with self.assertRaisesRegex(ValueError, "does not reproduce"):
            store.append("hedge-intent", replace(proposal, sequence=1),
                         intent_payload=forged_payload)

    def test_encode_decode_round_trip_binding(self):
        value = intent()
        event = StoreBackedHedgeIntentLedger(self.store, verifier=verifier).propose(
            value, at=AT1, actor="analyst-charlie",
        )
        entries = list(self.store.replay("hedge-intent"))
        entry = entries[0]
        self.assertIsInstance(entry, StoredLedgerEntry)
        document, entry_hash = encode_entry(
            "hedge-intent", 1, GENESIS_ENTRY_HASH, event, value.payload(), None,
        )
        self.assertEqual(entry_hash, entry.entry_hash)
        self.assertEqual(document["entry_hash"], entry_hash)
        self.assertEqual(decode_entry(document).event, event)


class PromoteTransitionTests(unittest.TestCase):
    """(c)+(d) The promote transition and its closed-policy refusal."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = JsonFileLedgerStore(Path(self.tmp.name))
        self.value = intent()
        self.cap, self.rights, self.kill, self.approvals = approval_evidence(self.value)
        StoreBackedHedgeIntentLedger(self.store).propose(
            self.value, at=AT1, actor="analyst-charlie",
        )
        self.stream = Path(self.tmp.name) / "ledgers" / "hedge-intent.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def test_promote_refuses_while_class_c_policy_is_closed(self):
        # Production reality: CLASS_C_POLICY == 'closed' is the deployed
        # constant.  NOTHING is patched here — the refusal must come from the
        # authoritative switch, before any evidence is examined or written.
        from farm_ontology.policy import CLASS_C_POLICY as DEPLOYED
        self.assertEqual(DEPLOYED, "closed")
        before = self.stream.read_text(encoding="utf-8") if self.stream.exists() else ""
        with self.assertRaisesRegex(PermissionError, "class-c-policy-closed"):
            promote_intent(
                self.value.intent_id, self.approvals, self.store,
                intent=self.value, cap_sheet=self.cap, source_rights=self.rights,
                kill_switch=self.kill, at=AT2, actor="reviewer-bob", verifier=verifier,
            )
        after = self.stream.read_text(encoding="utf-8") if self.stream.exists() else ""
        self.assertEqual(before, after, "a closed-policy refusal must not write")

    def test_promote_happy_path_under_patched_open_policy_with_two_approvals(self):
        with patch("farm_ontology.markets.finance_controls.CLASS_C_POLICY", "open"):
            event = promote_intent(
                self.value.intent_id, self.approvals, self.store,
                intent=self.value, cap_sheet=self.cap, source_rights=self.rights,
                kill_switch=self.kill, at=AT2, actor="reviewer-bob", verifier=verifier,
            )
        self.assertEqual(event.event_type, EventType.APPROVED_MANUAL)
        self.assertEqual(event.actor, "reviewer-bob")
        hydrated = StoreBackedHedgeIntentLedger(self.store, verifier=verifier)
        self.assertEqual(hydrated.state(self.value.intent_id, at=AT2), IntentState.APPROVED_MANUAL)
        witness = dict(hydrated.signing_witnesses)[2]
        self.assertEqual(
            {witness["risk-owner-approval"]["issuer"],
             witness["independent-approval"]["issuer"]},
            {"risk-alice", "reviewer-bob"},
        )
        # Second promotion is refused: the intent is no longer PROPOSED.
        with patch("farm_ontology.markets.finance_controls.CLASS_C_POLICY", "open"):
            with self.assertRaisesRegex(ValueError, "only a proposed intent"):
                promote_intent(
                    self.value.intent_id, self.approvals, self.store,
                    intent=self.value, cap_sheet=self.cap, source_rights=self.rights,
                    kill_switch=self.kill, at=AT2 + timedelta(seconds=1),
                    actor="reviewer-bob", verifier=verifier,
                )

    def test_promote_refuses_unknown_intent_and_gate_violations(self):
        stranger = intent(intent_id="intent-ghost")
        with patch("farm_ontology.markets.finance_controls.CLASS_C_POLICY", "open"):
            with self.assertRaisesRegex(ValueError, "does not bind"):
                promote_intent(
                    stranger.intent_id, self.approvals, self.store,
                    intent=stranger, cap_sheet=self.cap, source_rights=self.rights,
                    kill_switch=self.kill, at=AT2, actor="reviewer-bob",
                    verifier=verifier,
                )
        expired_cap = replace(self.cap, expires_at=AT2 - timedelta(seconds=1))
        with patch("farm_ontology.markets.finance_controls.CLASS_C_POLICY", "open"):
            with self.assertRaisesRegex(ValueError, "approval gates"):
                promote_intent(
                    self.value.intent_id, self.approvals, self.store,
                    intent=self.value, cap_sheet=expired_cap,
                    source_rights=self.rights, kill_switch=self.kill,
                    at=AT2, actor="reviewer-bob", verifier=verifier,
                )
        self.assertEqual(len(list(self.store.replay("hedge-intent"))), 1)


class GcsLedgerStoreTests(unittest.TestCase):
    """Same interface over the record-store seam, create-only objects."""

    def setUp(self):
        self.mem, self.store = gcs_store()
        self.value = intent()
        self.cap, self.rights, self.kill, self.approvals = approval_evidence(self.value)

    def test_full_lifecycle_replays_through_gcs_seam(self):
        ledger = StoreBackedHedgeIntentLedger(self.store)
        ledger.propose(self.value, at=AT1, actor="analyst-charlie")
        with patch("farm_ontology.markets.finance_controls.CLASS_C_POLICY", "open"):
            promote_intent(
                self.value.intent_id, self.approvals, self.store,
                intent=self.value, cap_sheet=self.cap, source_rights=self.rights,
                kill_switch=self.kill, at=AT2, actor="reviewer-bob", verifier=verifier,
            )
        hydrated = StoreBackedHedgeIntentLedger(self.store, verifier=verifier)
        hydrated.halt(
            self.value.intent_id, at=AT3, actor="independent-watchdog",
            kill_switch=halt_evidence(self.value), verifier=verifier,
        )
        reborn = StoreBackedHedgeIntentLedger.replay_from_store(self.store, verifier=verifier)
        self.assertEqual(
            [event.event_type for event in reborn.events],
            [EventType.PROPOSED, EventType.APPROVED_MANUAL, EventType.HALTED],
        )
        self.assertEqual(reborn.state(self.value.intent_id, at=AT3), IntentState.HALTED)
        entries = list(self.store.replay("hedge-intent"))
        self.assertEqual(self.store.last_hash("hedge-intent"), entries[-1].entry_hash)

    def test_create_only_writes_and_collision_refusal(self):
        ledger = StoreBackedHedgeIntentLedger(self.store)
        ledger.propose(self.value, at=AT1, actor="analyst-charlie")
        self.assertEqual(len(self.mem.objects), 1)
        name = sorted(self.mem.objects)[0]
        self.assertRegex(name, r"kinds/hedge-intent/entries/00000001\.json$")
        # A rival writer claims the NEXT entry slot inside the race window
        # between this store's listing and its create (hide it from listing
        # by patching the view; the underlying put still collides).
        rival_name = name.replace("00000001", "00000002")
        rival_blob = b'{"rival": true}'
        self.mem.objects[rival_name] = rival_blob
        with patch.object(self.store, "_sequences", return_value=[1]):
            with patch("farm_ontology.markets.finance_controls.CLASS_C_POLICY", "open"):
                with self.assertRaisesRegex(FileExistsError, "another writer appended"):
                    promote_intent(
                        self.value.intent_id, self.approvals, self.store,
                        intent=self.value, cap_sheet=self.cap, source_rights=self.rights,
                        kill_switch=self.kill, at=AT2, actor="reviewer-bob", verifier=verifier,
                    )
        # The rival's bytes were never replaced and no second stream appeared.
        self.assertEqual(self.mem.objects[rival_name], rival_blob)
        self.assertEqual(sum(1 for key in self.mem.objects if key.endswith("00000002.json")), 1)
        self.assertTrue(self.mem.token_calls >= 1)

    def test_gcs_tampered_object_is_refused_on_replay(self):
        ledger = StoreBackedHedgeIntentLedger(self.store)
        ledger.propose(self.value, at=AT1, actor="analyst-charlie")
        with patch("farm_ontology.markets.finance_controls.CLASS_C_POLICY", "open"):
            promote_intent(
                self.value.intent_id, self.approvals, self.store,
                intent=self.value, cap_sheet=self.cap, source_rights=self.rights,
                kill_switch=self.kill, at=AT2, actor="reviewer-bob", verifier=verifier,
            )
        name = sorted(self.mem.objects)[1]
        record = json.loads(self.mem.objects[name])
        record["sequence"] = 7
        self.mem.objects[name] = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
        with self.assertRaisesRegex(ValueError, "carries sequence|disagrees|hash"):
            StoreBackedHedgeIntentLedger.replay_from_store(self.store, verifier=verifier)

    def test_gcs_requires_bucket_and_reports_gap_numbering(self):
        with self.assertRaisesRegex(ValueError, "bucket"):
            GcsLedgerStore("")
        ledger = StoreBackedHedgeIntentLedger(self.store)
        ledger.propose(self.value, at=AT1, actor="analyst-charlie")
        name = sorted(self.mem.objects)[0]
        orphan = name.replace("00000001", "00000003")
        self.mem.objects[orphan] = self.mem.objects[name]
        with self.assertRaisesRegex(ValueError, "numbering gap"):
            self.store.last_hash("hedge-intent")

    def test_both_backends_share_the_seam_and_byte_format(self):
        ledger = StoreBackedHedgeIntentLedger(self.store)
        ledger.propose(self.value, at=AT1, actor="analyst-charlie")
        gcs_entry = list(self.store.replay("hedge-intent"))[0]
        tmp = tempfile.TemporaryDirectory()
        try:
            json_store = JsonFileLedgerStore(Path(tmp.name))
            json_store.append(
                "hedge-intent", gcs_entry.event,
                intent_payload=gcs_entry.intent_payload, witness=gcs_entry.witness,
            )
            json_entry = list(json_store.replay("hedge-intent"))[0]
            self.assertEqual(json_entry, gcs_entry)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
