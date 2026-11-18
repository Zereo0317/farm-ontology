"""Harvest-truth intake — the founder's hand-filled truth becomes a record
(Sprint-X1, task-18).

The loop this closes: the engine proposed (GDD stages, maturity windows);
the founder walks the farm once at harvest with a phone and a scale
ticket; THIS module turns what he witnessed into governed observations,
scores the engine's prediction against that truth, and drafts the
one-line ``prediction vs actual`` teaser for the landing report.

SIMPLE BEATS CLEVER. The founder hand-fills ONE JSON template (or
dictates it over the phone to an agent who types it). The template is
flat, every key is pronounceable, every key may be ``null`` except the
parcel and the collection date — at least ONE witnessed evidence item is
required, or the intake refuses with a named gap (an empty truth record
is an oxymoron this module will not store).

Honesty laws inherited unchanged:

* the Store decides (``Store.add_observation`` / ``add_boundary``); this
  module never writes around it;
* ingest assigns ``Screening``; promotion is somebody else's gate;
* dictated entries are typed as FARMER RECALL
  (``procedure/farmer-recall``, ``stated_as_recall``), self-typed
  ticket-in-hand entries as ``procedure/harvest-intake`` — the record
  states whose mouth the truth came from;
* GPS pins become a ``BoundaryVersion`` ONLY through
  ``Store.add_boundary`` with ``tenure='unknown'`` (tenure stays unknown
  until a source exists) and accuracy read from the PHONE SCREEN — a pin
  without a stated accuracy makes the whole version ``accuracy_unknown``
  (unknown stays unknown; it is never averaged into fake metres);
* timestamps are injected; no wall clock is read here.

Self-scoring: the engine re-derives its predicted R8 date from the
season's daily rows and the cultivar profile, then measures the delta to
the ACTUAL weigh date — in calendar days AND in GDD-days (the thermal
time between modelled maturity and the real combine stop). A weigh date
BEFORE predicted R8 is a flagged inconsistency (wet grain or a late
model), not an auto-pass. Tolerance is CONFIG.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Mapping, Sequence

from farm_ontology.agronomy.common import AgronomyGap
from farm_ontology.agronomy.phenology import (
    daily_gdd_contribution,
    profile_or_raise,
)
from farm_ontology.build import mint, screening_licence, screening_method
from farm_ontology.model import (
    BoundaryVersion,
    Interval,
    Observation,
    Quantity,
)
from farm_ontology.namespaces import KIND_MASS, UNIT
from farm_ontology.store import Store
from farm_ontology.timeutil import ensure_utc, parse_time

#: Template contract. A filled bundle must name exactly this.
TEMPLATE_ID = "harvest-truth-v1"

#: Days by which the actual weigh date may trail the predicted R8 date
#: and still count as a HIT. Founder-grade logistics (drying-shed queue,
#: weekends) justify a week; the number is CONFIG, not physics.
HIT_TOLERANCE_DAYS = 7

_UNIT_KILOGM = UNIT + "KiloGM"

_OBSERVED_PROPERTY = mint("observedProperty", "farm-harvest-truth-bundle")

_KNOWN_TEMPLATE_KEYS = frozenset(
    {
        "template", "parcel_iri", "collection_date", "dictated_over_phone",
        "weigh_ticket", "moisture", "grade_certificate", "photos",
        "gps_pins", "operator_notes",
    }
)


# ---------------------------------------------------------------------------
# The template.


def blank_template() -> dict:
    """The EXACT template the founder hand-fills (or dictates).

    Printed in docs/harvest-truth-protocol.md; shipped as
    ``fixtures/harvest/founder-template-blank.json``. Every key may be
    null; every null is honest.
    """
    return {
        "template": TEMPLATE_ID,
        "parcel_iri": None,
        "collection_date": None,
        "dictated_over_phone": None,
        "weigh_ticket": {
            "ticket_number": None,
            "gross_weight_kg": None,
            "weighed_at": None,
            "scale_description": None,
        },
        "moisture": {
            "percent": None,
            "measured_with": None,
            "sample_bag_photo": None,
        },
        "grade_certificate": {
            "present": None,
            "class": None,
            "inspector": None,
            "certificate_photo": None,
        },
        "photos": {
            "combine_display": None,
            "truck_scale_printout": None,
            "field_edge": None,
        },
        "gps_pins": [],
        "operator_notes": None,
    }


# ---------------------------------------------------------------------------
# Parsing.


@dataclass(frozen=True)
class WitnessedFact:
    """One thing the founder's trip actually witnessed."""

    kind: str
    detail: str
    evidence: tuple[tuple[str, object], ...] = ()

    def to_payload(self) -> dict:
        payload = {"kind": self.kind, "detail": self.detail}
        if self.evidence:
            payload["evidence"] = {key: value for key, value in self.evidence}
        return payload


