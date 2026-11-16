"""Publication text. Dropping support, error, licence, or use class fails."""

from __future__ import annotations

from datetime import datetime

from farm_ontology.model import Observation
from farm_ontology.query import associated_at, facts_at
from farm_ontology.rules import Violation
from farm_ontology.store import Store

REQUIRED_MARKERS = ("use_class:", "spatial_support:", "licence:", "error:")


def render_fact(obs: Observation) -> str:
    if obs.error is None:
        error = "unstated"
    else:
        error = obs.error.metric
    resolution = "unstated"
    if obs.native_resolution is not None:
        resolution = f"{obs.native_resolution.value} {obs.native_resolution.unit_iri}"
    kind = obs.product_kind or "unspecified"
    if obs.product_kind == "reanalysis":
        kind = "reanalysis (not a real-time operations observation)"
    result = "gap" if obs.result is None else f"{obs.result.value} {obs.result.unit_iri}"
    return "\n".join(
        [
            f"iri: {obs.iri}",
            f"use_class: {obs.use_class}",
            f"spatial_support: {obs.spatial_support}",
            f"native_resolution: {resolution}",
            f"feature: {obs.feature_of_interest}",
            f"product_kind: {kind}",
            f"licence: {obs.licence.instrument} financial_use={obs.licence.permits_financial_use}",
            f"error: {error}",
            f"result: {result}",
            f"method: {obs.method.product_version}",
        ]
    )


def check_publication(text: str) -> list[Violation]:
    missing = [marker for marker in REQUIRED_MARKERS if marker not in text]
    if not missing:
        return []
    return [
        Violation(
            "R-strip",
            "publication dropped " + ", ".join(marker.rstrip(":") for marker in missing),
        )
    ]


def render_memo(store: Store, t: datetime) -> str:
    lines = [
        f"On {t.isoformat()}, these entities were available.",
        "Each measurement states its phenomenon time, availability time, native spatial support, unit, licence, method version, and an error metric or an explicit unstated mark.",
        "Joins to boundaries are listed separately and do not change that support.",
        "A class B gate is stored only when the reviewer name is set and matches. The observation stays at its stored use class.",
        "Settlement, hedge, trigger, and nature-unit uses were refused.",
        "Hectare weather is present only where a calibrated sensor was present.",
        "Crop cuts, farmer recall, and administrative estimates are different procedures.",
        "Live Earth Engine export: not run.",
    ]
    sensor = False
    for row in facts_at(store, t):
        if not row["is_measurement"]:
            lines.append(
                f"refusal {row['rule_id']}: {row['attempted_change']}"
            )
            continue
        obs = store.observations[row["iri"]]
        if obs.sensor_iri:
            sensor = True
        lines.append(render_fact(obs))
    if not sensor:
        lines.append(
            "No calibrated on-farm sensor is in the facts available at this time. Hectare weather is unsupported."
        )
    for boundary_iri in store.boundaries:
        joins = associated_at(store, t, boundary_iri)
        for join in joins:
            resolution = join["native_resolution"]
            lines.append(
                "join {boundary} associated with cell {cell}; native_resolution {res}; support unchanged".format(
                    boundary=join["boundary"],
                    cell=join["cell_feature"],
                    res=resolution,
                )
            )
    for overlap in store.overlaps.values():
        if overlap.disposition is None:
            lines.append(
                f"overlap {overlap.iri} area_ha {overlap.area_ha} method {overlap.method}; no disposition; not read as distinct plots"
            )
    for gate in store.accepted_gates:
        lines.append(
            "gate {iri}: {frm} to {to}; stored use class unchanged".format(
                iri=gate["iri"],
                frm=gate["from_class"],
                to=gate["to_class"],
            )
        )
    return "\n".join(lines)
