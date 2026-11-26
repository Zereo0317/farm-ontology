"""Producer tests for the REAL-market backtest harness (audit gap G4).

Hermetic by default: no network anywhere. The always-on tests drive a
tiny synthetic, EXPLICITLY LABELLED stand-in frame (source
``test-stand-in``) whose expected numbers are hand-derived in the tests
themselves. The recorded-fixture test is opt-in via ``FARM_REAL_FIXTURES=1``
and additionally requires ``tests/fixtures/real/zs_daily_2021_2025.json``
to exist — the redistribution/licence question is documented in
``tests/fixtures/real/README.md``; without the file the test SKIPS.
"""

from __future__ import annotations

import inspect
import json
import os
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

from farm_ontology.markets import backtest as bt
from farm_ontology.markets import real_backtest as rb

T_EARLY = datetime(2026, 1, 1, tzinfo=timezone.utc)
T_LATE = datetime(2026, 6, 1, tzinfo=timezone.utc)
T_MID = datetime(2026, 3, 1, tzinfo=timezone.utc)
T_POST_ALL = datetime(2026, 12, 1, tzinfo=timezone.utc)

# The hand-computed universe (writes its own expectations, no fixtures):
# season 2021 window rows, closes in USD/bu (scale 1.0).
STAND_IN_ROWS_2021 = (
    (date(2021, 10, 5), 10.00),   # declared harvest day: L1 fires here
    (date(2021, 10, 6), 9.00),    # below breakout, before WASDE
    (date(2021, 12, 11), 12.00),  # >= 11.40 AND post-WASDE: L2 wins the row, L3 waits
    (date(2021, 12, 13), 11.00),  # post-WASDE: L3 fires
    (date(2022, 1, 31), 9.50),    # window end
)
# season 2025: the declared harvest day (Sunday 2025-10-05) has NO recorded
# session -> the harness must insert a calendar-carry row at 9.80.
STAND_IN_ROWS_2025_RAW = (
    (date(2025, 10, 3), 9.80),
    (date(2025, 11, 20), 11.75),  # first window close >= 11.40 -> L2
    (date(2025, 12, 11), 11.00),  # first close strictly after Dec 10 -> L3
    (date(2026, 1, 31), 10.60),   # window end
)

USD_FRAME_KWARGS = dict(
    symbol="ZS=F",
    interval="1d",
    source=rb.ROW_SOURCE_STAND_IN,
    citation_url="test://stand-in-real-shaped-frame",
    unit_note=rb.YAHOO_UNIT_NOTE_USD,
    captured_by="test-stand-in",
)

BU_3 = 3000.0 / bt.BU_KG  # 110.22927... bushels per hectare at 3.0 t/ha


def stand_in_frame() -> rb.RealPriceFrame:
    raw_rows = []
    for day, close in STAND_IN_ROWS_2021 + STAND_IN_ROWS_2025_RAW:
        raw_rows.append(
            rb.RealPriceRow(
                session_date=day,
                close=close,
                source=rb.ROW_SOURCE_STAND_IN,
                symbol="ZS=F",
                interval="1d",
                captured_at=T_EARLY,
                unit_note=rb.YAHOO_UNIT_NOTE_USD,
                note="stand-in real-shaped frame; synthetic values, not market truth",
            )
        )
    base = rb.RealPriceFrame(**USD_FRAME_KWARGS, captured_at=T_EARLY)
    # the 2025 declared harvest day (Sunday) has no row -> the harness's
    # own carry machinery must mark and fill it; 2021 keeps its session.
    rows = rb.with_carry_rows(base, tuple(raw_rows), years=("2021", "2025"))
    rows = tuple(sorted(rows, key=lambda row: row.session_date))
    return rb.replace(base, rows=rows)


def losing_frame() -> rb.RealPriceFrame:
    """A three-row season the staged rule LOSES (L3 sells into a crash)."""
    rows = tuple(
        rb.RealPriceRow(
            session_date=day,
            close=close,
            source=rb.ROW_SOURCE_STAND_IN,
            symbol="ZS=F",
            interval="1d",
            captured_at=T_EARLY,
            unit_note=rb.YAHOO_UNIT_NOTE_USD,
            note="stand-in real-shaped frame; synthetic values, not market truth",
        )
        for day, close in (
            (date(2021, 10, 5), 10.00),
            (date(2021, 12, 11), 12.00),
            (date(2021, 12, 13), 7.00),
        )
    )
    return rb.RealPriceFrame(**USD_FRAME_KWARGS, captured_at=T_EARLY, rows=rows)


