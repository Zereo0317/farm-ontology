"""ISO 11783-10 TaskSet ZIP builder (WS5.1) — offline export only.

Given a WGS84 polygon (parcel boundary ring), a prescription (either a zone
table ``zone -> {product, dose, unit}`` or a gridded prescription bundle) and
a crop-operation code (``IRRIG``, ``SPRAY``, ...), this module produces a
TaskSet-shaped ZIP archive: ``taskdata.xml``, ``taskdata.xsd`` (our packaged
profile schema) and, when the prescription is gridded, ``gridXXXX.bin`` with a
matching ``GridInfo`` element.

VALIDATION BACKLOG — stated plainly, as required by the spec: what is checked
offline is STRUCTURE ONLY (well-formed XML parsed with ElementTree, expected
root tag, namespace-free profile attributes present, Zone/Grid companions
consistent). Validation against a real ISO 11783-10 controller (a tractor
terminal accepting the file) is OUT OF SCOPE here and is pinned to the
Phase-4 field drill — see ``farm_ontology.actuation.gate``
(field_drill_completed) and docs/actuation-interface-spec.md §7. Nothing in
this module talks to a machine or a network; stdlib only
(xml.etree.ElementTree, zipfile, hashlib, io).

Numerically faithful within its claims: the shipped grid encoder implements a
*profile* of ISO 11783-10 grids (BLIN column-major uint16 treatment-zone
codes) honestly labelled as the farm-ontology profile; the same caveat
(applies) — a controller that reads the standard full grid dialect is a
Phase-4 acceptance test, not a promise made here.

House rules hold: every malformed input is a published ``ActuationGap``, a
valid-looking-but-unusable combination is an ``ActuationRefusal``; there is
no default dose, no silent unit conversion, no invented polygon.
"""

from __future__ import annotations

import hashlib
import io
import struct
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from farm_ontology.actuation.command_ledger import (
    ActuationGap,
    ActuationRefusal,
)

__all__ = [
    "KNOWN_OPERATIONS",
    "PROFILE_SCHEMA_VERSION",
    "build_grid_binary",
    "build_taskset_zip",
    "validate_taskset_zip",
]

#: Operation codes this exporter admits. Prescription payloads that do not
#: fit the operation are refused, not coerced (a sprayer does not accept mm).
KNOWN_OPERATIONS = {
    "IRRIG": {"products": ("WATER",)},
    "SPRAY": {"products": None},  # any product; doses validated numerically
}

#: Version of the farm-ontology TaskData profile schema shipped as taskdata.xsd.
PROFILE_SCHEMA_VERSION = "1.0"

_XSD_PATH = Path(__file__).with_name("TaskData.xsd")

_GRID_FILENAME = "grid{:04d}.bin"


# ---------------------------------------------------------------------------
# Input validation helpers.


def _read_packaged_xsd() -> str:
    try:
        return _XSD_PATH.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - packaging defect, not input
        raise ActuationGap(
            "xsd_fixture_missing",
            f"packaged TaskData.xsd unreadable: {exc}",
        ) from exc


def _require_ring(points, gap: str, what: str) -> list[tuple[float, float]]:
    if not isinstance(points, (list, tuple)) or len(points) < 3:
        raise ActuationGap(
            gap, f"{what}: a WGS84 ring needs at least 3 (lat, lon) points"
        )
    parsed: list[tuple[float, float]] = []
    for point in points:
        if (
            not isinstance(point, (list, tuple))
            or len(point) != 2
            or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in point)
        ):
            raise ActuationGap(
                gap, f"{what}: each point must be a numeric (lat, lon) pair"
            )
        lat, lon = float(point[0]), float(point[1])
        if not (-90.0 <= lat <= 90.0):
            raise ActuationGap(gap, f"{what}: latitude {lat} outside [-90, 90]")
        if not (-180.0 <= lon <= 180.0):
            raise ActuationGap(gap, f"{what}: longitude {lon} outside [-180, 180]")
        parsed.append((lat, lon))
    first, last = parsed[0], parsed[-1]
    if first == last:
        raise ActuationGap(
            gap,
            f"{what}: pass an open ring (first point not repeated); the exporter "
            "closes the polygon itself",
        )
    return parsed


