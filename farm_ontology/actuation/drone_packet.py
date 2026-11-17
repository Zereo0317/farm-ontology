"""Human-operated drone spray packet builder (WS5.2) — paperwork, not autopilot.

A drone spray packet is the portable sheet a HUMAN drone operator flies with:
a KML geofence polygon, a dosage table, the wind/rain/temperature window the
spraying is admitted into, and the advisory it derives from. This module
emits the packet; it never flies anything. There is no autopilot link, no
network call, no machine connection — stdlib only.

``AdvisoryRef`` points at the recommendation-record contract defined in
``decision-infra-roadmap.md`` WS3.5 (agronomy). The agronomy engine does not
exist yet (Phase P1), so callers supply FIXTURE advisory refs; this module
validates their shape, never their agronomy, and says so.

Emission rules (fail closed):
- ANY missing input is a published ``ActuationGap`` — geofence ring, dosage
  table, advisory reference, weather window, and the two stamps
  (``use_class`` and ``permits_financial_use``). A packet is never emitted
  with blanks filled by guesswork.
- ``permits_financial_use`` is an EXPLICIT boolean the caller must have
  derived elsewhere (grants engine, doctrine §4): the builder refuses to
  invent it, and forbids ``None``/"true"-as-string coercion. ``False`` is a
  perfectly respectable value and travels honestly.
- The emitted KML stamps both values verbatim in its metadata, so the flying
  sheet self-describes its licence posture.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

from farm_ontology.actuation.command_ledger import ActuationGap, ActuationRefusal

__all__ = [
    "AdvisoryRef",
    "KML_NAMESPACE",
    "RECOMMENDATION_CONTRACT",
    "WEATHER_WINDOW_FIELDS",
    "build_drone_packet",
    "weather_window_gaps",
]

#: KML 2.2 namespace the emitted document declares.
KML_NAMESPACE = "http://www.opengis.net/kml/2.2"

#: The recommendation-record contract this advisory reference points at.
#: Roadmap WS3.5: "every recommendation is a first-class record: inputs,
#: licences, uncertainties, expiry". Until that package lands (Phase P1),
#: callers pass fixture references only — validated for shape, not agronomy.
RECOMMENDATION_CONTRACT = (
    "farm_ontology.agronomy.RecommendationRecord (decision-infra-roadmap.md "
    "WS3.5; not yet implemented — fixtures only until Phase P1)"
)

#: Mandatory keys of the weather-window payload and what satisfies them.
WEATHER_WINDOW_FIELDS = {
    "window_start_utc": "ISO-8601 aware UTC start of the spraying window",
    "window_end_utc": "ISO-8601 aware UTC end of the spraying window",
    "wind_max_ms": "maximum admissible wind speed in m/s (> 0)",
    "rain_free_hours": "hours after window end expected rain-free (>= 0)",
    "temp_min_c": "minimum admissible air temperature in deg C",
    "temp_max_c": "maximum admissible air temperature in deg C (>= min)",
    "native_support": "non-empty support stamp of the weather data itself",
}

_ALLOWED_ADVISORY_EXTRAS: frozenset[str] = frozenset()


@dataclass(frozen=True)
class AdvisoryRef:
    """Pointer at an agronomy recommendation record (fixture-tolerant).

    ``reference_id`` addresses the recommendation (its future record id);
    ``issuer`` names whoever produced it; ``issued_at`` is an injected,
    timezone-aware ISO-8601 instant (never ``now()``). ``contract`` names the
    record contract — defaulted to the roadmap WS3.5 shape so the pointer is
    meaningful before the engine exists.
    """

    reference_id: str
    issuer: str
    issued_at: str
    contract: str = RECOMMENDATION_CONTRACT

    def validated(self) -> "AdvisoryRef":
        """Refuse an ill-formed advisory reference with a named gap."""
        if not isinstance(self.reference_id, str) or self.reference_id.strip() == "":
            raise ActuationGap(
                "advisory_reference_id_missing",
                "advisory_ref.reference_id must name the recommendation record",
            )
        if not isinstance(self.issuer, str) or self.issuer.strip() == "":
            raise ActuationGap(
                "advisory_issuer_missing", "advisory_ref.issuer is required"
            )
        if not isinstance(self.issued_at, str) or self.issued_at.strip() == "":
            raise ActuationGap(
                "advisory_issued_at_missing",
                "advisory_ref.issued_at must be an injected aware ISO-8601 instant",
            )
        try:
            moment = datetime.fromisoformat(self.issued_at)
        except ValueError as exc:
            raise ActuationGap(
                "advisory_issued_at_unparsable",
                f"advisory_ref.issued_at {self.issued_at!r}: {exc}",
            ) from exc
        if moment.tzinfo is None or moment.utcoffset() is None:
            raise ActuationGap(
                "advisory_issued_at_naive",
                "advisory_ref.issued_at must carry a timezone (replay determinism)",
            )
        if not isinstance(self.contract, str) or self.contract.strip() == "":
            raise ActuationGap(
                "advisory_contract_missing",
                "advisory_ref.contract must name the recommendation-record contract",
            )
        return self

    def to_dict(self) -> dict:
        return {
            "reference_id": self.reference_id,
            "issuer": self.issuer,
            "issued_at": self.issued_at,
            "contract": self.contract,
        }


def weather_window_gaps(window) -> list[str]:
    """Named gaps of a weather-window payload; empty list means usable."""
    if not isinstance(window, dict) or not window:
        return ["weather_window_missing"]
    gaps: list[str] = []
    for key, expectation in WEATHER_WINDOW_FIELDS.items():
        if key not in window or window[key] is None:
            gaps.append(f"weather_window.{key} missing ({expectation})")
    if gaps:
        return gaps
    if not isinstance(window["native_support"], str) or window["native_support"].strip() == "":
        gaps.append("weather_window.native_support must be a non-empty stamp")
    try:
        start = datetime.fromisoformat(str(window["window_start_utc"]))
        end = datetime.fromisoformat(str(window["window_end_utc"]))
    except ValueError as exc:
        gaps.append(f"weather_window ISO instants unparsable: {exc}")
        return gaps
    if start.tzinfo is None or end.tzinfo is None:
        gaps.append("weather_window.window_start_utc/window_end_utc must be aware")
        return gaps
    if end <= start:
        gaps.append("weather_window.window_end_utc must be after window_start_utc")
    for key in ("wind_max_ms", "rain_free_hours", "temp_min_c", "temp_max_c"):
        if isinstance(window[key], bool) or not isinstance(window[key], (int, float)):
            gaps.append(f"weather_window.{key} must be a number")
            return gaps
    if window["wind_max_ms"] <= 0:
        gaps.append("weather_window.wind_max_ms must be > 0")
    if window["rain_free_hours"] < 0:
        gaps.append("weather_window.rain_free_hours must be >= 0")
    if window["temp_max_c"] < window["temp_min_c"]:
        gaps.append("weather_window.temp_max_c must be >= temp_min_c")
    return gaps


def _packet_gaps(
    *, geofence_ring, dosage_table, advisory_ref, weather_window,
    use_class, permits_financial_use,
) -> list[str]:
    """Collect EVERY named gap before deciding anything (verbose refusals)."""
    gaps: list[str] = []
    if not isinstance(geofence_ring, (list, tuple)) or len(geofence_ring) < 3:
        gaps.append(
            "geofence_ring: a KML geofence needs >= 3 (lat, lon) WGS84 points"
        )
    else:
        for index, point in enumerate(geofence_ring):
            if (
                not isinstance(point, (list, tuple))
                or len(point) != 2
                or not all(
                    isinstance(v, (int, float)) and not isinstance(v, bool)
                    for v in point
                )
            ):
                gaps.append(
                    f"geofence_ring[{index}]: each point must be numeric (lat, lon)"
                )
                break
            lat, lon = float(point[0]), float(point[1])
            if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                gaps.append(
                    f"geofence_ring[{index}]: ({lat}, {lon}) outside WGS84 range"
                )
                break
        else:
            if tuple(map(float, geofence_ring[0])) == tuple(
                map(float, geofence_ring[-1])
            ):
                gaps.append(
                    "geofence_ring: pass an open ring; the packet closes the "
                    "polygon itself"
                )
    if not isinstance(dosage_table, dict) or not dosage_table:
        gaps.append("dosage_table: non-empty {zone: {product, dose, unit}} required")
    else:
        for zone, spec in dosage_table.items():
            if not isinstance(zone, str) or zone.strip() == "":
                gaps.append("dosage_table: zone keys must be non-empty strings")
                break
            if not isinstance(spec, dict):
                gaps.append(f"dosage_table[{zone}]: must be a mapping")
                break
            for field in ("product", "dose", "unit"):
                if spec.get(field) in (None, ""):
                    gaps.append(f"dosage_table[{zone}].{field} missing")
            dose = spec.get("dose") if isinstance(spec, dict) else None
            if dose is not None and (
                isinstance(dose, bool) or not isinstance(dose, (int, float)) or dose <= 0
            ):
                gaps.append(f"dosage_table[{zone}].dose must be a positive number")
    if not isinstance(advisory_ref, AdvisoryRef):
        gaps.append(
            "advisory_ref: must be an AdvisoryRef pointing at the "
            f"{RECOMMENDATION_CONTRACT}"
        )
    gaps.extend(weather_window_gaps(weather_window))
    if not isinstance(use_class, str) or use_class.strip() == "":
        gaps.append("use_class: non-empty stamp required on the emitted packet")
    if not isinstance(permits_financial_use, bool):
        gaps.append(
            "permits_financial_use: explicit boolean required (derived from a "
            "written grant elsewhere); the packet never guesses licence state"
        )
    return gaps


def build_drone_packet(
    *,
    geofence_ring,
    dosage_table,
    advisory_ref,
    weather_window,
    use_class: str,
    permits_financial_use: bool,
    designator: str = "",
) -> tuple[bytes, dict]:
    """Return ``(kml_bytes, report)`` or raise with the FULL gap list.

    The KML carries: the geofence polygon, one ``Data`` element per dosage
    zone, the weather window, the advisory reference, and the two stamps
    (``use_class``, ``permits_financial_use``) verbatim.
    """
    gaps = _packet_gaps(
        geofence_ring=geofence_ring,
        dosage_table=dosage_table,
        advisory_ref=advisory_ref,
        weather_window=weather_window,
        use_class=use_class,
        permits_financial_use=permits_financial_use,
    )
    if advisory_ref is not None and isinstance(advisory_ref, AdvisoryRef):
        try:
            advisory_ref.validated()
        except ActuationGap as exc:
            gaps.append(exc.gap + ": " + exc.detail)
    if gaps:
        raise ActuationRefusal(
            "drone_packet_inputs_incomplete",
            "refusing to emit a drone spray packet; collected gaps: "
            + "; ".join(sorted(set(gaps))),
            "supply every named input; a packet with blanks is a hazard, "
            "not a shortcut",
        )
    advisory = advisory_ref.validated()

    ET.register_namespace("", KML_NAMESPACE)
    kml = ET.Element(f"{{{KML_NAMESPACE}}}kml")
    document = ET.SubElement(kml, f"{{{KML_NAMESPACE}}}Document")
    desig = (designator or "").strip() or advisory.reference_id
    ET.SubElement(document, f"{{{KML_NAMESPACE}}}name").text = f"Drone spray: {desig}"

    description_lines = [
        f"use_class={use_class.strip()}",
        f"permits_financial_use={'true' if permits_financial_use else 'false'}",
        f"advisory_reference={advisory.reference_id}",
        f"advisory_issuer={advisory.issuer}",
        f"advisory_issued_at={advisory.issued_at}",
        f"advisory_contract={advisory.contract}",
        "operator_notice=HUMAN-flown packet: the operator flies, this sheet "
        "prescribes. No autopilot link is created by farm-ontology.",
    ]
    ET.SubElement(document, f"{{{KML_NAMESPACE}}}description").text = "\n".join(
        description_lines
    )

    # -- Geofence placemark (KML coords are lon,lat[,alt] — reversed on
    #    purpose; TaskSet callers use lat,lon order instead) -----------------
    placemark = ET.SubElement(document, f"{{{KML_NAMESPACE}}}Placemark")
    ET.SubElement(placemark, f"{{{KML_NAMESPACE}}}name").text = (
        f"Geofence: {desig}"
    )
    polygon = ET.SubElement(placemark, f"{{{KML_NAMESPACE}}}Polygon")
    ET.SubElement(polygon, f"{{{KML_NAMESPACE}}}altitudeMode").text = "clampToGround"
    outer = ET.SubElement(polygon, f"{{{KML_NAMESPACE}}}outerBoundaryIs")
    ring_el = ET.SubElement(outer, f"{{{KML_NAMESPACE}}}LinearRing")
    closed = [tuple(map(float, pt)) for pt in geofence_ring]
    closed.append(closed[0])  # explicit closure of the polygon
    coords_text = " ".join(f"{lon:.7f},{lat:.7f},0" for lat, lon in closed)
    ET.SubElement(ring_el, f"{{{KML_NAMESPACE}}}coordinates").text = coords_text

    # -- Dosage table as typed ExtendedData ---------------------------------
    ext = ET.SubElement(placemark, f"{{{KML_NAMESPACE}}}ExtendedData")
    for zone in sorted(dosage_table):
        spec = dosage_table[zone]
        payload = {
            "product": spec["product"],
            "dose": spec["dose"],
            "unit": spec["unit"],
        }
        data = ET.SubElement(ext, f"{{{KML_NAMESPACE}}}Data", {"name": f"dose:{zone}"})
        ET.SubElement(data, f"{{{KML_NAMESPACE}}}displayName").text = (
            f"Dosage zone {zone}"
        )
        ET.SubElement(data, f"{{{KML_NAMESPACE}}}value").text = json.dumps(
            payload, sort_keys=True, separators=(",", ":")
        )
    for key in sorted(WEATHER_WINDOW_FIELDS):
        data = ET.SubElement(ext, f"{{{KML_NAMESPACE}}}Data", {"name": f"weather:{key}"})
        ET.SubElement(data, f"{{{KML_NAMESPACE}}}value").text = str(weather_window[key])

    kml_bytes = ET.tostring(kml, encoding="utf-8", xml_declaration=True)
    report = {
        "sha256": hashlib.sha256(kml_bytes).hexdigest(),
        "use_class": use_class.strip(),
        "permits_financial_use": permits_financial_use,
        "advisory": advisory.to_dict(),
        "geofence_points": len(geofence_ring),
        "dosage_zones": sorted(dosage_table),
        "weather_window": copy.deepcopy(dict(weather_window)),
        "notice": "human-operated packet; agronomy engine lands Phase P1 — "
        "advisory refs are fixture-shaped until then",
    }
    return kml_bytes, report