class ProvenanceValidationTest(unittest.TestCase):
    """(a) anonymous / mislabelled rows are refused, loudly."""

    def test_valid_stand_in_frame_passes(self) -> None:
        rows = rb.validate_real_frame(stand_in_frame())
        # 9 raw rows + 1 harness-derived calendar-carry (2025-10-05)
        self.assertEqual(len(rows), 10)
        self.assertEqual(sum(1 for r in rows if r.source == rb.ROW_SOURCE_CARRY), 1)

    def test_blank_row_source_is_anonymous(self) -> None:
        frame = stand_in_frame()
        bad = rb.RealPriceRow(
            session_date=date(2021, 10, 7),
            close=9.1,
            source="",
            symbol="ZS=F",
            interval="1d",
            captured_at=T_EARLY,
            unit_note=rb.YAHOO_UNIT_NOTE_USD,
        )
        with self.assertRaisesRegex(rb.ProvenanceError, "anonymous row"):
            rb.validate_real_frame(rb.replace(frame, rows=(*frame.rows, bad)))

    def test_uncleared_row_source_is_refused(self) -> None:
        frame = stand_in_frame()
        bad = rb.replace(
            frame.rows[0],
            session_date=date(2021, 10, 7),
            source="some-screen-scrape",
        )
        with self.assertRaisesRegex(rb.ProvenanceError, "anonymous row"):
            rb.validate_real_frame(rb.replace(frame, rows=(*frame.rows, bad)))

    def test_row_unit_note_must_match_frame(self) -> None:
        frame = stand_in_frame()
        bad = rb.replace(frame.rows[0], unit_note="cents? whatever")
        with self.assertRaisesRegex(rb.ProvenanceError, "disagrees with the frame unit_note"):
            rb.validate_real_frame(rb.replace(frame, rows=(bad,) + frame.rows[1:]))

    def test_row_capture_must_be_timezone_aware(self) -> None:
        frame = stand_in_frame()
        bad = rb.replace(frame.rows[0], captured_at=datetime(2026, 1, 1))
        with self.assertRaisesRegex(rb.ProvenanceError, "timezone-aware"):
            rb.validate_real_frame(rb.replace(frame, rows=(bad,) + frame.rows[1:]))

    def test_row_capture_after_frame_capture_refused(self) -> None:
        frame = stand_in_frame()
        bad = rb.replace(frame.rows[0], captured_at=T_POST_ALL)
        with self.assertRaisesRegex(rb.ProvenanceError, "later than its frame"):
            rb.validate_real_frame(rb.replace(frame, rows=(bad,) + frame.rows[1:]))

    def test_unknown_unit_scale_is_refused_not_guessed(self) -> None:
        frame = rb.replace(stand_in_frame(), unit_note="jdmeshi per tan")
        with self.assertRaisesRegex(rb.ProvenanceError, "USD_PER_BU_SCALE"):
            rb.validate_real_frame(frame)

    def test_frame_without_citation_refused(self) -> None:
        frame = rb.replace(stand_in_frame(), citation_url="")
        with self.assertRaisesRegex(rb.ProvenanceError, "citation_url"):
            rb.validate_real_frame(frame)

    def test_empty_frame_refused(self) -> None:
        with self.assertRaisesRegex(rb.ProvenanceError, "empty"):
            rb.validate_real_frame(rb.replace(stand_in_frame(), rows=()))

    def test_nonpositive_close_refused(self) -> None:
        for value in (0.0, -1.0, float("nan"), float("inf")):
            with self.subTest(value=value):
                frame = stand_in_frame()
                bad = rb.replace(frame.rows[0], close=value)
                with self.assertRaisesRegex(rb.ProvenanceError, "finite and positive"):
                    rb.validate_real_frame(rb.replace(frame, rows=(bad,) + frame.rows[1:]))

    def test_duplicate_session_dates_refused(self) -> None:
        frame = stand_in_frame()
        twin = rb.replace(frame.rows[1], close=9.05)
        with self.assertRaisesRegex(rb.ProvenanceError, "duplicate session date"):
            rb.validate_real_frame(rb.replace(frame, rows=frame.rows + (twin,)))

    def test_carry_row_must_repeat_last_session_close(self) -> None:
        frame = stand_in_frame()
        # 2021-10-07 sits after the Oct-6 session (close 9.00); a carry
        # there valuing 10.75 invents a price the record does not carry.
        forged_carry = rb.RealPriceRow(
            session_date=date(2021, 10, 7),
            close=10.75,
            source=rb.ROW_SOURCE_CARRY,
            symbol="ZS=F",
            interval="1d",
            captured_at=T_EARLY,
            unit_note=rb.YAHOO_UNIT_NOTE_USD,
            note="forged carry",
        )
        with self.assertRaisesRegex(rb.ProvenanceError, "repeat the last"):
            rb.validate_real_frame(rb.replace(frame, rows=(forged_carry,) + frame.rows))

    def _carry(self, day: date, close: float) -> rb.RealPriceRow:
        return rb.RealPriceRow(
            session_date=day,
            close=close,
            source=rb.ROW_SOURCE_CARRY,
            symbol="ZS=F",
            interval="1d",
            captured_at=T_EARLY,
            unit_note=rb.YAHOO_UNIT_NOTE_USD,
            note="synthetic carry under test",
        )

    def test_two_carry_rows_in_one_season_refused(self) -> None:
        frame = stand_in_frame()
        # both carries sit after Dec 13 (close 11.00, the last non-carry
        # session before either date) — the VALUES are honest; two derived
        # rows in one season is what the validator refuses.
        carry_24 = self._carry(date(2021, 12, 24), 11.00)
        carry_25 = self._carry(date(2021, 12, 25), 11.00)
        rows = (*frame.rows[:3], carry_24, carry_25, *frame.rows[3:])
        with self.assertRaisesRegex(rb.ProvenanceError, "more than one carry row"):
            rb.validate_real_frame(rb.replace(frame, rows=rows))

    def test_engine_refuses_frame_validation_failure(self) -> None:
        frame = rb.replace(stand_in_frame(), citation_url="")
        with self.assertRaises(rb.ProvenanceError):
            rb.run_season("2021", frame, yield_t_per_ha=3.0)


