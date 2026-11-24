"""The Next page bridge writes the same record and does not call weather."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.page_io import dispatch


class PageIoTests(unittest.TestCase):
    def setUp(self):
        self._old = os.environ.get("FARM_RECORD_DIR")
        self._old_require_tenant = os.environ.get("FARM_REQUIRE_TENANT_CONTEXT")
        self._old_require_idempotency = os.environ.get("FARM_REQUIRE_IDEMPOTENCY")
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["FARM_RECORD_DIR"] = self._tmp.name
        os.environ.pop("FARM_REQUIRE_TENANT_CONTEXT", None)
        os.environ.pop("FARM_REQUIRE_IDEMPOTENCY", None)

    def tearDown(self):
        self._tmp.cleanup()
        if self._old is None:
            os.environ.pop("FARM_RECORD_DIR", None)
        else:
            os.environ["FARM_RECORD_DIR"] = self._old
        if self._old_require_tenant is None:
            os.environ.pop("FARM_REQUIRE_TENANT_CONTEXT", None)
        else:
            os.environ["FARM_REQUIRE_TENANT_CONTEXT"] = self._old_require_tenant
        if self._old_require_idempotency is None:
            os.environ.pop("FARM_REQUIRE_IDEMPOTENCY", None)
        else:
            os.environ["FARM_REQUIRE_IDEMPOTENCY"] = self._old_require_idempotency

    def test_observe_ignores_weather_and_stays_closed(self):
        saved = dispatch(
            {
                "op": "observe",
                "latitude": 1,
                "longitude": 2,
                "sample_id": "bridge-row",
                "note": "standing at the row",
                "attach_weather": True,
                "dry_run": False,
            }
        )
        obs = saved["observation"]
        self.assertEqual(obs["class_c_policy"], "closed")
        self.assertFalse(obs["permits_financial_use"])
        self.assertIsNone(obs["weather"]["value"])
        self.assertNotIn("attach_error", obs["weather"])
        self.assertEqual(obs["crop_ontology_id"], "CO_336")
        record = Path(self._tmp.name)
        self.assertTrue(saved["file"].startswith("obs-"))
        self.assertTrue(saved["file"].endswith(".json"))
        self.assertTrue((record / saved["file"]).is_file())
        listed = dispatch({"op": "list"})
        self.assertEqual(listed["observations"][0]["file"], saved["file"])
        note = dispatch(
            {
                "op": "note",
                "kind": "feedback",
                "text": "the type is large enough",
                "observation_file": saved["file"],
            }
        )
        self.assertEqual(note["note"]["kind"], "feedback")
        self.assertFalse(note["note"]["permits_financial_use"])
        self.assertTrue(note["file"].startswith("note-feedback-"))
        self.assertTrue((record / "notes" / note["file"]).is_file())

    def test_next_sources_do_not_call_weather_or_maps(self):
        root = Path(__file__).resolve().parents[1] / "web"
        parts = []
        for path in root.rglob("*"):
            if path.suffix not in {".ts", ".tsx", ".css", ".js"}:
                continue
            if "node_modules" in path.parts or ".next" in path.parts:
                continue
            parts.append(path.read_text(encoding="utf-8"))
        # WS8 architecture (2026-11-18): the browser never talks to third-party
        # weather/map vendors directly — every advisory value flows through OUR
        # decision backend (FARM_API_BASE proxies), which stamps native support
        # and licence verdicts onto the payload. The vendor ban bites where it
        # matters: NO fetching code in the web app may target a vendor. The
        # report DATA file may QUOTE the upstream URL as provenance lineage
        # (quoting sources is the product's religion; calling them is not).
        backend = (root / "lib" / "backend.ts").read_text(encoding="utf-8").lower()
        text = "\n".join(parts).lower()
        self.assertNotIn("open-meteo", backend)
        self.assertNotIn("api.open-meteo.com", backend)
        # no client-side direct fetch of a vendor host anywhere
        self.assertNotRegex(text, r"fetch\(\s*[\"'`]https://(api\.open-meteo|single-runs-api\.open-meteo)")
        self.assertNotIn("attach_weather", text)
        self.assertNotIn("maps.googleapis", text)
        self.assertNotIn("earthengine", text)
        self.assertNotIn("openstreetmap", text)
        # the proxy seam is mandatory: weather arrives named via our backend
        self.assertIn("farm_api_base", text)
        # honesty caption ships with the advisory panel (grid vs parcel)
        self.assertIn("support: grid", text)
        # founder directive 2026-11-18: five first-class locales
        self.assertIn("th", text)
        self.assertIn('"ja"', text)
        self.assertIn("zh-tw", text)
        self.assertIn("zh-cn", text)
        self.assertIn("geolocation", text)

    def test_mcp_and_fieldkit_write_the_same_coordinates(self):
        from farm_ontology.fieldkit import main
        from farm_ontology.mcp_stdio import call_tool

        kit_dir = tempfile.TemporaryDirectory()
        self.addCleanup(kit_dir.cleanup)
        out = Path(kit_dir.name) / "kit.json"
        self.assertEqual(
            main(["--lat", "1.25", "--lon", "2.5", "--sample-id", "shared-row", "--out", str(out)]),
            0,
        )
        kit = json.loads(out.read_text(encoding="utf-8"))
        saved = call_tool(
            "record_field_observation",
            {
                "latitude": 1.25,
                "longitude": 2.5,
                "sample_id": "shared-row",
                "attach_weather": False,
            },
        )
        body = json.loads(saved["content"][0]["text"])
        obs = body["observation"]
        record = Path(self._tmp.name)
        self.assertTrue(body["file"].startswith("obs-"))
        self.assertTrue((record / body["file"]).is_file())
        self.assertEqual(list(record.glob("kit.json")), [])
        self.assertEqual(set(kit), set(obs))
        self.assertEqual(set(kit["weather"]), set(obs["weather"]))
        self.assertEqual(kit["latitude"], obs["latitude"])
        self.assertEqual(kit["longitude"], obs["longitude"])
        self.assertEqual(kit["row_or_sample_id"], obs["row_or_sample_id"])
        self.assertEqual(obs["class_c_policy"], "closed")
        self.assertFalse(obs["permits_financial_use"])
        self.assertFalse(kit["permits_financial_use"])
        self.assertIsNone(obs["weather"]["value"])
        flags = (Path(__file__).resolve().parents[1] / "farm_ontology" / "fieldkit.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"--lat"', flags)
        self.assertIn('"--lon"', flags)

    def test_farm_records_and_reads_are_isolated_and_legacy_rows_stay_unassigned(self):
        legacy = dispatch(
            {"op": "observe", "latitude": 1, "longitude": 2, "note": "legacy"}
        )
        farm_a = dispatch(
            {
                "op": "observe",
                "farm_id": "biratori-a",
                "latitude": 3,
                "longitude": 4,
                "note": "farm a",
            }
        )
        farm_b = dispatch(
            {
                "op": "observe",
                "farm_id": "biratori-b",
                "latitude": 5,
                "longitude": 6,
                "note": "farm b",
            }
        )

        listed_a = dispatch({"op": "list", "farm_id": "biratori-a"})
        listed_b = dispatch({"op": "list", "farm_id": "biratori-b"})
        self.assertEqual([row["file"] for row in listed_a["observations"]], [farm_a["file"]])
        self.assertEqual([row["file"] for row in listed_b["observations"]], [farm_b["file"]])
        self.assertNotIn(legacy["file"], [row["file"] for row in listed_a["observations"]])
        self.assertNotIn(farm_b["file"], [row["file"] for row in listed_a["observations"]])
        self.assertEqual(listed_a["observations"][0]["farm_id"], "biratori-a")
        self.assertEqual(dispatch({"op": "status", "farm_id": "biratori-a"})["observation_count"], 1)

        corners = [
            {"corner": "NW", "lat": 42.0, "lon": 142.0, "accuracy_m": 3.0},
            {"corner": "NE", "lat": 42.0, "lon": 142.001, "accuracy_m": 3.0},
            {"corner": "SE", "lat": 41.999, "lon": 142.001, "accuracy_m": 3.0},
            {"corner": "SW", "lat": 41.999, "lon": 142.0, "accuracy_m": 3.0},
        ]
        walk_a = dispatch(
            {
                "op": "boundary_walk",
                "farm_id": "biratori-a",
                "parcel_name": "north field",
                "corners": corners,
            }
        )
        dispatch(
            {
                "op": "boundary_walk",
                "farm_id": "biratori-b",
                "parcel_name": "south field",
                "corners": corners,
            }
        )
        walks_a = dispatch({"op": "list_walks", "farm_id": "biratori-a"})["walks"]
        self.assertEqual([row["file"] for row in walks_a], [walk_a["file"]])
        self.assertEqual(walks_a[0]["parcel_name"], "north field")

        with self.assertRaisesRegex(ValueError, "not in the record"):
            dispatch(
                {
                    "op": "note",
                    "farm_id": "biratori-a",
                    "kind": "feedback",
                    "text": "cross farm link must refuse",
                    "observation_file": farm_b["file"],
                }
            )

    def test_hosted_record_operations_require_authenticated_farm_context(self):
        os.environ["FARM_REQUIRE_TENANT_CONTEXT"] = "true"
        for operation in ("status", "list", "list_walks"):
            with self.subTest(operation=operation):
                with self.assertRaisesRegex(ValueError, "farm_id is required"):
                    dispatch({"op": operation})
        with self.assertRaisesRegex(ValueError, "farm_id is required"):
            dispatch({"op": "observe", "latitude": 1, "longitude": 2})

        saved = dispatch(
            {
                "op": "observe",
                "farm_id": "biratori-a",
                "latitude": 1,
                "longitude": 2,
            }
        )
        self.assertEqual(saved["observation"]["farm_id"], "biratori-a")

    def test_invalid_farm_identifier_cannot_escape_tenant_prefix(self):
        for farm_id in ("../other", "Farm-A", "farm/a", "", "a." ):
            with self.subTest(farm_id=farm_id):
                with self.assertRaisesRegex(ValueError, "farm_id"):
                    dispatch({"op": "list", "farm_id": farm_id})

    def test_hosted_writes_require_stable_request_ids(self):
        os.environ["FARM_REQUIRE_TENANT_CONTEXT"] = "1"
        os.environ["FARM_REQUIRE_IDEMPOTENCY"] = "1"
        with self.assertRaisesRegex(ValueError, "request_id is required"):
            dispatch({"op": "observe", "farm_id": "biratori-a", "latitude": 1, "longitude": 2})

        observation_request = {
            "op": "observe",
            "farm_id": "biratori-a",
            "request_id": "550e8400-e29b-41d4-a716-446655440000",
            "latitude": 1,
            "longitude": 2,
            "note": "same payload",
        }
        first_observation = dispatch(observation_request)
        retried_observation = dispatch(observation_request)
        self.assertEqual(first_observation, retried_observation)
        self.assertEqual(len(list(Path(self._tmp.name).glob("farms/biratori-a/obs-*.json"))), 1)
        with self.assertRaisesRegex(ValueError, "reused with a different payload"):
            dispatch({**observation_request, "note": "changed payload"})

        other_farm = dispatch({**observation_request, "farm_id": "biratori-b"})
        self.assertEqual(first_observation["file"], other_farm["file"])
        self.assertTrue(
            (Path(self._tmp.name) / "farms" / "biratori-a" / first_observation["file"]).is_file()
        )
        self.assertTrue(
            (Path(self._tmp.name) / "farms" / "biratori-b" / other_farm["file"]).is_file()
        )

        note_request = {
            "op": "note",
            "farm_id": "biratori-a",
            "request_id": "550e8400-e29b-41d4-a716-446655440001",
            "kind": "verification",
            "text": "checked row",
            "observation_file": first_observation["file"],
        }
        first_note = dispatch(note_request)
        self.assertEqual(first_note, dispatch(note_request))
        self.assertEqual(len(list(Path(self._tmp.name).glob("farms/biratori-a/notes/*.json"))), 1)
        with self.assertRaisesRegex(ValueError, "reused with a different payload"):
            dispatch({**note_request, "text": "different note"})

        corners = [
            {"corner": "NW", "lat": 42.0, "lon": 142.0, "accuracy_m": 3.0},
            {"corner": "NE", "lat": 42.0, "lon": 142.001, "accuracy_m": 3.0},
            {"corner": "SE", "lat": 41.999, "lon": 142.001, "accuracy_m": 3.0},
            {"corner": "SW", "lat": 41.999, "lon": 142.0, "accuracy_m": 3.0},
        ]
        walk_request = {
            "op": "boundary_walk",
            "farm_id": "biratori-a",
            "request_id": "550e8400-e29b-41d4-a716-446655440002",
            "parcel_name": "North field",
            "corners": corners,
        }
        first_walk = dispatch(walk_request)
        self.assertEqual(first_walk, dispatch(walk_request))
        self.assertEqual(len(list(Path(self._tmp.name).glob("farms/biratori-a/boundary/*.json"))), 1)
        with self.assertRaisesRegex(ValueError, "reused with a different payload"):
            dispatch({**walk_request, "parcel_name": "South field"})


if __name__ == "__main__":
    unittest.main()
