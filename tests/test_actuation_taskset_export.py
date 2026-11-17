"""Tests for the ISO 11783-10 TaskSet ZIP builder (WS5.1, structural only)."""

import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from farm_ontology.actuation.taskset_export import (
    PROFILE_SCHEMA_VERSION,
    build_grid_binary,
    build_taskset_zip,
    validate_taskset_zip,
)
from farm_ontology.actuation.command_ledger import ActuationGap, ActuationRefusal

_RING = [(42.7000, 142.4000), (42.7100, 142.4000), (42.7100, 142.4100), (42.7000, 142.4100)]
_TABLE = {
    "1": {"product": "WATER", "dose": 12.5, "unit": "mm"},
    "2": {"product": "WATER", "dose": 5.0, "unit": "mm"},
}
_PRESCRIPTION_BASE = {"native_support": "grid-era5-9km", "use_class": "field-ops"}

_GRID = {
    "min_lat": 42.7000,
    "min_lon": 142.4000,
    "cell_deg_lat": 0.0025,
    "cell_deg_lon": 0.0025,
    "n_rows": 2,
    "n_cols": 3,
    "codes": [[1, 2, 1], [1, 1, 2]],
}


def _prescription(extra=None):
    out = dict(_PRESCRIPTION_BASE)
    out["zone_table"] = {zone: dict(spec) for zone, spec in _TABLE.items()}
    if extra:
        out.update(extra)
    return out


def _build(operation="IRRIG", **overrides):
    kwargs = dict(
        polygon_ring=list(_RING),
        prescription=_prescription(),
        operation=operation,
        partfield_id="PF-BIRATORI-01",
        task_id="T-2027-0001",
        designator="Biratori north paddock",
    )
    kwargs.update(overrides)
    return build_taskset_zip(**kwargs)


class HappyPathTests(unittest.TestCase):
    def test_table_mode_builds_and_validates(self):
        blob, report = _build()
        members = sorted(report["members"])
        self.assertEqual(members, ["taskdata.xml", "taskdata.xsd"])
        result = validate_taskset_zip(blob)
        self.assertTrue(result["ok"])
        self.assertEqual(result["root"], "Iso11783TaskData")
        self.assertFalse(result["gridded"])
        self.assertEqual(report["operation"], "IRRIG")
        self.assertEqual(report["use_class"], "field-ops")
        self.assertEqual(report["native_support"], "grid-era5-9km")

    def test_xml_carries_polygon_points_and_zone_attrs(self):
        blob, _ = _build()
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            root = ET.fromstring(zf.read("taskdata.xml"))
            self.assertEqual(root.tag, "Iso11783TaskData")
            self.assertEqual(root.get("ManagementSoftwareManufacturer"), "farm-ontology")
            self.assertEqual(root.get("VersionMinor"), PROFILE_SCHEMA_VERSION)
            partfield = root.find("Partfield")
            self.assertIsNotNone(partfield)
            points = partfield.findall("./Polygon/Point")
            self.assertEqual(len(points), len(_RING))
            self.assertEqual(points[0].get("PointNorth"), "42.7")
            self.assertEqual(points[0].get("PointEast"), "142.4")
            zones = partfield.findall("TreatmentZone")
            self.assertEqual(len(zones), 2)
            first_attr = zones[0].findall("Attr")
            names = {a.get("AttName") for a in first_attr}
            self.assertIn("WATER", names)
            dose_attr = next(a for a in first_attr if a.get("AttName") == "WATER")
            self.assertEqual(dose_attr.get("AttValue"), "12.5")
            self.assertEqual(dose_attr.get("Unit"), "mm")
            task = root.find("Task")
            self.assertEqual(task.get("TaskTreatmentProcessCode"), "IRRIG")
            self.assertEqual(task.get("TaskPartfieldIdRef"), "PF-BIRATORI-01")
            self.assertEqual(task.get("UseClass"), "field-ops")
            self.assertEqual(task.get("NativeSupport"), "grid-era5-9km")

    def test_grid_mode_embeds_isogrid_and_gridinfo(self):
        blob, _ = _build(prescription=_prescription({"grid": dict(_GRID)}))
        result = validate_taskset_zip(blob)
        self.assertTrue(result["ok"])
        self.assertTrue(result["gridded"])
        self.assertIn("grid0001.bin", result["members"])
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            root = ET.fromstring(zf.read("taskdata.xml"))
            gi = root.find("./Task/GridInfo")
            self.assertIsNotNone(gi)
            self.assertEqual(gi.get("GridFileReference"), "grid0001.bin")
            self.assertEqual(gi.get("GridRowCount"), "2")
            self.assertEqual(gi.get("GridColumnCount"), "3")
            self.assertEqual(gi.get("MaximumTreatmentZoneCode"), "2")
            self.assertEqual(gi.get("MinimumTreatmentZoneCode"), "1")
            self.assertEqual(gi.get("GridMinNorth"), "42.7")
            raw = zf.read("grid0001.bin")
            # BLIN column-major uint16 LE: col0 rows[1,1], col1 rows[2,1], col2 rows[1,2]
            expected = bytes([1, 0, 1, 0, 2, 0, 1, 0, 1, 0, 2, 0])
            self.assertEqual(raw, expected)

    def test_build_is_deterministic(self):
        blob_a, report_a = _build()
        blob_b, report_b = _build()
        self.assertEqual(blob_a, blob_b)
        self.assertEqual(report_a, report_b)

    def test_xsd_travels_inside_the_zip_and_parses(self):
        blob, _ = _build()
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            xsd = zf.read("taskdata.xsd").decode("utf-8")
        root = ET.fromstring(xsd)
        self.assertEqual(root.tag, "{http://www.w3.org/2001/XMLSchema}schema")
        names = {
            el.get("name")
            for el in root.findall("{http://www.w3.org/2001/XMLSchema}element")
        }
        self.assertIn("Iso11783TaskData", names)
        self.assertIn("Phase-4 field drill", xsd)  # honesty note carried along