class StandInHandComputedTest(unittest.TestCase):
    """(b) the full harness on the stand-in frame matches hand computation.

    Hand derivation (closes in USD/bu, weights 40/30/30, bu/ha =
    3000/27.216):

    season 2021 — L1@10.00 (harvest close), L2@12.00 (first close >= 11.40,
    beats the post-WASDE condition on the same row), L3@11.00 (first close
    strictly after Dec 10); staged wavg = 0.4*10 + 0.3*12 + 0.3*11 = 10.90;
    baseline = 10.00; delta = 0.90 $/bu x BU_3.

    season 2025 — harvest day 2025-10-05 is a Sunday: the harness must
    carry 9.80 from the Friday session into an honestly-marked carry row;
    L1@9.80 (carry), L2@11.75, L3@11.00; staged wavg = 10.745; baseline =
    9.80; delta = 0.945 $/bu x BU_3.

    Aggregates: baseline mean 9.90 x BU_3, staged mean 10.8225 x BU_3,
    delta mean 0.9225 x BU_3, hit 2W/0L.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.frame = stand_in_frame()
        cls.report = rb.run_real_backtest((cls.frame,), years=("2021", "2025"), yield_t_per_ha=3.0)
        cls.by_season = {o.season: o for o in cls.report.seasons}

    def test_2021_legs_fire_where_hand_computed(self) -> None:
        outcome = self.by_season["2021"]
        legs = [(e.leg, round(e.price, 9), e.trigger) for e in outcome.executions]
        self.assertEqual(
            legs,
            [
                (1, 10.00, "harvest_close"),
                (2, 12.00, "breakout_11.40"),
                (3, 11.00, "post_december_wasde"),
            ],
        )
        self.assertEqual(outcome.session_count, 5)

    def test_2021_delta_matches_hand_computation(self) -> None:
        expected_delta = (0.4 * 10.0 + 0.3 * 12.0 + 0.3 * 11.0 - 10.0) * BU_3
        outcome = self.by_season["2021"]
        self.assertAlmostEqual(outcome.delta_per_ha, expected_delta, places=6)
        self.assertAlmostEqual(outcome.baseline_revenue_per_ha, 10.0 * BU_3, places=6)
        self.assertAlmostEqual(outcome.staged_revenue_per_ha, 10.90 * BU_3, places=6)

    def test_2025_harvest_day_is_a_marked_calendar_carry(self) -> None:
        outcome = self.by_season["2025"]
        carry_legs = [e for e in outcome.executions if "calendar-carry" in e.note]
        self.assertEqual(len(carry_legs), 1)
        self.assertEqual(carry_legs[0].leg, 1)
        self.assertAlmostEqual(carry_legs[0].price, 9.80, places=9)
        self.assertEqual(carry_legs[0].day, date(2025, 10, 5))
        self.assertEqual(self.report.carry_dates, (date(2025, 10, 5),))

    def test_2025_legs_and_delta_match_hand_computation(self) -> None:
        outcome = self.by_season["2025"]
        legs = [(e.leg, round(e.price, 9), e.trigger) for e in outcome.executions]
        self.assertEqual(
            legs,
            [
                (1, 9.80, "harvest_close"),
                (2, 11.75, "breakout_11.40"),
                (3, 11.00, "post_december_wasde"),
            ],
        )
        expected_delta = (0.4 * 9.8 + 0.3 * 11.75 + 0.3 * 11.0 - 9.8) * BU_3
        self.assertAlmostEqual(outcome.delta_per_ha, expected_delta, places=6)

    def test_aggregate_matches_hand_computation(self) -> None:
        expected_baseline_mean = (10.0 + 9.8) / 2.0 * BU_3
        expected_staged_mean = (10.90 + 10.745) / 2.0 * BU_3
        expected_delta_mean = (0.90 + 0.945) / 2.0 * BU_3
        self.assertAlmostEqual(self.report.result.baseline_revenue_per_ha, expected_baseline_mean, places=6)
        self.assertAlmostEqual(self.report.result.staged_revenue_per_ha, expected_staged_mean, places=6)
        self.assertAlmostEqual(self.report.mean_delta_per_ha, expected_delta_mean, places=6)
        self.assertEqual((self.report.result.seasons_won, self.report.result.seasons_lost), (2, 0))

    def test_window_drawdown_hand_computed_on_printed_closes(self) -> None:
        # 2021: peak 12.00 -> trough 9.50 => 2.50 ; 2025: peak 11.75 -> trough 10.60 => 1.15
        self.assertAlmostEqual(self.by_season["2021"].window_max_drawdown, 2.50, places=9)
        self.assertAlmostEqual(self.by_season["2025"].window_max_drawdown, 1.15, places=9)

    def test_stand_in_label_travels_on_every_row(self) -> None:
        # the always-on test load must never masquerade as market truth:
        # stand-in rows carry the label; the one harness-derived carry row
        # carries the calendar-carry derivation in its note.
        for row in rb.validate_real_frame(self.frame):
            if row.source == rb.ROW_SOURCE_CARRY:
                self.assertIn("calendar-carry", row.note)
            else:
                self.assertEqual(row.source, rb.ROW_SOURCE_STAND_IN)
                self.assertIn("not market truth", row.note)
        self.assertEqual(self.frame.captured_by, "test-stand-in")


class PitDisciplineTest(unittest.TestCase):
    """(c) a row captured after decision time cannot inform that decision."""

    @classmethod
    def setUpClass(cls) -> None:
        # The leak scenario: an early row that WOULD fire L2 if its capture
        # instant were respected, and the SAME row captured LATER than the
        # decision. Informing the decision from the late capture is a leak.
        early_rows = []
        for day, close in STAND_IN_ROWS_2021:
            row = rb.RealPriceRow(
                session_date=day,
                close=close,
                source=rb.ROW_SOURCE_STAND_IN,
                symbol="ZS=F",
                interval="1d",
                captured_at=T_EARLY,
                unit_note=rb.YAHOO_UNIT_NOTE_USD,
                note="stand-in real-shaped frame; synthetic values, not market truth",
            )
            early_rows.append(row)
        # 2021-10-06 @ 12.50 captured LATE: at decision time T_MID only the
        # T_EARLY rows exist; the 12.50 close is unknowable then.
        late_row = rb.RealPriceRow(
            session_date=date(2021, 10, 6),
            close=12.50,
            source=rb.ROW_SOURCE_STAND_IN,
            symbol="ZS=F",
            interval="1d",
            captured_at=T_LATE,
            unit_note=rb.YAHOO_UNIT_NOTE_USD,
            note="late-captured close (unknowable at the decision instant)",
        )
        # frame = Oct 5 early + Oct 6 LATE + the rest early, captured_at T_LATE
        cls.leaky_frame = rb.RealPriceFrame(
            **USD_FRAME_KWARGS,
            captured_at=T_LATE,
            rows=tuple([early_rows[0], late_row, *early_rows[2:]]),
        )
        cls.early_only_frame = rb.RealPriceFrame(
            **USD_FRAME_KWARGS,
            captured_at=T_EARLY,
            rows=tuple(early_rows),
        )

    def test_uncut_frame_is_refused_at_decision_time(self) -> None:
        with self.assertRaisesRegex(rb.LeakError, "cut the frame with known_at"):
            rb.validate_decision_cut(self.leaky_frame, T_MID)

    def test_engine_structurally_refuses_leaky_input(self) -> None:
        # run_season must NOT silently trim: it fails closed.
        with self.assertRaises(rb.LeakError):
            rb.run_season("2021", self.leaky_frame, yield_t_per_ha=3.0, decision_time=T_MID)

    def test_known_at_returns_only_rows_captured_on_time(self) -> None:
        cut = rb.known_at(self.leaky_frame, T_MID)
        self.assertEqual(cut.dates, (date(2021, 10, 5), date(2021, 12, 11), date(2021, 12, 13), date(2022, 1, 31)))

    def test_cut_decision_equals_contemporaneous_knowledge(self) -> None:
        # The cut run (knowing only T_EARLY rows) must equal the run over a
        # frame that NEVER HELD the later row.
        cut = rb.known_at(self.leaky_frame, T_MID)
        contemporaneous = rb.RealPriceFrame(
            **USD_FRAME_KWARGS,
            captured_at=T_EARLY,
            rows=cut.rows,
        )
        from_cut = rb.run_season("2021", cut, yield_t_per_ha=3.0, decision_time=T_MID)
        from_clean = rb.run_season("2021", contemporaneous, yield_t_per_ha=3.0, decision_time=T_MID)
        self.assertEqual(from_cut, from_clean)

    def test_the_leak_would_have_mattered_materially(self) -> None:
        # Counterfactual: running the SAME decision ignoring captured_at
        # (i.e. as of T_LATE) fires L2 on the late 12.50 print. The cut
        # run fires L2 on 12.00 instead — the leak is material, which is
        # why validate_decision_cut refuses rather than trims.
        leaky_run = rb.run_season("2021", self.leaky_frame, yield_t_per_ha=3.0)  # default: as of T_LATE
        cut_run = rb.run_season(
            "2021",
            rb.known_at(self.leaky_frame, T_MID),
            yield_t_per_ha=3.0,
            decision_time=T_MID,
        )
        leaky_l2 = [e for e in leaky_run.executions if e.leg == 2][0]
        cut_l2 = [e for e in cut_run.executions if e.leg == 2][0]
        self.assertAlmostEqual(leaky_l2.price, 12.50, places=9)   # the leak
        self.assertAlmostEqual(cut_l2.price, 12.00, places=9)     # knowable truth
        self.assertNotEqual(leaky_run.staged_revenue_per_ha, cut_run.staged_revenue_per_ha)

    def test_naive_decision_time_refused(self) -> None:
        with self.assertRaises(ValueError):
            rb.known_at(self.leaky_frame, datetime(2026, 3, 1))
        with self.assertRaises(ValueError):
            rb.validate_decision_cut(self.leaky_frame, datetime(2026, 3, 1))

    def test_capture_later_than_decision_is_documented_semantics(self) -> None:
        # the module docstring/state: captured rows are never backdated;
        # availability is bounded below by the capture instant, exactly the
        # pit_dataset conservatism.
        self.assertIn("pit_dataset", (rb.__doc__ or ""))
        self.assertIn("fact_time", (rb.__doc__ or ""))


class RealFixtureGateTest(unittest.TestCase):
    """The opt-in gate mirrors FARM_ONLINE_TESTS semantics."""

    def test_gate_off_by_default(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(rb.REAL_FIXTURE_ENV, None)
            self.assertFalse(rb.real_fixture_gate_open())

    def test_gate_parses_truthy_values(self) -> None:
        for value in ("1", "true", "YES", "on"):
            with mock.patch.dict(os.environ, {rb.REAL_FIXTURE_ENV: value}):
                self.assertTrue(rb.real_fixture_gate_open())
        for value in ("", "0", "no", "off"):
            with mock.patch.dict(os.environ, {rb.REAL_FIXTURE_ENV: value}):
                self.assertFalse(rb.real_fixture_gate_open())

    def test_fixture_path_is_the_versioned_store(self) -> None:
        self.assertEqual(
            rb.real_fixture_path().relative_to(Path(__file__).resolve().parents[1]),
            rb.FIXTURE_RELATIVE_PATH,
        )

    def test_licensing_readme_documents_the_question(self) -> None:
        readme = rb.real_fixture_path().parent / "README.md"
        self.assertTrue(readme.exists(), "the licensing memo must live with the fixtures")
        text = readme.read_text(encoding="utf-8").lower()
        self.assertIn("licence", text)
        self.assertIn("farm_real_fixtures", text)
        self.assertIn("commercial", text)

    def test_fixture_path_names_the_committed_controlled_asset(self) -> None:
        self.assertEqual(
            rb.FIXTURE_RELATIVE_PATH.as_posix(),
            "tests/fixtures/real/zs_daily_captured_2026-11-20.json",
        )

    def test_missing_fixture_load_error_is_actionable(self) -> None:
        if rb.real_fixture_exists():
            self.skipTest("fixture present; the absent-fixture error path is moot")
        with self.assertRaisesRegex(FileNotFoundError, "tests/fixtures/real"):
            rb.load_default_fixture_frame()


@unittest.skipUnless(
    rb.real_fixture_exists() and rb.real_fixture_gate_open(),
    "recorded fixture not redistributable yet; opt in with "
    f"{rb.REAL_FIXTURE_ENV}=1 after placing {rb.FIXTURE_RELATIVE_PATH.as_posix()}",
)
class RealFixtureBacktestTest(unittest.TestCase):
    """(d) full pipeline over the RECORDED series — opt-in only."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.frame = rb.load_default_fixture_frame()
        cls.report = rb.run_real_backtest((cls.frame,), yield_t_per_ha=3.0)

    def test_fixture_validates_completely(self) -> None:
        rows = rb.validate_real_frame(self.frame)
        self.assertGreater(len(rows), 1000)
        # internal consistency: every non-carry row is counted as a candle
        self.assertEqual(
            self.report.candle_count + len(self.report.carry_dates),
            len(rows),
        )

    def test_five_seasons_with_honest_carry(self) -> None:
        self.assertEqual(len(self.report.seasons), 5)
        for outcome in self.report.seasons:
            # Oct 5 -> Jan 31 is ~118 calendar days: 62-86 weekday sessions
            # depending on holidays; 50/90 is the loose sanity band.
            self.assertGreaterEqual(outcome.session_count, 50)
            self.assertLessEqual(outcome.session_count, 90)
            for execution in outcome.executions:
                self.assertGreater(execution.price, 0)
        # the declared harvest weekends the exchange had no session for:
        # exactly these, marked and price-repeated by the loader
        self.assertEqual(
            self.report.carry_dates,
            (date(2024, 10, 5), date(2025, 10, 5)),
        )

    def test_cent_scale_conversion_exactly_once(self) -> None:
        # under the documented Yahoo capture (cents), the 2021 L1 fill must
        # be the printed 1250.50 cents expressed as $12.505/bu
        if self.frame.unit_note != rb.YAHOO_UNIT_NOTE_CENTS:
            self.skipTest("fixture is not the cents-scale Yahoo capture")
        outcome_2021 = next(o for o in self.report.seasons if o.season == "2021")
        l1 = outcome_2021.executions[0]
        self.assertAlmostEqual(l1.price, 12.505, places=6)
        self.assertAlmostEqual(l1.price * 100, 1250.5, places=6)

    def test_run_is_deterministic(self) -> None:
        again = rb.run_real_backtest((rb.load_default_fixture_frame(),), yield_t_per_ha=3.0)
        self.assertEqual(again.result, self.report.result)

    def test_percent_edge_is_in_a_honest_band(self) -> None:
        # decision-support sanity, not a fit: the staged-vs-baseline edge
        # on five recorded seasons must be a small percentage
        pct = self.report.delta_pct_vs_baseline
        self.assertGreater(abs(pct), 0.0)
        self.assertLess(abs(pct), 5.0)


