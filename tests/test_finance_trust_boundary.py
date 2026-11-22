from datetime import datetime, timezone
from dataclasses import replace
import unittest
from farm_ontology.licences.grants import Grant, load_grants, evaluate_grants
from farm_ontology.markets import rails, registry
from tests.test_markets_rails import artefact, grant, AS_OF, SUBJECT_AMS_BID, CONTRIB

class FinanceTrustBoundaryTests(unittest.TestCase):
    def test_non_boolean_grant_flags_are_not_coerced_to_authority(self):
        founder = next(g for g in load_grants() if g.grant_id == 'founder-operator-2026-11-19')
        for flag in ('specimen', 'permits_redistribution'):
            for bad in ('false', '', None, 0, 1):
                with self.subTest(flag=flag, value=bad), self.assertRaises(ValueError):
                    Grant.from_payload({**founder.to_payload(), flag: bad})

    def test_direct_truthfulness_gate_rejects_unverified_reference(self):
        a = artefact(contributions=(replace(CONTRIB[0], contribution_time=AS_OF),))
        self.assertEqual(rails.grant_state_at(a.grants_by_feed[SUBJECT_AMS_BID], AS_OF)[0], rails.GRANT_CLOSED)
        self.assertTrue(any("provider rights unverified" in v.detail
                            for v in rails.rail_5_truthfulness_gate(a, AS_OF)))

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
