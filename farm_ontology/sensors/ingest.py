"""Device payload to observation, through the Store's sensor plumbing.

This adapter mirrors how ``farm_ontology.adapters`` build observations:
payload in, one governed ``Observation`` per metric, ``Store.add_observation``
decides. It never writes around the store and never asserts a spatial join.

Native support is the sensed footprint that the sensor spec claims, never
a field or a boundary: a soil probe earns ``point-soil-probe-<depth>m3``
support on an ``instrument-point`` feature, a rain gauge earns
``instrument-point`` with ``raingauge-<device>`` as the feature, and so on.
Boundary membership, if anyone ever needs it, goes through
``Store.add_join`` elsewhere and is not this module's business.

Record-level meaning agreed with the calibration protocol
(``hardware/calibration-protocol.md``): only rows carrying a live
calibration activity and a due-date certificate may enter the store.
Uncalibrated or expired-cert rows are refused here and stay out of the
record. Those accepted rows are exactly the rows that may later support
the hectare-claim badge under the existing ``R-sensor`` rules.

One IRI is minted deterministically from device id and phenomenon time, so
the same payload replays to the same identity and the store's
``R-parallel`` rule refuses a duplicate instead of storing twins.

No network. No clock reads. Everything the store needs is in the payload.
"""

from __future__ import annotations

import os
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from farm_ontology.build import mint, screening_licence, screening_method
from farm_ontology.model import (
    CommitResult,
    ErrorStatement,
    Interval,
    Observation,
    Quantity,
)
from farm_ontology.namespaces import KIND, UNIT
from farm_ontology.store import Store
from farm_ontology.timeutil import parse_time

#: Emergency switch. A nonempty value refuses every sensor row before it
#: can reach the store, without touching any caller.
DISABLE_ENV = "FARM_SENSOR_INGEST_DISABLED"

DEVICE_CLASSES = frozenset(
    {"soil-vwc", "rain-tip", "leaf-wetness", "air-th", "air-temp"}
)

_REQUIRED_ALWAYS = ("device_id", "device_class", "phenomenon_time", "generated_at")

_DEVICE_ID = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{1,63}\Z")

METRIC_RMSE = "rmse"
METRIC_BIAS = "bias"

# Referenced QUDT local names, not vendored, matching the discipline in
# farm_ontology.namespaces.
_UNIT_PERCENT = UNIT + "PERCENT"
_UNIT_UNITLESS = UNIT + "UNITLESS"
_UNIT_MM = UNIT + "MilliM"
_UNIT_DEG_C = UNIT + "DEG_C"
_KIND_DIMENSIONLESS = KIND + "DimensionlessRatio"
_KIND_LENGTH = KIND + "Length"
_KIND_TEMPERATURE = KIND + "ThermodynamicTemperature"
_KIND_HUMIDITY = KIND + "RelativeHumidity"


@dataclass(frozen=True)
class _Spec:
    """What one device class measures, and where the value is native."""

    quantity_kind_iri: str
    unit_iri: str
    observed_property_local: str
    feature_template: str
    native_support: str
    low: float
    high: float
    value_required: bool = True


_SPECS: dict[str, _Spec] = {
    "soil-vwc": _Spec(
        quantity_kind_iri=_KIND_DIMENSIONLESS,
        unit_iri=_UNIT_PERCENT,
        observed_property_local="farm-soil-volumetric-water-content",
        feature_template="point-soil-probe-{depth}m3-{device}",
        native_support="point-soil-probe",
        low=0.0,
        high=100.0,
    ),
    "rain-tip": _Spec(
        quantity_kind_iri=_KIND_LENGTH,
        unit_iri=_UNIT_MM,
        observed_property_local="farm-precipitation-amount",
        feature_template="raingauge-{device}",
        native_support="instrument-point",
        low=0.0,
        high=500.0,
        value_required=False,
    ),
    "leaf-wetness": _Spec(
        quantity_kind_iri=_KIND_DIMENSIONLESS,
        unit_iri=_UNIT_UNITLESS,
        observed_property_local="farm-leaf-wetness-index",
        feature_template="leafwetness-{device}",
        native_support="instrument-point",
        low=0.0,
        high=1.0,
    ),
    "air-th": _Spec(
        quantity_kind_iri=_KIND_HUMIDITY,
        unit_iri=_UNIT_PERCENT,
        observed_property_local="farm-air-relative-humidity",
        feature_template="airth-{device}",
        native_support="instrument-point",
        low=0.0,
        high=100.0,
    ),
    "air-temp": _Spec(
        quantity_kind_iri=_KIND_TEMPERATURE,
        unit_iri=_UNIT_DEG_C,
        observed_property_local="farm-air-temperature",
        feature_template="airth-{device}",
        native_support="instrument-point",
        low=-40.0,
        high=85.0,
    ),
}


