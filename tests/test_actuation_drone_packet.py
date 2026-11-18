"""Tests for the human-operated drone spray packet (WS5.2)."""

import json
import unittest
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

from farm_ontology.actuation.command_ledger import ActuationGap, ActuationRefusal
from farm_ontology.actuation.drone_packet import (
    KML_NAMESPACE,
    RECOMMENDATION_CONTRACT,
    AdvisoryRef,
    SignoffRelease,
    build_drone_packet,
    weather_window_gaps,
)

_NS = {"k": KML_NAMESPACE}
_RING = [(42.7000, 142.4000), (42.7100, 142.4000), (42.7100, 142.4100)]
_DOSE = {"z1": {"product": "pesticide-x", "dose": 1.5, "unit": "L/ha"}}
_WINDOW = {
    "window_start_utc": "2027-01-15T21:00:00+00:00",
    "window_end_utc": "2027-01-16T02:00:00+00:00",
    "wind_max_ms": 4.0,
    "rain_free_hours": 6,
    "temp_min_c": 10,
    "temp_max_c": 28,
    "native_support": "jma-msm-point",
}
_ADVISORY = AdvisoryRef(
    reference_id="REC-2027-0001",
    issuer="agronomy-engine-fixture",
    issued_at="2027-01-15T08:00:00+00:00",
)
_RELEASE = SignoffRelease(
    signer="risk-owner",
    signed_at="2027-01-15T12:00:00+00:00",
    signature="SIG-ACK/REC-2027-0001/seed",
    recommendation_id="REC-2027-0001",
)


def _packet(**overrides):
    kwargs = dict(
        geofence_ring=list(_RING),
        dosage_table=json.loads(json.dumps(_DOSE)),
        advisory_ref=_ADVISORY,
        weather_window=dict(_WINDOW),
        use_class="field-ops",
        permits_financial_use=False,
        signoff_release=_RELEASE,
    )
    kwargs.update(overrides)
    return build_drone_packet(**kwargs)


class EmitTests(unittest.TestCase):
    def test_emits_well_formed_namespaced_kml(self):
        kml, report = _packet()
        root = ET.fromstring(kml)
        self.assertEqual(root.tag, f"{{{KML_NAMESPACE}}}kml")
        polygon = root.find(".//k:Polygon/k:outerBoundaryIs/k:LinearRing/"
                            "k:coordinates", _NS)
        self.assertIsNotNone(polygon)
        coords = polygon.text.split()
        # closure point appended by the builder
        self.assertEqual(len(coords), len(_RING) + 1)
        self.assertEqual(coords[0], coords[-1])
        # KML order is lon,lat — the reversal is deliberate
        first = coords[0].split(",")
        self.assertAlmostEqual(float(first[0]), _RING[0][1], places=5)
        self.assertAlmostEqual(float(first[1]), _RING[0][0], places=5)

    def test_stamps_travel_verbatim_into_document_and_report(self):
        kml, report = _packet(use_class="financial-analytics",
                              permits_financial_use=True)
        self.assertEqual(report["use_class"], "financial-analytics")
        self.assertIs(report["permits_financial_use"], True)
        text = kml.decode("utf-8")
        self.assertIn("use_class=financial-analytics", text)
        self.assertIn("permits_financial_use=true", text)
        self.assertIn("HUMAN-flown packet", text)
        self.assertIn(RECOMMENDATION_CONTRACT[:30], text)

    def test_dosage_and_weather_extended_data(self):
        kml, report = _packet()
        root = ET.fromstring(kml)
        data = {
            d.get("name"): d.find("k:value", _NS).text
            for d in root.findall(".//k:ExtendedData/k:Data", _NS)
        }
        dose_payload = json.loads(data["dose:z1"])
        self.assertEqual(dose_payload, {"product": "pesticide-x", "dose": 1.5, "unit": "L/ha"})
        self.assertEqual(data["weather:wind_max_ms"], "4.0")
        self.assertEqual(data["weather:native_support"], "jma-msm-point")
        self.assertEqual(report["advisory"]["reference_id"], "REC-2027-0001")

    def test_advisory_ref_defaults_to_roadmap_ws35_contract(self):
        self.assertIn("RecommendationRecord", RECOMMENDATION_CONTRACT)
        self.assertIn("WS3.5", RECOMMENDATION_CONTRACT)
        self.assertIn("agronomy", AdvisoryRef("x", "y", "2027-01-01T00:00:00+00:00").contract)

    def test_permissive_false_is_a_legitimate_stamp(self):
        _, report = _packet(permits_financial_use=False)
        self.assertIs(report["permits_financial_use"], False)


