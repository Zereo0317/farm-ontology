import json
import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.adapters.cwa import live_status, load_township, load_wrf
from farm_ontology.adapters.earth_engine import load_sidecar, plan_export
from farm_ontology.adapters.open_meteo import parse_forecast, store_series
from farm_ontology.identity import load_synthetic_pilot
from farm_ontology.query import associated_at, facts_at, observations_of
from farm_ontology.store import Store
from tests.support import FIXTURES, NOW, load_json


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.saved = {
            key: os.environ.get(key)
            for key in ("GCLOUD_CONFIGURATION", "GCP_PROJECT", "EE_PROJECT", "CWA_API_KEY")
        }
        os.environ["GCLOUD_CONFIGURATION"] = "segescloud"
        os.environ["GCP_PROJECT"] = "seges-ai"
        os.environ.pop("EE_PROJECT", None)
        os.environ.pop("CWA_API_KEY", None)

    def tearDown(self):
        for key, value in self.saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_plans_read_env_and_do_not_export(self):
        os.environ.pop("GCLOUD_CONFIGURATION", None)
        os.environ.pop("GCP_PROJECT", None)
        os.environ.pop("EE_PROJECT", None)
        missing = plan_export("CHIRPS", crs="EPSG:4326", crs_transform=[1, 0, 0, 0, -1, 0])
        self.assertFalse(missing.ok)
        self.assertFalse(missing.executed)
        os.environ["GCLOUD_CONFIGURATION"] = "segescloud"
        os.environ["GCP_PROJECT"] = "seges-ai"
        transform = [0.05, 0.0, 120.0, 0.0, -0.05, 23.0]
        dry = plan_export("CHIRPS", crs="EPSG:4326", crs_transform=transform)
        self.assertTrue(dry.ok)
        self.assertFalse(dry.executed)
        self.assertEqual(dry.plan["gcp_project"], "seges-ai")
        self.assertEqual(dry.plan["gcloud_configuration"], "segescloud")
        self.assertEqual(dry.plan["asset"], "UCSB-CHG/CHIRPS/DAILY")
        self.assertIsNone(dry.plan["gcs_uri"])
        self.assertIsNone(dry.plan["task_id"])
        self.assertFalse(dry.plan["best_effort"])
        os.environ["GCP_PROJECT"] = "other-project"
        other = plan_export("ERA5-Land", crs="EPSG:4326", crs_transform=transform)
        self.assertEqual(other.plan["gcp_project"], "other-project")
        self.assertFalse(plan_export("GRIDMET", crs="EPSG:4326", crs_transform=transform).ok)
        self.assertFalse(plan_export("DAYMET", crs="EPSG:4326", crs_transform=transform).ok)
        self.assertFalse(plan_export("HRRR", crs="EPSG:4326", crs_transform=transform).ok)
        self.assertIn(
            "scale alone",
            plan_export("CHIRPS", scale=30).reason,
        )
        self.assertIn("bestEffort", plan_export("CHIRPS", crs="EPSG:4326", crs_transform=transform, best_effort=True).reason)
        live = plan_export("CHIRPS", crs="EPSG:4326", crs_transform=transform, confirm_live=True)
        self.assertFalse(live.ok)
        self.assertFalse(live.executed)
        self.assertIsNotNone(live.plan)
        self.assertFalse(live.plan["executed"])
        recorded = load_json("ee_export_plan.json")
        self.assertFalse(recorded["executed"])
        self.assertIsNone(recorded["gcs_uri"])
        self.assertIsNone(recorded["task_id"])
        self.assertIsNotNone(recorded["crs_transform"])

    def test_sidecar_keeps_cell_support_and_fails_closed(self):
        store = Store()
        pilot = load_synthetic_pilot(store)
        doc = load_json("ee_sidecar_chirps.json")
        loaded = load_sidecar(store, doc, at=NOW)
        self.assertTrue(loaded.ok, loaded.refusal.attempted_change if loaded.refusal else "")
        obs = store.observations[loaded.iri]
        self.assertEqual(obs.native_resolution.value, 0.05)
        self.assertEqual(obs.use_class, "Screening")
        self.assertFalse(obs.licence.permits_financial_use)
        self.assertEqual(obs.method.ee_registration, "unknown")
        self.assertTrue(obs.dry_run)
        self.assertEqual(obs.method.product_version, "recorded-dry-run")
        phenomenon_day = datetime(2024, 6, 5, 12, tzinfo=timezone.utc)
        visible_ids = {row["iri"] for row in facts_at(store, phenomenon_day) if row["is_measurement"]}
        self.assertNotIn(obs.iri, visible_ids)
        later = datetime(2024, 7, 16, tzinfo=timezone.utc)
        joined = store.add_join(
            observation=obs.iri,
            boundary=pilot.parcel,
            relation="geo:sfIntersects",
            crs="EPSG:4326",
            generated_at=later,
            at=NOW,
        )
        self.assertTrue(joined.ok)
        self.assertEqual(store.observations[obs.iri].native_resolution.value, 0.05)
        self.assertEqual(observations_of(store, pilot.parcel, later), [])
        rows = associated_at(store, later, pilot.parcel)
        self.assertEqual(rows[0]["native_resolution"]["value"], 0.05)
        self.assertNotIn("boundary_result", rows[0])

        missing = dict(doc)
        missing.pop("crs_transform")
        missing["local"] = "missing-transform"
        self.assertEqual(load_sidecar(store, missing, at=NOW).refusal.rule_id, "R-sidecar")
        completed = dict(doc)
        completed["state"] = "COMPLETED"
        completed["coverage_checked"] = False
        completed["local"] = "completed-unchecked"
        self.assertIn("coverage", load_sidecar(store, completed, at=NOW).refusal.attempted_change)
        copied = dict(doc)
        copied["copy_result_to_boundary"] = True
        copied["local"] = "copied"
        self.assertEqual(load_sidecar(store, copied, at=NOW).refusal.rule_id, "R-foi")
        paid = dict(doc)
        paid["ee_registration"] = "noncommercial"
        paid["permits_financial_use"] = True
        paid["local"] = "paid"
        self.assertEqual(load_sidecar(store, paid, at=NOW).refusal.rule_id, "R-licence")
        zero = dict(doc)
        zero["nodata_as_zero"] = True
        zero["local"] = "zero"
        self.assertEqual(load_sidecar(store, zero, at=NOW).refusal.rule_id, "R-zero")

    def test_forecasts_keep_native_support_and_issue_time(self):
        store = Store()
        pilot = load_synthetic_pilot(store)
        jma = load_json("open_meteo_jma_msm.json")
        ifs = load_json("open_meteo_ecmwf_ifs.json")
        loaded = store_series(store, [jma, ifs], at=NOW)
        self.assertTrue(all(item.ok for item in loaded))
        self.assertEqual(
            {store.observations[item.iri].result.value for item in loaded},
            {1.2, 4.0},
        )
        jma_obs = store.observations[loaded[0].iri]
        ifs_obs = store.observations[loaded[1].iri]
        self.assertEqual(jma_obs.native_resolution.value, 0.05)
        self.assertIn("DEG", jma_obs.native_resolution.unit_iri)
        self.assertEqual(ifs_obs.native_resolution.value, 9)
        self.assertIn("not-legal-authority", jma_obs.method.product_version)
        self.assertFalse(jma_obs.licence.permits_financial_use)
        self.assertNotEqual(jma_obs.issue_time, jma_obs.phenomenon.start)
        mean = dict(jma)
        mean["local"] = "consensus-hectare"
        mean["mean_of_models"] = True
        mean["value_mm"] = 2.6
        self.assertFalse(parse_forecast(store, mean, at=NOW).ok)
        self.assertEqual(len([obs for obs in store.observations.values() if obs.is_forecast]), 2)
        finer = dict(jma)
        finer["local"] = "ten-metre"
        finer["requested_resolution_m"] = 10
        self.assertEqual(parse_forecast(store, finer, at=NOW).refusal.rule_id, "R-support")
        missing_issue = dict(jma)
        missing_issue["local"] = "no-issue"
        missing_issue.pop("issue_time")
        self.assertEqual(parse_forecast(store, missing_issue, at=NOW).refusal.rule_id, "R-issue")
        best = dict(jma)
        best["model"] = "best_match"
        best["local"] = "best"
        best.pop("resolved_model_id", None)
        self.assertIn("best_match", parse_forecast(store, best, at=NOW).refusal.attempted_change)
        windy = dict(jma)
        windy["model"] = "windy-point"
        windy["local"] = "windy"
        self.assertIn("Taiwan primary", parse_forecast(store, windy, at=NOW).refusal.attempted_change)
        authority = dict(jma)
        authority["local"] = "authority"
        authority["legal_meteorological_authority"] = True
        self.assertIn("legal meteorological authority", parse_forecast(store, authority, at=NOW).refusal.attempted_change)

        township = load_township(store, load_json("cwa_fd0047.json"), at=NOW)
        self.assertTrue(township.ok, township.refusal.attempted_change if township.refusal else "")
        township_obs = store.observations[township.iri]
        self.assertEqual(township_obs.feature_kind, "township")
        self.assertIn("township-office", township_obs.method.product_version)
        self.assertNotEqual(township_obs.feature_of_interest, pilot.parcel)
        blank = dict(load_json("cwa_fd0047.json"))
        blank["service_name"] = ""
        blank["local"] = "blank-service"
        self.assertEqual(load_township(store, blank, at=NOW).refusal.rule_id, "R-national")
        field = dict(load_json("cwa_fd0047.json"))
        field["representative_point"] = "field"
        field["local"] = "field-point"
        self.assertEqual(load_township(store, field, at=NOW).refusal.rule_id, "R-foi")

        wrf = load_wrf(store, load_json("cwa_wrf_3km.json"), at=NOW)
        self.assertTrue(wrf.ok, wrf.refusal.attempted_change if wrf.refusal else "")
        self.assertEqual(store.observations[wrf.iri].native_resolution.value, 3)
        rewritten = dict(load_json("cwa_wrf_3km.json"))
        rewritten["local"] = "wrf-rewritten"
        rewritten["rewritten_support_km"] = 0.1
        self.assertEqual(load_wrf(store, rewritten, at=NOW).refusal.rule_id, "R-support")
        joined = store.add_join(
            observation=wrf.iri,
            boundary=pilot.parcel,
            relation="geo:sfIntersects",
            crs="EPSG:4326",
            generated_at=NOW,
            at=NOW,
        )
        self.assertTrue(joined.ok)
        self.assertEqual(store.observations[wrf.iri].native_resolution.value, 3)
        self.assertEqual(observations_of(store, pilot.parcel, NOW), [])

        os.environ["CWA_API_KEY"] = "do-not-commit-this-value"
        status = live_status()
        self.assertTrue(status["key_present"])
        self.assertFalse(status["live_fetch"])
        self.assertNotIn("do-not-commit-this-value", json.dumps(status))
        preflight = load_json("gcp-preflight.json")
        self.assertEqual(preflight["gcloud"]["project_id"], "seges-ai")
        self.assertEqual(preflight["gcloud"]["active_configuration"], "segescloud")
        self.assertFalse(preflight["earth_engine"]["live_export"])
        self.assertEqual(preflight["earth_engine"]["registration_type"], "unknown")
        self.assertTrue(FIXTURES.joinpath("gcp-preflight.json").is_file())


if __name__ == "__main__":
    unittest.main()