def sensor_support_disabled() -> bool:
    return bool(os.environ.get(DISABLE_ENV, "").strip())


def _refuse(
    store: Store, rule_id: str, entity: str, detail: str, at: datetime
) -> CommitResult:
    return store._refuse(rule_id, entity, detail, at)


def _sanitise_device(device_id: object) -> str | None:
    if not isinstance(device_id, str) or not _DEVICE_ID.match(device_id):
        return None
    return device_id


def _parse_expiry(text: str):
    """Certificate expiries may be a date or a full ISO-8601 instant.

    A bare date is read as midnight UTC on that day, which is the strictest
    honest reading of an expiry: the certificate dies with the day it names.
    """
    normalised = text.replace("Z", "+00:00")
    if len(normalised) == 10 and normalised.count("-") == 2:
        return parse_time(normalised + "T00:00:00+00:00")
    return parse_time(normalised)


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _reject_reasons(record: dict) -> list[tuple[str, str]]:
    """Adapter-side refusals. The store keeps its own final judgement."""
    reasons: list[tuple[str, str]] = []
    device_class = record.get("device_class")
    if device_class not in DEVICE_CLASSES:
        reasons.append(("R-property", f"unknown device class {device_class!r}; refusing"))
        return reasons
    spec = _SPECS[device_class]
    device_id = _sanitise_device(record.get("device_id"))
    if device_id is None:
        reasons.append(("R-property", "device_id is missing or unsafe"))
        return reasons
    for key in _REQUIRED_ALWAYS:
        if record.get(key) is None:
            reasons.append(("R-property", f"missing required key {key!r}"))
    if reasons:
        return reasons
    value = _number(record.get("value"))
    if spec.value_required and value is None:
        reasons.append(("R-property", f"missing required key 'value' for {device_class}"))
        return reasons
    if device_class == "rain-tip":
        tips = _number(record.get("tip_count"))
        tip_mm = _number(record.get("tip_mm"))
        if tips is None or tips < 0:
            reasons.append(("R-property", "tip_count must be a non-negative number"))
        if tip_mm is None or tip_mm <= 0:
            reasons.append(("R-property", "tip_mm must be positive"))
        if tips is not None and tip_mm is not None and tip_mm > 0 and tips * tip_mm > spec.high:
            reasons.append(("R-property", "derived rainfall exceeds the class range"))
    elif device_class == "soil-vwc" and (_number(record.get("depth_cm")) is None or _number(record.get("depth_cm")) <= 0):
        reasons.append(("R-property", "depth_cm must be explicitly provided and positive"))
    elif value is not None and not spec.low <= value <= spec.high:
        reasons.append(
            ("R-property", f"value {value} outside the {device_class} range")
        )
    # The calibration gate. Uncalibrated and expired-cert rows never load.
    activity = record.get("calibration_activity")
    if not isinstance(activity, str) or not activity.strip():
        reasons.append(
            (
                "R-sensor",
                "calibration_activity is missing: uncalibrated rows may not become observations",
            )
        )
    else:
        due = record.get("recalibration_due")
        if not isinstance(due, str) or not due.strip():
            reasons.append(
                ("R-sensor", "recalibration_due is missing: the certificate must carry an expiry")
            )
        else:
            try:
                due_at = _parse_expiry(due)
                at_phenomenon = parse_time(str(record["phenomenon_time"]))
                parse_time(str(record["generated_at"]))
            except ValueError as error:
                reasons.append(("R-property", f"bad timestamp: {error}"))
            else:
                if due_at <= at_phenomenon:
                    reasons.append(
                        (
                            "R-sensor",
                            "recalibration_due has passed: an expired certificate earns no rows",
                        )
                    )
    return reasons


def _depth_token(record: dict) -> str:
    depth = _number(record.get("depth_cm"))
    assert depth is not None and depth > 0
    if float(depth).is_integer():
        return str(int(depth)).zfill(2)
    return str(depth).replace(".", "p")


def _error_statement(record: dict) -> ErrorStatement | None:
    blob = record.get("calibration_error")
    if not isinstance(blob, dict):
        return None
    metric = str(blob.get("metric") or "").strip()
    value = _number(blob.get("value_fraction"))
    if metric not in {METRIC_RMSE, METRIC_BIAS} or value is None:
        return None
    return ErrorStatement(
        metric=metric,
        sample_region=str(blob.get("region_demo") or "unknown-demo-region"),
        sample_crop=str(blob.get("crop") or "soybean"),
        sample_season=str(blob.get("season") or "unknown"),
        citation=str(blob.get("reference_doc") or "hardware/calibration-protocol.md"),
        held_out=False,
        independent_of_product=True,
        value=Quantity(
            value=value,
            unit_iri=_UNIT_UNITLESS,
            quantity_kind_iri=_KIND_DIMENSIONLESS,
        ),
    )