class ReportRenderingTest(unittest.TestCase):
    def test_render_contains_honest_artefact_markers(self) -> None:
        report = rb.run_real_backtest((stand_in_frame(),), years=("2021",), yield_t_per_ha=3.0)
        text = rb.render_report(report)
        self.assertIn("NOT ADVICE", text)
        self.assertIn("per hectare", text)
        self.assertIn("point-in-time", text.lower())
        self.assertIn("GRANT WALL", text.upper())
        self.assertIn("LICENSING (CONTROLLED ASSET)".upper(), text.upper())
        self.assertIn("| 2021 |", text)

    def test_negative_delta_renders_as_minus_dollars(self) -> None:
        report = rb.run_real_backtest((losing_frame(),), years=("2021",), yield_t_per_ha=3.0)
        self.assertLess(report.mean_delta_per_ha, 0)
        text = rb.render_report(report)
        self.assertIn("-$", text)

    def test_write_report_persists_numbers_only(self) -> None:
        report = rb.run_real_backtest((stand_in_frame(),), years=("2021",), yield_t_per_ha=3.0)
        with tempfile.TemporaryDirectory() as tmp:
            path = rb.write_report(report, Path(tmp) / "sub" / "report.md")
            text = path.read_text(encoding="utf-8")
            self.assertIn("Headline", text)
            # no raw series dumping: row-level closes must not be inlined
            self.assertNotIn("[[", text)


