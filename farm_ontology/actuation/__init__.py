"""Machine/actuator interfaces — SPEC-FIRST (WS5).

Everything here is specification and offline tooling around machine commands:
a hash-chained command ledger, ISO 11783-10 TaskSet export, human-operated
drone spray packets, and the Phase-4 gate that must pass BEFORE any of it
touches a real machine. No module in this package opens a socket to a
machine, an autopilot, or a network.
"""

from farm_ontology.actuation.command_ledger import (
    COMMAND_STATES,
    GENESIS_HASH,
    PRESCRIPTION_STAMP_KEYS,
    ActuationError,
    ActuationGap,
    ActuationRefusal,
    CommandLedger,
    IllegalTransition,
    canonical_json,
    command_id_for,
)
from farm_ontology.actuation.drone_packet import (
    AdvisoryRef,
    KML_NAMESPACE,
    RECOMMENDATION_CONTRACT,
    WEATHER_WINDOW_FIELDS,
    build_drone_packet,
    weather_window_gaps,
)
from farm_ontology.actuation.gate import (
    GATE_FACT_MEANINGS,
    GATE_FACT_NAMES,
    SATISFYING_EVIDENCE,
    GateCheck,
)
from farm_ontology.actuation.taskset_export import (
    KNOWN_OPERATIONS,
    PROFILE_SCHEMA_VERSION,
    build_grid_binary,
    build_taskset_zip,
    validate_taskset_zip,
)

__all__ = [
    # command_ledger
    "COMMAND_STATES",
    "GENESIS_HASH",
    "PRESCRIPTION_STAMP_KEYS",
    "ActuationError",
    "ActuationGap",
    "ActuationRefusal",
    "CommandLedger",
    "IllegalTransition",
    "canonical_json",
    "command_id_for",
    # drone_packet
    "AdvisoryRef",
    "KML_NAMESPACE",
    "RECOMMENDATION_CONTRACT",
    "WEATHER_WINDOW_FIELDS",
    "build_drone_packet",
    "weather_window_gaps",
    # gate
    "GATE_FACT_MEANINGS",
    "GATE_FACT_NAMES",
    "SATISFYING_EVIDENCE",
    "GateCheck",
    # taskset_export
    "KNOWN_OPERATIONS",
    "PROFILE_SCHEMA_VERSION",
    "build_grid_binary",
    "build_taskset_zip",
    "validate_taskset_zip",
]
