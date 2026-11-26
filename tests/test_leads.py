"""Sprint-K lead capture tests: consent-first, hashed, CORS, admin listing."""

from __future__ import annotations

import os
import tempfile
import unittest

from farm_ontology.http_service import handle_lead_post, _leads_admin
from farm_ontology.leads import lead_hash


class LeadsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._old = os.environ.pop("FARM_RECORD_DIR", None)
        self._old_origins = os.environ.pop("LEADS_ALLOWED_ORIGINS", None)
        os.environ["FARM_RECORD_DIR"] = self._tmp.name
        self._old_tok = os.environ.pop("WEB_ACCESS_TOKEN", None)
        os.environ["WEB_ACCESS_TOKEN"] = "test-token"

    def tearDown(self):
        os.environ["FARM_RECORD_DIR"] = self._old or ""
        os.environ.pop("FARM_RECORD_DIR", None)
        os.environ.pop("LEADS_ALLOWED_ORIGINS", None)
        if self._old_origins is not None:
            os.environ["LEADS_ALLOWED_ORIGINS"] = self._old_origins
        os.environ.pop("WEB_ACCESS_TOKEN", None)
        if self._old_tok:
            os.environ["WEB_ACCESS_TOKEN"] = self._old_tok
        self._tmp.cleanup()

    def _body(self, **overrides):
        payload = {
            "kind": "pro-waitlist",
            "name": "Bean Fan",
            "email": "fan@example.jp",
            "locale": "ja",
            "statement": "shown consent sentence",
            "consent": True,
        }
        payload.update(overrides)
        import json

        return json.dumps(payload).encode("utf-8")

    def test_valid_lead_is_hashed_and_returned(self):
        status, row, _headers = handle_lead_post(self._body(), origin=None)
        self.assertEqual(status, 200)
        self.assertTrue(row["ok"])
        self.assertEqual(len(row["hash"]), 64)
        self.assertTrue(row["file"].startswith("leads/"))
        self.assertTrue(row["file"].endswith(".json"))

    def test_consent_false_is_refused_422(self):
        status, payload, _ = handle_lead_post(self._body(consent=False), origin=None)
        self.assertEqual(status, 422)
        self.assertIn("consent", payload["gap"])

    def test_bad_kind_and_email_refused(self):
        status, payload, _ = handle_lead_post(self._body(kind="spam"), origin=None)
        self.assertEqual(status, 422)
        status, payload, _ = handle_lead_post(self._body(email="nope"), origin=None)
        self.assertEqual(status, 422)

    def test_audience_and_farm_context_are_stored_for_routing(self):
        import json

        status, result, _headers = handle_lead_post(
            self._body(
                kind="access-code-request",
                audience="farmer",
                farm_name="North Field",
                region="Hidaka",
            ),
            origin=None,
        )
        self.assertEqual(status, 200)
        from farm_ontology.record import record_dir
        from farm_ontology.record_store import open_backend

        body = json.loads(open_backend(record_dir()).read_text(result["file"]))
        self.assertEqual(body["audience"], "farmer")
        self.assertEqual(body["farm_name"], "North Field")
        self.assertEqual(body["region"], "Hidaka")

    def test_unknown_audience_is_refused(self):
        status, payload, _headers = handle_lead_post(self._body(audience="trader"), origin=None)
        self.assertEqual(status, 422)
        self.assertIn("audience", payload["gap"])

    def test_cors_headers_echo_the_landing_origin(self):
        from farm_ontology.leads import _LANDING_ORIGINS, cors_preflight

        self.assertIn("https://seges.ai", _LANDING_ORIGINS)
        self.assertIn("https://www.seges.ai", _LANDING_ORIGINS)
        status, _row, headers = handle_lead_post(self._body(), origin="https://seges.ai")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Access-Control-Allow-Origin"], "https://seges.ai")
        self.assertEqual(
            cors_preflight("https://seges.ai")["Access-Control-Allow-Origin"],
            "https://seges.ai",
        )
        self.assertNotIn("Access-Control-Allow-Origin", cors_preflight("https://attacker.example"))

    def test_cors_does_not_echo_an_unlisted_origin(self):
        status, _payload, headers = handle_lead_post(self._body(), origin="https://attacker.example")
        self.assertEqual(status, 200)
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_admin_listing_needs_the_token(self):
        status, payload, _ = _leads_admin(token="WRONG")
        self.assertEqual(status, 401)
        handle_lead_post(self._body(), origin=None)
        status, payload, _ = _leads_admin(token="test-token")
        self.assertEqual(status, 200)
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["leads"][0]["kind"], "pro-waitlist")


if __name__ == "__main__":
    unittest.main()
