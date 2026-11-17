"""Fertility skeleton tests (WS3.4): the engine refuses without soil
chemistry, and humbly hands dosing to the agronomist."""

import unittest
from datetime import datetime, timedelta, timezone

from farm_ontology.agronomy.common import AgronomyGap
from farm_ontology.agronomy.fertility import (
    REQUIRED_SOIL_ANALYTES,
    SOURCE_NOTE,
    soil_fertility_note,
)
from tests.agronomy_fixtures import soil_rows

AT = datetime(2026, 11, 18, 4, 0, tzinfo=timezone.utc)


class RefusalTests(unittest.TestCase):
    def test_no_rows_yields_enumerated_needs_soil_chemistry_gap(self):
        with self.assertRaises(AgronomyGap) as ctx:
            soil_fertility_note([], at=AT)
        gap = ctx.exception
        self.assertEqual(gap.gap, "needs-soil-chemistry")
        self.assertEqual(set(gap.missing), set(REQUIRED_SOIL_ANALYTES))
        self.assertTrue(gap.remediation)

    def test_partial_set_enumerates_exactly_the_missing_analytes(self):
        rows = soil_rows(full=False)  # fixture minus two analytes
        with self.assertRaises(AgronomyGap) as ctx:
            soil_fertility_note(rows, at=AT)
        self.assertEqual(ctx.exception.gap, "needs-soil-chemistry")
        self.assertEqual(set(ctx.exception.missing), {"k_available", "om_percent"})

    def test_unknown_analyte_refused_not_ignored(self):
        rows = soil_rows() + [
            {"analyte": "magic-index", "value": 1.0, "unit": "?",
             "sampled_at": "2026-10-20T02:00:00+00:00",
             "native_support": "soil-sample-grid-composite"}
        ]
        with self.assertRaises(AgronomyGap) as ctx:
            soil_fertility_note(rows, at=AT)
        self.assertEqual(ctx.exception.gap, "unknown-analyte")
        self.assertIn("magic-index", ctx.exception.args[0])

    def test_stale_chemistry_refused(self):
        rows = [
            {**row,
             "sampled_at": (datetime.now(timezone.utc) - timedelta(days=4 * 365))
             .strftime("%Y-%m-%dT%H:%M:%S+00:00")}
            for row in soil_rows()
        ]
        with self.assertRaises(AgronomyGap) as ctx:
            soil_fertility_note(rows, at=AT)
        self.assertEqual(ctx.exception.gap, "soil-chemistry-stale")

    def test_duplicate_analyte_refused(self):
        rows = soil_rows() + [soil_rows()[0]]
        with self.assertRaises(AgronomyGap) as ctx:
            soil_fertility_note(rows, at=AT)
        self.assertEqual(ctx.exception.gap, "duplicate-analyte")

    def test_mixed_native_supports_refused(self):
        rows = soil_rows()
        rows = [dict(row) for row in rows]
        rows[0] = {**rows[0], "native_support": "something-else"}
        with self.assertRaises(AgronomyGap) as ctx:
            soil_fertility_note(rows, at=AT)
        self.assertEqual(ctx.exception.gap, "support-mixed")

    def test_row_without_support_declaration_refused(self):
        rows = [dict(row) for row in soil_rows()]
        del rows[2]["native_support"]
        with self.assertRaises(AgronomyGap) as ctx:
            soil_fertility_note(rows, at=AT)
        self.assertEqual(ctx.exception.gap, "missing-native-support")


class HumbleOutputTests(unittest.TestCase):
    def test_complete_chemistry_yields_review_required_note_set(self):
        note = soil_fertility_note(soil_rows(), at=AT)
        self.assertTrue(note.review_required)
        self.assertTrue(any("REVIEW REQUIRED" in n for n in note.notes))
        self.assertTrue(any("agronomist signs every dose" in n for n in note.notes))
        # NO quantified dose anywhere in a v0 note set: a regex on
        # kg/ha-style prescriptions fails loudly if doses ever appear.
        import re

        for line in note.notes:
            self.assertIsNone(
                re.search(r"\d+(\.\d+)?\s*(kg|g)\s*/\s*ha", line, re.IGNORECASE),
                f"quantified dose leaked into a REVIEW-REQUIRED note: {line}",
            )

    def test_acidic_hokkaido_like_ph_is_flagged_not_prescribed(self):
        note = soil_fertility_note(soil_rows(), at=AT)
        flagged = [n for n in note.notes if "comfort band" in n]
        self.assertTrue(flagged)
        self.assertIn("no lime dose", flagged[0])

    def test_all_analytes_echoed_for_human_interpretation(self):
        note = soil_fertility_note(soil_rows(), at=AT)
        self.assertEqual(len(note.analytes), 6)
        echoed = [n for n in note.notes if "echo for human interpretation" in n]
        self.assertEqual(len(echoed), 4)  # N, P, K, OM
        self.assertIn("Hokkaido prefecture", " ".join(echoed))

    def test_values_trimmed_echo_carry_units_and_methods(self):
        note = soil_fertility_note(soil_rows(), at=AT)
        ph = next(v for v in note.values if v["analyte"] == "ph")
        self.assertAlmostEqual(ph["value"], 5.6)
        self.assertEqual(ph["method"], "1:2.5 water suspension")
        self.assertTrue(ph["native_support"])


class StampTests(unittest.TestCase):
    def test_support_carried_and_use_class_set(self):
        note = soil_fertility_note(soil_rows(), at=AT)
        self.assertEqual(note.support.base, "soil-sample-grid-composite")
        self.assertEqual(note.use_class, "field-ops")
        self.assertIn("VERIFY [SOIL-CHEM]", note.source_note)
        self.assertIn("VERIFY [SOIL-CHEM]", SOURCE_NOTE)

    def test_naive_at_refused(self):
        with self.assertRaises(ValueError):
            soil_fertility_note(soil_rows(), at=datetime(2026, 11, 18))


if __name__ == "__main__":
    unittest.main()
