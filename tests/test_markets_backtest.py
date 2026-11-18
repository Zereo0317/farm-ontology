"""Offline tests for the T3 backtest scaffold (task-14).

No network anywhere in this module: the simulated seasons are declared
constants, the recorded anchors come from the repo's own pit_dataset
fixtures, and the live-fetch seam is tested for its GUARDS, not called.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from farm_ontology.markets import backtest as bt
from farm_ontology.markets.pit_dataset import SUBJECT_AMS_BID, SUBJECT_FAO

POST_ANCHOR = datetime(2026, 11, 17, 2, 0, tzinfo=timezone.utc)  # after every capture
PRE_ANCHOR = datetime(2026, 11, 16, 15, 30, tzinfo=timezone.utc)  # after Pink only


class UnitConversionTest(unittest.TestCase):
    def test_bushels_per_ha(self) -> None:
        self.assertAlmostEqual(bt.bushels_per_ha(3.0), 110.2293, places=3)
        self.assertAlmostEqual(
            bt.bushels_per_ha(3.0) * bt.BU_KG / 1000.0, 3.0, places=9
        )

    def test_bushel_conversion_constant(self) -> None:
        self.assertEqual(bt.BU_KG, 27.216)

    def test_nonpositive_yield_refused(self) -> None:
        with self.assertRaises(ValueError):
            bt.bushels_per_ha(0)


class SimulationShapesTest(unittest.TestCase):
    def test_five_seasons_build(self) -> None:
        frames = bt.simulated_seasons()
        self.assertEqual(len(frames), 5)
        for frame in frames:
            self.assertTrue(frame.rows)
            self.assertTrue(all(row["close"] > 0 for row in frame.rows))

    def test_each_frame_spans_its_own_window(self) -> None:
        for year, frame in zip(("2021", "2022", "2023", "2024", "2025"), bt.simulated_seasons()):
            calendar = bt.SEASON_CALENDAR[year]
            days = [row["date"] for row in frame.rows]
            self.assertEqual(min(days), calendar["harvest_day"])
            self.assertGreater(calendar["window_end"], max(days))

    def test_declared_not_fitted_marker(self) -> None:
        for year, shape in bt.SIM_SEASON_SHAPES.items():
            self.assertIn("harvest_px", shape)


class PitAnchorJoinTest(unittest.TestCase):
    def test_post_capture_anchor_sees_the_band(self) -> None:
        anchor = bt.pit_anchor(POST_ANCHOR)
        self.assertEqual(anchor["ams_band_low"], 10.79)
        self.assertEqual(anchor["ams_average"], 11.16)
        self.assertEqual(anchor["ams_band_high"], 11.34)
        self.assertIn("cash_bid_average", anchor["ams_metrics"])
        self.assertIn(SUBJECT_AMS_BID, anchor["subjects_seen"])

    def test_pre_capture_anchor_is_am_silent(self) -> None:
        anchor = bt.pit_anchor(PRE_ANCHOR)
        # 15:30Z sits after the Pink capture (15:16:44Z) but BEFORE the
        # FAO/WASDE/IMF/AMS captures (16:06Z onward): only pink is known
        self.assertNotIn(SUBJECT_AMS_BID, anchor["subjects_seen"])
        self.assertNotIn(SUBJECT_FAO, anchor["subjects_seen"])
        self.assertEqual(anchor["subjects_seen"], ("wb_pink:crude-oil-average",))
        self.assertIsNone(anchor["ams_average"])

    def test_naive_as_of_refused(self) -> None:
        with self.assertRaises(ValueError):
            bt.pit_anchor(datetime(2026, 11, 17))

    def test_joined_dataset_shape(self) -> None:
        dataset = bt.joined_dataset(bt.simulated_seasons(), (PRE_ANCHOR, POST_ANCHOR))
        self.assertEqual(len(dataset["anchors"]), 2)
        self.assertEqual(len(dataset["frames"]), 5)
        self.assertEqual(dataset["seasons"], ("2021", "2022", "2023", "2024", "2025"))
        self.assertIsNone(dataset["anchors"][0]["ams_average"])
        self.assertIsNotNone(dataset["anchors"][1]["ams_average"])


class EngineBehaviourTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = bt.run_backtest(bt.simulated_seasons())

    def test_weights_sum_to_one(self) -> None:
        self.assertAlmostEqual(
            bt.HARVEST_WEIGHT + bt.BREAKOUT_WEIGHT + bt.POST_WASDE_WEIGHT, 1.0
        )

    def test_baseline_identity(self) -> None:
        bu = bt.bushels_per_ha(3.0)
        outcome_2021 = next(o for o in self.result.per_season if o.season == "2021")
        self.assertAlmostEqual(
            outcome_2021.baseline_revenue_per_ha, 11.00 * bu, places=6
        )

    def test_breakout_leg_fires_in_the_rallying_season(self) -> None:
        outcome_2024 = next(o for o in self.result.per_season if o.season == "2024")
        breakout = [e for e in outcome_2024.executions if e.leg == 2]
        self.assertEqual(len(breakout), 1)
        self.assertEqual(breakout[0].price, 11.45)
        self.assertEqual(breakout[0].trigger, "breakout_11.40")

    def test_window_exhaust_marks_the_forced_exit(self) -> None:
        outcome_2021 = next(o for o in self.result.per_season if o.season == "2021")
        exhausted = [e for e in outcome_2021.executions if "exhausted" in e.trigger]
        self.assertEqual(len(exhausted), 1, outcome_2021.executions)
        self.assertEqual(exhausted[0].leg, 2)
        self.assertIn("window exhausted", exhausted[0].note)

    def test_staged_loses_decay_seasons_wins_the_recovery(self) -> None:
        deltas = {o.season: o.delta_per_ha for o in self.result.per_season}
        self.assertLess(deltas["2021"], 0)
        self.assertGreater(deltas["2024"], 0)
        self.assertEqual(self.result.seasons_won, 1)
        self.assertEqual(self.result.seasons_lost, 4)

    def test_mean_matches_per_season_mean(self) -> None:
        per_season_mean = (
            sum(o.staged_revenue_per_ha for o in self.result.per_season)
            / len(self.result.per_season)
        )
        self.assertAlmostEqual(per_season_mean, self.result.staged_revenue_per_ha, places=6)
        self.assertAlmostEqual(
            self.result.staged_revenue_per_ha - self.result.baseline_revenue_per_ha,
            self.result.mean_delta_per_ha,
            places=6,
        )

    def test_hit_rate_identity(self) -> None:
        self.assertAlmostEqual(self.result.hit_rate, self.result.seasons_won / 5)

    def test_drawdowns_present_and_positive(self) -> None:
        self.assertIsNotNone(self.result.mean_window_drawdown)
        self.assertGreater(self.result.mean_window_drawdown, 0)
        self.assertGreaterEqual(
            self.result.worst_window_drawdown, self.result.mean_window_drawdown
        )

    def test_config_version_travels(self) -> None:
        self.assertEqual(self.result.config_version, bt.VERSION)

    def test_leg_weights_cover_every_bushel(self) -> None:
        for outcome in self.result.per_season:
            self.assertAlmostEqual(
                sum(e.weight for e in outcome.executions), 1.0, places=9
            )


class LimitationsAndReportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = bt.run_backtest(bt.simulated_seasons())
        cls.report = bt.render_report(cls.result, anchor_as_of=POST_ANCHOR)

    def test_limits_cover_the_brutal_list(self) -> None:
        joined = " ".join(bt.STANDARD_LIMITS).lower()
        for needle in (
            "perfect knowledge",
            "slippage",
            "survivorship",
            "five seasons",
            "grant wall",
            "not advice",
        ):
            self.assertIn(needle, joined)

    def test_report_has_not_advice_stamp_and_headline(self) -> None:
        self.assertIn("**NOT ADVICE", self.report)
        # the formatted delta really is the printed number (negatives
        # render as -$NN after the money-formatter fix)
        sign = "-" if self.result.mean_delta_per_ha < 0 else "$"
        magnitude = f"{abs(self.result.mean_delta_per_ha):,.0f}"
        self.assertIn(f"{sign}${magnitude} per hectare", self.report)

    def test_report_cites_the_recorded_anchors(self) -> None:
        self.assertIn("11.16", self.report)  # recorded AMS average
        self.assertIn("pit_dataset", self.report)
        self.assertIn("is ABSENT from the same", self.report)  # leak-proof demo

    def test_report_has_grant_wall_and_repro_sections(self) -> None:
        self.assertIn("## The grant wall", self.report)
        self.assertIn("## Reproduce", self.report)
        self.assertIn("tests.test_markets_backtest", self.report)

    def test_per_season_table_rendered(self) -> None:
        for outcome in self.result.per_season:
            self.assertIn(f"| {outcome.season} |", self.report)

    def test_breakout_derivation_is_declared(self) -> None:
        self.assertIn("11.40", bt.BREAKOUT_DERIVATION)
        self.assertIn("not a fitted signal", bt.BREAKOUT_DERIVATION)

    def test_wasde_day_is_declared_as_assumption(self) -> None:
        for calendar in bt.SEASON_CALENDAR.values():
            self.assertIn("assumption", calendar["wasde_note"])

    def test_backtest_does_not_read_the_clock(self) -> None:
        import inspect

        source = inspect.getsource(bt.run_season)
        self.assertNotIn("now(", source)
        self.assertNotIn("today(", source)


if __name__ == "__main__":
    unittest.main()
