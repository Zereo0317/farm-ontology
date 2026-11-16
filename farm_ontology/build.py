"""Constructors for screening records. Ingest stays at Screening."""

from __future__ import annotations

from datetime import datetime

from farm_ontology.model import (
    Interval,
    LicenceGrant,
    MethodVersion,
    Observation,
    Quantity,
)
from farm_ontology.namespaces import (
    IRI_BASE,
    KIND_ANGLE,
    KIND_LENGTH,
    KIND_MASS,
    UNIT_DEG,
    UNIT_HA,
    UNIT_KM,
    UNIT_M,
    UNIT_MM,
    UNIT_TONNE,
)


def mint(kind: str, local: str) -> str:
    if not kind or not local or "/" in local or " " in local:
        raise ValueError("local id must be one path segment")
    return f"{IRI_BASE}{kind}/{local}"


def kilometres(value: float) -> Quantity:
    return Quantity(value=value, unit_iri=UNIT_KM, quantity_kind_iri=KIND_LENGTH)


def metres(value: float) -> Quantity:
    return Quantity(value=value, unit_iri=UNIT_M, quantity_kind_iri=KIND_LENGTH)


def millimetres(value: float) -> Quantity:
    return Quantity(value=value, unit_iri=UNIT_MM, quantity_kind_iri=KIND_LENGTH)


def degrees(value: float) -> Quantity:
    return Quantity(value=value, unit_iri=UNIT_DEG, quantity_kind_iri=KIND_ANGLE)


def tonnes(value: float) -> Quantity:
    return Quantity(value=value, unit_iri=UNIT_TONNE, quantity_kind_iri=KIND_MASS)


def tonnes_per_hectare_as_mass(value: float) -> Quantity:
    """A non-conformant quantity: a per-hectare rate labelled with the mass kind."""
    return Quantity(
        value=value,
        unit_iri=UNIT_TONNE,
        quantity_kind_iri=KIND_MASS,
        per_unit_iri=UNIT_HA,
    )


def screening_licence() -> LicenceGrant:
    return LicenceGrant(
        instrument="grant not recorded",
        permits_financial_use=False,
        permits_redistribution=False,
        attribution="none stated",
        purpose="screening",
        territory="not stated",
        expiry="none stated",
        lawful_basis=None,
        rerun_if_vendor_stops="unknown",
    )


def screening_method(**overrides) -> MethodVersion:
    base = dict(
        software_commit="synthetic-fixture",
        ontology_releases=(
            "sosa-ssn-2017-10-19",
            "geosparql-1.1.1",
            "owl-time-recommendation",
            "qudt-referenced-not-vendored",
            "prov-o-2013-04-30",
            "skos-2009-08-18",
            "fd-decision-2026-11-16",
        ),
        product_version="fixture",
    )
    base.update(overrides)
    return MethodVersion(**base)


PRECIP = mint("observedProperty", "cf-p07-v95-precipitation-amount-unresolved")


def grid_observation(
    *,
    local: str,
    feature_local: str,
    resolution: Quantity,
    result: Quantity,
    phenomenon: tuple[datetime, datetime],
    availability: datetime,
    product_kind: str,
    procedure: str | None = None,
    **extra,
) -> Observation:
    start, end = phenomenon
    if procedure is None:
        procedure = (
            mint("procedure", "reanalysis")
            if product_kind == "reanalysis"
            else mint("procedure", "gridded-product")
        )
    return Observation(
        iri=mint("observation", local),
        phenomenon=Interval(start, end),
        generated_at=extra.pop("generated_at", availability),
        observed_property=extra.pop("observed_property", PRECIP),
        feature_of_interest=mint("cell", feature_local),
        feature_kind="grid-cell",
        spatial_support="grid-cell",
        procedure=procedure,
        use_class="Screening",
        licence=extra.pop("licence", screening_licence()),
        method=extra.pop("method", screening_method()),
        personal_data=False,
        availability_time=availability,
        availability_known=True,
        native_resolution=resolution,
        result=result,
        product_kind=product_kind,
        **extra,
    )