class PriorStudyConstantTest(unittest.TestCase):
    """The comparison constants must stay internally coherent."""

    def test_per_season_mean_matches_documented_mean(self) -> None:
        prior = rb.PRIOR_ADHOC_STUDY
        mean = sum(prior["per_season_delta"]) / len(prior["per_season_delta"])
        self.assertAlmostEqual(mean, prior["mean_delta_per_ha"], places=6)

    def test_years_match_defaults(self) -> None:
        self.assertEqual(rb.PRIOR_ADHOC_STUDY["years"], rb.DEFAULT_YEARS)

    def test_documented_numbers_survive_intact(self) -> None:
        prior = rb.PRIOR_ADHOC_STUDY
        self.assertEqual(prior["report"], "reports/backtest-t3-real-REPORT.md")
        self.assertEqual((prior["seasons_won"], prior["seasons_lost"]), (3, 2))


class ClockHygieneTest(unittest.TestCase):
    def test_comparison_section_renders_when_years_match(self) -> None:
        report = rb.run_real_backtest(
            (rb.load_recorded_frame(
                self._stand_in_cache_path(), years=rb.DEFAULT_YEARS
            ),),
            years=rb.DEFAULT_YEARS,
            yield_t_per_ha=3.0,
        )
        text = rb.render_report(report)
        self.assertIn("Comparison with the ad-hoc", text)
        self.assertIn("TRIGGER EVALUATION", text)
        # the cents equivalence is COMPUTED, never '>= 11 printed cents'
        self.assertNotIn("≥ 11 printed cents", text)
        self.assertIn("≥ 1140 printed cents", text)

    @staticmethod
    def _stand_in_cache_path() -> str:
        import json
        import tempfile

        payload = [[row.session_date.isoformat(), row.close] for row in stand_in_frame().rows]
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(payload, handle)
        handle.close()
        return handle.name

    def test_engine_reads_no_wall_clock(self) -> None:
        for function in (rb.run_season, rb.run_real_backtest, rb.render_report):
            source = inspect.getsource(function)
            self.assertNotIn("now(", source)
            self.assertNotIn("today(", source)
        # (audit-defect D5 hardening) the ban extends to the WHOLE module:
        # no time.time()/utcnow call may creep into real_backtest.py —
        # every instant in the engine must come from declared captured_at
        # / decision_time values, never the wall clock.
        module_source = inspect.getsource(rb)
        self.assertNotIn("time.time(", module_source)
        self.assertNotIn("utcnow(", module_source)