class ValidationRefusalTests(unittest.TestCase):
    def _problem_names(self, exc: ActuationRefusal) -> str:
        return exc.detail

    def test_validator_rejects_non_zip(self):
        with self.assertRaises(ActuationGap) as ctx:
            validate_taskset_zip(b"certainly not a zip")
        self.assertEqual(ctx.exception.gap, "taskset_zip_unreadable")

    def test_validator_flags_corrupted_xml_member(self):
        blob, _ = _build()
        with zipfile.ZipFile(io.BytesIO(blob)) as zin, io.BytesIO() as out:
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
                for info in zin.infolist():
                    data = zin.read(info.filename)
                    if info.filename == "taskdata.xml":
                        data = data[:-6]  # chop the closing tag
                    zf.writestr(info, data)
            with self.assertRaises(ActuationRefusal) as ctx:
                validate_taskset_zip(out.getvalue())
            self.assertIn("does not parse", ctx.exception.detail)

    def test_validator_flags_grid_reference_without_member(self):
        blob, _ = _build(prescription=_prescription({"grid": dict(_GRID)}))
        with zipfile.ZipFile(io.BytesIO(blob)) as zin, io.BytesIO() as out:
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
                for info in zin.infolist():
                    if info.filename == "grid0001.bin":
                        continue  # orphan the GridInfo reference
                    zf.writestr(info, zin.read(info.filename))
            with self.assertRaises(ActuationRefusal) as ctx:
                validate_taskset_zip(out.getvalue())
            self.assertIn("absent from the ZIP", ctx.exception.detail)

    def test_validator_flags_bad_root_and_missing_attributes(self):
        blob, _ = _build()
        with zipfile.ZipFile(io.BytesIO(blob)) as zin:
            xml = zin.read("taskdata.xml")
        root = ET.fromstring(xml)
        root.tag = "WrongRoot"
        root.attrib.pop("VersionMajor", None)
        mutated = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        with zipfile.ZipFile(io.BytesIO(blob)) as zin, io.BytesIO() as out:
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
                for info in zin.infolist():
                    zf.writestr(info, mutated if info.filename == "taskdata.xml" else zin.read(info.filename))
            with self.assertRaises(ActuationRefusal) as ctx:
                validate_taskset_zip(out.getvalue())
            detail = ctx.exception.detail
            self.assertIn("unexpected root element", detail)
            self.assertIn("VersionMajor", detail)

    def test_validator_flags_pointless_task_reference(self):
        blob, _ = _build()
        with zipfile.ZipFile(io.BytesIO(blob)) as zin:
            xml = zin.read("taskdata.xml")
        root = ET.fromstring(xml)
        root.find("Task").set("TaskPartfieldIdRef", "PF-NOWHERE")
        mutated = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        with zipfile.ZipFile(io.BytesIO(blob)) as zin, io.BytesIO() as out:
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
                for info in zin.infolist():
                    zf.writestr(info, mutated if info.filename == "taskdata.xml" else zin.read(info.filename))
            with self.assertRaises(ActuationRefusal):
                validate_taskset_zip(out.getvalue())


