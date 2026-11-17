"""Tests for the hash-chained command ledger (WS5.3)."""

import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path

from farm_ontology.actuation.command_ledger import (
    COMMAND_STATES,
    GENESIS_HASH,
    ActuationGap,
    ActuationRefusal,
    CommandLedger,
    IllegalTransition,
    canonical_json,
    command_id_for,
)

_T0 = datetime(2027, 1, 15, 9, 0, tzinfo=timezone.utc)
_SERVICE = {"kind": "service", "id": "agronomy-engine"}
_HUMAN = {"kind": "human", "id": "risk-owner"}
_OPERATOR = {"kind": "human", "id": "tractor-operator"}
_PRESCRIPTION = {
    "dose_mm": 12.5,
    "native_support": "ws4-soil-probe-cal-v2",
    "use_class": "field-ops",
}
_POLYGON = "urn:farm:polygon:bv-2027-001"


def _elapsed(seconds: int) -> datetime:
    return _T0 + timedelta(seconds=seconds)


def _new_ledger() -> tuple[CommandLedger, str]:
    ledger = CommandLedger()
    record = ledger.propose(
        prescription=dict(_PRESCRIPTION), actor=_SERVICE, at=_T0, polygon_ref=_POLYGON
    )
    return ledger, record["event"]["command_id"]


def _drive_to_acknowledged(ledger: CommandLedger, cid: str) -> None:
    ledger.approve(cid, approver=_HUMAN, at=_elapsed(60))
    ledger.dispatch(
        cid, actor=_SERVICE, receipt={"transport": "usb", "frame": 1}, at=_elapsed(120)
    )
    ledger.acknowledge(
        cid, actor=_OPERATOR, receipt={"controller": "IsoTerminal-A", "ack_seq": 7}, at=_elapsed(180)
    )


class CanonicalAndIdentityTests(unittest.TestCase):
    def test_canonical_json_is_sorted_and_stable(self):
        left = canonical_json({"b": 1, "a": 2})
        right = canonical_json({"a": 2, "b": 1})
        self.assertEqual(left, right)
        self.assertEqual(left, b'{"a":2,"b":1}')

    def test_genesis_hash_shape(self):
        self.assertEqual(GENESIS_HASH, "0" * 64)
        self.assertEqual(len(COMMAND_STATES), 5)

    def test_command_id_deterministic_and_content_bound(self):
        first = command_id_for(
            prescription=_PRESCRIPTION, polygon_ref=_POLYGON, proposer=_SERVICE["id"]
        )
        again = command_id_for(
            prescription=dict(_PRESCRIPTION), polygon_ref=_POLYGON, proposer=_SERVICE["id"]
        )
        self.assertEqual(first, again)
        changed = command_id_for(
            prescription={**_PRESCRIPTION, "dose_mm": 9.0},
            polygon_ref=_POLYGON,
            proposer=_SERVICE["id"],
        )
        self.assertNotEqual(first, changed)

    def test_proposed_record_shape(self):
        ledger, cid = _new_ledger()
        record = ledger.records[0]
        self.assertEqual(record["seq"], 1)
        self.assertEqual(record["type"], "command_event")
        self.assertEqual(record["prev"], GENESIS_HASH)
        self.assertEqual(record["event"]["name"], "propose")
        self.assertEqual(record["event"]["to_state"], "proposed")
        self.assertIsNone(record["event"]["from_state"])
        self.assertEqual(record["event"]["command_id"], cid)
        self.assertEqual(record["event"]["prescription"], _PRESCRIPTION)
        self.assertTrue(record["hash"])
        # injected, not wall-clock: timestamp is exactly the one passed in
        self.assertEqual(
            datetime.fromisoformat(record["ts"]).astimezone(timezone.utc), _T0
        )

    def test_state_folds_through_the_whole_chain(self):
        ledger, cid = _new_ledger()
        self.assertEqual(ledger.state_of(cid), "proposed")
        _drive_to_acknowledged(ledger, cid)
        self.assertEqual(ledger.state_of(cid), "acknowledged")
        ledger.void(cid, reason="season closeout", actor=_HUMAN, at=_elapsed(240))
        self.assertEqual(ledger.state_of(cid), "voided")
        snapshot = ledger.snapshot()
        self.assertEqual(snapshot, {cid: "voided"})
        self.assertEqual(len(ledger.events_of(cid)), 5)


