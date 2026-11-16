"""Point-in-time reads.

factsAt returns a fact only when it could have been known at t.
associatedAt returns joins and the cell's own support. It does not copy
the result onto the boundary.

Public terms are local classes plus SOSA, GeoSPARQL, OWL Time, QUDT, PROV,
and SKOS. There is no SPARQL server in this build (the production store is
still a human decision).
"""

from __future__ import annotations

from datetime import datetime

from farm_ontology.model import Observation
from farm_ontology.store import Store
from farm_ontology.timeutil import ensure_utc

PUBLIC_TERMS = (
    "fd:",
    "sosa:",
    "ssn:",
    "geo:",
    "time:",
    "qudt:",
    "prov:",
    "skos:",
)

EXAMPLE_QUERIES = (
    "SELECT ?obs ?support ?class WHERE { ?obs a sosa:Observation ; fd:nativeResolution ?support ; fd:useClass ?class }",
    "SELECT ?join ?cell ?support WHERE { ?join a fd:SpatialJoin ; fd:ofObservation ?cell . ?cell fd:nativeResolution ?support }",
)


def _visible(obs: Observation, t: datetime) -> bool:
    if not obs.availability_known or obs.availability_time is None:
        return False
    if obs.availability_time > t:
        return False
    if obs.is_forecast:
        if obs.issue_time is None or obs.issue_time > t:
            return False
    return True


def _superseded(store: Store, iri: str, t: datetime) -> bool:
    for other in store.observations.values():
        if other.revision_of == iri and _visible(other, t):
            return True
    return False


def _resolution(obs: Observation) -> dict | None:
    if obs.native_resolution is None:
        return None
    return {
        "value": obs.native_resolution.value,
        "unit_iri": obs.native_resolution.unit_iri,
    }


def _measurement_row(obs: Observation) -> dict:
    return {
        "record_type": "measurement",
        "is_measurement": True,
        "iri": obs.iri,
        "use_class": obs.use_class,
        "feature_of_interest": obs.feature_of_interest,
        "feature_kind": obs.feature_kind,
        "spatial_support": obs.spatial_support,
        "native_resolution": _resolution(obs),
        "product_kind": obs.product_kind,
        "operations_observation": obs.operations_observation,
        "availability_time": obs.availability_time,
        "issue_time": obs.issue_time,
        "phenomenon_start": obs.phenomenon.start,
        "result_value": None if obs.result is None else obs.result.value,
        "result_unit": None if obs.result is None else obs.result.unit_iri,
        "dry_run": obs.dry_run,
    }


def facts_at(store: Store, t: datetime) -> list[dict]:
    """Return measurements knowable at t, plus refusals already recorded by t.

    The use class is the class stored on the entity. Accepted gates are not
    produced while class C is closed and Q13 is unanswered, so a later
    promotion cannot leak backward.
    """
    t = ensure_utc(t, "t")
    rows: list[dict] = []
    for obs in store.observations.values():
        if not _visible(obs, t) or _superseded(store, obs.iri, t):
            continue
        row = _measurement_row(obs)
        later = [
            gate
            for gate in store.accepted_gates
            if gate["observation"] == obs.iri and gate["time"] <= t
        ]
        if later:
            row["use_class"] = sorted(later, key=lambda item: item["time"])[-1]["to_class"]
        rows.append(row)
    for refusal in store.refusals:
        if refusal.time <= t:
            rows.append(
                {
                    "record_type": "refusal",
                    "is_measurement": False,
                    "iri": refusal.iri,
                    "rule_id": refusal.rule_id,
                    "input_entity": refusal.input_entity,
                    "attempted_change": refusal.attempted_change,
                    "time": refusal.time,
                }
            )
    rows.sort(key=lambda row: row["iri"])
    return rows


def associated_at(store: Store, t: datetime, boundary_iri: str) -> list[dict]:
    t = ensure_utc(t, "t")
    rows = []
    for join in store.joins.values():
        if join.boundary != boundary_iri or join.generated_at > t:
            continue
        obs = store.observations.get(join.observation)
        if obs is None or not _visible(obs, t) or _superseded(store, obs.iri, t):
            continue
        rows.append(
            {
                "record_type": "spatial-join",
                "is_measurement": False,
                "join": join.iri,
                "boundary": join.boundary,
                "observation": obs.iri,
                "cell_feature": obs.feature_of_interest,
                "relation": join.relation,
                "native_resolution": _resolution(obs),
                "cell_result_value": None if obs.result is None else obs.result.value,
                "cell_result_unit": None if obs.result is None else obs.result.unit_iri,
            }
        )
    rows.sort(key=lambda row: row["join"])
    return rows


def observations_of(store: Store, feature_iri: str, t: datetime) -> list[dict]:
    return [
        row
        for row in facts_at(store, t)
        if row["is_measurement"] and row["feature_of_interest"] == feature_iri
    ]