def _fmt(value: float) -> str:
    return f"{float(value):.7f}".rstrip("0").rstrip(".")


def _validate_operation(operation: str) -> str:
    op = operation.strip().upper() if isinstance(operation, str) else ""
    if op not in KNOWN_OPERATIONS:
        raise ActuationGap(
            "operation_unknown",
            f"crop operation {operation!r} not in {sorted(KNOWN_OPERATIONS)}",
            "register the operation code in taskset_export.KNOWN_OPERATIONS first",
        )
    return op


def _validate_zone_table(zone_table, operation: str) -> dict:
    if not isinstance(zone_table, dict) or not zone_table:
        raise ActuationGap(
            "prescription_missing",
            "zone_table must be a non-empty {zone: {product, dose, unit}} mapping",
        )
    cleaned: dict[str, dict] = {}
    allowed_products = KNOWN_OPERATIONS[operation]["products"]
    for zone, spec in zone_table.items():
        if not isinstance(zone, str) or zone.strip() == "":
            raise ActuationGap(
                "zone_id_ill_formed", f"zone keys must be non-empty strings, got {zone!r}"
            )
        if not isinstance(spec, dict):
            raise ActuationGap(
                "zone_spec_ill_formed",
                f"zone {zone!r}: prescription must be a "
                "{product, dose, unit} mapping",
            )
        product = spec.get("product")
        dose = spec.get("dose")
        unit = spec.get("unit")
        if not isinstance(product, str) or product.strip() == "":
            raise ActuationGap(
                "product_missing", f"zone {zone!r}: product is required"
            )
        if allowed_products is not None and product.upper() not in allowed_products:
            raise ActuationRefusal(
                "product_wrong_for_operation",
                f"operation {operation} admits products "
                f"{allowed_products}; zone {zone!r} carries {product!r}",
            )
        if (
            not isinstance(dose, (int, float))
            or isinstance(dose, bool)
            or dose <= 0
        ):
            raise ActuationGap(
                "dose_ill_formed",
                f"zone {zone!r}: dose must be a positive number (never inferred)",
            )
        if not isinstance(unit, str) or unit.strip() == "":
            raise ActuationGap(
                "unit_missing", f"zone {zone!r}: dose unit is required and travels verbatim"
            )
        cleaned[zone.strip()] = {
            "product": product.strip(),
            "dose": float(dose),
            "unit": unit.strip(),
        }
    return cleaned


def _require_stamps(prescription: dict) -> tuple[str, str]:
    native_support = prescription.get("native_support")
    use_class = prescription.get("use_class")
    if not isinstance(native_support, str) or native_support.strip() == "":
        raise ActuationGap(
            "native_support_missing",
            "prescription must carry a non-empty 'native_support' stamp",
        )
    if not isinstance(use_class, str) or use_class.strip() == "":
        raise ActuationGap(
            "use_class_missing",
            "prescription must carry a non-empty 'use_class' stamp",
        )
    return native_support.strip(), use_class.strip()


# ---------------------------------------------------------------------------
# Grid encoding (farm-ontology BLIN profile, honestly labelled).


