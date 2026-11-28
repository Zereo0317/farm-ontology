from __future__ import annotations

import unittest
from datetime import datetime, timezone

from farm_ontology.agronomy.common import AgronomyGap
from farm_ontology.agronomy.state_estimation import (
    CalibratedMeasurement,
    StateEstimate,
    assimilate_measurement,
)


NOW = datetime(2026, 11, 28, 4, 0, tzinfo=timezone.utc)


def prior(**changes):
    values = {
        "state_key": "soil-vwc|parcel:p1|zone:z1|layer:0-20cm|support:probe:sp1",
        "value": 0.20,
        "variance": 0.01,
        "unit": "m3/m3",
        "valid_at": NOW,
        "source_ref": "forecast:f1",
    }
    return StateEstimate(**{**values, **changes})


def measurement(**changes):
    values = {
        "state_key": "soil-vwc|parcel:p1|zone:z1|layer:0-20cm|support:probe:sp1",
        "value": 0.24,
        "variance": 0.0025,
        "unit": "m3/m3",
        "observed_at": NOW,
        "sensor_ref": "sensor:s1:reading:1",
        "calibration_ref": "calibration:s1:v2",
        "calibrated": True,
    }
    return CalibratedMeasurement(**{**values, **changes})


class StateEstimationTests(unittest.TestCase):
    def test_assimilates_matching_calibrated_reading_and_emits_replayable_receipt(self):
        result = assimilate_measurement(prior(), measurement(), as_of=NOW, max_age_seconds=60)
        self.assertAlmostEqual(result.gain, 0.8)
        self.assertAlmostEqual(result.posterior_value, 0.232)
        self.assertAlmostEqual(result.posterior_variance, 0.002)
        self.assertAlmostEqual(result.residual, 0.04)
        payload = result.to_payload()
        self.assertEqual(payload["status"], "state-updated-advisory-only")
        self.assertFalse(payload["actuation_authorized"])
        replay = assimilate_measurement(prior(), measurement(), as_of=NOW, max_age_seconds=60)
        self.assertEqual(result.assimilation_id, replay.assimilation_id)

    def test_refuses_different_native_support_or_layer(self):
        with self.assertRaisesRegex(AgronomyGap, "state-support-mismatch"):
            assimilate_measurement(
                prior(), measurement(state_key="soil-vwc|parcel:p1|zone:z1|layer:20-40cm|support:probe:sp1"),
                as_of=NOW, max_age_seconds=60,
            )

    def test_refuses_uncalibrated_stale_future_and_bad_variance(self):
        cases = [
            (prior(), measurement(calibrated=False), NOW, "uncalibrated-measurement"),
            (prior(valid_at=NOW.replace(hour=2)), measurement(observed_at=NOW.replace(hour=2)), NOW, "stale-measurement"),
            (prior(valid_at=NOW.replace(hour=2)), measurement(observed_at=NOW.replace(hour=3)), NOW.replace(hour=3), "stale-prior-state"),
            (prior(), measurement(observed_at=NOW.replace(hour=5)), NOW, "future-measurement"),
            (prior(), measurement(variance=0), NOW, "invalid-state-variance"),
        ]
        for prior_state, reading, as_of, reason in cases:
            with self.subTest(reason=reason), self.assertRaisesRegex(AgronomyGap, reason):
                assimilate_measurement(prior_state, reading, as_of=as_of, max_age_seconds=60)

    def test_refuses_unit_mismatch_and_naive_time(self):
        with self.assertRaisesRegex(AgronomyGap, "state-unit-mismatch"):
            assimilate_measurement(prior(), measurement(unit="percent"), as_of=NOW, max_age_seconds=60)
        with self.assertRaisesRegex(AgronomyGap, "invalid-state-time"):
            assimilate_measurement(prior(), measurement(), as_of=datetime(2026, 11, 28), max_age_seconds=60)


if __name__ == "__main__":
    unittest.main()