class GapRefusalTests(unittest.TestCase):
    def test_no_input_means_full_verbose_refusal(self):
        with self.assertRaises(ActuationRefusal) as ctx:
            build_drone_packet(
                geofence_ring=[],
                dosage_table={},
                advisory_ref=None,
                weather_window={},
                use_class="",
                permits_financial_use=None,
            )
        detail = ctx.exception.detail
        for fragment in (
            "geofence_ring",
            "dosage_table",
            "advisory_ref",
            "weather_window",
            "use_class",
            "permits_financial_use",
        ):
            self.assertIn(fragment, detail)

    def test_closed_ring_refused(self):
        with self.assertRaises(ActuationRefusal) as ctx:
            _packet(geofence_ring=_RING + [_RING[0]])
        self.assertIn("open ring", ctx.exception.detail)

    def test_out_of_range_point_named_with_index(self):
        with self.assertRaises(ActuationRefusal) as ctx:
            _packet(geofence_ring=[(42.7, 999.0), (42.71, 142.4), (42.71, 142.41)])
        self.assertIn("geofence_ring[0]", ctx.exception.detail)

    def test_dose_gaps_named_per_field(self):
        with self.assertRaises(ActuationRefusal) as ctx:
            _packet(dosage_table={"z1": {"product": "x", "dose": 0}})
        detail = ctx.exception.detail
        self.assertIn("dose must be a positive number", detail)
        self.assertIn("unit missing", detail)

    def test_window_gaps_aggregated_before_emit(self):
        window = dict(_WINDOW)
        window["wind_max_ms"] = 0
        window["temp_max_c"] = 5  # < temp_min_c
        with self.assertRaises(ActuationRefusal) as ctx:
            _packet(weather_window=window)
        detail = ctx.exception.detail
        self.assertIn("wind_max_ms must be > 0", detail)
        self.assertIn("temp_max_c must be >= temp_min_c", detail)

    def test_string_true_never_coerced_to_bool(self):
        with self.assertRaises(ActuationRefusal) as ctx:
            _packet(permits_financial_use="true")
        self.assertIn("explicit boolean required", ctx.exception.detail)


class AdvisoryRefTests(unittest.TestCase):
    def test_validation_gaps(self):
        cases = [
            (AdvisoryRef("", "issuer", "2027-01-01T00:00:00+00:00"), "advisory_reference_id_missing"),
            (AdvisoryRef("id", "", "2027-01-01T00:00:00+00:00"), "advisory_issuer_missing"),
            (AdvisoryRef("id", "issuer", ""), "advisory_issued_at_missing"),
            (AdvisoryRef("id", "issuer", "not-a-date"), "advisory_issued_at_unparsable"),
            (AdvisoryRef("id", "issuer", "2027-01-01T00:00:00"), "advisory_issued_at_naive"),
        ]
        for ref, gap in cases:
            with self.subTest(gap=gap):
                with self.assertRaises(expected_exception=type(ref.__class__.__mro__[0]).__name__
                                       if False else Exception):
                    ref.validated()
                try:
                    ref.validated()
                except Exception as exc:
                    from farm_ontology.actuation.command_ledger import ActuationGap

                    self.assertIsInstance(exc, ActuationGap)
                    self.assertEqual(exc.gap, gap)
                else:
                    self.fail("expected a gap")

    def test_weather_window_helper(self):
        self.assertEqual(weather_window_gaps(None), ["weather_window_missing"])
        window = dict(_WINDOW)
        window.pop("rain_free_hours")
        gaps = weather_window_gaps(window)
        self.assertEqual(len(gaps), 1)
        self.assertIn("rain_free_hours", gaps[0])


