"""Acceptance ids from the implementation spec. Closed switches stay closed."""

import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import REASONER
from farm_ontology.adapters.cwa import load_township, load_wrf
from farm_ontology.adapters.earth_engine import TAIWAN_FORBIDDEN, load_sidecar, plan_export
from farm_ontology.adapters.open_meteo import parse_forecast, store_series
from farm_ontology.build import millimetres, mint
from farm_ontology.identity import load_synthetic_pilot
from farm_ontology.layers import SOIL_MISSING, SoilProfile
from farm_ontology.manifest import load_manifest, manifest_ok, manifest_violations
from farm_ontology.model import ErrorStatement, Interval, Observation
from farm_ontology.namespaces import MAIZE_AGROVOC
from farm_ontology.policy import CLASS_C_POLICY, INSTRUMENT, class_c_policy
from farm_ontology.publish import check_publication, render_memo
from farm_ontology.query import EXAMPLE_QUERIES, PUBLIC_TERMS, associated_at, facts_at, observations_of
from farm_ontology.rules import class_b_blockers
from farm_ontology.store import Store
from tests.support import NOW, load_json, sample_grid

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "docs" / "decision-log.md"


def _deg(value: float):
    resolution = sample_grid().native_resolution
    return resolution.__class__(
        value=value,
        unit_iri="http://qudt.org/vocab/unit/DEG",
        quantity_kind_iri="http://qudt.org/vocab/quantitykind/Angle",
    )