class TransitionLegalityTests(unittest.TestCase):
    def test_legal_lifecycle_verify_chain_ok(self):
        ledger, cid = _new_ledger()
        _drive_to_acknowledged(ledger, cid)
        report = ledger.verify_chain()
        self.assertTrue(report["ok"], report["problems"])
        self.assertEqual(report["records"], 4)

    def test_approve_requires_human_distinct_from_proposer(self):
        ledger, cid = _new_ledger()
        with self.assertRaises(ActuationRefusal) as ctx:
            ledger.approve(cid, approver=_SERVICE, at=_elapsed(10))
        self.assertEqual(ctx.exception.refusal, "approver_must_be_human")
        # a DIFFERENT human is fine
        ledger.approve(
            cid, approver={"kind": "human", "id": "second-owner"}, at=_elapsed(10)
        )
        self.assertEqual(ledger.state_of(cid), "approved")

    def test_self_approval_blocked_when_proposer_is_human(self):
        solo = {"kind": "human", "id": "sole-operator"}
        ledger = CommandLedger()
        record = ledger.propose(
            prescription=dict(_PRESCRIPTION), actor=solo, at=_T0, polygon_ref=_POLYGON
        )
        cid = record["event"]["command_id"]
        with self.assertRaises(ActuationRefusal) as ctx:
            ledger.approve(cid, approver=solo, at=_elapsed(10))
        self.assertEqual(ctx.exception.refusal, "approver_equals_proposer")

    def test_illegal_backward_and_skip_transitions_raise(self):
        ledger, cid = _new_ledger()
        ledger.approve(cid, approver=_HUMAN, at=_elapsed(10))
        with self.assertRaises(IllegalTransition):
            ledger.approve(cid, approver={"kind": "human", "id": "again"}, at=_elapsed(20))
        with self.assertRaises(IllegalTransition):
            ledger.acknowledge(cid, actor=_OPERATOR, receipt={"ok": 1}, at=_elapsed(30))
        ledger.dispatch(cid, actor=_SERVICE, receipt={"carrier": "taskset.zip"}, at=_elapsed(40))
        with self.assertRaises(IllegalTransition):
            ledger.dispatch(cid, actor=_SERVICE, receipt={"again": 1}, at=_elapsed(50))
        ledger.acknowledge(cid, actor=_OPERATOR, receipt={"seq": 1}, at=_elapsed(60))
        with self.assertRaises(IllegalTransition):
            ledger.acknowledge(cid, actor=_OPERATOR, receipt={"seq": 2}, at=_elapsed(70))
        # the REFUSED attempts never entered the chain: 4 clean records remain
        report = ledger.verify_chain()
        self.assertTrue(report["ok"], report["problems"])
        self.assertEqual(report["records"], 4)

    def test_failed_attempts_never_touch_the_chain(self):
        ledger, cid = _new_ledger()
        before = len(ledger.records)
        with self.assertRaises(IllegalTransition):
            ledger.dispatch(cid, actor=_SERVICE, receipt={"x": 1}, at=_elapsed(5))
        self.assertEqual(len(ledger.records), before)
        self.assertEqual(ledger.state_of(cid), "proposed")

    def test_void_allowed_from_every_state_but_not_twice(self):
        drivers = {
            "proposed": lambda lg, c: None,
            "approved": lambda lg, c: lg.approve(c, approver=_HUMAN, at=_elapsed(60)),
            "dispatched": lambda lg, c: (
                lg.approve(c, approver=_HUMAN, at=_elapsed(60)),
                lg.dispatch(c, actor=_SERVICE, receipt={"t": 1}, at=_elapsed(120)),
            ),
            "acknowledged": lambda lg, c: _drive_to_acknowledged(lg, c),
        }
        for state, driver in drivers.items():
            with self.subTest(state=state):
                ledger, cid = _new_ledger()
                driver(ledger, cid)
                self.assertEqual(ledger.state_of(cid), state)
                ledger.void(cid, reason="surface flooding", actor=_HUMAN, at=_elapsed(300))
                self.assertEqual(ledger.state_of(cid), "voided")
                with self.assertRaises(IllegalTransition):
                    ledger.void(cid, reason="twice", actor=_HUMAN, at=_elapsed(310))
                # history survived voiding
                self.assertGreaterEqual(len(ledger.events_of(cid)), 2)

    def test_dispatch_and_ack_require_receipts(self):
        ledger, cid = _new_ledger()
        ledger.approve(cid, approver=_HUMAN, at=_elapsed(10))
        for bad in (None, "", "   ", {}, []):
            with self.subTest(receipt=bad):
                with self.assertRaises(ActuationGap) as ctx:
                    ledger.dispatch(cid, actor=_SERVICE, receipt=bad, at=_elapsed(20))
                self.assertEqual(ctx.exception.gap, "dispatch_receipt_missing")
        ledger.dispatch(cid, actor=_SERVICE, receipt={"blob": [1, 2]}, at=_elapsed(30))
        for bad in (None, "", {}):
            with self.subTest(receipt=bad):
                with self.assertRaises(ActuationGap) as ctx:
                    ledger.acknowledge(cid, actor=_OPERATOR, receipt=bad, at=_elapsed(40))
                self.assertEqual(ctx.exception.gap, "ack_receipt_missing")
        # a plain string receipt is a legitimate blob
        ledger.acknowledge(cid, actor=_OPERATOR, receipt="ACK T-0001 ok", at=_elapsed(50))
        self.assertEqual(ledger.state_of(cid), "acknowledged")

    def test_timestamp_regression_is_a_gap(self):
        ledger, cid = _new_ledger()
        with self.assertRaises(ActuationGap) as ctx:
            ledger.approve(cid, approver=_HUMAN, at=_T0 - timedelta(hours=1))
        self.assertEqual(ctx.exception.gap, "timestamp_regression")

    def test_unknown_command_is_a_named_gap(self):
        ledger, _ = _new_ledger()
        with self.assertRaises(ActuationGap) as ctx:
            ledger.state_of("nosuchcommand")
        self.assertEqual(ctx.exception.gap, "unknown_command")

    def test_naive_timestamps_refused_everywhere(self):
        ledger, cid = _new_ledger()
        naive = datetime(2027, 1, 15, 9, 0)
        with self.assertRaises(ActuationGap) as ctx:
            ledger.void(cid, reason="late", actor=_HUMAN, at=naive)
        self.assertEqual(ctx.exception.gap, "naive_timestamp")
        fresh = CommandLedger()
        with self.assertRaises(ActuationGap) as ctx:
            fresh.halt(reason="storm", actor=_HUMAN, at=naive)
        self.assertEqual(ctx.exception.gap, "naive_timestamp")