@dataclass(frozen=True)
class HarvestTruthDoc:
    """The parsed, validated founder bundle. Immutable."""

    parcel_iri: str
    collection_date: str               # ISO date of the farm visit
    dictated_over_phone: bool
    weighed_at: datetime | None
    gross_weight_kg: float | None
    ticket_number: str | None
    moisture_percent: float | None
    moisture_measured_with: str | None
    grade_class: str | None
    grade_present: bool
    photo_filenames: tuple[str, ...]
    gps_pins: tuple[dict, ...]         # raw, accuracy-preserving
    operator_notes: str | None
    stated_as_recall: bool
    witnessed: tuple[WitnessedFact, ...]
    unknown_keys_ignored: tuple[str, ...]

    def to_payload(self) -> dict:
        return {
            "parcel_iri": self.parcel_iri,
            "collection_date": self.collection_date,
            "dictated_over_phone": self.dictated_over_phone,
            "stated_as_recall": self.stated_as_recall,
            "weighed_at": self.weighed_at.isoformat() if self.weighed_at else None,
            "gross_weight_kg": self.gross_weight_kg,
            "ticket_number": self.ticket_number,
            "moisture_percent": self.moisture_percent,
            "moisture_measured_with": self.moisture_measured_with,
            "grade_class": self.grade_class,
            "grade_present": self.grade_present,
            "photo_filenames": list(self.photo_filenames),
            "gps_pins": [dict(pin) for pin in self.gps_pins],
            "operator_notes": self.operator_notes,
            "witnessed": [fact.to_payload() for fact in self.witnessed],
            "unknown_keys_ignored": list(self.unknown_keys_ignored),
        }


def _aware(value: object, name: str, template_key: str) -> datetime:
    if isinstance(value, datetime):
        return ensure_utc(value, name)
    if not isinstance(value, str) or not value.strip():
        raise AgronomyGap(
            "malformed-truth-row",
            f"{template_key} must be an ISO-8601 timestamp with a timezone",
            missing=(template_key,),
            remediation="a phone photo time or the clock at the scale",
        )
    try:
        return parse_time(value)
    except ValueError as error:
        raise AgronomyGap(
            "malformed-truth-row",
            f"{template_key}: unparseable timestamp {value!r}: {error}",
        ) from error


