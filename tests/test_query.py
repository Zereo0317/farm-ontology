import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.build import mint, tonnes
from farm_ontology.model import Interval, Observation
from farm_ontology.query import EXAMPLE_QUERIES, PUBLIC_TERMS, facts_at
from farm_ontology.store import Store
from tests.support import NOW, sample_grid


class QueryTests(unittest.TestCase):
    def test_revision_does_not_delete_or_look_ahead(self):
        store = Store()
        start = datetime(2024, 3, 1, tzinfo=timezone.utc)
        end = datetime(2024, 3, 2, tzinfo=timezone.utc)
        first_time = datetime(2024, 4, 1, tzinfo=timezone.utc)
        second_time = datetime(2024, 6, 1, tzinfo=timezone.utc)
        first = self._admin("yearbook-1", 10.0, first_time, start, end, None)
        second = self._admin("yearbook-2", 8.0, second_time, start, end, first.iri)
        self.assertTrue(store.add_observation(first, at=NOW).ok)
        self.assertTrue(store.add_observation(second, at=NOW).ok)
        april = self._values(store, datetime(2024, 5, 1, tzinfo=timezone.utc))
        july = self._values(store, datetime(2024, 7, 1, tzinfo=timezone.utc))
        self.assertEqual(april, {first.iri: 10.0})
        self.assertEqual(july, {second.iri: 8.0})
        self.assertIn(first.iri, store.observations)
        deleted = store.delete(first.iri, at=NOW)
        self.assertFalse(deleted.ok)
        self.assertEqual(deleted.refusal.rule_id, "R-parallel")
        self.assertIn(first.iri, store.observations)

    def test_reanalysis_is_not_an_operations_observation(self):
        store = Store()
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 8, tzinfo=timezone.utc)
        available = datetime(2024, 4, 1, tzinfo=timezone.utc)
        era = sample_grid(
            iri=mint("observation", "era5"),
            product_kind="reanalysis",
            phenomenon=Interval(start, end),
            availability_time=available,
            generated_at=available,
            procedure=mint("procedure", "reanalysis"),
        )
        self.assertTrue(store.add_observation(era, at=NOW).ok)
        during = datetime(2024, 1, 3, tzinfo=timezone.utc)
        self.assertFalse(
            any(row["iri"] == era.iri for row in facts_at(store, during) if row["is_measurement"])
        )
        labelled = sample_grid(
            iri=mint("observation", "era5-ops"),
            product_kind="reanalysis",
            phenomenon=Interval(start, end),
            availability_time=available,
            generated_at=available,
            procedure=mint("procedure", "reanalysis"),
            operations_observation=True,
        )
        refused = store.add_observation(labelled, at=NOW)
        self.assertFalse(refused.ok)
        self.assertEqual(refused.refusal.rule_id, "R-reanalysis")
        same_day = sample_grid(
            iri=mint("observation", "era5-same-day"),
            product_kind="reanalysis",
            phenomenon=Interval(start, end),
            availability_time=start,
            generated_at=start,
            procedure=mint("procedure", "reanalysis"),
        )
        same = store.add_observation(same_day, at=NOW)
        self.assertFalse(same.ok)
        self.assertEqual(same.refusal.rule_id, "R-reanalysis")

    def test_unknown_availability_is_not_a_backtest_fact(self):
        store = Store()
        hidden = sample_grid(
            iri=mint("observation", "unknown-availability"),
            availability_known=False,
            availability_time=None,
        )
        self.assertTrue(store.add_observation(hidden, at=NOW).ok)
        self.assertFalse(
            any(row["iri"] == hidden.iri and row["is_measurement"] for row in facts_at(store, NOW))
        )

    def test_public_terms_do_not_name_bfo(self):
        blob = " ".join(PUBLIC_TERMS + EXAMPLE_QUERIES).lower()
        self.assertNotIn("bfo", blob)
        source = (Path(__file__).resolve().parents[1] / "farm_ontology" / "query.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("bfo", source.lower())

    def _admin(self, local, value, available, start, end, revision):
        base = sample_grid()
        return Observation(
            **{
                **base.__dict__,
                "iri": mint("observation", local),
                "feature_of_interest": mint("admin", "synthetic-district"),
                "feature_kind": "admin-unit",
                "spatial_support": "admin-unit",
                "native_resolution": None,
                "result": tonnes(value),
                "procedure": mint("procedure", "administrative-estimate"),
                "product_kind": "administrative-estimate",
                "phenomenon": Interval(start, end),
                "availability_time": available,
                "generated_at": available,
                "revision_of": revision,
            }
        )

    def _values(self, store, moment):
        return {
            row["iri"]: row["result_value"]
            for row in facts_at(store, moment)
            if row["is_measurement"]
        }


if __name__ == "__main__":
    unittest.main()