class SeasonWindowCoverageTest(unittest.TestCase):
    """(audit defect D1) a window the frame does not carry to window_end
    must be REFUSED, not silently run with exhausted legs priced at the
    record's abrupt stop. Boundary: pending legs are legal exactly when
    the frame's own extent demonstrates the window ran to its end."""

    @staticmethod
    def _mid_window_2025_frame() -> rb.RealPriceFrame:
        # 2025 season window: harvest 2025-10-05, window_end 2026-01-31.
        # The capture simply STOPS at 2025-11-01 — no breakout level is
        # crossed (all closes < 11.40) and the WASDE day never arrives,
        # so L2/L3 would both "exhaust" at a stop that is not the end.
        rows = tuple(
            rb.RealPriceRow(
                session_date=day,
                close=close,
                source=rb.ROW_SOURCE_STAND_IN,
                symbol="ZS=F",
                interval="1d",
                captured_at=T_EARLY,
                unit_note=rb.YAHOO_UNIT_NOTE_USD,
                note="stand-in real-shaped frame; synthetic values, not market truth",
            )
            for day, close in (
                (date(2025, 10, 5), 10.00),
                (date(2025, 10, 20), 10.10),
                (date(2025, 11, 1), 9.90),
            )
        )
        return rb.RealPriceFrame(**USD_FRAME_KWARGS, captured_at=T_EARLY, rows=rows)

    def test_frame_ending_mid_window_refused_for_2025(self) -> None:
        with self.assertRaisesRegex(
            ValueError, r"season 2025.*short of the declared window_end"
        ):
            rb.run_season("2025", self._mid_window_2025_frame(), yield_t_per_ha=3.0)

    def test_pending_legs_with_full_window_extent_exhaust_honestly(self) -> None:
        # coverage-law boundary: with the frame's last session ON the
        # declared window_end, an unfired leg MAY still be priced at the
        # final close (the record demonstrates the window really ended).
        rows = tuple(
            rb.RealPriceRow(
                session_date=day,
                close=close,
                source=rb.ROW_SOURCE_STAND_IN,
                symbol="ZS=F",
                interval="1d",
                captured_at=T_EARLY,
                unit_note=rb.YAHOO_UNIT_NOTE_USD,
                note="stand-in real-shaped frame; synthetic values, not market truth",
            )
            for day, close in (
                (date(2021, 10, 5), 10.00),
                (date(2022, 1, 31), 9.50),
            )
        )
        frame = rb.RealPriceFrame(**USD_FRAME_KWARGS, captured_at=T_EARLY, rows=rows)
        outcome = rb.run_season("2021", frame, yield_t_per_ha=3.0)
        triggers = [execution.trigger for execution in outcome.executions]
        self.assertIn("breakout_11.40_window_exhausted", triggers)


