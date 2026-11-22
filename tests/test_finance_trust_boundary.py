from datetime import datetime, timezone
import unittest
from farm_ontology.licences.grants import load_grants, evaluate_grants
from farm_ontology.markets import rails, registry
from tests.test_markets_rails import artefact, grant, AS_OF, SUBJECT_AMS_BID

class FinanceTrustBoundaryTests(unittest.TestCase):
    def test_founder_permission_does_not_authorize_vendor_finance(self):
        grants = load_grants()
        for feed in next(g for g in grants if g.grant_id == 'founder-operator-2026-11-19').feeds:
            allowed, _, reason = evaluate_grants(grants, feed, 'settlement', AS_OF.replace(day=20))
            self.assertFalse(allowed)
            self.assertEqual(reason, 'provider_rights_unverified')

    def test_no_registry_and_borrowed_fingerprint_both_refuse(self):
        self.assertTrue(rails.validate_playbook_artefact(artefact(), AS_OF))
        fingerprints = registry.RegisteredGrants.default().fingerprints()
        self.assertTrue(fingerprints)
        forged = grant(fingerprint=fingerprints[0], expiry='2099-01-01T00:00:00+00:00')
        a = artefact(grants_by_feed={SUBJECT_AMS_BID: forged}, grant_registry=registry.RegisteredGrants.default())
        self.assertTrue(any(v.rail == 'R5-provenance' for v in rails.validate_playbook_artefact(a, AS_OF)))

    def test_self_asserted_cap_sheet_cannot_unlock_large_budget(self):
        reg = registry.RegisteredCapSheets([('2026Q4', 'a' * 64, False)])
        a = artefact(state=rails.STATE_UNCERTAIN, families=(rails.F_COST_CAPPED_STRADDLE,),
                     premium_budget=rails.PremiumBudget(50.0, 99.0, '2026Q4', 'human', cap_sheet_hash='a'*64),
                     cap_sheet_registry=reg)
        self.assertTrue(any(v.rail == rails.RAIL_6_PREMIUM_CAP for v in rails.validate_playbook_artefact(a, AS_OF)))