def _positive_number(value: object, kind: str, template_key: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AgronomyGap(
            "malformed-truth-row",
            f"{template_key} must be a number, got {value!r}",
        )
    number = float(value)
    if kind == "moisture":
        if not 0.0 < number < 100.0:
            raise AgronomyGap(
                "malformed-truth-row",
                f"{template_key} {number} is not a plausible moisture percent",
            )
        return number
    if number <= 0:
        raise AgronomyGap(
            "malformed-truth-row",
            f"{template_key} must be positive, got {number}",
        )
    return number


def parse_template(doc: Mapping) -> HarvestTruthDoc:
    """Validate the filled template; refuse loudly, tolerate dictation.

    Hand-filled reality is messy: unknown keys are COLLECTED and carried
    on the record (``unknown_keys_ignored``), never silently dropped — a
    dictated stray key surfaces instead of disappearing.
    """
    if not isinstance(doc, Mapping):
        raise AgronomyGap(
            "malformed-template", "the harvest-truth bundle must be a JSON object"
        )
    template_id = doc.get("template")
    if template_id != TEMPLATE_ID:
        raise AgronomyGap(
            "unknown-template",
            f"expected template {TEMPLATE_ID!r}, got {template_id!r}; the "
            "field protocol prints the current one",
            remediation="copy fixtures/harvest/founder-template-blank.json",
        )
    parcel = doc.get("parcel_iri")
    if not isinstance(parcel, str) or not parcel.strip():
        raise AgronomyGap(
            "missing-parcel",
            "parcel_iri binds the truth to a field; the protocol sheet "
            "pre-prints it",
            missing=("parcel_iri",),
        )
    collection = doc.get("collection_date")
    if not isinstance(collection, str) or len(collection) != 10:
        raise AgronomyGap(
            "malformed-truth-row",
            "collection_date must be the farm-visit date as YYYY-MM-DD",
            missing=("collection_date",),
        )
    try:
        date.fromisoformat(collection)
    except ValueError as error:
        raise AgronomyGap(
            "malformed-truth-row",
            f"collection_date {collection!r} is not a real date: {error}",
        ) from error

    dictated = bool(doc.get("dictated_over_phone"))
    unknown_keys = tuple(
        str(key) for key in doc.keys() if key not in _KNOWN_TEMPLATE_KEYS
    )

    ticket = doc.get("weigh_ticket") or {}
    gross = _positive_number(
        ticket.get("gross_weight_kg"), "mass", "weigh_ticket.gross_weight_kg"
    )
    ticket_number = ticket.get("ticket_number")
    if ticket_number is not None and (
        not isinstance(ticket_number, str) or not ticket_number.strip()
    ):
        raise AgronomyGap(
            "malformed-truth-row",
            "weigh_ticket.ticket_number must be a non-empty string (the "
            "physical ticket's number, exactly as printed)",
        )
    weighed_at = (
        _aware(ticket.get("weighed_at"), "weighed_at", "weigh_ticket.weighed_at")
        if ticket.get("weighed_at") is not None
        else None
    )
    if gross is not None and weighed_at is None:
        raise AgronomyGap(
            "malformed-truth-row",
            "a gross weight without its weighed_at timestamp cannot anchor "
            "the R8 comparison",
            missing=("weigh_ticket.weighed_at",),
        )
    if weighed_at is not None and gross is None:
        raise AgronomyGap(
            "malformed-truth-row",
            "weighed_at without gross_weight_kg: the ticket exists but no "
            "mass was entered",
            missing=("weigh_ticket.gross_weight_kg",),
        )

    moisture_blob = doc.get("moisture") or {}
    moisture = _positive_number(
        moisture_blob.get("percent"), "moisture", "moisture.percent"
    )
    moisture_with = moisture_blob.get("measured_with")
    if moisture is not None and (
        not isinstance(moisture_with, str) or not moisture_with.strip()
    ):
        raise AgronomyGap(
            "malformed-truth-row",
            "moisture.percent requires measured_with (a meter id, or "
            "'sample-bag-for-lab')",
            missing=("moisture.measured_with",),
        )

    grade_blob = doc.get("grade_certificate") or {}
    grade_present = bool(grade_blob.get("present"))
    grade_class = grade_blob.get("class")
    if grade_class is not None and not isinstance(grade_class, str):
        raise AgronomyGap(
            "malformed-truth-row", "grade_certificate.class must be a string"
        )

    photos_blob = doc.get("photos") or {}
    photo_names = tuple(
        str(photos_blob[key])
        for key in ("combine_display", "truck_scale_printout", "field_edge")
        if isinstance(photos_blob.get(key), str) and photos_blob.get(key).strip()
    )

    pins_blob = doc.get("gps_pins")
    if pins_blob is None:
        pins_blob = []
    if not isinstance(pins_blob, list):
        raise AgronomyGap(
            "malformed-truth-row", "gps_pins must be a list of pin objects"
        )
    pins: list[dict] = []
    for index, pin in enumerate(pins_blob):
        if not isinstance(pin, Mapping):
            raise AgronomyGap(
                "malformed-truth-row", f"gps_pins[{index}] must be an object"
            )
        lat_raw, lon_raw = pin.get("lat"), pin.get("lon")

        def _decimal_text(value: object, name: str) -> tuple[float, int]:
            """Number + the decimals the founder provably typed.

            Numeric strings keep their typed precision; bare JSON numbers
            degrade to the shortest round-trip repr (typed trailing zeros
            are lost to float parsing — the protocol therefore recommends
            pasting coordinates as strings when precision matters).
            """
            if isinstance(value, str) and value.strip():
                text = value.strip()
                try:
                    number = float(text)
                except ValueError as error:
                    raise AgronomyGap(
                        "malformed-truth-row",
                        f"{name} {value!r} is not a decimal degree",
                    ) from error
                decimals = (
                    len(text.split(".")[1]) if "." in text else 0
                )
                return number, decimals
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return float(value), _decimals_of(float(value))
            raise AgronomyGap(
                "malformed-truth-row",
                f"{name} must be a decimal degree number",
                missing=(name,),
            )

        lat, lat_decimals = _decimal_text(lat_raw, f"gps_pins[{index}].lat")
        lon, lon_decimals = _decimal_text(lon_raw, f"gps_pins[{index}].lon")
        accuracy = pin.get("accuracy_m")
        if accuracy is not None and (
            isinstance(accuracy, bool)
            or not isinstance(accuracy, (int, float))
            or float(accuracy) < 0
        ):
            raise AgronomyGap(
                "malformed-truth-row",
                f"gps_pins[{index}].accuracy_m must be a non-negative number "
                "as read from the phone screen",
            )
        pins.append(
            {
                "lat": lat,
                "lon": lon,
                "accuracy_m": float(accuracy) if accuracy is not None else None,
                "corner": str(pin.get("corner") or f"corner-{index + 1}"),
                "_typed_decimals": min(lat_decimals, lon_decimals),
            }
        )

    witnessed: list[WitnessedFact] = []
    if gross is not None:
        witnessed.append(
            WitnessedFact(
                "weigh-ticket",
                f"gross {gross:g} kg on ticket {ticket_number!r}",
                (("ticket_number", ticket_number), ("gross_weight_kg", gross)),
            )
        )
    if moisture is not None:
        witnessed.append(
            WitnessedFact(
                "moisture", f"{moisture:g} % measured with {moisture_with}"
            )
        )
    if grade_present:
        witnessed.append(
            WitnessedFact("grade-certificate", str(grade_class or "graded"))
        )
    if photo_names:
        witnessed.append(
            WitnessedFact("photos", f"{len(photo_names)} photo(s) attached")
        )
    if pins:
        witnessed.append(
            WitnessedFact(
                "gps-pins",
                f"{len(pins)} corner pin(s), "
                + (
                    "all with stated accuracy"
                    if all(p["accuracy_m"] is not None for p in pins)
                    else "accuracy incomplete on at least one pin"
                ),
            )
        )
    if not witnessed:
        raise AgronomyGap(
            "empty-truth",
            "the bundle witnesses nothing (no weigh ticket, no moisture, "
            "no grade, no photos, no pins); an empty truth record is an "
            "oxymoron and is not stored",
            remediation="bring any ONE evidence item from the protocol checklist",
        )

    return HarvestTruthDoc(
        parcel_iri=parcel.strip(),
        collection_date=collection,
        dictated_over_phone=dictated,
        weighed_at=weighed_at,
        gross_weight_kg=gross,
        ticket_number=(
            ticket_number.strip() if isinstance(ticket_number, str) else None
        ),
        moisture_percent=moisture,
        moisture_measured_with=(
            moisture_with.strip() if isinstance(moisture_with, str) else None
        ),
        grade_class=grade_class,
        grade_present=grade_present,
        photo_filenames=photo_names,
        gps_pins=tuple(pins),
        operator_notes=(
            str(doc["operator_notes"]).strip()
            if isinstance(doc.get("operator_notes"), str)
            and doc["operator_notes"].strip()
            else None
        ),
        stated_as_recall=dictated,
        witnessed=tuple(witnessed),
        unknown_keys_ignored=unknown_keys,
    )


# ---------------------------------------------------------------------------
# Store intake.


def _decimals_of(value: float) -> int:
    text = repr(abs(float(value)))
    return len(text.split(".")[1]) if "." in text else 0


def _ring_is_sane(pins: Sequence[Mapping]) -> bool:
    """Degenerate-ring guard: three collinear points make a line, not a field."""
    (x1, y1), (x2, y2), (x3, y3) = ((pin["lon"], pin["lat"]) for pin in pins[:3])
    doubled_area = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
    return abs(doubled_area) > 1e-9


def _pins_to_boundary(doc: HarvestTruthDoc) -> BoundaryVersion:
    """Three-plus ordered corner pins → the FIRST parcel polygon attempt.

    Accuracy: the WORST stated pin accuracy governs (a chain is as weak
    as its loosest link); any unstated accuracy ⇒ accuracy_unknown. The
    WKT ring is written at six decimals for the closed polygon; the
    DECIMALS THE FOUNDER ACTUALLY TYPED are recorded separately in
    ``coordinate_decimals`` (the typed precision is the honest one).
    """
    if len(doc.gps_pins) < 3:
        raise AgronomyGap(
            "pins-insufficient",
            f"{len(doc.gps_pins)} pin(s) cannot start a polygon; the "
            "protocol asks for three corners minimum",
            remediation="stand on the third corner and pin it",
        )
    if not _ring_is_sane(doc.gps_pins):
        raise AgronomyGap(
            "pins-degenerate",
            "the corner pins are collinear/degenerate; a polygon from them "
            "would be fiction",
            remediation="re-walk the corners; a field is not a line",
        )
    accuracies = [pin["accuracy_m"] for pin in doc.gps_pins]
    any_unknown = any(value is None for value in accuracies)
    worst = None if any_unknown else max(accuracies)
    coords = [(pin["lon"], pin["lat"]) for pin in doc.gps_pins]
    ring_pairs = coords + [coords[0]]
    ring = ", ".join(f"{lon:.6f} {lat:.6f}" for lon, lat in ring_pairs)
    # The decimals the founder PROVABLY typed (the tightest of lat/lon,
    # weakest pin governs), per the parse contract in parse_template.
    decimals = min(int(pin["_typed_decimals"]) for pin in doc.gps_pins)
    stamp = doc.collection_date.replace("-", "")
    return BoundaryVersion(
        iri=mint("boundary", f"bv-harvest-pins-{stamp}"),
        geometry_iri=mint("geometry", f"wkt-harvest-pins-{stamp}"),
        wkt=f"POLYGON (({ring}))",
        crs="EPSG:4326",
        digitising_method="gps-corner-pins-phone",
        boundary_date=parse_time(doc.collection_date + "T12:00:00+00:00"),
        accuracy_unknown=any_unknown,
        accuracy_m=worst,
        area_method="gps-pin-ring (area not yet computed)",
        surveyor="founder-hand-entry",
        tenure="unknown",
        personal_data=False,
        coordinate_decimals=decimals,
        accuracy_note=(
            (
                "phone-screen accuracy, worst of "
                f"{len(doc.gps_pins)} pins"
            )
            if not any_unknown
            else "at least one pin lacked a stated phone-screen accuracy"
        ),
    )


@dataclass(frozen=True)
class IntakeOutcome:
    """Everything one intake run produced or refused. Nothing silent."""

    doc: HarvestTruthDoc
    observation_result: object        # store.CommitResult
    boundary_result: object | None    # store.CommitResult | None
    validation_row: "ValidationRow | None"
    teaser_line: str | None

    def to_payload(self) -> dict:
        refusal = getattr(self.observation_result, "refusal", None)
        refusal_payload = None
        if refusal is not None:
            refusal_payload = {
                "iri": refusal.iri,
                "rule_id": refusal.rule_id,
                "input_entity": refusal.input_entity,
                "attempted_change": refusal.attempted_change,
                "time": refusal.time.isoformat(),
            }
        return {
            "template": TEMPLATE_ID,
            "parcel_iri": self.doc.parcel_iri,
            "observation_iri": getattr(self.observation_result, "iri", None),
            "observation_ok": bool(
                getattr(self.observation_result, "ok", False)
            ),
            "refusal": refusal_payload,
            "boundary_attempted": self.boundary_result is not None,
            "boundary_ok": bool(getattr(self.boundary_result, "ok", False)),
            "validation": (
                self.validation_row.to_payload()
                if self.validation_row is not None
                else None
            ),
            "teaser_line": self.teaser_line,
        }


def intake_harvest_truth(
    store: Store,
    doc: Mapping | HarvestTruthDoc,
    *,
    at: datetime,
    season_rows: Sequence[Mapping] | None = None,
    sowing: datetime | None = None,
    cultivar_profile: str | None = None,
) -> IntakeOutcome:
    """Full intake: parse → observe (Store decides) → boundary attempt →
    self-score (when season context supplied) → teaser.

    Named gaps propagate (parse failures, degenerate pins, unreachable
    R8 in scoring); the STORE's refusals ride the returned CommitResult
    per house convention. ``season_rows``/``sowing``/``cultivar_profile``
    come from the record (WS2 ingest / the store's own season); their
    absence disables scoring HONESTLY — the truth is stored, the
    validation row simply does not exist and the teaser stays None.
    """
    moment = ensure_utc(at, "at")
    parsed = doc if isinstance(doc, HarvestTruthDoc) else parse_template(doc)

    observation = build_harvest_observation(parsed, store, at=moment)
    observation_result = store.add_observation(observation, at=moment)

    boundary_result = None
    if len(parsed.gps_pins) >= 3:
        boundary = _pins_to_boundary(parsed)
        boundary_result = store.add_boundary(boundary, at=moment)

    validation_row = None
    teaser = None
    if season_rows and sowing is not None:
        validation_row = score_weigh_date_against_model(
            season_rows,
            sowing=sowing,
            actual_weigh_date=(
                parsed.weighed_at
                if parsed.weighed_at is not None
                else parse_time(parsed.collection_date + "T12:00:00+00:00")
            ),
            cultivar_profile=cultivar_profile,
            scored_at=moment,
            parcel_iri=parsed.parcel_iri,
        )
        teaser = landing_teaser(validation_row)
    return IntakeOutcome(
        doc=parsed,
        observation_result=observation_result,
        boundary_result=boundary_result,
        validation_row=validation_row,
        teaser_line=teaser,
    )


def build_harvest_observation(
    doc: HarvestTruthDoc, store: Store, *, at: datetime
) -> Observation:
    """The harvest-truth bundle as ONE governed Observation."""
    moment = ensure_utc(at, "at")
    registered = doc.parcel_iri in store.boundaries
    feature = doc.parcel_iri
    stamp = doc.collection_date.replace("-", "")
    iri = mint(
        "observation",
        f"harvest-truth-{stamp}-{feature.rsplit('/', 1)[-1]}",
    )
    if doc.gross_weight_kg is not None:
        result: Quantity | None = Quantity(
            value=float(doc.gross_weight_kg),
            unit_iri=_UNIT_KILOGM,
            quantity_kind_iri=KIND_MASS,
        )
    else:
        result = None
    witnessed_summary = "; ".join(fact.kind for fact in doc.witnessed)
    procedure = (
        "procedure/farmer-recall"
        if doc.stated_as_recall
        else "procedure/harvest-intake"
    )
    return Observation(
        iri=iri,
        # The witnessed event interval: the exact weigh instant when the
        # ticket carries one, else the farm-visit day (aware, positive).
        phenomenon=Interval(
            doc.weighed_at
            if doc.weighed_at is not None
            else parse_time(doc.collection_date + "T00:00:00+00:00"),
            parse_time(doc.collection_date + "T23:59:59+00:00"),
        ),
        generated_at=moment,
        observed_property=_OBSERVED_PROPERTY,
        feature_of_interest=feature,
        feature_kind="boundary" if registered else "parcel-unregistered",
        spatial_support="founder-direct",
        procedure=procedure,
        use_class="Screening",
        licence=screening_licence(),
        method=screening_method(product_version=f"harvest-truth-{TEMPLATE_ID}"),
        personal_data=False,
        availability_time=moment,
        availability_known=True,
        native_resolution=None,
        result=result,
        product_kind=None,
        # When no mass exists the bundle STILL carries witness value; the
        # store's own rule demands an explicit unsupported statement.
        unsupported_reason=(
            None
            if result is not None
            else f"bundle witnessed {witnessed_summary}; no weighbridged mass"
        ),
        stated_as_recall=doc.stated_as_recall,
        gap_reason=None,
        sensor_iri=None,
        calibration_activity=None,
        dry_run=False,
    )


# ---------------------------------------------------------------------------
# Engine self-scoring.


@dataclass(frozen=True)
class ValidationRow:
    """The engine grading its OWN homework against the founder's truth."""

    parcel_iri: str
    cultivar_profile: str
    predicted_r8_date: str
    actual_weigh_date: str
    delta_days: int                  # actual − predicted (negative = early)
    delta_gdd_days: float | None     # GDD accumulated between the two events
    tolerance_days: int
    outcome: str                     # "hit" | "miss"
    plausible_order: bool            # weigh happened at-or-after modelled R8
    notes: tuple[str, ...]
    scored_at: datetime
    engine_config_version: str

    def to_payload(self) -> dict:
        return {
            "parcel_iri": self.parcel_iri,
            "cultivar_profile": self.cultivar_profile,
            "predicted_r8_date": self.predicted_r8_date,
            "actual_weigh_date": self.actual_weigh_date,
            "delta_days": self.delta_days,
            "delta_gdd_days": self.delta_gdd_days,
            "tolerance_days": self.tolerance_days,
            "outcome": self.outcome,
            "plausible_order": self.plausible_order,
            "notes": list(self.notes),
            "scored_at": self.scored_at.isoformat(),
            "engine_config_version": self.engine_config_version,
        }


def predicted_stage_crossing(
    season_rows: Sequence[Mapping],
    *,
    sowing: datetime,
    stage: str,
    cultivar_profile: str | None = None,
) -> tuple[date, float]:
    """First date the running GDD reaches ``stage``'s threshold.

    Returns (date, cumulative-at-crossing). Raises
    ``AgronomyGap("stage-never-reached")`` when the season's rows run out
    first — a refusal to extrapolate, per the house rule.
    """
    profile = profile_or_raise(cultivar_profile)
    table = dict(profile.thresholds)
    if stage not in table:
        raise AgronomyGap(
            "unknown-stage",
            f"stage {stage!r} is not in profile {profile.profile_id!r}",
            missing=(f"stage:{stage}",),
        )
    threshold = table[stage]
    anchor = sowing.date()
    cumulative = 0.0
    for row in season_rows:
        day_raw = row.get("date")
        if not isinstance(day_raw, str):
            continue
        try:
            day = date.fromisoformat(day_raw)
        except ValueError:
            continue
        if day < anchor:
            continue
        value = row.get("t_mean_c")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        cumulative += daily_gdd_contribution(float(value))
        if cumulative >= threshold:
            return day, round(cumulative, 1)
    raise AgronomyGap(
        "stage-never-reached",
        f"the season rows end before {stage} ({threshold:g} GDD; banked "
        f"{cumulative:.1f}); no date is extrapolated",
        remediation="supply daily rows through harvest, or score a lower stage",
    )


def score_weigh_date_against_model(
    season_rows: Sequence[Mapping],
    *,
    sowing: datetime,
    actual_weigh_date: datetime,
    cultivar_profile: str | None = None,
    tolerance_days: int = HIT_TOLERANCE_DAYS,
    scored_at: datetime | None = None,
    parcel_iri: str = "",
) -> ValidationRow:
    """Predicted-R8 vs actual weigh date, in days AND GDD-days."""
    from farm_ontology.agronomy.common import CONFIG_VERSION

    if tolerance_days < 0:
        raise AgronomyGap(
            "malformed-tolerance", "tolerance_days must be non-negative"
        )
    scored = ensure_utc(scored_at or actual_weigh_date, "scored_at")
    profile = profile_or_raise(cultivar_profile)
    predicted_date, _cumulative_at_crossing = predicted_stage_crossing(
        season_rows,
        sowing=sowing,
        stage="R8",
        cultivar_profile=profile.profile_id,
    )
    weigh_day = actual_weigh_date.date()
    delta_days = (weigh_day - predicted_date).days

    # Thermal time between the two events: the GDD the season deposited
    # between modelled maturity and the combine stop (or vice versa).
    between = 0.0
    low, high = min(predicted_date, weigh_day), max(predicted_date, weigh_day)
    for row in season_rows:
        day_raw = row.get("date")
        if not isinstance(day_raw, str):
            continue
        try:
            day = date.fromisoformat(day_raw)
        except ValueError:
            continue
        if low < day <= high:
            value = row.get("t_mean_c")
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            between += daily_gdd_contribution(float(value))

    notes: list[str] = []
    plausible_order = delta_days >= 0
    if not plausible_order:
        notes.append(
            "the combine rolled BEFORE the model's R8: either wet grain "
            "went in early or the model is late — check the moisture%"
        )
    else:
        notes.append(
            f"harvest ran {delta_days} d past modelled maturity "
            f"({between:.1f} GDD-d of dry-down head-room)"
        )
    outcome = "hit" if abs(delta_days) <= tolerance_days else "miss"
    return ValidationRow(
        parcel_iri=parcel_iri,
        cultivar_profile=profile.profile_id,
        predicted_r8_date=predicted_date.isoformat(),
        actual_weigh_date=weigh_day.isoformat(),
        delta_days=delta_days,
        delta_gdd_days=round(between, 1),
        tolerance_days=tolerance_days,
        outcome=outcome,
        plausible_order=plausible_order,
        notes=tuple(notes),
        scored_at=scored,
        engine_config_version=CONFIG_VERSION,
    )


def landing_teaser(row: ValidationRow) -> str:
    """The one-line 'prediction vs actual' for the landing report."""
    sign = "+" if row.delta_days > 0 else ""
    gdd_text = (
        f"{row.delta_gdd_days:+g} GDD-d"
        if row.delta_gdd_days is not None
        else "GDD-d n/a"
    )
    return (
        f"prediction vs actual [{row.parcel_iri or 'parcel'}]: model R8 "
        f"{row.predicted_r8_date} → weigh {row.actual_weigh_date} "
        f"= {sign}{row.delta_days} d ({gdd_text}) — {row.outcome.upper()} "
        f"(±{row.tolerance_days} d tolerance, engine "
        f"{row.engine_config_version})"
    )


# ---------------------------------------------------------------------------
# One-command entry point.


def main(argv: list[str] | None = None) -> int:  # pragma: no cover — CLI glue
    """``python -m farm_ontology.harvest_truth filled.json [--at iso] [--out r.json]``

    Without ``--at``: parse-validate only and print the parsed bundle.
    With ``--at``: full Store intake (observation + boundary attempt +
    scoring when the optional ``_season_rows``/``_sowing``/
    ``_cultivar_profile`` context keys ride in the file) and print the
    outcome payload incl. the teaser line. No network, no wall clock.
    """
    import argparse
    import json
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(prog="harvest_truth")
    parser.add_argument("template", help="path to the filled JSON template")
    parser.add_argument("--at", help="intake instant (ISO-8601, aware)")
    parser.add_argument("--out", help="write the outcome payload to this JSON path")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    raw = json.loads(Path(args.template).read_text(encoding="utf-8"))
    if args.at:
        store = Store()
        season_rows = raw.pop("_season_rows", None)
        sowing_raw = raw.pop("_sowing", None)
        profile = raw.pop("_cultivar_profile", None)
        outcome = intake_harvest_truth(
            store,
            raw,
            at=parse_time(args.at),
            season_rows=season_rows,
            sowing=parse_time(sowing_raw) if sowing_raw else None,
            cultivar_profile=profile,
        )
        payload = outcome.to_payload()
    else:
        payload = parse_template(raw).to_payload()
    if args.out:
        Path(args.out).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