class ProposalValidationTests(unittest.TestCase):
    def test_stamp_gaps_are_named(self):
        for missing in ("native_support", "use_class"):
            with self.subTest(stamp=missing):
                broken = {k: v for k, v in _PRESCRIPTION.items() if k != missing}
                ledger = CommandLedger()
                with self.assertRaises(ActuationGap) as ctx:
                    ledger.propose(prescription=broken, actor=_SERVICE, at=_T0)
                self.assertEqual(ctx.exception.gap, f"{missing}_missing")

    def test_blank_stamp_values_refused(self):
        ledger = CommandLedger()
        with self.assertRaises(ActuationGap) as ctx:
            ledger.propose(
                prescription={**_PRESCRIPTION, "use_class": "   "},
                actor=_SERVICE,
                at=_T0,
            )
        self.assertEqual(ctx.exception.gap, "use_class_missing")

    def test_prescription_must_be_object(self):
        ledger = CommandLedger()
        for bad in (None, [], "spray 20mm", 42):
            with self.subTest(value=bad):
                with self.assertRaises(ActuationGap):
                    ledger.propose(prescription=bad, actor=_SERVICE, at=_T0)

    def test_polygon_ref_pending_is_none_else_string(self):
        ledger = CommandLedger()
        record = ledger.propose(prescription=dict(_PRESCRIPTION), actor=_SERVICE, at=_T0)
        self.assertIsNone(record["event"]["polygon_ref"])
        with self.assertRaises(ActuationGap) as ctx:
            ledger.propose(prescription=dict(_PRESCRIPTION), actor=_SERVICE, at=_T0, polygon_ref=17)
        self.assertEqual(ctx.exception.gap, "polygon_ref_ill_formed")

    def test_actor_validation(self):
        ledger = CommandLedger()
        cases = [
            (None, "proposer_missing"),
            ({"kind": "robot", "id": "r2"}, "actor_kind_invalid"),
            ({"kind": "human"}, "actor_id_missing"),
            ({"kind": "human", "id": "  "}, "actor_id_missing"),
        ]
        for actor, gap in cases:
            with self.subTest(actor=actor):
                with self.assertRaises(ActuationGap) as ctx:
                    ledger.propose(prescription=dict(_PRESCRIPTION), actor=actor, at=_T0)
                self.assertEqual(ctx.exception.gap, gap)

    def test_identical_proposal_is_one_command(self):
        ledger, cid = _new_ledger()
        with self.assertRaises(IllegalTransition) as ctx:
            ledger.propose(
                prescription=dict(_PRESCRIPTION), actor=_SERVICE, at=_elapsed(30), polygon_ref=_POLYGON
            )
        self.assertIn("already exists", ctx.exception.detail)

    def test_different_proposer_same_content_is_a_different_command(self):
        ledger, cid = _new_ledger()
        other = ledger.propose(
            prescription=dict(_PRESCRIPTION),
            actor={"kind": "service", "id": "irrigation-worker"},
            at=_elapsed(30),
            polygon_ref=_POLYGON,
        )
        self.assertNotEqual(other["event"]["command_id"], cid)


