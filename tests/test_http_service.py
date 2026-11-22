"""Offline tests for the HTTP service wiring."""

from __future__ import annotations

import json
import os
import subprocess
import sys
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

    def test_environment_flags_cannot_unlock_public_financial_metadata(self):
        env = {**os.environ, "FARM_FINANCIAL_USE": "true", "FARM_USE_CLASS": "Settlement"}
        script = "from farm_ontology.http_service import STATUS_JSON; import json; print(json.dumps(STATUS_JSON))"
        payload = json.loads(subprocess.check_output([sys.executable, "-c", script], env=env, text=True))
        self.assertEqual(payload["use_class"], "Screening")
        self.assertFalse(payload["permits_financial_use"])
        with mock.patch.dict(hs.os.environ, env), mock.patch.object(hs, "_get_json", return_value=(200, "application/json", b"{}")):
            self.assertFalse(hs._open_meteo_current(42.7, 142.4)["permits_financial_use"])
            with mock.patch.object(hs, "_metadata_token", return_value=None):
                self.assertFalse(hs._ee_catalog()["permits_financial_use"])
        with mock.patch.dict(hs.os.environ, {**env, "PLANET_API_KEY": "test"}), mock.patch.object(hs, "_planet_post", return_value=(200, {"features": []}, "Basic")):
            self.assertFalse(hs._planet_search(42.7, 142.4)["permits_financial_use"])

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

    def test_licences_snapshot_shows_the_operator_unlock(self):
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
            # controller authorization is not evidence of provider rights
            self.assertFalse(verdict["settlement_allowed"], feed)
            self.assertEqual(verdict["settlement_reason"], "provider_rights_unverified", feed)
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


