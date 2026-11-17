"""Grant certificates v2: loading, fingerprints, fail-closed evaluation."""

import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.licences.grants import (  # noqa: E402
    DEFAULT_GRANTS_DIR,
    KNOWN_FEEDS,
    Grant,
    build_state,
    evaluate,
    evaluate_grants,
    load_grants,
)

NOW = datetime(2026, 11, 17, tzinfo=timezone.utc)
VALID_SPECIMEN = dict(
    grant_id="specimen-1",
    issuer="Test Issuer",
    grantee_seat="seat@example.test",
    feeds=["planet.psscene"],
    uses=["screening"],
    territory="*",
    purpose="shape only",
    expiry_utc="2026-12-17T14:59:59+00:00",
    evidence_url="https://example.test/grant",
)


def _grant(**overrides) -> Grant:
    payload = {**VALID_SPECIMEN, **overrides}
    return Grant.from_payload(payload)


class LoadingTests(unittest.TestCase):
    def test_repo_grants_load_as_three_specimens(self):
        grants = load_grants(DEFAULT_GRANTS_DIR)
        self.assertEqual(len(grants), 3)
        self.assertEqual(
            [grant.grant_id for grant in grants],
            [
                "ee-commercial-specimen",
                "open-meteo-q9-specimen",
                "planet-trial-specimen",
            ],
        )
        for grant in grants:
            self.assertTrue(grant.specimen, grant.grant_id)
            self.assertIsNotNone(grant.specimen_note)

    def test_state_dot_json_is_skipped_by_the_loader(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "one.json").write_text(
                json.dumps(VALID_SPECIMEN), encoding="utf-8"
            )
            (tmp / "state.json").write_text('{"schema": "noise"}', encoding="utf-8")
            grants = load_grants(tmp)
            self.assertEqual([grant.grant_id for grant in grants], ["specimen-1"])
        finally:
            shutil.rmtree(tmp)

    def test_missing_required_field_and_unknown_field_die_loudly(self):
        broken = {k: v for k, v in VALID_SPECIMEN.items() if k != "issuer"}
        with self.assertRaises(ValueError):
            Grant.from_payload(broken)
        noisy = {**VALID_SPECIMEN, "spectmen": True}
        with self.assertRaises(ValueError):
            Grant.from_payload(noisy)

    def test_naive_or_bad_expiry_never_constructs(self):
        with self.assertRaises(ValueError):
            _grant(expiry_utc="2026-12-17T14:59:59")  # no offset
        with self.assertRaises(ValueError):
            _grant(expiry_utc="not-a-time")

    def test_unknown_feed_rejected_at_construction(self):
        with self.assertRaises(ValueError):
            _grant(feeds=["vendor.nonexistent"])

    def test_duplicate_grant_ids_across_files_are_a_loading_bug(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            for name in ("a.json", "b.json"):
                (tmp / name).write_text(
                    json.dumps(VALID_SPECIMEN), encoding="utf-8"
                )
            with self.assertRaises(ValueError):
                load_grants(tmp)
        finally:
            shutil.rmtree(tmp)


class FingerprintTests(unittest.TestCase):
    def test_fingerprint_is_stable_sha256_of_canonical_json(self):
        first = _grant()
        again = Grant.from_payload(dict(reversed(list(first.to_payload().items()))))
        self.assertEqual(first.fingerprint, again.fingerprint)
        self.assertEqual(len(first.fingerprint), 64)
        self.assertTrue(all(char in "0123456789abcdef" for char in first.fingerprint))

    def test_one_changed_byte_changes_the_fingerprint(self):
        tweaked = _grant(purpose="a genuinely different purpose")
        self.assertNotEqual(_grant().fingerprint, tweaked.fingerprint)

    def test_json_round_trip_preserves_the_certificate(self):
        grant = _grant(permits_redistribution=True)
        restored = Grant.from_payload(json.loads(json.dumps(grant.to_payload())))
        self.assertEqual(restored, grant)
        self.assertEqual(restored.fingerprint, grant.fingerprint)


class EvaluationTests(unittest.TestCase):
    def test_every_repo_grant_is_a_specimen_refusal_for_its_own_feeds(self):
        grants = load_grants(DEFAULT_GRANTS_DIR)
        for grant in grants:
            for feed in grant.feeds:
                allowed, winner, reason = evaluate_grants(
                    grants, feed, grant.uses[0], NOW
                )
                self.assertFalse(allowed)
                self.assertEqual(reason, "specimen")
                self.assertIsNotNone(winner)

    def test_unknown_feed_and_unknown_use_fail_closed_before_anything_else(self):
        allowed, winner, reason = evaluate_grants([], "vendor.x", "screening", NOW)
        self.assertEqual((allowed, winner, reason), (False, None, "unknown_feed"))
        allowed, _, reason = evaluate_grants([], KNOWN_FEEDS[0], "gambling", NOW)
        self.assertEqual((allowed, winner, reason), (False, None, "unknown_use"))

    def test_no_grant_and_use_not_granted(self):
        allowed, winner, reason = evaluate_grants([], KNOWN_FEEDS[0], "screening", NOW)
        self.assertEqual((allowed, winner, reason), (False, None, "no_grant"))
        allowed, _, reason = evaluate_grants(
            [_grant()], KNOWN_FEEDS[0], "settlement", NOW
        )
        self.assertEqual((allowed, winner, reason), (False, None, "use_not_granted"))

    def test_valid_grant_wins_and_picks_the_earliest_expiry(self):
        soon = _grant(
            grant_id="soon",
            uses=["settlement"],
            expiry_utc="2026-11-20T00:00:00+00:00",
        )
        late = _grant(
            grant_id="late",
            uses=["settlement"],
            expiry_utc="2027-01-01T00:00:00+00:00",
            specimen=False,
        )
        allowed, winner, reason = evaluate_grants(
            [late, soon], KNOWN_FEEDS[0], "settlement", NOW
        )
        self.assertTrue(allowed)
        self.assertEqual((winner.grant_id, reason), ("soon", "ok"))

    def test_expired_beats_specimen_when_a_real_candidate_exists(self):
        expired = _grant(
            grant_id="dead",
            uses=["screening"],
            expiry_utc="2026-01-01T00:00:00+00:00",
        )
        allowed, winner, reason = evaluate_grants(
            [expired], KNOWN_FEEDS[0], "screening", NOW
        )
        self.assertFalse(allowed)
        self.assertEqual((winner.grant_id, reason), ("dead", "expired"))

    def test_expiry_boundary_is_inclusive_and_timezone_normalised(self):
        grant = _grant(uses=["screening"])
        at_expiry_tokyo = datetime.fromisoformat("2026-12-17T23:59:59+09:00")
        allowed, _, reason = evaluate_grants([grant], KNOWN_FEEDS[0], "screening", at_expiry_tokyo)
        self.assertEqual((allowed, reason), (True, "ok"))
        one_second_later = datetime.fromisoformat("2026-12-18T08:00:00+09:00")
        allowed, _, reason = evaluate_grants([grant], KNOWN_FEEDS[0], "screening", one_second_later)
        self.assertEqual((allowed, reason), (False, "expired"))

    def test_evaluation_is_deterministic_and_does_not_mutate_inputs(self):
        grants = [_grant(), _grant(grant_id="specimen-2", expiry_utc="2027-01-01T00:00:00+00:00")]
        snapshot = [grant.to_payload() for grant in grants]
        runs = {evaluate_grants(grants, KNOWN_FEEDS[0], "screening", NOW) for _ in range(3)}
        self.assertEqual(len(runs), 1)
        self.assertEqual([grant.to_payload() for grant in grants], snapshot)

    def test_module_level_evaluate_reads_the_repo_dir(self):
        allowed, _, reason = evaluate("planet.psscene", "settlement", NOW)
        self.assertEqual((allowed, reason), (False, "specimen"))

    def test_naive_at_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_grants([], KNOWN_FEEDS[0], "screening", datetime(2026, 11, 17))


class StateTests(unittest.TestCase):
    def test_build_state_marks_every_feed_screening_under_specimens(self):
        state = build_state(load_grants(DEFAULT_GRANTS_DIR), NOW)
        self.assertEqual(state["schema"], "farm-ontology.grants.state/1")
        self.assertTrue(state["fail_closed"])
        self.assertEqual(set(state["feeds"]), set(KNOWN_FEEDS))
        # feeds with a specimen shelf report 'specimen'; feeds with nothing
        # at all report 'no_grant'. Everything stays Screening/false.
        expected_reason = {
            "planet.psscene": "specimen",
            "planet.planetary-variable.soil-water-content": "specimen",
            "earth-engine.export": "specimen",
            "open-meteo.jma-msm": "specimen",
            "jma.hazard": "no_grant",
            "usdm.hazard": "no_grant",
            # WS7 market-lane feeds: registered 2026-11-18, no specimen yet,
            # so they read no_grant until real certificates land.
            "usda.wasde": "no_grant",
            "ams.soybean-bid": "no_grant",
            "fao.food-price-index": "no_grant",
            "imf.pcps": "no_grant",
            "worldbank.pink-sheet": "no_grant",
        }
        for feed, row in state["feeds"].items():
            self.assertEqual(row["use_class"], "Screening", feed)
            self.assertFalse(row["permits_financial_use"], feed)
            self.assertEqual(row["reason"], expected_reason[feed], feed)
        for entry in state["grants"]:
            self.assertIn("fingerprint", entry)

    def test_a_valid_grant_flips_only_its_own_feed(self):
        live = _grant(
            grant_id="real-one",
            specimen=False,
            uses=["settlement", "screening"],
            expiry_utc="2027-06-30T00:00:00+00:00",
        )
        state = build_state([live], NOW)
        self.assertTrue(state["feeds"]["planet.psscene"]["permits_financial_use"])
        self.assertEqual(state["feeds"]["planet.psscene"]["reason"], "ok")
        flipped = {
            feed
            for feed, row in state["feeds"].items()
            if row["permits_financial_use"]
        }
        self.assertEqual(flipped, {"planet.psscene"})


if __name__ == "__main__":
    unittest.main()
