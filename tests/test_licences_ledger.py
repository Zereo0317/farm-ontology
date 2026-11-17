"""Unlock ledger: automatic demotion when a grant expires mid-timeline."""

import unittest
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.licences.grants import Grant, load_grants, DEFAULT_GRANTS_DIR  # noqa: E402
from farm_ontology.licences.ledger import (  # noqa: E402
    demoted_reason,
    effective_permits_financial_use,
    expiry_alarm_rows,
)

EXPIRY = "2026-12-17T14:59:59+00:00"  # 2026-12-17 23:59:59 JST


def _live_grant(**overrides) -> Grant:
    payload = dict(
        grant_id="ledger-live",
        issuer="Issuer",
        grantee_seat="seat",
        feeds=["planet.psscene"],
        uses=["settlement", "hedge"],
        territory="*",
        purpose="ledger test",
        expiry_utc=EXPIRY,
        evidence_url="https://example.test/live",
    )
    payload.update(overrides)
    return Grant.from_payload(payload)


# The timeline table: same feed, same grant, three instants straddling expiry.
TIMELINE = (
    (datetime(2026, 12, 1, tzinfo=timezone.utc), True),      # mid-grant
    (datetime.fromisoformat(EXPIRY), True),                  # expiry instant, inclusive
    (datetime(2026, 12, 17, 15, 0, 0, tzinfo=timezone.utc), False),  # one tick past
)
_FIN_STATE = {"feed_id": "planet.psscene", "permits_financial_use": True}
_REC_FALSE = {"feed_id": "planet.psscene", "permits_financial_use": False}


class MidTimelineDemotionTests(unittest.TestCase):
    def test_automatic_demotion_across_the_three_dates(self):
        grant = _live_grant()
        for at, expected in TIMELINE:
            self.assertEqual(
                effective_permits_financial_use(_FIN_STATE, [grant], at),
                expected,
                f"at {at.isoformat()} the ledger must return {expected}",
            )

    def test_demotion_leaves_no_trace_of_promotion_afterwards(self):
        grant = _live_grant()
        before = _FIN_STATE.copy()
        for at, expected in TIMELINE:
            self.assertEqual(effective_permits_financial_use(before, [grant], at), expected)
        # ...and the recorded state object was never mutated by evaluation
        self.assertEqual(_FIN_STATE, before)

    def test_the_ledger_never_promotes_a_feed_that_records_false(self):
        grant = _live_grant()
        for at, _ in TIMELINE:
            self.assertFalse(effective_permits_financial_use(_REC_FALSE, [grant], at))

    def test_specimen_grants_never_unlock_even_mid_timeline(self):
        specimens = load_grants(DEFAULT_GRANTS_DIR)
        for at, _ in TIMELINE:
            self.assertFalse(effective_permits_financial_use(_FIN_STATE, specimens, at))

    def test_one_tick_past_expiry_equals_zero_grants(self):
        grant = _live_grant()
        after = datetime(2026, 12, 17, 15, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(
            effective_permits_financial_use(_FIN_STATE, [grant], after),
            effective_permits_financial_use(_FIN_STATE, [], after),
        )
        self.assertFalse(effective_permits_financial_use(_FIN_STATE, [], after))

    def test_other_grants_do_not_bleed_across_feeds(self):
        alien = _live_grant(feeds=["open-meteo.jma-msm"])
        for at, _ in TIMELINE[:2]:
            self.assertFalse(effective_permits_financial_use(_FIN_STATE, [alien], at))


class EdgeAndNarrativeTests(unittest.TestCase):
    def test_missing_or_lying_feed_state_stays_demoted(self):
        grant = _live_grant()
        at = TIMELINE[0][0]
        self.assertFalse(effective_permits_financial_use({}, [grant], at))
        self.assertFalse(effective_permits_financial_use(None, [grant], at))
        self.assertFalse(
            effective_permits_financial_use({"permits_financial_use": True}, [grant], at)
        )
        self.assertFalse(
            effective_permits_financial_use(
                {"feed_id": "no-such-feed", "permits_financial_use": True}, [grant], at
            )
        )

    def test_non_financial_uses_do_not_unlock_the_financial_flag(self):
        screening_only = _live_grant(uses=["screening", "research"])
        self.assertFalse(
            effective_permits_financial_use(_FIN_STATE, [screening_only], TIMELINE[0][0])
        )

    def test_naive_at_raises_like_the_house_time_utility(self):
        with self.assertRaises(ValueError):
            effective_permits_financial_use(_FIN_STATE, [], datetime(2026, 12, 1))

    def test_demoted_reason_narrates_each_failure_family(self):
        grant = _live_grant()
        self.assertIsNone(demoted_reason(_FIN_STATE, [grant], TIMELINE[0][0]))
        self.assertEqual(demoted_reason(_REC_FALSE, [grant], TIMELINE[0][0]), "recorded_false")
        self.assertEqual(demoted_reason(_FIN_STATE, [], TIMELINE[0][0]), "no_grant")
        financial_specimen = Grant.from_payload(
            {**grant.__dict__, "grant_id": "spec-fin", "specimen": True}
        )
        self.assertEqual(
            demoted_reason(_FIN_STATE, [financial_specimen], TIMELINE[0][0]),
            "specimen",
        )
        self.assertEqual(demoted_reason(_FIN_STATE, [grant], TIMELINE[2][0]), "expired")
        self.assertEqual(
            demoted_reason({"permits_financial_use": True}, [grant], TIMELINE[0][0]),
            "no_feed_state",
        )
        self.assertEqual(
            demoted_reason({"feed_id": "ghost.feed", "permits_financial_use": True}, [grant], TIMELINE[0][0]),
            "unknown_feed",
        )

    def test_expiry_alarm_rows_skip_specimens_and_sort_by_expiry(self):
        rows = expiry_alarm_rows(
            [
                _live_grant(grant_id="z-second", expiry_utc="2027-01-01T00:00:00+00:00"),
                _live_grant(grant_id="a-first", expiry_utc="2026-11-20T00:00:00+00:00"),
                Grant.from_payload(
                    {**_live_grant().__dict__, "grant_id": "spec", "specimen": True}
                ),
            ],
            datetime(2026, 11, 17, tzinfo=timezone.utc),
        )
        self.assertEqual([row["grant_id"] for row in rows], ["a-first", "z-second"])
        self.assertEqual([row["expired"] for row in rows], [False, False])
        a_year_later = datetime(2027, 2, 1, tzinfo=timezone.utc)
        self.assertTrue(all(row["expired"] for row in expiry_alarm_rows(
            [_live_grant()], a_year_later
        )))

    def test_purity_demotion_function_returns_bool_alone(self):
        grant = _live_grant()
        result = effective_permits_financial_use(_FIN_STATE, [grant], TIMELINE[0][0])
        self.assertIsInstance(result, bool)


if __name__ == "__main__":
    unittest.main()