def ingest_record(store: Store, record: dict, *, at: datetime) -> CommitResult:
    """Convert one device record into an Observation through the store.

    Deterministic IRI:
    ``observation/sensed-<device>-<property>-<phenomenon stamp>``.
    Ingesting the same payload twice is refused by the store's R-parallel
    rule, which is the intended replay behaviour.
    """
    if sensor_support_disabled():
        return _refuse(
            store,
            "R-sensor",
            str(record.get("device_id") or "record"),
            f"{DISABLE_ENV} is set: sensor ingest is switched off",
            at,
        )
    problems = _reject_reasons(record)
    if problems:
        first_rule, first_detail = problems[0]
        return _refuse(
            store, first_rule, str(record.get("device_id") or "record"), first_detail, at
        )
    device_class = str(record["device_class"])
    device_id = _sanitise_device(record["device_id"])
    spec = _SPECS[device_class]
    assert device_id is not None
    phenomenon_start = parse_time(str(record["phenomenon_time"]))
    generated_at = parse_time(str(record["generated_at"]))
    phenomenon_end = phenomenon_start + timedelta(hours=1)
    availability_blob = record.get("availability_time")
    availability_at = generated_at
    if isinstance(availability_blob, str) and availability_blob.strip():
        availability_at = parse_time(availability_blob)
    value = _number(record.get("value"))
    if device_class == "rain-tip":
        tips = _number(record.get("tip_count")) or 0.0
        tip_mm = _number(record.get("tip_mm"))
        assert tip_mm is not None
        value = tips * tip_mm
    assert value is not None
    stamp = phenomenon_start.strftime("%Y%m%dT%H%M%SZ")
    iri = mint(
        "observation",
        f"sensed-{device_id}-{spec.observed_property_local}-{stamp}",
    )
    feature_local = (
        spec.feature_template.format(device=device_id, depth=_depth_token(record))
        if "{depth}" in spec.feature_template
        else spec.feature_template.format(device=device_id)
    )
    obs = Observation(
        iri=iri,
        phenomenon=Interval(phenomenon_start, phenomenon_end),
        generated_at=generated_at,
        observed_property=mint("observedProperty", spec.observed_property_local),
        feature_of_interest=mint("instrument", feature_local),
        feature_kind="instrument-point",
        spatial_support=spec.native_support,
        procedure=mint("procedure", "sensor"),
        use_class="Screening",
        licence=screening_licence(),
        method=screening_method(product_version=f"sensor-kit-{device_class}"),
        personal_data=False,
        availability_time=availability_at,
        native_resolution=None,
        result=Quantity(
            value=value,
            unit_iri=spec.unit_iri,
            quantity_kind_iri=spec.quantity_kind_iri,
        ),
        error=_error_statement(record),
        product_kind=None,
        sensor_iri=mint("sensor", device_id),
        calibration_activity=mint(
            "activity", str(record["calibration_activity"]).rstrip("/").split("/")[-1]
        ),
        dry_run=bool(record.get("dry_run", True)),
    )
    return store.add_observation(obs, at=at)


def ingest_device_json(store: Store, doc: dict, *, at: datetime) -> list[CommitResult]:
    """One device JSON document: a single record, or a batch with records.

    Batch records inherit every top-level key and may override it per
    record. The same calibration certificate guards every inherited row.
    """
    if sensor_support_disabled():
        return [
            _refuse(
                store,
                "R-sensor",
                str(doc.get("device_id") or "device-json"),
                f"{DISABLE_ENV} is set: sensor ingest is switched off",
                at,
            )
        ]
    records = doc.get("records")
    if isinstance(records, list) and records:
        results: list[CommitResult] = []
        # The document's own telemetry is a record too; batch records ride
        # on top of it and inherit every top-level key.
        head = {key: value for key, value in doc.items() if key != "records"}
        results.append(ingest_record(store, head, at=at))
        for item in records:
            if not isinstance(item, dict):
                results.append(
                    _refuse(store, "R-property", "batch", "record must be an object", at)
                )
                continue
            merged = {key: value for key, value in doc.items() if key != "records"}
            merged.update(item)
            results.append(ingest_record(store, merged, at=at))
        return results
    return [ingest_record(store, doc, at=at)]