class HaltdDoctrine6Tests(unittest.TestCase):
    def test_halt_freezes_lifecycle_but_not_voiding(self):
        ledger, cid = _new_ledger()
        ledger.halt(reason="typhoon w12 inbound", actor=_HUMAN, at=_elapsed(30))
        self.assertTrue(ledger.halted())
        for action in (
            lambda: ledger.propose(prescription=dict(_PRESCRIPTION), actor=_SERVICE, at=_elapsed(40)),
            lambda: ledger.approve(cid, approver=_HUMAN, at=_elapsed(40)),
            lambda: ledger.dispatch(cid, actor=_SERVICE, receipt={"x": 1}, at=_elapsed(40)),
            lambda: ledger.acknowledge(cid, actor=_OPERATOR, receipt={"x": 1}, at=_elapsed(40)),
        ):
            with self.assertRaises(ActuationRefusal) as ctx:
                action()
            self.assertEqual(ctx.exception.refusal, "halted")
        ledger.void(cid, reason="abort field ops for storm", actor=_HUMAN, at=_elapsed(50))
        self.assertEqual(ledger.state_of(cid), "voided")

    def test_halt_requires_human_and_reason(self):
        ledger = CommandLedger()
        with self.assertRaises(ActuationRefusal) as ctx:
            ledger.halt(reason="auto-stop", actor=_SERVICE, at=_T0)
        self.assertEqual(ctx.exception.refusal, "halt_actor_must_be_human")
        with self.assertRaises(ActuationGap):
            ledger.halt(reason="", actor=_HUMAN, at=_T0)

    def test_lift_cycle_restores_operations(self):
        ledger, cid = _new_ledger()
        ledger.halt(reason="storm", actor=_HUMAN, at=_elapsed(10))
        self.assertTrue(ledger.halted())
        ledger.lift_halt(reason="storm passed", actor=_HUMAN, at=_elapsed(30))
        self.assertFalse(ledger.halted())
        with self.assertRaises(ActuationRefusal) as ctx:
            ledger.lift_halt(reason="nothing active", actor=_HUMAN, at=_elapsed(35))
        self.assertEqual(ctx.exception.refusal, "halt_not_active")
        ledger.approve(cid, approver=_HUMAN, at=_elapsed(40))
        self.assertEqual(ledger.state_of(cid), "approved")
        # a SECOND emergency after a lift is legitimate; a DOUBLE raise is not
        ledger.halt(reason="second squall line", actor=_HUMAN, at=_elapsed(50))
        self.assertTrue(ledger.halted())
        with self.assertRaises(ActuationRefusal) as ctx:
            ledger.halt(reason="double raise", actor=_HUMAN, at=_elapsed(55))
        self.assertEqual(ctx.exception.refusal, "halt_already_active")


