"""Common vocabulary tests (WS3 base): gaps, support stamps, ids."""

import unittest
from datetime import datetime, timezone

from farm_ontology.agronomy.common import (
    CONFIG_VERSION,
    DRAFTED_BY,
    PERMITS_FINANCIAL_USE_V0,
    USE_CLASS_FIELD_OPS,
    AgronomyGap,
    AgronomyRefusal,
    Gap,
    SupportDeclaration,
    canonical_json,
    deterministic_id,
)

T0 = datetime(2026, 8, 10, 4, 0, tzinfo=timezone.utc)


class CanonicalJsonTests(unittest.TestCase):
    def test_sorted_keys_stable_across_insertion_order(self):
        self.assertEqual(
            canonical_json({"b": 1, "a": [2, {"z": 1, "y": 2}]}),
            canonical_json({"a": [2, {"y": 2, "z": 1}], "b": 1}),
        )
        self.assertEqual(canonical_json({"a": 1}), b'{"a":1}')

    def test_unicode_survives_unescaped_utf8(self):
        self.assertEqual(canonical_json({"k": "水田"}), '{"k":"水田"}'.encode("utf-8"))


class DeterministicIdTests(unittest.TestCase):
    def test_deterministic_across_processes_and_key_order(self):
        left = deterministic_id("rec", {"a": 1, "b": [1, 2]})
        right = deterministic_id("rec", {"b": [1, 2], "a": 1})
        self.assertEqual(left, right)
        self.assertTrue(left.startswith("rec:"))
        self.assertEqual(len(left) - 4, 32)

    def test_namespace_and_content_change_the_id(self):
        self.assertNotEqual(
            deterministic_id("rec", {"a": 1}), deterministic_id("other", {"a": 1})
        )
        self.assertNotEqual(
            deterministic_id("rec", {"a": 1}), deterministic_id("rec", {"a": 2})
        )


class GapVocabularyTests(unittest.TestCase):
    def test_gap_message_rendering_and_payload_round_trip(self):
        gap = AgronomyGap(
            "needs-soil-chemistry", "refusing",
            missing=("ph", "ec"), remediation="send samples",
        )
        self.assertIn("[gap:needs-soil-chemistry]", str(gap))
        self.assertIn("ph, ec", str(gap))
        record = gap.as_gap()
        self.assertIsInstance(record, Gap)
        payload = record.to_payload()
        self.assertEqual(
            payload,
            {"gap": "needs-soil-chemistry", "detail": "refusing",
             "missing": ["ph", "ec"], "remediation": "send samples"},
        )

    def test_refusal_message_rendering(self):
        refusal = AgronomyRefusal("refused-use", "no hedging", "route to WS7")
        self.assertIn("[refusal:refused-use]", str(refusal))
        self.assertIn("(remedy: route to WS7)", str(refusal))


class SupportDeclarationTests(unittest.TestCase):
    def test_render_climbing_the_ladder(self):
        grid_only = SupportDeclaration(base="grid-support (native 5 km)")
        self.assertEqual(grid_only.render(), "grid-support (native 5 km)")

        probed = SupportDeclaration(
            base="grid-support (native 5 km)",
            extras=("probe-support (instrument-point, probe footprint radius 2 m)",),
        )
        self.assertIn("grid-support", probed.render())
        self.assertIn("probe-support", probed.render())

    def test_areas_only_come_from_sensors_and_travels(self):
        sensor_stamped = SupportDeclaration(
            base="grid-support (native 5 km)",
            extras=("parcel-support (sensor-reported 0.4 ha coverage)",),
            areas=("parcel-support (0.4 ha, sensor-declared)",),
        )
        self.assertIn("0.4 ha", sensor_stamped.render())
        self.assertIn("sensor-declared", sensor_stamped.render())
        payload = sensor_stamped.to_payload()
        self.assertEqual(payload["use_class"], USE_CLASS_FIELD_OPS)

    def test_module_constants(self):
        self.assertEqual(PERMITS_FINANCIAL_USE_V0, False)
        self.assertEqual(DRAFTED_BY, "agronomy-engine")
        self.assertTrue(CONFIG_VERSION)
        self.assertEqual(USE_CLASS_FIELD_OPS, "field-ops")


if __name__ == "__main__":
    unittest.main()
