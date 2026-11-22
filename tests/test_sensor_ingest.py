import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.build import mint
from farm_ontology.identity import load_synthetic_pilot
from farm_ontology.namespaces import IRI_BASE
from farm_ontology.sensors import (
    DEVICE_CLASSES,
    ingest_device_json,
    ingest_record,
    sensor_support_disabled,
)
from farm_ontology.store import Store
from tests.support import NOW

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "sensors"

TIP_MM = 0.2794


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def soil_payload(**changes) -> dict:
    base = load_fixture("device-proto-soil.json")
    base.update(changes)
    return base


class SensorIngestTests(unittest.TestCase):
    def test_soil_payload_builds_calibrated_instrument_point(self):
        store = Store()
        doc = load_fixture("device-proto-soil.json")
        (result,) = ingest_device_json(store, doc, at=NOW)
        self.assertTrue(result.ok)
        obs = store.observations[result.iri]
        self.assertEqual(obs.feature_kind, "instrument-point")
        self.assertEqual(obs.spatial_support, "point-soil-probe")
        self.assertTrue(
            obs.feature_of_interest.startswith(IRI_BASE + "instrument/point-soil-probe-10m3-"),
            obs.feature_of_interest,
        )
        self.assertEqual(obs.sensor_iri, IRI_BASE + "sensor/protokit-se02-soila")
        self.assertIsNotNone(obs.calibration_activity)
        self.assertIsNotNone(obs.error)
        self.assertEqual(obs.error.metric, "rmse")
        self.assertAlmostEqual(obs.error.value.value, 0.018)
        self.assertEqual(obs.result.unit_iri.split("/")[-1], "PERCENT")
        self.assertEqual(
            obs.result.quantity_kind_iri.split("/")[-1], "DimensionlessRatio"
        )
        self.assertEqual(obs.procedure, IRI_BASE + "procedure/sensor")
        self.assertTrue(obs.dry_run)

    def test_soil_depth_changes_the_native_feature_label(self):
        store = Store()
        (deep,) = ingest_device_json(
            store, soil_payload(depth_cm=50, device_id="protokit-se02-soilb"), at=NOW
        )
        self.assertTrue(deep.ok)
        deep_obs = store.observations[deep.iri]
        self.assertIn("point-soil-probe-50m3-", deep_obs.feature_of_interest)

    def test_rain_tips_convert_to_millimetres_with_shared_certificate(self):
        store = Store()
        doc = load_fixture("device-proto-rain.json")
        results = ingest_device_json(store, doc, at=NOW)
        self.assertTrue(all(item.ok for item in results), [r.refusal for r in results])
        self.assertEqual(len(results), 2)
        rain = store.observations[results[0].iri]
        self.assertAlmostEqual(rain.result.value, 8 * TIP_MM)
        self.assertEqual(rain.result.unit_iri.split("/")[-1], "MilliM")
        self.assertEqual(
            rain.result.quantity_kind_iri.split("/")[-1], "Length"
        )
        self.assertIn("raingauge-", rain.feature_of_interest)
        wetness = store.observations[results[1].iri]
        self.assertIn("leafwetness-", wetness.feature_of_interest)
        self.assertIsNotNone(wetness.error)
        self.assertNotEqual(rain.iri, wetness.iri)

    def test_missing_sensor_constants_refuse_instead_of_assuming(self):
        soil = soil_payload()
        soil.pop("depth_cm")
        self.assertFalse(ingest_record(Store(), soil, at=NOW).ok)
        rain = load_fixture("device-proto-rain.json")
        rain.pop("tip_mm")
        self.assertFalse(ingest_record(Store(), rain, at=NOW).ok)
        rain["tip_mm"] = float("nan")
        self.assertFalse(ingest_record(Store(), rain, at=NOW).ok)

    def test_uncalibrated_rows_are_refused_before_the_store(self):
        store = Store()
        (result,) = ingest_device_json(
            store, soil_payload(calibration_activity=None), at=NOW
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.refusal.rule_id, "R-sensor")
        self.assertIn("calibration", result.refusal.attempted_change)
        self.assertEqual(store.observations, {})

    def test_expired_certificate_rows_are_refused(self):
        store = Store()
        (result,) = ingest_device_json(
            store, soil_payload(recalibration_due="2026-01-01T00:00:00+00:00"), at=NOW
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.refusal.rule_id, "R-sensor")
        self.assertIn("expired", result.refusal.attempted_change)

    def test_unknown_device_class_and_bad_device_ids_refuse(self):
        store = Store()
        (unknown,) = ingest_device_json(
            store, soil_payload(device_class="telepathy"), at=NOW
        )
        self.assertEqual(unknown.refusal.rule_id, "R-property")
        (unsafe,) = ingest_device_json(
            store, soil_payload(device_id="../escape"), at=NOW
        )
        self.assertEqual(unsafe.refusal.rule_id, "R-property")
        self.assertEqual(store.observations, {})
        self.assertEqual(store.refusals[-1].rule_id, "R-property")

    def test_naive_timestamps_refuse_instead_of_crashing(self):
        store = Store()
        (result,) = ingest_device_json(
            store, soil_payload(phenomenon_time="2026-11-15T02:30:00"), at=NOW
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.refusal.rule_id, "R-property")
        (generated,) = ingest_device_json(
            store, soil_payload(generated_at="not-a-time"), at=NOW
        )
        self.assertFalse(generated.ok)

    def test_replayed_payload_hits_deterministic_parallel_refusal(self):
        store = Store()
        doc = load_fixture("device-proto-soil.json")
        (first,) = ingest_device_json(store, doc, at=NOW)
        self.assertTrue(first.ok)
        (again,) = ingest_device_json(store, dict(doc), at=NOW + timedelta(hours=1))
        self.assertFalse(again.ok)
        self.assertEqual(again.refusal.rule_id, "R-parallel")

    def test_sensor_values_never_land_on_a_boundary(self):
        store = Store()
        pilot = load_synthetic_pilot(store)
        (result,) = ingest_device_json(store, load_fixture("device-proto-soil.json"), at=NOW)
        self.assertTrue(result.ok)
        join_attempt = store.add_observation(
            type(store.observations[result.iri])(
                **{
                    **store.observations[result.iri].__dict__,
                    "iri": mint("observation", "sensed-on-boundary"),
                    "feature_of_interest": pilot.parcel,
                    "feature_kind": "boundary-polygon",
                    "spatial_support": "boundary-polygon",
                }
            ),
            at=NOW,
        )
        self.assertFalse(join_attempt.ok)
        self.assertEqual(join_attempt.refusal.rule_id, "R-sensor")

    def test_hectare_claim_requires_the_sensor_plumbing_it_got(self):
        store = Store()
        doc = load_fixture("device-proto-soil.json")
        base = None
        (result,) = ingest_device_json(store, doc, at=NOW)
        self.assertTrue(result.ok)
        base = store.observations[result.iri]
        claimed = type(base)(
            **{
                **base.__dict__,
                "iri": mint("observation", "claimed"),
                "hectare_weather_claim": True,
            }
        )
        self.assertTrue(store.add_observation(claimed, at=NOW).ok)
        # Uncalibrated sources can never make the claim: proven on a twin
        # stripped of its calibration activity.
        bare = type(base)(
            **{
                **base.__dict__,
                "iri": mint("observation", "claimed-bare"),
                "hectare_weather_claim": True,
                "sensor_iri": None,
                "calibration_activity": None,
            }
        )
        refused = store.add_observation(bare, at=NOW)
        self.assertFalse(refused.ok)
        self.assertEqual(refused.refusal.rule_id, "R-sensor")

    def test_disable_switch_refuses_everything(self):
        import os

        store = Store()
        previous = os.environ.get("FARM_SENSOR_INGEST_DISABLED")
        os.environ["FARM_SENSOR_INGEST_DISABLED"] = "1"
        try:
            self.assertTrue(sensor_support_disabled())
            (result,) = ingest_device_json(
                store, load_fixture("device-proto-soil.json"), at=NOW
            )
            self.assertFalse(result.ok)
            self.assertIn("switched off", result.refusal.attempted_change)
        finally:
            if previous is None:
                os.environ.pop("FARM_SENSOR_INGEST_DISABLED", None)
            else:
                os.environ["FARM_SENSOR_INGEST_DISABLED"] = previous
        self.assertFalse(sensor_support_disabled())

    def test_every_device_class_converts_through_one_contract(self):
        self.assertEqual(
            DEVICE_CLASSES,
            frozenset({"soil-vwc", "rain-tip", "leaf-wetness", "air-th", "air-temp"}),
        )
        store = Store()
        moment = datetime(2026, 11, 15, tzinfo=timezone.utc)
        humidity = {
            "device_id": "protokit-s31b-air",
            "device_class": "air-th",
            "value": 71.5,
            "phenomenon_time": moment.isoformat(),
            "generated_at": moment.isoformat(),
            "calibration_activity": "activity/proto-air-2026q4",
            "recalibration_due": "2027-06-01T00:00:00+00:00",
        }
        temperature = {
            **humidity,
            "device_class": "air-temp",
            "value": 6.4,
        }
        (rh_result,) = ingest_device_json(store, humidity, at=NOW)
        (t_result,) = ingest_device_json(store, temperature, at=NOW)
        self.assertTrue(rh_result.ok, rh_result.refusal and rh_result.refusal.attempted_change)
        self.assertTrue(t_result.ok, t_result.refusal and t_result.refusal.attempted_change)
        rh_obs = store.observations[rh_result.iri]
        t_obs = store.observations[t_result.iri]
        self.assertEqual(rh_obs.result.quantity_kind_iri.split("/")[-1], "RelativeHumidity")
        self.assertEqual(t_obs.result.unit_iri.split("/")[-1], "DEG_C")
        self.assertEqual(t_obs.result.quantity_kind_iri.split("/")[-1], "ThermodynamicTemperature")

    def test_wetness_out_of_range_refuses(self):
        store = Store()
        (result,) = ingest_device_json(
            store,
            {
                "device_id": "protokit-sn50-raingauge",
                "device_class": "leaf-wetness",
                "value": 5,
                "phenomenon_time": "2026-11-15T14:00:00+00:00",
                "generated_at": "2026-11-15T14:00:36+00:00",
                "calibration_activity": "activity/proto-gauge-volume-check-2026q2",
                "recalibration_due": "2027-05-01T00:00:00+00:00",
            },
            at=NOW,
        )
        self.assertFalse(result.ok)
        self.assertIn("range", result.refusal.attempted_change)


if __name__ == "__main__":
    unittest.main()