class TamperDetectionTests(unittest.TestCase):
    def _serialized(self, ledger: CommandLedger) -> str:
        return ledger.to_jsonl_text()

    def test_edited_entry_breaks_verify(self):
        ledger, cid = _new_ledger()
        _drive_to_acknowledged(ledger, cid)
        raw = json.loads(self._serialized(ledger).splitlines()[0])
        raw["event"]["prescription"]["dose_mm"] = 999.0
        tampered = CommandLedger([raw] + [
            json.loads(line) for line in self._serialized(ledger).splitlines()[1:]
        ])
        report = tampered.verify_chain()
        self.assertFalse(report["ok"])
        self.assertTrue(any("hash mismatch" in p for p in report["problems"]))

    def test_deleted_record_breaks_seq(self):
        ledger, _ = _new_ledger()
        ledger.approve(ledger.records[0]["event"]["command_id"], approver=_HUMAN, at=_elapsed(60))
        lines = self._serialized(ledger).splitlines()
        thinned = [json.loads(line) for line in lines if json.loads(line)["seq"] != 1]
        report = CommandLedger(thinned).verify_chain()
        self.assertFalse(report["ok"])
        self.assertTrue(any("seq broken" in p for p in report["problems"]))

    def test_reordered_records_break_prev(self):
        ledger, _ = _new_ledger()
        ledger.approve(ledger.records[0]["event"]["command_id"], approver=_HUMAN, at=_elapsed(60))
        records = list(ledger.records)
        records[0], records[1] = records[1], records[0]
        report = CommandLedger(records).verify_chain()
        self.assertFalse(report["ok"])
        self.assertTrue(any("prev hash mismatch" in p for p in report["problems"]))

    def test_semantically_impossible_history_caught_even_with_forged_hashes(self):
        """A forger rewrites the chain consistently (hashes re-forged) but
        the SEQUENCE skips the approve/dispatch steps — replay must catch it."""
        ledger, cid = _new_ledger()
        _drive_to_acknowledged(ledger, cid)
        survivors = [
            record
            for record in ledger.records
            if record["event"]["name"] in ("propose", "acknowledge")
        ]
        forged = []
        prev = GENESIS_HASH
        for index, record in enumerate(survivors, start=1):
            record = copy.deepcopy(record)
            record["seq"] = index
            record["prev"] = prev
            body = {"type": record["type"], "ts": record["ts"], "event": record["event"]}
            record["hash"] = sha256(prev.encode("ascii") + canonical_json(body)).hexdigest()
            prev = record["hash"]
            forged.append(record)
        report = CommandLedger(forged).verify_chain()
        self.assertFalse(report["ok"])
        self.assertTrue(any("illegal transition" in p for p in report["problems"]))

    def test_verify_detects_structural_garbage(self):
        garbage = [
            {"seq": 1, "type": "hologram", "ts": "x", "prev": GENESIS_HASH,
             "event": {}, "hash": "ff"},
        ]
        report = CommandLedger(garbage).verify_chain()
        self.assertFalse(report["ok"])
        self.assertTrue(any("unknown record type" in p for p in report["problems"]))


class PersistenceTests(unittest.TestCase):
    def test_save_reload_roundtrip_verifies(self):
        ledger, cid = _new_ledger()
        _drive_to_acknowledged(ledger, cid)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "commands.jsonl"
            ledger.save(path)
            reloaded = CommandLedger.from_path(path)
            self.assertTrue(reloaded.verify_chain()["ok"])
            self.assertEqual(reloaded.snapshot(), ledger.snapshot())
            self.assertEqual(reloaded.tail_hash(), ledger.tail_hash())

    def test_loading_a_tampered_file_is_refused(self):
        ledger, _ = _new_ledger()
        text = ledger.to_jsonl_text()
        mutated = text.replace('"to_state":"proposed"', '"to_state":"acknowledged"', 1)
        with self.assertRaises(ActuationRefusal) as ctx:
            CommandLedger.from_jsonl_text(mutated)
        self.assertEqual(ctx.exception.refusal, "ledger_verify_failed")

    def test_unparsable_line_is_a_named_gap(self):
        with self.assertRaises(ActuationGap) as ctx:
            CommandLedger.from_jsonl_text("{not json\n")
        self.assertEqual(ctx.exception.gap, "ledger_line_unparsable")

    def test_save_failure_names_the_gap(self):
        ledger, _ = _new_ledger()
        with self.assertRaises(ActuationGap) as ctx:
            ledger.save(Path(tempfile.gettempdir()) / "no-such-dir-xyz" / "l.jsonl")
        self.assertEqual(ctx.exception.gap, "ledger_write_failed")

    def test_records_property_defends_copies(self):
        ledger, _ = _new_ledger()
        grabbed = ledger.records[0]
        grabbed["event"]["to_state"] = "acknowledged"
        self.assertEqual(ledger.state_of(ledger.records[0]["event"]["command_id"]), "proposed")


if __name__ == "__main__":
    unittest.main()
