from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from farm_ontology.actuation import (
    ActuationGap,
    ActuationRefusal,
    CommandLedger,
    GateCheck,
    IrrigationCapability,
    SupervisedIrrigationSimulator,
)


T0 = datetime(2026, 11, 28, 4, 0, tzinfo=timezone.utc)


def workflow(gate=None):
    return SupervisedIrrigationSimulator(
        ledger=CommandLedger(),
        gate=gate or GateCheck(),
        capability=IrrigationCapability(
            site_id="site:tea-test",
            zone_id="zone:terrace-1",
            device_ref="simulator:valve-1",
            calibration_ref="calibration:flow-meter-1",
            max_volume_l=1000,
            max_duration_s=900,
            native_support="zone:terrace-1:survey-v1",
        ),
    )


def propose(flow, **changes):
    values = {
        "actor": {"kind": "service", "id": "irrigation-adviser"},
        "at": T0,
        "expires_at": T0 + timedelta(minutes=10),
        "volume_l": 300,
        "duration_s": 180,
        "recommendation_ref": "recommendation:water-1",
        "profile_ref": "profile:tea-test@0.1.0",
        "polygon_ref": "boundary:tea-test:v1",
    }
    return flow.propose(**{**values, **changes})


class SupervisedIrrigationTests(unittest.TestCase):
    def test_four_eyes_human_approval_simulation_and_outcome(self):
        flow = workflow()
        command_id = propose(flow)
        self.assertEqual(flow.ledger.state_of(command_id), "proposed")
        with self.assertRaisesRegex(ActuationRefusal, "approver_equals_proposer"):
            flow.approve(command_id, approver={"kind": "human", "id": "irrigation-adviser"}, at=T0 + timedelta(seconds=10))
        flow.approve(command_id, approver={"kind": "human", "id": "farm-operator"}, at=T0 + timedelta(seconds=10))
        outcome = flow.simulate_delivery(
            command_id, delivered_volume_l=290, meter_ref="sim-meter:1", at=T0 + timedelta(seconds=20)
        )
        self.assertEqual(flow.ledger.state_of(command_id), "acknowledged")
        self.assertEqual(outcome.commanded_volume_l, 300)
        self.assertEqual(outcome.delivery_error_l, -10)
        self.assertTrue(outcome.to_payload()["simulation_only"])
        self.assertFalse(outcome.to_payload()["actuation_authorized"])
        self.assertFalse(flow.real_actuation_assessment["eligible_for_live_commands"])
        self.assertTrue(flow.ledger.verify_chain()["ok"])

    def test_expired_command_cannot_be_approved_or_simulated(self):
        flow = workflow()
        command_id = propose(flow, expires_at=T0 + timedelta(seconds=5))
        with self.assertRaisesRegex(ActuationRefusal, "irrigation_command_expired"):
            flow.approve(command_id, approver={"kind": "human", "id": "operator"}, at=T0 + timedelta(seconds=6))

    def test_limits_and_missing_provenance_fail_closed(self):
        flow = workflow()
        with self.assertRaisesRegex(ActuationRefusal, "irrigation_limit_exceeded"):
            propose(flow, volume_l=1001)
        with self.assertRaisesRegex(ActuationGap, "irrigation_field_missing"):
            propose(flow, profile_ref="")

    def test_delivery_requires_approved_state_and_records_zero_as_failure(self):
        flow = workflow()
        command_id = propose(flow)
        with self.assertRaisesRegex(ActuationRefusal, "irrigation_not_approved"):
            flow.simulate_delivery(command_id, delivered_volume_l=0, meter_ref="meter:1", at=T0 + timedelta(seconds=1))
        flow.approve(command_id, approver={"kind": "human", "id": "operator"}, at=T0 + timedelta(seconds=1))
        outcome = flow.simulate_delivery(command_id, delivered_volume_l=0, meter_ref="meter:1", at=T0 + timedelta(seconds=2))
        self.assertEqual(outcome.delivery_error_l, -300)


if __name__ == "__main__":
    unittest.main()