def build_grid_binary(grid) -> tuple[bytes, dict]:
    """Encode a gridded prescription to (binary, grid_meta).

    ``grid`` shape (all mandatory)::

        {"min_lat": float, "min_lon": float,
         "cell_deg_lat": float, "cell_deg_lon": float,
         "n_rows": int, "n_cols": int,
         "codes": [[uint16 zone code per cell, row-major] per row]}

    Encoding: unsigned 16-bit little-endian treatment-zone codes, column-major
    (BLIN order), first cell = (min_lat, min_lon) corner. No production data,
    no dose floats — codes index the TaskData TreatmentZone table.
    """
    if not isinstance(grid, dict):
        raise ActuationGap("grid_ill_formed", "grid must be a mapping")
    for key in (
        "min_lat",
        "min_lon",
        "cell_deg_lat",
        "cell_deg_lon",
        "n_rows",
        "n_cols",
    ):
        if key not in grid:
            raise ActuationGap("grid_missing_field", f"grid.{key} is required")
    try:
        min_lat = float(grid["min_lat"])
        min_lon = float(grid["min_lon"])
        cell_lat = float(grid["cell_deg_lat"])
        cell_lon = float(grid["cell_deg_lon"])
        n_rows = int(grid["n_rows"])
        n_cols = int(grid["n_cols"])
    except (TypeError, ValueError) as exc:
        raise ActuationGap(
            "grid_ill_formed", f"grid numeric fields unusable: {exc}"
        ) from exc
    for name, value in (("cell_deg_lat", cell_lat), ("cell_deg_lon", cell_lon)):
        if value <= 0:
            raise ActuationGap(
                "grid_cell_nonpositive", f"grid.{name} must be positive"
            )
    if n_rows <= 0 or n_cols <= 0:
        raise ActuationGap(
            "grid_shape_nonpositive", "grid.n_rows/n_cols must be positive integers"
        )
    if not (-90.0 <= min_lat <= 90.0) or not (-180.0 <= min_lon <= 180.0):
        raise ActuationGap(
            "grid_origin_out_of_range", "grid.min_lat/min_lon outside WGS84 range"
        )
    codes = grid.get("codes")
    if (
        not isinstance(codes, (list, tuple))
        or len(codes) != n_rows
        or any(not isinstance(row, (list, tuple)) or len(row) != n_cols for row in codes)
    ):
        raise ActuationGap(
            "grid_codes_shape",
            f"grid.codes must be {n_rows} rows x {n_cols} cols",
        )
    flat: list[int] = []
    max_code = 0
    min_code: int | None = None
    for row in codes:
        for value in row:
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or not (0 <= value <= 65535)
            ):
                raise ActuationGap(
                    "grid_code_ill_formed",
                    f"grid codes must be ints in [0, 65535], got {value!r}",
                )
            flat.append(value)
            max_code = max(max_code, value)
            min_code = value if min_code is None else min(min_code, value)
    # BLIN: column-major, north row first within each column.
    blin: list[int] = []
    for col in range(n_cols):
        for row in range(n_rows):
            blin.append(flat[row * n_cols + col])
    payload = struct.pack(f"<{len(blin)}H", *blin)
    meta = {
        "GridMinNorth": _fmt(min_lat),
        "GridMinEast": _fmt(min_lon),
        "GridCellWidth": _fmt(cell_lon),
        "GridCellHeight": _fmt(cell_lat),
        "GridRowCount": str(n_rows),
        "GridColumnCount": str(n_cols),
        "MaximumTreatmentZoneCode": str(max_code),
        "MinimumTreatmentZoneCode": str(min_code if min_code is not None else 0),
    }
    return payload, meta


# ---------------------------------------------------------------------------
# TaskData.xml construction.


def _taskdata_xml(
    *,
    ring,
    zone_table: dict | None,
    grid_meta: dict | None,
    operation: str,
    stamps: tuple[str, str],
    partfield_id: str,
    task_id: str,
    designator: str,
) -> bytes:
    native_support, use_class = stamps
    root = ET.Element(
        "Iso11783TaskData",
        {
            "VersionMajor": "4",
            "VersionMinor": PROFILE_SCHEMA_VERSION,
            "DataTransferOrigin": "2",
            "ManagementSoftwareManufacturer": "farm-ontology",
            "ManagementSoftwareVersion": PROFILE_SCHEMA_VERSION,
            "TransferFileLanguage": "en",
        },
    )
    ET.SubElement(
        root,
        "Partfield",
        {
            "PartfieldId": partfield_id,
            "PartfieldDesignator": designator,
        },
    )
    partfield = root.find("Partfield")
    polygon = ET.SubElement(partfield, "Polygon", {"PolygonType": "1"})
    for lat, lon in ring:
        ET.SubElement(
            polygon,
            "Point",
            {"PointNorth": _fmt(lat), "PointEast": _fmt(lon)},
        )
    if zone_table:
        for zone, spec in zone_table.items():
            tz = ET.SubElement(
                partfield,
                "TreatmentZone",
                {
                    "TreatmentZoneCode": zone,
                    "TreatmentZoneDesignator": f"{spec['product']} {spec['dose']:g} {spec['unit']}",
                },
            )
            ET.SubElement(
                tz,
                "Attr",
                {
                    "AttName": "product",
                    "AttValue": spec["product"],
                    "Unit": "unitless",
                },
            )
            ET.SubElement(
                tz,
                "Attr",
                {
                    "AttName": spec["product"].upper(),
                    "AttValue": f"{spec['dose']:g}",
                    "Unit": spec["unit"],
                },
            )
    task_attrs = {
        "TaskId": task_id,
        "TaskDesignator": designator,
        "TaskStatus": "1",  # planned
        "TaskTreatmentProcessCode": operation,
        "TaskPartfieldIdRef": partfield_id,
        "DefaultQuantityValuesFlag": "1",
        "UseClass": use_class,
    }
    task = ET.SubElement(root, "Task", task_attrs)
    task.set("NativeSupport", native_support)
    if grid_meta is not None:
        ET.SubElement(
            task,
            "GridInfo",
            {
                **grid_meta,
                "GridFileReference": _GRID_FILENAME.format(1),
            },
        )
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