class BreakoutLabelDerivationTest(unittest.TestCase):
    """(audit defect D3) trigger and rule labels compose from
    ``bt.BREAKOUT_LEVEL`` exactly as ``backtest.run_season`` composes
    them — a moved level moves every label, never a stale hard-coded
    11.40."""

    def test_leg_log_and_rule_name_follow_the_patched_level(self) -> None:
        with mock.patch.object(bt, "BREAKOUT_LEVEL", 12.0):
            frame = stand_in_frame()
            outcome_2021 = rb.run_season("2021", frame, yield_t_per_ha=3.0)
            outcome_2025 = rb.run_season("2025", frame, yield_t_per_ha=3.0)
            report = rb.run_real_backtest(
                (frame,), years=("2021", "2025"), yield_t_per_ha=3.0
            )
        # 2021: the 12.00 close still crosses the raised level — and the
        # fired leg's label must say 12.00, not the stale 11.40.
        triggers_2021 = [execution.trigger for execution in outcome_2021.executions]
        self.assertIn("breakout_12.00", triggers_2021)
        self.assertNotIn("breakout_11.40", triggers_2021)
        # 2025: no stand-in close reaches 12.0, so L2 exhausts — and the
        # exhausted leg's label must follow the patched level too.
        triggers_2025 = [execution.trigger for execution in outcome_2025.executions]
        self.assertIn("breakout_12.00_window_exhausted", triggers_2025)
        self.assertNotIn("breakout_11.40_window_exhausted", triggers_2025)
        # the RESULT's rule label is composed, not hard-coded:
        self.assertIn("12.00 breakout", report.result.rule_name)
        self.assertNotIn("11.40", report.result.rule_name)