class SignoffGateTests(unittest.TestCase):
    """D8 regressions (ws/fix/actuation-ledger): no packet on an UNSIGNED rec."""

    def test_unsigned_recommendation_refused_naming_the_signature(self):
        with self.assertRaises(ActuationRefusal) as ctx:
            _packet(signoff_release=None)
        self.assertEqual(ctx.exception.refusal, "signature_missing")
        detail = ctx.exception.detail
        self.assertIn("REC-2027-0001", detail)
        self.assertIn("requires_human_signoff=True", detail)
        self.assertIn("UNSIGNED", detail)
        self.assertIn("SignoffRelease", ctx.exception.remediation)
        self.assertIn("operator_override", ctx.exception.remediation)

    def test_override_path_emits_with_override_recorded_into_payload(self):
        justification = (
            "operator re-checked window after stall report FL-42; takes "
            "responsibility for the unsigned rec"
        )
        kml, report = _packet(signoff_release=None, operator_override=justification)
        text = kml.decode("utf-8")
        self.assertIn(f"operator_override={justification}", text)
        self.assertIn("signature=none-operator-override-recorded", text)
        self.assertIsNone(report["signoff"])
        self.assertEqual(report["operator_override"], justification)

    def test_whitespace_override_counts_as_absent(self):
        with self.assertRaises(ActuationRefusal) as ctx:
            _packet(signoff_release=None, operator_override="   ")
        self.assertEqual(ctx.exception.refusal, "signature_missing")

    def test_non_string_override_refused(self):
        for bad in (True, 1, ["because"]):
            with self.subTest(override=bad):
                with self.assertRaises(ActuationRefusal) as ctx:
                    _packet(signoff_release=None, operator_override=bad)
                self.assertEqual(ctx.exception.refusal, "operator_override_ill_formed")

    def test_release_binding_enforced_against_cited_recommendation(self):
        stranger = SignoffRelease(
            signer="risk-owner",
            signed_at="2027-01-15T12:00:00+00:00",
            signature="SIG-ACK/other/seed",
            recommendation_id="REC-2026-9999",
        )
        with self.assertRaises(ActuationRefusal) as ctx:
            _packet(signoff_release=stranger)
        self.assertEqual(ctx.exception.refusal, "signoff_target_mismatch")
        self.assertIn("REC-2027-0001", ctx.exception.detail)

    def test_malformed_release_refused_loudly(self):
        broken = SignoffRelease(
            signer="  ",
            signed_at="2027-01-15T12:00:00+00:00",
            signature="SIG-ACK/x",
            recommendation_id="REC-2027-0001",
        )
        with self.assertRaises(ActuationRefusal) as ctx:
            _packet(signoff_release=broken)
        self.assertEqual(ctx.exception.refusal, "signoff_release_invalid")
        self.assertIn("signer", ctx.exception.detail)
        # override must not silently rescue a malformed release the caller intended
        with self.assertRaises(ActuationRefusal):
            _packet(signoff_release=broken, operator_override="oops")

    def test_release_evidence_travels_into_payload_and_report(self):
        kml, report = _packet()
        text = kml.decode("utf-8")
        self.assertIn("signoff=risk-owner@2027-01-15T12:00:00+00:00", text)
        self.assertIn("signoff_recommendation=REC-2027-0001", text)
        self.assertIn("signoff_signature=SIG-ACK/REC-2027-0001/seed", text)
        self.assertEqual(
            report["signoff"],
            {
                "signer": "risk-owner",
                "signed_at": "2027-01-15T12:00:00+00:00",
                "signature": "SIG-ACK/REC-2027-0001/seed",
                "recommendation_id": "REC-2027-0001",
            },
        )
        self.assertEqual(report["operator_override"], "")

    def test_upstream_signed_advisory_emits_without_release_or_override(self):
        signed_upstream = AdvisoryRef(
            reference_id="REC-2027-0002",
            issuer="agronomy-engine-fixture",
            issued_at="2027-01-15T08:00:00+00:00",
            requires_human_signoff=False,
        )
        kml, report = _packet(
            advisory_ref=signed_upstream, signoff_release=None
        )
        self.assertIn(
            "requires_human_signoff=false (recommendation signed upstream)",
            kml.decode("utf-8"),
        )
        self.assertIsNone(report["signoff"])
        self.assertEqual(report["operator_override"], "")
        self.assertIs(report["advisory"]["requires_human_signoff"], False)

    def test_signoff_flag_must_be_boolean(self):
        sloppy = AdvisoryRef(
            reference_id="REC-2027-0003",
            issuer="agronomy-engine-fixture",
            issued_at="2027-01-15T08:00:00+00:00",
            requires_human_signoff="yes",
        )
        with self.assertRaises(ActuationRefusal) as ctx:
            _packet(advisory_ref=sloppy, signoff_release=None)
        self.assertIn("advisory_signoff_flag_not_boolean", ctx.exception.detail)

    def test_signoff_release_shape_gaps(self):
        cases = [
            (SignoffRelease("", "2027-01-15T12:00:00+00:00", "sig", "R"), "signoff_signer_missing"),
            (SignoffRelease("o", "2027-01-15T12:00:00+00:00", "", "R"), "signoff_signature_missing"),
            (SignoffRelease("o", "", "sig", "R"), "signoff_signed_at_missing"),
            (SignoffRelease("o", "not-a-date", "sig", "R"), "signoff_signed_at_unparsable"),
            (SignoffRelease("o", "2027-01-15T12:00:00", "sig", "R"), "signoff_signed_at_naive"),
            (SignoffRelease("o", "2027-01-15T12:00:00+00:00", "sig", "  "), "signoff_recommendation_id_missing"),
        ]
        for release, gap in cases:
            with self.subTest(gap=gap):
                with self.assertRaises(ActuationGap) as ctx:
                    release.validated()
                self.assertEqual(ctx.exception.gap, gap)


if __name__ == "__main__":
    unittest.main()