# ---------------------------------------------------------------------------
# ZIP assembly and offline structural validation.


def build_taskset_zip(
    *,
    polygon_ring,
    prescription,
    operation: str,
    partfield_id: str,
    task_id: str,
    designator: str = "",
) -> tuple[bytes, dict]:
    """Return ``(zip_bytes, report)`` for a TaskSet shaped archive.

    ``prescription`` is either ``{"zone_table": {...}, "native_support": ...,
    "use_class": ...}`` (table mode) or the same plus ``{"grid": {...}}``
    (gridded mode; zone_table then still describes the zone codes).
    ``report`` carries the archive members and their sha256 for the command
    ledger receipt.
    """
    op = _validate_operation(operation)
    if not isinstance(prescription, dict):
        raise ActuationGap(
            "prescription_missing", "prescription must be a mapping"
        )
    stamps = _require_stamps(prescription)
    pf_id = partfield_id.strip() if isinstance(partfield_id, str) else ""
    tk_id = task_id.strip() if isinstance(task_id, str) else ""
    if pf_id == "":
        raise ActuationGap("partfield_id_missing", "partfield_id is required")
    if tk_id == "":
        raise ActuationGap("task_id_missing", "task_id is required")
    desig = designator.strip() if isinstance(designator, str) else pf_id

    ring = _require_ring(polygon_ring, "polygon_ring_ill_formed", "polygon_ring")

    zone_table = prescription.get("zone_table")
    grid_payload_meta = None
    if zone_table is not None:
        cleaned = _validate_zone_table(zone_table, op)
    else:
        raise ActuationGap(
            "prescription_missing",
            "prescription.zone_table is required (zone -> {product, dose, unit}); "
            "grid-only prescriptions still declare their zone table",
        )
    grid_meta = None
    grid_bytes = None
    if "grid" in prescription and prescription["grid"] is not None:
        grid_bytes, grid_meta = build_grid_binary(prescription["grid"])

    xml_bytes = _taskdata_xml(
        ring=ring,
        zone_table=cleaned,
        grid_meta=grid_meta,
        operation=op,
        stamps=stamps,
        partfield_id=pf_id,
        task_id=tk_id,
        designator=desig or pf_id,
    )
    xsd_text = _read_packaged_xsd()

    buf = io.BytesIO()
    members: dict[str, str] = {}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("taskdata.xml", xml_bytes)
        members["taskdata.xml"] = hashlib.sha256(xml_bytes).hexdigest()
        zf.writestr("taskdata.xsd", xsd_text)
        members["taskdata.xsd"] = hashlib.sha256(xsd_text.encode("utf-8")).hexdigest()
        if grid_bytes is not None:
            name = _GRID_FILENAME.format(1)
            zf.writestr(name, grid_bytes)
            members[name] = hashlib.sha256(grid_bytes).hexdigest()
    report = {
        "members": members,
        "operation": op,
        "task_id": tk_id,
        "partfield_id": pf_id,
        "use_class": stamps[1],
        "native_support": stamps[0],
    }
    return buf.getvalue(), report