class CapturedAtConflictTest(unittest.TestCase):
    """(audit defect D4) ONE captured_at semantic, documented in the
    loader's docstring: an explicit caller instant and the store's
    ``meta.captured_at`` must AGREE — disagreement REFUSES instead of
    silently overriding the caller."""

    @staticmethod
    def _meta_store_path() -> str:
        payload = {
            "meta": {
                "source": rb.ROW_SOURCE_STAND_IN,
                "symbol": "ZS=F",
                "interval": "1d",
                "citation_url": "test://stand-in-meta-store",
                "unit_note": rb.YAHOO_UNIT_NOTE_USD,
                "captured_at": "2026-05-05T00:00:00+00:00",
            },
            "rows": [["2025-10-03", 1018.0]],
        }
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(payload, handle)
        handle.close()
        return handle.name

    def test_meta_captured_at_conflicting_with_caller_refused(self) -> None:
        caller_instant = datetime(2026, 11, 20, tzinfo=timezone.utc)
        with self.assertRaisesRegex(ValueError, "conflicting captured_at sources"):
            rb.load_recorded_frame(
                self._meta_store_path(), captured_at=caller_instant, years=()
            )

    def test_equal_meta_and_caller_captured_at_agree(self) -> None:
        same = datetime(2026, 5, 5, tzinfo=timezone.utc)
        frame = rb.load_recorded_frame(self._meta_store_path(), captured_at=same, years=())
        self.assertEqual(frame.captured_at, same)

    def test_absent_caller_value_falls_back_to_meta_then_declared_default(self) -> None:
        adopted = rb.load_recorded_frame(self._meta_store_path(), years=())
        self.assertEqual(adopted.captured_at, datetime(2026, 5, 5, tzinfo=timezone.utc))


class UnknownYearErrorTest(unittest.TestCase):
    """(audit defect D5) an unknown season year fails FRIENDLY at the
    run_real_backtest level — a named ValueError with the available
    seasons, never a bare KeyError out of the window selector."""

    def test_unknown_season_year_raises_friendly_value_error(self) -> None:
        with self.assertRaisesRegex(
            ValueError, r"no season calendar for '1999'.*available seasons"
        ):
            rb.run_real_backtest(
                (stand_in_frame(),), years=("1999",), yield_t_per_ha=3.0
            )


if __name__ == "__main__":
    unittest.main()
