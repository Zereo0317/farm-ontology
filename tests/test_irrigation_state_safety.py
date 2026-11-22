import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from farm_ontology.agronomy.common import AgronomyGap
from farm_ontology.agronomy.irrigation import IrrigationInitialState, irrigation_advisory

AT = datetime(2026, 8, 10, 12, tzinfo=timezone.utc)
READING = SimpleNamespace(stage="R1", cultivar_profile="hokkaido-short")
STATE = IrrigationInitialState("2026-08-06", 250, 30, 10, "synthetic initial state")

def rows():
    return [{"date": f"2026-08-{day:02d}", "t_mean_c": 20, "eto_mm": 3,
             "rain_mm": 0, "native_resolution_km": 5,
             "source_kind": "observation", "availability_time": "2026-08-10T00:00:00+00:00"}
            for day in range(7, 10)]

class IrrigationStateSafetyTests(unittest.TestCase):
    def call(self, data, state=STATE):
        return irrigation_advisory(data, reading=READING, at=AT, initial_state=state)

    def test_missing_or_disconnected_state_refuses(self):
        for state in (None, IrrigationInitialState("2026-08-05", 0, 30, 10, "evidence"),
                      IrrigationInitialState("2026-08-06", float("nan"), 30, 10, "evidence")):
            with self.subTest(state=state), self.assertRaises(AgronomyGap):
                self.call(rows(), state)

    def test_temperature_and_availability_are_required(self):
        for field in ("t_mean_c", "availability_time", "source_kind"):
            data = rows(); data[0].pop(field)
            with self.subTest(field=field), self.assertRaises(AgronomyGap):
                self.call(data)
        data = rows(); data[0]["availability_time"] = "2026-08-11T00:00:00+00:00"
        with self.assertRaises(AgronomyGap): self.call(data)

    def test_future_observation_refuses_but_available_forecast_is_explicit(self):
        data = rows(); data[-1]["date"] = "2026-08-10"
        data[1]["date"] = "2026-08-09"
        data[0]["date"] = "2026-08-08"
        state = IrrigationInitialState("2026-08-07", 250, 30, 10, "synthetic")
        with self.assertRaises(AgronomyGap): self.call(data, state)
        data[-1]["source_kind"] = "forecast"
        self.assertEqual(len(self.call(data, state).daily_trace), 3)

    def test_full_trace_matches_sliced_trace_with_returned_state(self):
        data = rows()
        whole = self.call(data)
        first = self.call(data[:2])
        second = self.call(data[2:], first.ending_state)
        self.assertAlmostEqual(whole.root_depletion_mm, second.root_depletion_mm)
        self.assertAlmostEqual(whole.ending_state.cumulative_gdd, second.ending_state.cumulative_gdd)
        self.assertAlmostEqual(whole.ending_state.surface_depletion_mm, second.ending_state.surface_depletion_mm)

if __name__ == "__main__": unittest.main()
