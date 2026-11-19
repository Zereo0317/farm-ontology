"""Publication integrity under a SPECIMEN-only grants directory.

Two proofs live here:
1. the existing render_memo/check_publication pathways keep refusing
   financial-use claims while grants/ holds only SPECIMEN grants - a
   specimen (flag `specimen: true`) never unlocks any feed and evaluation
   answers reason 'specimen';
2. the WS6 contract stub (ContractStubTests below) is fail-closed: a
   buyer-facing consent set is permitted only when every referenced row
   carries a live, non-revoked consent. This is the composition shape the
   real contract wiring consumes; specimens cover nothing.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.support import NOW, sample_grid  # noqa: E402
from farm_ontology.publish import check_publication, render_fact, render_memo  # noqa: E402
from farm_ontology.licences.grants import (  # noqa: E402
    DEFAULT_GRANTS_DIR,
    load_grants,
    evaluate_grants,
)
from farm_ontology.licences.ledger import effective_permits_financial_use  # noqa: E402
from farm_ontology.store import Store  # noqa: E402


class MemoIntegrityUnderSpecimensTests(unittest.TestCase):
    def setUp(self):
        self.grants = load_grants(DEFAULT_GRANTS_DIR)  # SPECIMEN-only by repo rule
        self.store = Store()
        self.obs = sample_grid()  # already carries screening_licence/method
        result = self.store.add_observation(self.obs, at=NOW)
        self.assertTrue(result.ok)
        self.memo = render_memo(self.store, NOW)

    def test_all_repo_grants_are_specimens_except_the_operator_grant(self):
        self.assertGreaterEqual(len(self.grants), 4)
        specimens = [grant for grant in self.grants if grant.specimen]
        self.assertGreaterEqual(len(specimens), 3)
        self.assertTrue(any(not grant.specimen for grant in self.grants))

    def test_specimens_fail_evaluation_with_reason_specimen(self):
        # evaluated ALONE at a moment the specimens EXIST (after their own
        # issuance), a specimen still refuses its own feeds; the executed
        # operator grant is deliberately out of this shelf
        specimens = [grant for grant in self.grants if grant.specimen]
        eval_at = max(
            (grant.issued_dt for grant in specimens if grant.issued_dt),
            default=NOW,
        )
        for grant in specimens:
            for feed in grant.feeds:
                allowed, winner, reason = evaluate_grants(
                    [g for g in specimens], feed, grant.uses[0], eval_at
                )
                self.assertEqual(
                    (allowed, winner is not None, reason),
                    (False, True, "specimen"),
                    f"{feed} unlocked by {grant.grant_id}?!",
                )

    def test_rendered_fact_keeps_financial_use_false(self):
        fact = render_fact(self.obs)
        self.assertIn(f"licence: {self.obs.licence.instrument}", fact)
        self.assertIn("financial_use=False", fact)

    def test_memo_shows_the_screening_lock_while_specimens_exist(self):
        self.assertIn("use_class: Screening", self.memo)
        self.assertIn("financial_use=False", self.memo)
        for grant in self.grants:
            # no publication text may assert a feed was unlocked by a specimen
            self.assertNotIn(
                f"licence: {grant.grant_id}", self.memo
            )

    def test_check_publication_accepts_the_honest_memo(self):
        self.assertEqual(check_publication(self.memo), [])

    def test_check_publication_refuses_text_that_drops_required_markers(self):
        stripping = (
            "Everything is fine. The following observation was used for "
            "settlement pricing and hedge decisions on the derivatives book."
        )
        violations = check_publication(stripping)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_id, "R-strip")
        self.assertIn("use_class", violations[0].detail)

    def test_effective_financial_flag_stays_down_with_only_specimens(self):
        fin_state = {
            "feed_id": "planet.psscene",
            "permits_financial_use": True,  # even a lying recorded state...
        }
        self.assertFalse(
            effective_permits_financial_use(fin_state, self.grants, NOW)
        )
        honest = {"feed_id": "open-meteo.jma-msm", "permits_financial_use": False}
        self.assertFalse(
            effective_permits_financial_use(honest, self.grants, NOW)
        )


class ContractStubTests(unittest.TestCase):
    """Fail-closed consent stub for the WS6 contract wiring (draft shape)."""

    ROW_A = "GRANT-001"
    ROW_B = "SUPPLIER-X"

    @staticmethod
    def _contract(rows):
        return {"buyer": "operator", "rows": list(rows)}

    @staticmethod
    def _consent(row, *, ok=True, revoked=False):
        return {"row": row, "ok": ok, "revoked": revoked}

    def _stub(self, contracts, consents):
        covered = {
            row["row"] for row in consents if row["ok"] and not row["revoked"]
        }
        missing = [row for row in contracts["rows"] if row not in covered]
        return not missing, missing

    def test_every_referenced_row_must_hold_a_live_consent(self):
        self.assertEqual(
            self._stub(self._contract([self.ROW_A]), [self._consent(self.ROW_A)]),
            (True, []),
        )
        self.assertEqual(
            self._stub(
                self._contract([self.ROW_A, self.ROW_B]),
                [self._consent(self.ROW_A)],
            ),
            (False, [self.ROW_B]),
        )
        self.assertEqual(self._stub(self._contract([]), []), (True, []))

    def test_revoked_or_unsigned_consents_fail_closed(self):
        for kwargs in ({"revoked": True}, {"ok": False}):
            self.assertEqual(
                self._stub(
                    self._contract([self.ROW_A]),
                    [self._consent(self.ROW_A, **kwargs)],
                ),
                (False, [self.ROW_A]),
            )


if __name__ == "__main__":
    unittest.main()