def validate_taskset_zip(zip_bytes) -> dict:
    """Offline structural validation of a TaskSet ZIP.

    Opens the archive, parses ``taskdata.xml`` with ElementTree, asserts the
    expected root element and the mandatory profile attributes, checks that a
    ``GridInfo`` reference names a member really present in the ZIP, and —
    when the packaged XSD travelled along — parses the XSD itself for
    well-formedness. Structural only, per module docstring.
    """
    if not isinstance(zip_bytes, (bytes, bytearray)) or len(zip_bytes) == 0:
        raise ActuationGap(
            "taskset_bytes_missing", "validate_taskset_zip needs non-empty ZIP bytes"
        )
    problems: list[str] = []
    try:
        zf = zipfile.ZipFile(io.BytesIO(bytes(zip_bytes)))
    except (zipfile.BadZipFile, OSError) as exc:
        raise ActuationGap("taskset_zip_unreadable", f"not a readable ZIP: {exc}") from exc
    names = set(zf.namelist())
    for required in ("taskdata.xml", "taskdata.xsd"):
        if required not in names:
            problems.append(f"member missing: {required}")
    if problems:
        raise ActuationRefusal(
            "taskset_structure_invalid", "; ".join(problems)
        )
    try:
        root = ET.fromstring(zf.read("taskdata.xml"))
    except ET.ParseError as exc:
        raise ActuationRefusal(
            "taskset_xml_unparsable", f"taskdata.xml does not parse: {exc}"
        ) from exc
    if root.tag != "Iso11783TaskData":
        problems.append(f"unexpected root element {root.tag!r}")
    for attr in ("VersionMajor", "VersionMinor", "DataTransferOrigin",
                 "ManagementSoftwareManufacturer", "ManagementSoftwareVersion"):
        if root.get(attr) in (None, ""):
            problems.append(f"root attribute missing: {attr}")
    partfields = root.findall("Partfield")
    if not partfields:
        problems.append("no Partfield element")
    for partfield in partfields:
        pf_id = partfield.get("PartfieldId")
        if not pf_id:
            problems.append("Partfield without PartfieldId")
        polygon = partfield.find("Polygon")
        if polygon is None:
            problems.append(f"Partfield {pf_id!r} without Polygon")
        else:
            pts = polygon.findall("Point")
            if len(pts) < 3:
                problems.append(
                    f"Partfield {pf_id!r} polygon has {len(pts)} points (<3)"
                )
            for pt in pts:
                if not pt.get("PointNorth") or not pt.get("PointEast"):
                    problems.append(
                        f"Partfield {pf_id!r} point missing PointNorth/PointEast"
                    )
    tasks = root.findall("Task")
    if not tasks:
        problems.append("no Task element")
    pf_ids = {pf.get("PartfieldId") for pf in partfields}
    for task in tasks:
        tid = task.get("TaskId")
        for attr in ("TaskStatus", "TaskTreatmentProcessCode", "TaskPartfieldIdRef",
                     "DefaultQuantityValuesFlag", "UseClass"):
            if task.get(attr) in (None, ""):
                problems.append(f"Task {tid!r} attribute missing: {attr}")
        if task.get("TaskPartfieldIdRef") not in pf_ids:
            problems.append(
                f"Task {tid!r} references unknown Partfield "
                f"{task.get('TaskPartfieldIdRef')!r}"
            )
        grid_infos = task.findall("GridInfo")
        if len(grid_infos) > 1:
            problems.append(f"Task {tid!r} carries more than one GridInfo")
        for gi in grid_infos:
            ref = gi.get("GridFileReference")
            if not ref:
                problems.append(f"Task {tid!r} GridInfo without GridFileReference")
            elif ref not in names:
                problems.append(
                    f"Task {tid!r} GridInfo references member {ref!r} "
                    "absent from the ZIP"
                )
            for attr in ("GridMinNorth", "GridMinEast", "GridCellWidth",
                         "GridCellHeight", "GridRowCount", "GridColumnCount",
                         "MaximumTreatmentZoneCode", "MinimumTreatmentZoneCode"):
                if gi.get(attr) in (None, ""):
                    problems.append(f"Task {tid!r} GridInfo attribute missing: {attr}")
    try:
        ET.fromstring(zf.read("taskdata.xsd"))
    except ET.ParseError as exc:
        problems.append(f"taskdata.xsd not well-formed: {exc}")
    if problems:
        raise ActuationRefusal(
            "taskset_structure_invalid",
            "; ".join(sorted(set(problems))),
        )
    return {
        "ok": True,
        "members": sorted(names),
        "root": root.tag,
        "partfields": len(partfields),
        "tasks": len(tasks),
        "gridded": any(t.findall("GridInfo") for t in tasks),
    }
