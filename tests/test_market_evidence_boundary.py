from dataclasses import replace
from datetime import datetime
import unittest
from farm_ontology.markets import rails as rl
from tests.test_markets_rails import artefact, AS_OF, CONTRIB, SUBJECT_AMS_BID

class MarketEvidenceBoundaryTest(unittest.TestCase):
    def _r5(self, value):
        return rl.rail_5_truthfulness_gate(value, AS_OF)

    def test_omitting_every_source_does_not_bypass_truth_gate(self):
        a = artefact(market_decisive_feeds=(), contributions=(), grants_by_feed={})
        self.assertTrue(any('no market-decisive' in v.detail for v in self._r5(a)))

    def test_undeclared_contribution_and_duplicate_feed_are_rejected(self):
        other = replace(CONTRIB[0], feed='other-feed')
        a = artefact(contributions=(CONTRIB[0], other))
        self.assertTrue(any('without a declared' in v.detail for v in self._r5(a)))
        a = artefact(contributions=(CONTRIB[0], CONTRIB[0]))
        self.assertTrue(any('duplicate contributions' in v.detail for v in self._r5(a)))

    def test_missing_and_naive_availability_times_fail_closed(self):
        for timestamp in (None, datetime(2026, 11, 17)):
            a = artefact(contributions=(replace(CONTRIB[0], contribution_time=timestamp),))
            self.assertTrue(any('availability time' in v.detail for v in self._r5(a)))

    def test_self_asserted_farmer_consent_is_not_trusted(self):
        consent = rl.ConsentGrant('farmer', 'hedge', 'crop data', '2099-01-01T00:00:00+00:00', 'https://example.com/evidence')
        a = artefact(carries_farmer_level_data=True, consent=consent)
        self.assertTrue(any('trusted consent registry' in v.detail for v in rl.rail_4_consent_first_upward_flow(a, AS_OF)))
