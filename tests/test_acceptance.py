"""Acceptance: look-ahead, scale laundering, and the closed class C switch."""

import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.build import mint
from farm_ontology.identity import load_synthetic_pilot
from farm_ontology.model import Observation
from farm_ontology.policy import class_c_policy
from farm_ontology.publish import render_memo
from farm_ontology.query import associated_at, facts_at, observations_of
from farm_ontology.store import Store
from tests.support import NOW, sample_grid


class AcceptanceTests(unittest.TestCase):
    def test_ten_km_value_is_not_a_farm_measurement(self):
        store = Store()
        pilot = load_synthetic_pilot(store)
        cell = sample_grid()
        stored = store.add_observation(cell, at=NOW)
        self.assertTrue(stored.ok)

        laundered = Observation(
            **{
                **cell.__dict__,
                "iri": mint("observation", "farm-rainfall"),
                "feature_of_interest": pilot.parcel,
                "feature_kind": "boundary-polygon",
                "spatial_support": "boundary-polygon",
            }
        )
        refused = store.add_observation(laundered, at=NOW)
        self.assertFalse(refused.ok)
        self.assertEqual(refused.refusal.rule_id, "R-foi")
        self.assertNotIn(laundered.iri, store.observations)

        rewritten = Observation(
            **{
                **cell.__dict__,
                "iri": mint("observation", "rewritten-resolution"),
                "revision_of": cell.iri,
                "native_resolution": sample_grid().native_resolution.__class__(
                    value=0.01,
                    unit_iri=cell.native_resolution.unit_iri,
                    quantity_kind_iri=cell.native_resolution.quantity_kind_iri,
                ),
            }
        )
        rewrite = store.add_observation(rewritten, at=NOW)
        self.assertFalse(rewrite.ok)
        self.assertEqual(rewrite.refusal.rule_id, "R-support")
        self.assertEqual(store.observations[cell.iri].native_resolution.value, 10)

        joined = store.add_join(
            observation=cell.iri,
            boundary=pilot.parcel,
            relation="geo:sfIntersects",
            crs="EPSG:4326",
            generated_at=NOW,
            at=NOW,
        )
        self.assertTrue(joined.ok)
        self.assertEqual(store.observations[cell.iri].native_resolution.value, 10)
        self.assertNotIn(joined.iri, store.observations)
        self.assertEqual(observations_of(store, pilot.parcel, NOW), [])
        rows = associated_at(store, NOW, pilot.parcel)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["native_resolution"]["value"], 10)
        self.assertNotIn("boundary_result", rows[0])
        self.assertNotEqual(rows[0]["cell_feature"], pilot.parcel)

        memo = render_memo(store, NOW)
        for line in memo.splitlines():
            if "12.5" in line:
                self.assertNotIn(pilot.parcel, line)
        self.assertIn("support unchanged", memo)
        self.assertNotIn(
            "The farm's yield, the farm's rainfall, a hedge ratio, or a nature unit.",
            memo,
        )

    def test_look_ahead_respects_availability_and_issue_time(self):
        store = Store()
        start = datetime(2024, 6, 5, tzinfo=timezone.utc)
        end = datetime(2024, 6, 6, tzinfo=timezone.utc)
        published = datetime(2024, 7, 15, tzinfo=timezone.utc)
        final = sample_grid(
            iri=mint("observation", "chirps-final"),
            product_kind="chirps-final",
            phenomenon=sample_grid().phenomenon.__class__(start, end),
            availability_time=published,
            generated_at=published,
            native_resolution=sample_grid().native_resolution.__class__(
                value=0.05,
                unit_iri="http://qudt.org/vocab/unit/DEG",
                quantity_kind_iri="http://qudt.org/vocab/quantitykind/Angle",
            ),
        )
        self.assertTrue(store.add_observation(final, at=NOW).ok)
        phenomenon_day = datetime(2024, 6, 5, 23, tzinfo=timezone.utc)
        before_publication = datetime(2024, 7, 14, tzinfo=timezone.utc)
        on_publication = datetime(2024, 7, 15, tzinfo=timezone.utc)
        self.assertFalse(self._has(store, phenomenon_day, final.iri))
        self.assertFalse(self._has(store, before_publication, final.iri))
        self.assertTrue(self._has(store, on_publication, final.iri))

        same_day = sample_grid(
            iri=mint("observation", "chirps-same-day"),
            product_kind="chirps-final",
            phenomenon=final.phenomenon,
            availability_time=start,
            generated_at=start,
        )
        refused = store.add_observation(same_day, at=NOW)
        self.assertFalse(refused.ok)
        self.assertEqual(refused.refusal.rule_id, "R-lookahead")

        issue = datetime(2024, 6, 1, tzinfo=timezone.utc)
        valid = datetime(2024, 6, 3, tzinfo=timezone.utc)
        valid_end = datetime(2024, 6, 3, 1, tzinfo=timezone.utc)
        forecast = sample_grid(
            iri=mint("observation", "forecast-step"),
            is_forecast=True,
            issue_time=issue,
            lead_seconds=int((valid - issue).total_seconds()),
            phenomenon=final.phenomenon.__class__(valid, valid_end),
            availability_time=issue,
            generated_at=issue,
            product_kind="forecast",
            procedure=mint("procedure", "forecast"),
        )
        self.assertTrue(store.add_observation(forecast, at=NOW).ok)
        self.assertFalse(
            self._has(store, datetime(2024, 5, 31, tzinfo=timezone.utc), forecast.iri)
        )
        self.assertTrue(
            self._has(store, datetime(2024, 6, 2, tzinfo=timezone.utc), forecast.iri)
        )
        collapsed = sample_grid(
            iri=mint("observation", "forecast-no-issue-gap"),
            is_forecast=True,
            issue_time=valid,
            lead_seconds=0,
            phenomenon=final.phenomenon.__class__(valid, valid_end),
            availability_time=valid,
            generated_at=valid,
            product_kind="forecast",
        )
        collapsed_result = store.add_observation(collapsed, at=NOW)
        self.assertFalse(collapsed_result.ok)
        self.assertEqual(collapsed_result.refusal.rule_id, "R-issue")

    def test_class_c_cannot_be_set_by_data(self):
        os.environ["FD_CLASS_C_POLICY"] = "open"
        try:
            self.assertEqual(class_c_policy(), "closed")
            with self.assertRaises(TypeError):
                Store(class_c_policy="open")
            store = Store()
            self.assertEqual(store.accepted_gates, [])
            payload = store.ingest_payload(
                {"classCPolicy": "open", "useClass": "Settlement", "iri": "payload-1"},
                at=NOW,
            )
            self.assertFalse(payload.ok)
            self.assertEqual(payload.refusal.rule_id, "R-classC")
            hedge = store.add_annotation("hedge", at=NOW)
            trigger = store.add_annotation("trigger", at=NOW)
            nature = store.add_annotation("nature-unit", at=NOW)
            self.assertEqual(hedge.refusal.rule_id, "R-instrument")
            self.assertEqual(trigger.refusal.rule_id, "R-instrument")
            self.assertEqual(nature.refusal.rule_id, "R-nature")
            gate = store.promote(
                "missing",
                to_class="Settlement",
                reviewer="synthetic-reviewer",
                checklist={str(i): "pass" for i in range(1, 12)},
                region="synthetic",
                crop="maize",
                at=NOW,
            )
            self.assertFalse(gate.ok)
            self.assertEqual(gate.refusal.rule_id, "R-classC")
            self.assertEqual(store.accepted_gates, [])
            rows = [row for row in facts_at(store, NOW) if not row["is_measurement"]]
            rules = {row["rule_id"] for row in rows}
            self.assertIn("R-classC", rules)
            self.assertTrue(all(row["record_type"] == "refusal" for row in rows))
            policy = Path(__file__).resolve().parents[1] / "farm_ontology" / "policy.py"
            text = policy.read_text(encoding="utf-8")
            self.assertNotIn("os.environ", text)
            self.assertNotIn("getenv", text)
            self.assertIn('CLASS_C_POLICY = "closed"', text)
        finally:
            os.environ.pop("FD_CLASS_C_POLICY", None)

    def _has(self, store, moment, iri) -> bool:
        return any(row["iri"] == iri and row["is_measurement"] for row in facts_at(store, moment))


if __name__ == "__main__":
    unittest.main()