class SpecIdTests(unittest.TestCase):
    def test_p0_1_decision_log_records_answered_questions(self):
        text = LOG.read_text(encoding="utf-8")
        self.assertLess(text.count("\n"), 40)
        for number in range(1, 22):
            self.assertIn(f"Q{number} | 2026-11-16 |", text)
        self.assertEqual(text.count("not named"), 20)
        self.assertIn("Q21 | 2026-11-16 | 宇辰 洪 |", text)
        self.assertIn("Class C stays closed.", text)
        self.assertIn("Financial use stays false.", text)
        self.assertIn("No soil rows are recorded.", text)
        self.assertIn("No yield is recorded.", text)
        self.assertIn("No GPS metres are recorded.", text)
        self.assertIn("No futures contract is recorded.", text)

    def test_p0_2_earth_engine_export_stays_deferred(self):
        preflight = load_json("gcp-preflight.json")
        self.assertEqual(preflight["gcloud"]["project_id"], "seges-ai")
        self.assertEqual(preflight["gcloud"]["active_configuration"], "segescloud")
        self.assertFalse(preflight["earth_engine"]["live_export"])
        saved = {
            key: os.environ.get(key)
            for key in ("GCLOUD_CONFIGURATION", "GCP_PROJECT", "EE_PROJECT")
        }
        os.environ["GCLOUD_CONFIGURATION"] = "segescloud"
        os.environ["GCP_PROJECT"] = "seges-ai"
        os.environ.pop("EE_PROJECT", None)
        try:
            live = plan_export(
                "CHIRPS",
                crs="EPSG:4326",
                crs_transform=[0.05, 0.0, 120.0, 0.0, -0.05, 23.0],
                confirm_live=True,
            )
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        self.assertFalse(live.ok)
        self.assertFalse(live.executed)

    def test_p1_1_glosis_sdgio_and_seont_imports_fail(self):
        document = load_manifest()
        self.assertEqual(document["imports"], [])
        for iri in (
            "https://github.com/glosis-ld/glosis",
            "https://github.com/SDG-InterfaceOntology/sdgio",
            "https://github.com/AgriculturalSemantics/SEOnt",
        ):
            bad = dict(document)
            bad["imports"] = [iri]
            self.assertFalse(manifest_ok(bad))
            self.assertTrue(manifest_violations(bad))

    def test_p1_2_chirps_on_a_boundary_fails(self):
        store = Store()
        pilot = load_synthetic_pilot(store)
        refused = store.add_observation(
            sample_grid(
                iri=mint("observation", "chirps-on-boundary"),
                product_kind="chirps-prelim",
                feature_of_interest=pilot.parcel,
                feature_kind="boundary-polygon",
                spatial_support="grid-cell",
            ),
            at=NOW,
        )
        self.assertEqual(refused.refusal.rule_id, "R-foi")
        self.assertNotIn(mint("observation", "chirps-on-boundary"), store.observations)

    def test_p1_3_join_keeps_native_resolution(self):
        store = Store()
        pilot = load_synthetic_pilot(store)
        loaded = load_sidecar(store, load_json("ee_sidecar_chirps.json"), at=NOW)
        self.assertTrue(loaded.ok)
        joined = store.add_join(
            observation=loaded.iri,
            boundary=pilot.parcel,
            relation="geo:sfIntersects",
            crs="EPSG:4326",
            generated_at=NOW,
            at=NOW,
        )
        self.assertTrue(joined.ok)
        self.assertEqual(store.observations[loaded.iri].native_resolution.value, 0.05)
        self.assertNotIn(joined.iri, store.observations)
        self.assertEqual(observations_of(store, pilot.parcel, NOW), [])

    def test_p1_4_exact_match_passes_and_equivalent_class_fails(self):
        store = Store()
        passed = store.add_label(
            local_iri=mint("crop", "maize"),
            concept_iri=MAIZE_AGROVOC,
            relation="skos:exactMatch",
            language="en",
            extra_grant=False,
            at=NOW,
        )
        refused = store.add_label(
            local_iri=mint("crop", "maize"),
            concept_iri=MAIZE_AGROVOC,
            relation="owl:equivalentClass",
            language="en",
            extra_grant=False,
            at=NOW,
        )
        self.assertTrue(passed.ok)
        self.assertEqual(refused.refusal.rule_id, "R-agrovoc")
        self.assertIn("c_12332", MAIZE_AGROVOC)

    def test_p1_5_settlement_gate_fails_while_closed(self):
        self.assertEqual(class_c_policy(), "closed")
        self.assertEqual(CLASS_C_POLICY, "closed")
        store = Store()
        gate = store.promote(
            "missing",
            to_class="Settlement",
            reviewer="synthetic-reviewer",
            checklist={str(i): "pass" for i in range(1, 12)},
            region="synthetic",
            crop="maize",
            at=NOW,
        )
        self.assertEqual(gate.refusal.rule_id, "R-classC")
        self.assertEqual(store.accepted_gates, [])

    def test_p1_6_public_queries_do_not_name_bfo(self):
        blob = " ".join(PUBLIC_TERMS + EXAMPLE_QUERIES).lower()
        self.assertNotIn("bfo", blob)

    def test_p1_7_reasoner_is_none(self):
        self.assertEqual(REASONER, "none")
        self.assertEqual(load_manifest()["reasoner"], "none")
        build = (ROOT / "ontology" / "BUILD.txt").read_text(encoding="utf-8")
        self.assertIn("reasoner: none", build)

    def test_p2_1_split_and_merge_keep_previous_iris(self):
        store = Store()
        pilot = load_synthetic_pilot(store)
        self.assertIn(pilot.split_parent, store.boundaries)
        self.assertNotEqual(pilot.split_a, pilot.split_parent)
        self.assertNotEqual(pilot.split_b, pilot.split_parent)
        self.assertIn(pilot.merge_a, store.boundaries)
        self.assertIn(pilot.merge_b, store.boundaries)
        self.assertNotEqual(pilot.merged, pilot.merge_a)
        self.assertEqual(
            store.boundaries[pilot.merged].predecessors,
            (pilot.merge_a, pilot.merge_b),
        )

    def test_p2_2_tenure_and_distinct_parties(self):
        store = Store()
        pilot = load_synthetic_pilot(store)
        self.assertEqual(store.boundaries[pilot.unknown_tenure].tenure, "unknown")
        self.assertNotEqual(pilot.operator, pilot.right_holder)
        self.assertTrue(any(item.rule_id == "R-tenure" for item in store.refusals))
        self.assertNotIn(mint("boundary", "tenure-titled-no-source"), store.boundaries)

    def test_p2_3_six_decimals_without_metres_have_no_eudr_claim(self):
        store = Store()
        pilot = load_synthetic_pilot(store)
        phone = store.boundaries[pilot.phone]
        self.assertEqual(phone.coordinate_decimals, 6)
        self.assertTrue(phone.accuracy_unknown)
        self.assertIsNone(phone.accuracy_m)
        self.assertFalse(
            store.record_eudr_syntax(
                phone.iri,
                commodity="soya",
                production_date=datetime(2024, 6, 1, tzinfo=timezone.utc),
            )
        )
        self.assertFalse(store.boundaries[phone.iri].eudr_syntactic_claim)

    def test_p2_4_two_crops_require_mixed(self):
        store = Store()
        pilot = load_synthetic_pilot(store)
        self.assertEqual(store.croppings[pilot.mixed].mix, "mixed")
        self.assertEqual(len(store.croppings[pilot.mixed].crops), 2)
        self.assertNotIn(mint("cropping", "mono-two-crops"), store.croppings)
        self.assertTrue(any(item.rule_id == "R-mix" for item in store.refusals))

    def test_p2_5_overlap_is_not_distinct_plots(self):
        store = Store()
        pilot = load_synthetic_pilot(store)
        overlap = store.overlaps[pilot.overlap]
        self.assertGreater(overlap.area_ha, 0)
        self.assertIsNone(overlap.disposition)
        reading = store.distinct_plots_reading(
            pilot.overlap_a, pilot.overlap_b, pilot.season, at=NOW
        )
        self.assertEqual(reading.refusal.rule_id, "R-overlap")

    def test_p2_6_survey_point_is_not_a_boundary(self):
        store = Store()
        load_synthetic_pilot(store)
        self.assertTrue(store.survey_points)
        self.assertNotIn(mint("boundary", "household-survey-point"), store.boundaries)
        self.assertTrue(
            all(point.iri not in store.boundaries for point in store.survey_points.values())
        )

    def test_p2_7_fixture_store_has_no_real_person(self):
        store = Store()
        load_synthetic_pilot(store)
        for party in store.parties.values():
            self.assertTrue(party.label.startswith("synthetic-"))
            self.assertFalse(party.personal_data)
        for boundary in store.boundaries.values():
            self.assertFalse(boundary.personal_data)

    def test_h_1_joined_cell_does_not_become_boundary_rainfall(self):
        store = Store()
        pilot = load_synthetic_pilot(store)
        loaded = load_sidecar(store, load_json("ee_sidecar_chirps.json"), at=NOW)
        self.assertTrue(loaded.ok)
        cell = store.observations[loaded.iri]
        self.assertEqual(cell.native_resolution.value, 0.05)
        joined = store.add_join(
            observation=cell.iri,
            boundary=pilot.parcel,
            relation="geo:sfIntersects",
            crs="EPSG:4326",
            generated_at=NOW,
            at=NOW,
        )
        self.assertTrue(joined.ok)
        self.assertEqual(store.observations[cell.iri].native_resolution.value, 0.05)
        self.assertEqual(observations_of(store, pilot.parcel, NOW), [])
        rows = associated_at(store, NOW, pilot.parcel)
        self.assertEqual(rows[0]["native_resolution"]["value"], 0.05)
        self.assertNotIn("boundary_result", rows[0])

    def test_h_2_sidecar_without_required_fields_does_not_load(self):
        store = Store()
        doc = dict(load_json("ee_sidecar_chirps.json"))
        doc.pop("crc32c")
        doc["local"] = "missing-crc"
        refused = load_sidecar(store, doc, at=NOW)
        self.assertEqual(refused.refusal.rule_id, "R-sidecar")
        self.assertIn("crc32c", refused.refusal.attempted_change)

    def test_h_3_reanalysis_is_not_an_operations_fact(self):
        store = Store()
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 8, tzinfo=timezone.utc)
        available = datetime(2024, 4, 1, tzinfo=timezone.utc)
        era = sample_grid(
            iri=mint("observation", "era5-h3"),
            product_kind="reanalysis",
            phenomenon=Interval(start, end),
            availability_time=available,
            generated_at=available,
            procedure=mint("procedure", "reanalysis"),
            native_resolution=_deg(0.1),
        )
        self.assertTrue(store.add_observation(era, at=NOW).ok)
        during = datetime(2024, 1, 3, tzinfo=timezone.utc)
        self.assertFalse(
            any(row["iri"] == era.iri and row["is_measurement"] for row in facts_at(store, during))
        )
        same_day = sample_grid(
            iri=mint("observation", "era5-same-day-h3"),
            product_kind="reanalysis",
            phenomenon=Interval(start, end),
            availability_time=start,
            generated_at=start,
            procedure=mint("procedure", "reanalysis"),
            native_resolution=_deg(0.1),
        )
        refused = store.add_observation(same_day, at=NOW)
        self.assertEqual(refused.refusal.rule_id, "R-reanalysis")

    def test_h_4_final_blend_is_invisible_on_the_phenomenon_day(self):
        store = Store()
        start = datetime(2024, 6, 5, tzinfo=timezone.utc)
        end = datetime(2024, 6, 6, tzinfo=timezone.utc)
        published = datetime(2024, 7, 15, tzinfo=timezone.utc)
        final = sample_grid(
            iri=mint("observation", "chirps-final-h4"),
            product_kind="chirps-final",
            phenomenon=Interval(start, end),
            availability_time=published,
            generated_at=published,
            native_resolution=_deg(0.05),
        )
        self.assertTrue(store.add_observation(final, at=NOW).ok)
        phenomenon_day = datetime(2024, 6, 5, 23, tzinfo=timezone.utc)
        self.assertFalse(
            any(
                row["iri"] == final.iri and row["is_measurement"]
                for row in facts_at(store, phenomenon_day)
            )
        )

    def test_h_5_cloud_gap_fill_and_nodata_zero(self):
        store = Store()
        gap = sample_grid(
            iri=mint("observation", "cloud-gap-h5"),
            gap_reason="cloud",
            result=None,
        )
        self.assertTrue(store.add_observation(gap, at=NOW).ok)
        zero = sample_grid(
            iri=mint("observation", "nodata-zero-h5"),
            nodata=True,
        )
        self.assertEqual(store.add_observation(zero, at=NOW).refusal.rule_id, "R-zero")
        filled = sample_grid(
            iri=mint("observation", "gap-fill-h5"),
            product_kind="gap-fill",
            procedure=mint("procedure", "gap-fill"),
        )
        stored = store.add_observation(filled, at=NOW)
        self.assertTrue(stored.ok)
        self.assertEqual(store.observations[filled.iri].use_class, "Screening")

    def test_h_6_noncommercial_registration_forces_financial_use_false(self):
        store = Store()
        doc = dict(load_json("ee_sidecar_chirps.json"))
        loaded = load_sidecar(store, doc, at=NOW)
        self.assertFalse(store.observations[loaded.iri].licence.permits_financial_use)
        paid = dict(doc)
        paid["ee_registration"] = "noncommercial"
        paid["permits_financial_use"] = True
        paid["local"] = "noncommercial-paid"
        self.assertEqual(load_sidecar(store, paid, at=NOW).refusal.rule_id, "R-licence")

    def test_h_7_gridmet_daymet_and_hrrr_are_absent(self):
        self.assertEqual(TAIWAN_FORBIDDEN, ("GRIDMET", "DAYMET", "HRRR"))
        saved = {
            key: os.environ.get(key)
            for key in ("GCLOUD_CONFIGURATION", "GCP_PROJECT", "EE_PROJECT")
        }
        os.environ["GCLOUD_CONFIGURATION"] = "segescloud"
        os.environ["GCP_PROJECT"] = "seges-ai"
        os.environ.pop("EE_PROJECT", None)
        try:
            transform = [0.05, 0.0, 120.0, 0.0, -0.05, 23.0]
            for name in TAIWAN_FORBIDDEN:
                refused = plan_export(name, crs="EPSG:4326", crs_transform=transform)
                self.assertFalse(refused.ok)
                self.assertIn("Taiwan AOI", refused.reason)
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_h_8_completed_without_coverage_is_not_a_pass(self):
        store = Store()
        doc = dict(load_json("ee_sidecar_chirps.json"))
        self.assertIsNone(doc["gcs_uri"])
        completed = dict(doc)
        completed["state"] = "COMPLETED"
        completed["coverage_checked"] = False
        completed["local"] = "completed-unchecked-h8"
        refused = load_sidecar(store, completed, at=NOW)
        self.assertFalse(refused.ok)
        self.assertIn("coverage", refused.refusal.attempted_change)
        self.assertEqual(store.observations, {})

    def test_f_1_forecast_needs_an_issue_time(self):
        store = Store()
        doc = dict(load_json("open_meteo_jma_msm.json"))
        doc.pop("issue_time")
        doc["local"] = "no-issue-f1"
        refused = parse_forecast(store, doc, at=NOW)
        self.assertEqual(refused.refusal.rule_id, "R-issue")

    def test_f_2_township_forecast_uses_the_township_office(self):
        store = Store()
        pilot = load_synthetic_pilot(store)
        loaded = load_township(store, load_json("cwa_fd0047.json"), at=NOW)
        self.assertTrue(loaded.ok)
        obs = store.observations[loaded.iri]
        self.assertEqual(obs.feature_kind, "township")
        self.assertIn("township-office", obs.method.product_version)
        self.assertNotEqual(obs.feature_of_interest, pilot.parcel)

    def test_f_3_wrf_support_stays_3_or_15_km(self):
        store = Store()
        pilot = load_synthetic_pilot(store)
        self.assertEqual(store.boundaries[pilot.customary].area_ha, 1.0)
        for support, local in ((3, "cwa-wrf-3km-f3"), (15, "cwa-wrf-15km-f3")):
            doc = dict(load_json("cwa_wrf_3km.json"))
            doc["support_km"] = support
            doc["local"] = local
            loaded = load_wrf(store, doc, at=NOW)
            self.assertTrue(loaded.ok, loaded.refusal.attempted_change if loaded.refusal else "")
            joined = store.add_join(
                observation=loaded.iri,
                boundary=pilot.customary,
                relation="geo:sfIntersects",
                crs="EPSG:4326",
                generated_at=NOW,
                at=NOW,
            )
            self.assertTrue(joined.ok)
            self.assertEqual(store.observations[loaded.iri].native_resolution.value, support)
            self.assertEqual(observations_of(store, pilot.customary, NOW), [])

    def test_f_4_two_models_remain_and_no_consensus_hectare(self):
        store = Store()
        loaded = store_series(
            store,
            [load_json("open_meteo_jma_msm.json"), load_json("open_meteo_ecmwf_ifs.json")],
            at=NOW,
        )
        self.assertEqual(len(loaded), 2)
        self.assertTrue(all(item.ok for item in loaded))
        mean = dict(load_json("open_meteo_jma_msm.json"))
        mean["local"] = "consensus-hectare-f4"
        mean["mean_of_models"] = True
        self.assertFalse(parse_forecast(store, mean, at=NOW).ok)
        forecasts = [obs for obs in store.observations.values() if obs.is_forecast]
        self.assertEqual(len(forecasts), 2)

    def test_f_5_blank_service_name_does_not_load(self):
        store = Store()
        blank = dict(load_json("cwa_fd0047.json"))
        blank["service_name"] = ""
        blank["local"] = "blank-service-f5"
        refused = load_township(store, blank, at=NOW)
        self.assertEqual(refused.refusal.rule_id, "R-national")

    def test_f_6_open_meteo_is_not_the_legal_authority(self):
        store = Store()
        loaded = parse_forecast(store, load_json("open_meteo_jma_msm.json"), at=NOW)
        obs = store.observations[loaded.iri]
        self.assertFalse(obs.licence.permits_financial_use)
        self.assertIn("not-legal-authority", obs.method.product_version)
        claimed = dict(load_json("open_meteo_jma_msm.json"))
        claimed["local"] = "authority-f6"
        claimed["legal_meteorological_authority"] = True
        refused = parse_forecast(store, claimed, at=NOW)
        self.assertIn("legal meteorological authority", refused.refusal.attempted_change)

    def test_f_7_windy_and_predictwind_are_absent(self):
        store = Store()
        for model in ("windy-point", "predictwind"):
            doc = dict(load_json("open_meteo_jma_msm.json"))
            doc["model"] = model
            doc["local"] = model
            refused = parse_forecast(store, doc, at=NOW)
            self.assertIn("Taiwan primary", refused.refusal.attempted_change)

    def test_s_1_hectare_weather_needs_a_calibrated_sensor(self):
        store = Store()
        pilot = load_synthetic_pilot(store)
        claim = sample_grid(
            iri=mint("observation", "hectare-claim-s1"),
            hectare_weather_claim=True,
            native_resolution=None,
            feature_of_interest=pilot.parcel,
            feature_kind="boundary-polygon",
            spatial_support="boundary-polygon",
        )
        self.assertEqual(store.add_observation(claim, at=NOW).refusal.rule_id, "R-sensor")
        bare = sample_grid(
            iri=mint("observation", "uncalibrated-s1"),
            hectare_weather_claim=True,
            native_resolution=None,
            feature_of_interest=mint("sensor", "s1"),
            feature_kind="instrument-point",
            spatial_support="instrument-point",
        )
        self.assertEqual(store.add_observation(bare, at=NOW).refusal.rule_id, "R-sensor")

    def test_s_2_recall_is_not_a_crop_cut(self):
        store = Store()
        as_cut = sample_grid(
            iri=mint("observation", "recall-as-cut-s2"),
            procedure=mint("procedure", "crop-cut"),
            stated_as_recall=True,
            native_resolution=None,
            feature_of_interest=mint("sample", "recall-s2"),
            feature_kind="admin-unit",
            spatial_support="admin-unit",
        )
        self.assertIn("crop-cut", store.add_observation(as_cut, at=NOW).refusal.attempted_change)
        recall = sample_grid(
            iri=mint("observation", "recall-s2"),
            procedure=mint("procedure", "farmer-recall"),
            stated_as_recall=True,
            native_resolution=None,
            feature_of_interest=mint("sample", "recall-ok-s2"),
            feature_kind="admin-unit",
            spatial_support="admin-unit",
        )
        self.assertTrue(store.add_observation(recall, at=NOW).ok)
        self.assertEqual(store.observations[recall.iri].use_class, "Screening")

    def test_s_3_one_cut_cannot_train_and_prove_the_fit(self):
        store = Store()
        cut = mint("observation", "cut-s3")
        self.assertEqual(
            store.add_fit(used=(cut,), error_cut=cut, at=NOW).refusal.rule_id,
            "R-split-sample",
        )
        self.assertTrue(
            store.add_fit(used=(cut,), error_cut=mint("observation", "other-s3"), at=NOW).ok
        )

    def test_s_4_revision_keeps_the_first_figure(self):
        store = Store()
        start = datetime(2024, 3, 1, tzinfo=timezone.utc)
        end = datetime(2024, 3, 2, tzinfo=timezone.utc)
        first = self._admin("yearbook-s4-1", start, end, datetime(2024, 4, 1, tzinfo=timezone.utc), None)
        second = self._admin(
            "yearbook-s4-2", start, end, datetime(2024, 6, 1, tzinfo=timezone.utc), first.iri
        )
        self.assertTrue(store.add_observation(first, at=NOW).ok)
        self.assertTrue(store.add_observation(second, at=NOW).ok)
        april = {
            row["iri"]
            for row in facts_at(store, datetime(2024, 5, 1, tzinfo=timezone.utc))
            if row["is_measurement"]
        }
        self.assertEqual(april, {first.iri})
        self.assertIn(first.iri, store.observations)

    def test_s_5_crop_cut_rejects_a_privacy_displaced_point(self):
        store = Store()
        load_synthetic_pilot(store)
        point = next(iter(store.survey_points))
        attempted = sample_grid(
            iri=mint("observation", "crop-cut-on-survey"),
            procedure=mint("procedure", "crop-cut"),
            feature_of_interest=point,
            feature_kind="admin-unit",
            spatial_support="admin-unit",
            native_resolution=None,
            result=None,
            unsupported_reason="privacy-displaced survey point",
        )
        refused = store.add_observation(attempted, at=NOW)
        self.assertEqual(refused.refusal.rule_id, "R-foi")
        self.assertIn("crop-cut location", refused.refusal.attempted_change)
        self.assertNotIn(attempted.iri, store.observations)

    def test_s_6_sensor_value_is_not_copied_onto_another_boundary(self):
        store = Store()
        pilot = load_synthetic_pilot(store)
        sensor = mint("sensor", "station-s6")
        kept = sample_grid(
            iri=mint("observation", "sensor-at-instrument"),
            procedure=mint("procedure", "sensor"),
            hectare_weather_claim=True,
            native_resolution=None,
            feature_of_interest=sensor,
            feature_kind="instrument-point",
            spatial_support="instrument-point",
            sensor_iri=sensor,
            calibration_activity=mint("activity", "calibration-s6"),
        )
        self.assertTrue(store.add_observation(kept, at=NOW).ok)
        copied = sample_grid(
            iri=mint("observation", "sensor-on-other-boundary"),
            procedure=mint("procedure", "sensor"),
            native_resolution=None,
            feature_of_interest=pilot.parcel,
            feature_kind="boundary-polygon",
            spatial_support="boundary-polygon",
            sensor_iri=sensor,
        )
        refused = store.add_observation(copied, at=NOW)
        self.assertEqual(refused.refusal.rule_id, "R-sensor")
        self.assertNotIn(copied.iri, store.observations)
        self.assertEqual(observations_of(store, pilot.parcel, NOW), [])
        self.assertNotEqual(store.observations[kept.iri].feature_of_interest, pilot.customary)

    def test_qy_1_facts_at_hides_the_final_blend_on_the_phenomenon_day(self):
        store = Store()
        loaded = load_sidecar(store, load_json("ee_sidecar_chirps.json"), at=NOW)
        phenomenon_day = datetime(2024, 6, 5, 12, tzinfo=timezone.utc)
        visible = {row["iri"] for row in facts_at(store, phenomenon_day) if row["is_measurement"]}
        self.assertNotIn(loaded.iri, visible)

    def test_qy_2_associated_at_returns_the_join_and_the_cell_size(self):
        store = Store()
        pilot = load_synthetic_pilot(store)
        loaded = load_sidecar(store, load_json("ee_sidecar_chirps.json"), at=NOW)
        later = datetime(2024, 7, 16, tzinfo=timezone.utc)
        self.assertTrue(
            store.add_join(
                observation=loaded.iri,
                boundary=pilot.parcel,
                relation="geo:sfIntersects",
                crs="EPSG:4326",
                generated_at=later,
                at=NOW,
            ).ok
        )
        rows = associated_at(store, later, pilot.parcel)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["native_resolution"]["value"], 0.05)
        self.assertEqual(rows[0]["boundary"], pilot.parcel)

    def test_qy_3_class_b_without_an_error_statement_fails(self):
        blockers = class_b_blockers(sample_grid(), "Taiwan", "maize")
        self.assertEqual(blockers[0].rule_id, "R-error")

    def test_qy_4_service_account_cannot_promote(self):
        saved = os.environ.pop("FARM_NAMED_REVIEWER", None)
        os.environ["FARM_NAMED_REVIEWER"] = "later"
        try:
            store = Store()
            cell = sample_grid(iri=mint("observation", "gate-qy4"))
            self.assertTrue(store.add_observation(cell, at=NOW).ok)
            account = store.promote(
                cell.iri,
                to_class="Portfolio",
                reviewer="worker@seges-ai.iam.gserviceaccount.com",
                checklist={"1": "pass"},
                region="Taiwan",
                crop="maize",
                at=NOW,
            )
            self.assertEqual(account.refusal.rule_id, "R-gate")
            named = store.promote(
                cell.iri,
                to_class="Portfolio",
                reviewer="later",
                checklist={"1": "pass"},
                region="Taiwan",
                crop="maize",
                at=NOW,
            )
            self.assertFalse(named.ok)
            self.assertEqual(store.observations[cell.iri].use_class, "Screening")
            self.assertEqual(store.accepted_gates, [])
            self.assertEqual(named.refusal.rule_id, "R-error")
            for local, error in (
                ("gate-qy4-uncalibrated", self._uncalibrated()),
                ("gate-qy4-cited", self._same_region_error()),
            ):
                obs = sample_grid(iri=mint("observation", local), error=error)
                self.assertTrue(store.add_observation(obs, at=NOW).ok)
                promoted = store.promote(
                    obs.iri,
                    to_class="Portfolio",
                    reviewer="later",
                    checklist={"1": "pass"},
                    region="Taiwan",
                    crop="maize",
                    at=NOW,
                )
                self.assertTrue(promoted.ok, promoted.refusal.attempted_change if promoted.refusal else "")
                kept = store.observations[obs.iri]
                self.assertEqual(kept.use_class, "Screening")
                self.assertFalse(kept.licence.permits_financial_use)
                self.assertEqual(kept.iri, obs.iri)
                reading = [
                    row
                    for row in facts_at(store, NOW)
                    if row["iri"] == obs.iri and row["is_measurement"]
                ]
                self.assertEqual(reading[0]["use_class"], "Portfolio")
            self.assertEqual(class_c_policy(), "closed")
            self.assertEqual(len(store.accepted_gates), 2)
        finally:
            os.environ.pop("FARM_NAMED_REVIEWER", None)
            if saved is not None:
                os.environ["FARM_NAMED_REVIEWER"] = saved

    def test_qy_5_publication_without_an_error_statement_fails(self):
        stripped = check_publication("use_class: Screening\nspatial_support: x\nlicence: x\n")
        self.assertEqual(stripped[0].rule_id, "R-strip")

    def test_qy_6_forged_settlement_checklist_fails(self):
        store = Store()
        gate = store.promote(
            "forged",
            to_class="Settlement",
            reviewer="synthetic-reviewer",
            checklist={str(i): "pass" for i in range(1, 12)},
            region="synthetic",
            crop="maize",
            at=NOW,
        )
        self.assertEqual(gate.refusal.rule_id, "R-classC")
        self.assertFalse(store.observations)

    def test_qy_7_refusals_stay_visible_as_refusals(self):
        store = Store()
        pilot = load_synthetic_pilot(store)
        boundary = sample_grid(
            iri=mint("observation", "qy7-boundary"),
            feature_of_interest=pilot.parcel,
            feature_kind="boundary-polygon",
            spatial_support="grid-cell",
        )
        self.assertEqual(store.add_observation(boundary, at=NOW).refusal.rule_id, "R-foi")
        store.promote(
            "qy7-settlement",
            to_class="Settlement",
            reviewer="synthetic-reviewer",
            checklist={"1": "pass"},
            region="synthetic",
            crop="maize",
            at=NOW,
        )
        rows = [row for row in facts_at(store, NOW) if not row["is_measurement"]]
        rules = {row["rule_id"] for row in rows if row["record_type"] == "refusal"}
        self.assertIn("R-foi", rules)
        self.assertIn("R-classC", rules)
        self.assertTrue(all(row["record_type"] == "refusal" for row in rows if row["rule_id"]))

    def test_qy_8_memo_states_support_and_refusals_without_a_farm_claim(self):
        store = Store()
        pilot = load_synthetic_pilot(store)
        loaded = load_sidecar(store, load_json("ee_sidecar_chirps.json"), at=NOW)
        self.assertTrue(loaded.ok)
        store.promote(
            loaded.iri,
            to_class="Settlement",
            reviewer="synthetic-reviewer",
            checklist={str(i): "pass" for i in range(1, 12)},
            region="synthetic",
            crop="maize",
            at=NOW,
        )
        memo = render_memo(store, NOW)
        self.assertIn("spatial_support:", memo)
        self.assertIn("licence:", memo)
        self.assertIn("error:", memo)
        self.assertIn("R-classC", memo)
        self.assertNotIn("hedge ratio", memo)
        for line in memo.splitlines():
            if "hedge" in line.lower() or "nature" in line.lower():
                self.assertTrue(
                    line.startswith("refusal") or "were refused" in line,
                    line,
                )
            if pilot.parcel in line and "12.5" in line:
                self.fail(line)
        self.assertTrue(SOIL_MISSING)
        self.assertEqual(SoilProfile(feature_iri="empty").observation_iris, ())
        self.assertIsNone(INSTRUMENT)
        self.assertEqual(class_c_policy(), "closed")

    def test_recording_paths_do_not_call_weather_or_maps(self):
        page = (ROOT / "farm_ontology" / "page_io.py").read_text(encoding="utf-8")
        fieldkit = (ROOT / "farm_ontology" / "fieldkit.py").read_text(encoding="utf-8")
        self.assertIn("attach_weather=False", page)
        self.assertNotIn("open-meteo.com", page)
        self.assertNotIn("maps.googleapis", page)
        self.assertIn('"--lat"', fieldkit)
        self.assertIn('"--lon"', fieldkit)
        self.assertNotIn("open-meteo.com", fieldkit)

    def _uncalibrated(self):
        return ErrorStatement(
            metric="uncalibrated",
            sample_region="other",
            sample_crop="other",
            sample_season="synthetic",
            citation="none",
            held_out=False,
            independent_of_product=None,
        )

    def _same_region_error(self):
        return ErrorStatement(
            metric="rmse",
            sample_region="Taiwan",
            sample_crop="maize",
            sample_season="synthetic",
            citation="synthetic-same-region",
            held_out=True,
            independent_of_product=True,
            value=millimetres(1.0),
        )

    def _admin(self, local, start, end, available, revision):
        base = sample_grid()
        return Observation(
            **{
                **base.__dict__,
                "iri": mint("observation", local),
                "feature_of_interest": mint("admin", "synthetic-district"),
                "feature_kind": "admin-unit",
                "spatial_support": "admin-unit",
                "native_resolution": None,
                "procedure": mint("procedure", "administrative-estimate"),
                "product_kind": "administrative-estimate",
                "phenomenon": Interval(start, end),
                "availability_time": available,
                "generated_at": available,
                "revision_of": revision,
            }
        )


if __name__ == "__main__":
    unittest.main()
