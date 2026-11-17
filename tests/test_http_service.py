"""Offline tests for the HTTP service wiring."""

from __future__ import annotations

import json
import unittest
from unittest import mock

from farm_ontology import http_service as hs
from farm_ontology.http_service import (
    STATUS_JSON,
    handle_target,
)


class HttpServiceRoutingTests(unittest.TestCase):
    def test_root_reports_farm_screening_closed(self):
        status, payload, kind = handle_target("/")
        self.assertEqual(status, 200)
        self.assertEqual(kind, "json")
        self.assertEqual(payload["use_class"], "Screening")
        self.assertEqual(payload["class_c"], "closed")
        self.assertFalse(payload["permits_financial_use"])

    def test_farm_pin_is_the_current_location(self):
        farm = STATUS_JSON["farm"]
        self.assertAlmostEqual(farm["latitude"], 42.7018152)
        self.assertAlmostEqual(farm["longitude"], 142.4071291)
        self.assertIn("Biratori", farm["label"])
        self.assertEqual(farm["tenure"], "unknown")

    def test_livez_answers(self):
        status, payload, kind = handle_target("/livez")
        self.assertEqual(status, 200)
        self.assertEqual(kind, "json")
        self.assertEqual(payload["status"], "live")

    def test_unknown_route_is_404_json(self):
        status, payload, kind = handle_target("/nope")
        self.assertEqual(status, 404)
        self.assertEqual(kind, "json")
        self.assertIn("error", payload)

    def test_secrets_block_reports_presence_without_values(self):
        text = json.dumps(STATUS_JSON)
        self.assertIn("PLANET_API_KEY", text)
        self.assertLessEqual(len(json.dumps(STATUS_JSON["secrets_mounted"])), 200)

    def test_weather_failure_is_a_gap_not_a_value(self):
        with mock.patch.object(hs, "_open_meteo_current", side_effect=OSError("network down")):
            status, payload, kind = handle_target("/farm/weather")
        self.assertEqual(status, 200)
        self.assertEqual(kind, "json")
        self.assertIn("gap", payload)
        self.assertIn("network down", payload["gap"])

    def test_planet_without_key_refuses(self):
        with mock.patch.dict(hs.os.environ, {}, clear=False):
            hs.os.environ.pop("PLANET_API_KEY", None)
            result = hs._planet_search(42.7, 142.4)
        self.assertIn("gap", result)
        self.assertIn("PLANET_API_KEY", result["gap"])

    def test_planet_success_lists_header_rows_only(self):
        scene_props = {
            "acquired": "2026-11-16T01:23:45.000Z",
            "cloud_cover": 0.12,
            "instrument": "PSB.SD",
            "publishing_stage": "finalized",
            "quality_category": "standard",
            "strip_id": "123456",
        }
        payload = {"features": [{"id": "20261116_012345_88", "properties": scene_props}]}
        fake_response = mock.MagicMock()
        fake_response.read.return_value = json.dumps(payload).encode("utf-8")
        fake_response.__enter__.return_value = fake_response
        with mock.patch.dict(hs.os.environ, {"PLANET_API_KEY": "test-key"}, clear=False):
            with mock.patch.object(hs.urllib.request, "urlopen", return_value=fake_response):
                result = hs._planet_search(42.7, 142.4)
        self.assertNotIn("gap", result)
        self.assertEqual(result["scenes"][0]["id"], "20261116_012345_88")
        self.assertFalse(result["permits_financial_use"])

    def test_memo_states_the_rules(self):
        _status, text, kind = handle_target("/farm/memo")
        self.assertEqual(kind, "text")
        self.assertIn("permits_financial_use: false", text)
        self.assertIn("no hectare extrapolation", text)
        self.assertIn("refused", text)


if __name__ == "__main__":
    unittest.main()