class InputGapTests(unittest.TestCase):
    def test_ring_gaps(self):
        for ring, frag in (
            ([], "needs at least 3"),
            (_RING[:2], "needs at least 3"),
            ([("lat", "lon")] * 4, "numeric (lat, lon) pair"),
            ([(_RING[0][0], 999.0)] + _RING[1:], "outside [-180, 180]"),
            ([(99.0, 142.4)] + _RING[1:], "outside [-90, 90]"),
            (_RING + [_RING[0]], "open ring"),
        ):
            with self.subTest(ring=frag):
                with self.assertRaises(ActuationGap) as ctx:
                    _build(polygon_ring=ring)
                self.assertEqual(ctx.exception.gap, "polygon_ring_ill_formed")
                self.assertIn("polygon", ctx.exception.detail.lower())

    def test_operation_gaps(self):
        with self.assertRaises(ActuationGap) as ctx:
            _build(operation="HARVEST")
        self.assertEqual(ctx.exception.gap, "operation_unknown")

    def test_irrigation_refuses_non_water_product(self):
        rx = _prescription()
        rx["zone_table"]["1"] = {"product": "FUNGICIDE-X", "dose": 1.0, "unit": "L/ha"}
        with self.assertRaises(ActuationRefusal) as ctx:
            _build(prescription=rx)
        self.assertEqual(ctx.exception.refusal, "product_wrong_for_operation")

    def test_stamp_gaps(self):
        for drop in ("native_support", "use_class"):
            rx = _prescription()
            rx.pop(drop)
            with self.subTest(stamp=drop):
                with self.assertRaises(ActuationGap) as ctx:
                    _build(prescription=rx)
                self.assertEqual(ctx.exception.gap, f"{drop}_missing")

    def test_zone_table_gaps(self):
        cases = [
            ({}, "non-empty"),
            ({1: {"product": "WATER", "dose": 1, "unit": "mm"}}, "non-empty strings"),
            ({"1": [1, 2]}, "must be a"),
            ({"1": {"dose": 1, "unit": "mm"}}, "product is required"),
            ({"1": {"product": "WATER", "dose": 0, "unit": "mm"}}, "positive number"),
            ({"1": {"product": "WATER", "dose": True, "unit": "mm"}}, "positive number"),
            ({"1": {"product": "WATER", "dose": 2.0}}, "dose unit is required"),
        ]
        for table, fragment in cases:
            with self.subTest(table=fragment):
                rx = _prescription()
                rx["zone_table"] = table
                with self.assertRaises(ActuationGap) as ctx:
                    _build(prescription=rx)
                self.assertIn(fragment, ctx.exception.detail)

    def test_identifier_gaps(self):
        with self.assertRaises(ActuationGap) as ctx:
            _build(partfield_id="   ")
        self.assertEqual(ctx.exception.gap, "partfield_id_missing")
        with self.assertRaises(ActuationGap) as ctx:
            _build(task_id="")
        self.assertEqual(ctx.exception.gap, "task_id_missing")


class GridEncoderTests(unittest.TestCase):
    def test_meta_bounds_computed(self):
        payload, meta = build_grid_binary(dict(_GRID))
        self.assertIsInstance(payload, bytes)
        self.assertEqual(meta["MaximumTreatmentZoneCode"], "2")
        self.assertEqual(meta["MinimumTreatmentZoneCode"], "1")
        self.assertEqual(int(meta["GridRowCount"]) * int(meta["GridColumnCount"]), len(payload) // 2)

    def test_encoder_gaps(self):
        cases = [
            ({}, "required"),
            ({**_GRID, "cell_deg_lat": 0}, "must be positive"),
            ({**_GRID, "n_rows": 0}, "must be positive"),
            ({**_GRID, "min_lon": 999}, "outside WGS84"),
            ({**_GRID, "codes": [[1, 2]]}, "rows x"),
            ({**_GRID, "codes": [[1, 2, 70000], [1, 1, 2]]}, "ints in"),
            ({**_GRID, "codes": [[1, 2, True], [1, 1, 2]]}, "ints in"),
        ]
        for grid, fragment in cases:
            with self.subTest(grid=fragment):
                with self.assertRaises(ActuationGap) as ctx:
                    build_grid_binary(grid)
                self.assertIn(fragment, ctx.exception.detail)

    def test_column_major_layout(self):
        payload, _ = build_grid_binary(dict(_GRID))
        import struct

        flat = list(struct.unpack("<6H", payload))
        self.assertEqual(
            flat,
            [
                _GRID["codes"][0][0],
                _GRID["codes"][1][0],  # column 0: both rows, north first
                _GRID["codes"][0][1],
                _GRID["codes"][1][1],
                _GRID["codes"][0][2],
                _GRID["codes"][1][2],
            ],
        )


if __name__ == "__main__":
    unittest.main()
