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
        doc = {
            "features": [
                {
                    "id": "20261116_012345_88",
                    "properties": {
                        "acquired": "2026-11-16T01:23:45.000Z",
                        "cloud_cover": 0.12,
                        "instrument": "PSB.SD",
                        "publishing_stage": "finalized",
                        "quality_category": "standard",
                        "strip_id": "123456",
                    },
                }
            ]
        }
        with mock.patch.dict(hs.os.environ, {"PLANET_API_KEY": "test-key"}, clear=False):
            with mock.patch.object(
                hs, "_planet_post", return_value=(200, doc, "Basic")
            ) as poster:
                result = hs._planet_search(42.7, 142.4)
        self.assertNotIn("gap", result)
        self.assertEqual(result["scenes"][0]["id"], "20261116_012345_88")
        self.assertEqual(result["auth_scheme"], "Basic")
        self.assertFalse(result["permits_financial_use"])
        poster.assert_called_once()

    def test_planet_auth_failure_reports_hint(self):
        with mock.patch.dict(hs.os.environ, {"PLANET_API_KEY": "bad-key"}, clear=False):
            with mock.patch.object(
                hs,
                "_planet_post",
                side_effect=hs.PlanetAuthError(401, '{"message":"api_key not found"}'),
            ):
                result = hs._planet_search(42.7, 142.4)
        self.assertIn("gap", result)
        self.assertIn("planet.com/account", result["hint"])

    def test_memo_states_the_rules(self):
        _status, text, kind = handle_target("/farm/memo")
        self.assertEqual(kind, "text")
        self.assertIn("permits_financial_use: false", text)
        self.assertIn("no hectare extrapolation", text)
        self.assertIn("refused", text)

    def test_ee_catalog_uses_runtime_identity_when_available(self):
        with mock.patch.object(hs, "_metadata_token", return_value="tok-xyz"), mock.patch.object(
            hs, "_get_json", return_value=(200, "application/json", b"{}")
        ):
            result = hs._ee_catalog()
        self.assertEqual(result["catalog_http_status"], 200)
        self.assertTrue(result["used_runtime_identity"])

    def test_licences_snapshot_is_fail_closed_now(self):
        result = hs._licences_snapshot()
        self.assertNotIn("gap", result)
        self.assertTrue(result["feeds"])
        self.assertEqual(set(result["feeds"]), {
            "earth-engine.export",
            "jma.hazard",
            "open-meteo.jma-msm",
            "planet.planetary-variable.soil-water-content",
            "planet.psscene",
            "usdm.hazard",
        })
        for feed, verdict in result["feeds"].items():
            self.assertFalse(verdict["settlement_allowed"], feed)
            self.assertTrue(verdict["settlement_reason"], feed)
            self.assertIsInstance(verdict["screening_allowed"], bool)
            self.assertTrue(verdict["screening_reason"], feed)
        self.assertIn("Specimen certificates exist", result["note"])

    def test_licences_route_registered(self):
        status, payload, kind = handle_target("/farm/licences")
        self.assertEqual(status, 200)
        self.assertEqual(kind, "json")
        self.assertIn("feeds", payload)

    def test_metadata_token_off_platform_is_none(self):
        with mock.patch.object(
            hs.urllib.request, "urlopen", side_effect=OSError("no metadata")
        ):
            self.assertIsNone(hs._metadata_token())


if __name__ == "__main__":
    unittest.main()
