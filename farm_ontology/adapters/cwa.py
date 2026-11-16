"""CWA forecast adapter for the named Taiwan products.

No membership key is read into the repository. Live fetch stays off.
"""

from __future__ import annotations

import os
from datetime import datetime

from farm_ontology.build import kilometres, millimetres, mint, screening_licence, screening_method
from farm_ontology.model import CommitResult, Interval, Observation
from farm_ontology.store import Store
from farm_ontology.timeutil import parse_time


def live_status() -> dict:
    present = bool(os.environ.get("CWA_API_KEY") or os.environ.get("CWA_OPEN_DATA_KEY"))
    return {
        "live_fetch": False,
        "key_present": present,
        "reason": "This build does not call CWA. A membership key is never written into the repository.",
    }


def _forecast_shell(doc: dict, *, feature_kind: str, support: str, resolution, local: str, product_version: str):
    issue = parse_time(doc["issue_time"])
    start = parse_time(doc["valid_time"])
    end = parse_time(doc["valid_end"])
    return Observation(
        iri=mint("observation", local),
        phenomenon=Interval(start, end),
        generated_at=issue,
        observed_property=mint(
            "observedProperty", "cf-p07-v95-precipitation-amount-unresolved"
        ),
        feature_of_interest=mint(feature_kind, local),
        feature_kind=feature_kind,
        spatial_support=support,
        procedure=mint("procedure", "forecast"),
        use_class="Screening",
        licence=screening_licence(),
        method=screening_method(product_version=product_version),
        personal_data=False,
        availability_time=issue,
        native_resolution=resolution,
        result=millimetres(float(doc["value_mm"])),
        is_forecast=True,
        issue_time=issue,
        lead_seconds=int((start - issue).total_seconds()),
        product_kind="forecast",
        dry_run=not bool(doc.get("captured_live", False)),
    )


def load_township(store: Store, doc: dict, *, at: datetime) -> CommitResult:
    service = str(doc.get("service_name") or "").strip()
    instrument = str(doc.get("licence_instrument") or "").strip()
    if not service or not instrument:
        return store._refuse(
            "R-national",
            "bulletin",
            "a national bulletin needs a service name and a licence grant",
            at,
        )
    if doc.get("representative_point") != "township-office":
        return store._refuse(
            "R-foi",
            service,
            "the F-D0047 representative point is the township office, not the field",
            at,
        )
    if not doc.get("issue_time"):
        return store._refuse("R-issue", service, "township forecast requires an issue time", at)
    local = str(doc.get("local") or "cwa-township")
    # The licence instrument from the file replaces the default "grant not recorded"
    # only as text. Financial use stays false (Q11).
    obs = _forecast_shell(
        doc,
        feature_kind="township",
        support="township",
        resolution=None,
        local=local,
        product_version="cwa-fd0047-township-office-not-the-field",
    )
    obs = Observation(
        **{
            **obs.__dict__,
            "licence": screening_licence().__class__(
                instrument=instrument,
                permits_financial_use=False,
                permits_redistribution=False,
                attribution="CWA open data; counsel review not done (Q11)",
                purpose="township narrative",
                territory="Taiwan",
                expiry="none stated",
                rerun_if_vendor_stops="unknown",
            ),
        }
    )
    return store.add_observation(obs, at=at)


def load_wrf(store: Store, doc: dict, *, at: datetime) -> CommitResult:
    service = str(doc.get("service_name") or "").strip()
    instrument = str(doc.get("licence_instrument") or "").strip()
    if not service or not instrument:
        return store._refuse(
            "R-national",
            "wrf",
            "a national bulletin needs a service name and a licence grant",
            at,
        )
    support_km = doc.get("support_km")
    if support_km not in (3, 15, 3.0, 15.0):
        return store._refuse(
            "R-support",
            service,
            "WRF support is the 3 km cell or the 15 km cell named by the file",
            at,
        )
    rewritten = doc.get("rewritten_support_km")
    if rewritten is not None and float(rewritten) != float(support_km):
        return store._refuse(
            "R-support",
            service,
            "a join or a rewrite cannot change the WRF cell size",
            at,
        )
    if not doc.get("issue_time"):
        return store._refuse("R-issue", service, "WRF forecast requires an issue time", at)
    local = str(doc.get("local") or f"cwa-wrf-{int(support_km)}km")
    obs = _forecast_shell(
        doc,
        feature_kind="grid-cell",
        support="grid-cell",
        resolution=kilometres(float(support_km)),
        local=local,
        product_version=f"cwa-wrf-{int(float(support_km))}km",
    )
    return store.add_observation(obs, at=at)
