"""Human-supervised irrigation workflow with a simulation-only executor.

This module proves the command and receipt contract without opening a socket
or writing to a valve. A real driver is deliberately absent. Real command
eligibility must still be assessed from deployment evidence by ``GateCheck``
and the required site/device/human safety approvals.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math

from farm_ontology.actuation.command_ledger import (
    ActuationGap,
    ActuationRefusal,
    CommandLedger,
)
from farm_ontology.actuation.gate import GateCheck
from farm_ontology.agronomy.common import deterministic_id


_SIMULATOR = {"kind": "service", "id": "irrigation-simulator"}


def _aware(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ActuationGap("irrigation_time_invalid", f"{name} must be timezone-aware")
    return value


def _positive(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ActuationGap("irrigation_number_invalid", f"{name} must be a finite positive number")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ActuationGap("irrigation_number_invalid", f"{name} must be a finite positive number")
    return result


def _nonnegative(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ActuationGap("irrigation_number_invalid", f"{name} must be a finite non-negative number")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ActuationGap("irrigation_number_invalid", f"{name} must be a finite non-negative number")
    return result


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ActuationGap("irrigation_field_missing", f"{name} must be a non-empty string")
    return value


@dataclass(frozen=True)
class IrrigationCapability:
    """Site-scoped validated simulator capability; limits are supplied by caller."""

    site_id: str
    zone_id: str
    device_ref: str
    calibration_ref: str
    max_volume_l: float
    max_duration_s: float
    native_support: str


@dataclass(frozen=True)
class IrrigationActionOutcome:
    """Append-only simulation result linked to an acknowledged command."""

    outcome_id: str
    command_id: str
    commanded_volume_l: float
    delivered_volume_l: float
    delivery_error_l: float
    meter_ref: str
    observed_at: datetime
    simulation_only: bool = True

    def to_payload(self) -> dict:
        return {
            "outcome_id": self.outcome_id,
            "command_id": self.command_id,
            "commanded_volume_l": self.commanded_volume_l,
            "delivered_volume_l": self.delivered_volume_l,
            "delivery_error_l": self.delivery_error_l,
            "meter_ref": self.meter_ref,
            "observed_at": self.observed_at.isoformat(),
            "simulation_only": True,
            "actuation_authorized": False,
        }


class SupervisedIrrigationSimulator:
    """Four-eyes command flow exercised against a deterministic fake device."""

    def __init__(
        self,
        *,
        ledger: CommandLedger,
        gate: GateCheck,
        capability: IrrigationCapability,
    ) -> None:
        if not isinstance(ledger, CommandLedger):
            raise TypeError("ledger must be a CommandLedger")
        if not isinstance(gate, GateCheck):
            raise TypeError("gate must be a GateCheck")
        if not isinstance(capability, IrrigationCapability):
            raise TypeError("capability must be an IrrigationCapability")
        # This class is permanently simulation-only. It cannot gain a live
        # path when the deployment gate changes state.
        self.ledger = ledger
        self.gate = gate
        self.capability = capability
        for name in ("site_id", "zone_id", "device_ref", "calibration_ref", "native_support"):
            _text(getattr(capability, name), name)
        _positive(capability.max_volume_l, "capability.max_volume_l")
        _positive(capability.max_duration_s, "capability.max_duration_s")
        self._outcomes: list[IrrigationActionOutcome] = []

    @property
    def outcomes(self) -> tuple[IrrigationActionOutcome, ...]:
        return tuple(self._outcomes)

    @property
    def real_actuation_assessment(self) -> dict:
        """This simulator never opens a real command path, even if facts pass."""
        return {
            "eligible_for_live_commands": False,
            "phase4_gate": self.gate.assessment(),
            "reason": "simulation-only workflow; no physical transport is implemented",
        }

    def propose(
        self,
        *,
        actor: dict,
        at: datetime,
        expires_at: datetime,
        volume_l: float,
        duration_s: float,
        recommendation_ref: str,
        profile_ref: str,
        polygon_ref: str | None = None,
    ) -> str:
        now = _aware(at, "at")
        expiry = _aware(expires_at, "expires_at")
        volume = _positive(volume_l, "volume_l")
        duration = _positive(duration_s, "duration_s")
        if expiry <= now:
            raise ActuationGap("irrigation_expired", "expiry must be later than proposal time")
        if volume > self.capability.max_volume_l or duration > self.capability.max_duration_s:
            raise ActuationRefusal("irrigation_limit_exceeded", "proposal exceeds the site/device capability limits")
        prescription = {
            "operation": "IRRIG",
            "action": "irrigate",
            "site_id": _text(self.capability.site_id, "site_id"),
            "zone_id": _text(self.capability.zone_id, "zone_id"),
            "device_ref": _text(self.capability.device_ref, "device_ref"),
            "device_calibration_ref": _text(self.capability.calibration_ref, "calibration_ref"),
            "volume_l": volume,
            "duration_s": duration,
            "native_support": _text(self.capability.native_support, "native_support"),
            "use_class": "field-ops",
            "recommendation_ref": _text(recommendation_ref, "recommendation_ref"),
            "profile_ref": _text(profile_ref, "profile_ref"),
            "expires_at": expiry.isoformat(),
            "simulation_only": True,
        }
        record = self.ledger.propose(
            prescription=prescription, actor=actor, at=now, polygon_ref=polygon_ref
        )
        return record["event"]["command_id"]

    def approve(self, command_id: str, *, approver: dict, at: datetime) -> dict:
        self._assert_fresh(command_id, at)
        return self.ledger.approve(command_id, approver=approver, at=at)

    def simulate_delivery(
        self,
        command_id: str,
        *,
        delivered_volume_l: float,
        meter_ref: str,
        at: datetime,
    ) -> IrrigationActionOutcome:
        now = _aware(at, "at")
        self._assert_fresh(command_id, now)
        if self.ledger.state_of(command_id) != "approved":
            raise ActuationRefusal("irrigation_not_approved", "simulation requires a human-approved command")
        delivered = _nonnegative(delivered_volume_l, "delivered_volume_l")
        meter = _text(meter_ref, "meter_ref")
        proposal = self.ledger.events_of(command_id)[0]["event"]["prescription"]
        commanded = float(proposal["volume_l"])
        if delivered > self.capability.max_volume_l:
            raise ActuationRefusal("irrigation_delivery_out_of_bounds", "simulated delivery exceeds device limit")
        # No network or hardware operation occurs. These receipts only prove
        # local lifecycle wiring and are marked simulation-only in both logs.
        dispatch_receipt = {
            "transport": "simulator",
            "simulation_only": True,
            "command_id": command_id,
        }
        self.ledger.dispatch(command_id, actor=_SIMULATOR, receipt=dispatch_receipt, at=now)
        ack_receipt = {
            "controller": "irrigation-simulator-v1",
            "simulation_only": True,
            "meter_ref": meter,
            "delivered_volume_l": delivered,
        }
        self.ledger.acknowledge(command_id, actor=_SIMULATOR, receipt=ack_receipt, at=now)
        identity = {
            "command_id": command_id,
            "commanded_volume_l": commanded,
            "delivered_volume_l": delivered,
            "meter_ref": meter,
            "observed_at": now.isoformat(),
            "simulation_only": True,
        }
        outcome = IrrigationActionOutcome(
            outcome_id=deterministic_id("irrigation-outcome", identity),
            command_id=command_id,
            commanded_volume_l=commanded,
            delivered_volume_l=delivered,
            delivery_error_l=delivered - commanded,
            meter_ref=meter,
            observed_at=now,
        )
        self._outcomes.append(outcome)
        return outcome

    def _assert_fresh(self, command_id: str, at: datetime) -> None:
        now = _aware(at, "at")
        events = self.ledger.events_of(command_id)
        prescription = events[0]["event"]["prescription"]
        expiry = datetime.fromisoformat(prescription["expires_at"])
        if now > expiry:
            raise ActuationRefusal("irrigation_command_expired", "expired proposal cannot be approved or simulated")


__all__ = [
    "IrrigationActionOutcome",
    "IrrigationCapability",
    "SupervisedIrrigationSimulator",
]