class ObservationsRouteTests(unittest.TestCase):
    """GET /farm/observations: token-gated record read (final wave)."""

    def setUp(self):
        self.expected = "0f3ae1c8719c4b5aa0d5ff2b6c8e77d41c9c0dbe2f7a49b58e2f7a1d3c5b6e70"
        patcher = mock.patch.dict(
            hs.os.environ, {"WEB_ACCESS_TOKEN": self.expected}, clear=False
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.stamps = [
            {
                "file": "obs-20261118T075203Z.json",
                "recorded_at": "2026-11-18T07:52:03+00:00",
                "availability_time": "2026-11-18T07:52:10+00:00",
                "support": {
                    "native_resolution_deg": 0.05,
                    "spatial_support": "grid-cell",
                    "shrunk_to_plant": False,
                    "gps_accuracy": "unknown",
                },
                "use_class": "Screening",
                "class_c_policy": "closed",
                "permits_financial_use": False,
                "dry_run": False,
            }
        ]

    def _with_reader(self, stamps):
        return mock.patch.object(hs, "_latest_observations", return_value=list(stamps))

    def test_header_returns_stamped_observations(self):
        with self._with_reader(self.stamps):
            status, payload, kind = handle_target("/farm/observations", token=self.expected)
        self.assertEqual(status, 200)
        self.assertEqual(kind, "json")
        self.assertEqual(payload["count"], 1)
        row = payload["observations"][0]
        self.assertEqual(row["file"], "obs-20261118T075203Z.json")
        self.assertIn("support", row)
        self.assertEqual(row["support"]["spatial_support"], "grid-cell")
        self.assertFalse(row["support"]["shrunk_to_plant"])
        self.assertEqual(row["use_class"], "Screening")
        self.assertFalse(row["permits_financial_use"])

    def test_query_tokens_are_rejected_even_with_valid_header(self):
        for path in ("/farm/observations?token=secret", "/leads?token=", "/leads?token=secret"):
            with self.subTest(path=path):
                status, payload, _ = handle_target(path, token=self.expected)
                self.assertEqual(status, 400)
                self.assertIn("query-string credentials", payload["gap"])

    def test_header_token_honoured(self):
        with self._with_reader(self.stamps):
            status, payload, _kind = handle_target("/farm/observations", token=self.expected)
        self.assertEqual(status, 200)
        self.assertEqual(payload["count"], 1)

    def test_bad_token_is_401_gap(self):
        status, payload, kind = handle_target("/farm/observations", token="WRONG")
        self.assertEqual(status, 401)
        self.assertEqual(kind, "json")
        self.assertIn("gap", payload)
        self.assertNotIn("observations", payload)

    def test_absent_token_is_401_gap(self):
        status, payload, _kind = handle_target("/farm/observations")
        self.assertEqual(status, 401)
        self.assertIn("gap", payload)

    def test_unmounted_secret_fails_closed_even_with_any_token(self):
        with mock.patch.dict(hs.os.environ, clear=False):
            hs.os.environ.pop("WEB_ACCESS_TOKEN", None)
            status, payload, _kind = handle_target("/farm/observations", token="whatever")
        self.assertEqual(status, 401)
        self.assertIn("fails closed", payload["gap"])

    def test_limit_is_parsed_capped_and_floor_safe(self):
        with self._with_reader([]):
            _status, payload, _k = handle_target("/farm/observations?limit=999", token=self.expected)
        self.assertEqual(payload["limit"], hs.OBSERVATIONS_MAX_LIMIT)
        with self._with_reader([]):
            _status, payload, _k = handle_target("/farm/observations?limit=nonsense", token=self.expected)
        self.assertEqual(payload["limit"], hs.OBSERVATIONS_DEFAULT_LIMIT)

    def test_backend_failure_is_a_gap_not_a_crash(self):
        with mock.patch.object(hs, "_latest_observations", side_effect=OSError("backend down")):
            status, payload, kind = handle_target("/farm/observations", token=self.expected)
        self.assertEqual(status, 200)
        self.assertEqual(kind, "json")
        self.assertIn("gap", payload)
        self.assertIn("backend down", payload["gap"])

    def test_latest_observations_read_through_the_record_seam(self):
        with mock.patch("farm_ontology.record_store.open_backend") as fake_factory:
            store = mock.Mock()
            store.list_paths.side_effect = lambda sub, pattern: (
                ["obs-20261118T075203Z.json", "obs-20261118T120948Z.json"]
                if not sub
                else []
            )
            store.read_text.side_effect = lambda name: json.dumps(
                {
                    "phenomenon_time": "2026-11-18T12:09:48+00:00",
                    "availability_time": "2026-11-18T12:09:55+00:00",
                    "gps_accuracy": "unknown",
                    "use_class": "Screening",
                    "class_c_policy": "closed",
                    "permits_financial_use": False,
                    "dry_run": True,
                    "weather": {
                        "native_resolution_deg": 0.05,
                        "spatial_support": "grid-cell",
                        "shrunk_to_plant": False,
                    },
                }
            )
            fake_factory.return_value = store
            stamps = hs._latest_observations(5)
        self.assertEqual([s["file"] for s in stamps], ["obs-20261118T120948Z.json", "obs-20261118T075203Z.json"])
        newest = stamps[0]
        self.assertEqual(newest["recorded_at"], "2026-11-18T12:09:48+00:00")
        self.assertEqual(newest["support"]["native_resolution_deg"], 0.05)
        self.assertTrue(newest["dry_run"])

    def test_access_tokens_never_reach_the_request_log_line(self):
        import io
        import contextlib

        handler = hs.Handler.__new__(hs.Handler)  # bypass init; test log_message alone
        logged = io.StringIO()
        with contextlib.redirect_stderr(logged):
            handler.client_address = ("203.0.113.9", 44444)
            handler.address_string = lambda: "203.0.113.9"  # type: ignore[method-assign]
            handler.log_message('"GET /farm/observations?token=%s HTTP/1.1" 200 -', "SUPERSECRET")
        line = logged.getvalue()
        self.assertNotIn("SUPERSECRET", line)
        self.assertIn("<redacted>", line)


if __name__ == "__main__":
    unittest.main()
