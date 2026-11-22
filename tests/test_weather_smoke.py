import unittest
from deploy.verify_weather_smoke import verify_weather

class WeatherSmokeTests(unittest.TestCase):
    def test_current_weather_passes(self):
        verify_weather({"http_status": 200, "returned": {"time": "2026-11-22T00:00", "temperature_2m": 0}})
    def test_gaps_and_missing_values_fail(self):
        for payload in ({"gap": "unreachable"}, {"http_status": 500, "returned": {"time": "t", "temperature_2m": 1}}, {"http_status": 200, "returned": {}}, {"http_status": 200, "returned": {"time": "t", "temperature_2m": float("nan")}}):
            with self.subTest(payload=payload), self.assertRaises(ValueError): verify_weather(payload)
