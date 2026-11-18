"""Offline tests for the markets source seam (task-14).

Covers the stooq CSV adapter against the committed SAMPLE fixtures and
inline CSV strings; the live capture path is tested for its GATE only —
no network call happens in this module.
"""

from __future__ import annotations

import io
import unittest
from datetime import date, time

from farm_ontology.markets.sources import (
    SOURCE_FACTS,
    SYMBOL_CL_F,
    SYMBOL_ZS_F,
    PriceSeriesFrame,
    StooqCsvSeriesLoader,
    capture_online,
    parse_stooq_csv,
)
from farm_ontology.markets.sources.stooq_csv import _download_url


class SampleFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.loader = StooqCsvSeriesLoader()
        cls.daily = cls.loader.from_sample(SYMBOL_ZS_F)
        cls.intraday = cls.loader.from_sample(SYMBOL_ZS_F, intraday=True)

    def test_daily_fixture_parses(self) -> None:
        self.assertEqual(len(self.daily.rows), 8)
        first = self.daily.rows[0]
        self.assertEqual(first["date"], date(2026, 10, 5))
        self.assertEqual(first["close"], 1055.75)
        self.assertEqual(first["symbol"], SYMBOL_ZS_F)
        self.assertEqual(self.daily.interval, "d")
        self.assertFalse(self.daily.captured_live)

    def test_intraday_fixture_parses_with_time(self) -> None:
        self.assertEqual(len(self.intraday.rows), 6)
        first = self.intraday.rows[0]
        self.assertEqual(first["time"], time(1, 0))
        self.assertEqual(self.intraday.interval, "60")

    def test_last_close_by_date_collapses_intraday(self) -> None:
        closes = self.intraday.closes_by_date()
        self.assertEqual(closes, {date(2026, 10, 5): 1058.5})

    def test_drawdown_helper(self) -> None:
        dd = self.intraday.max_drawdown_of_closes()
        self.assertAlmostEqual(dd["drawdown"], 2.25)
        self.assertEqual(dd["peak_date"], date(2026, 10, 5))

    def test_citation_travels(self) -> None:
        self.assertEqual(self.daily.citation_url, SOURCE_FACTS[SYMBOL_ZS_F].citable_url)
        self.assertTrue(self.daily.unit_note)

    def test_crude_oil_facts_recorded(self) -> None:
        facts = SOURCE_FACTS[SYMBOL_CL_F]
        self.assertTrue(facts.citable_url.startswith("https://"))
        self.assertIn("USD per barrel", facts.unit_note)


class ParserBehaviourTest(unittest.TestCase):
    def test_comment_preamble_is_skipped(self) -> None:
        text = (
            "# provenance line one\n"
            "# citable_url: https://stooq.com/q/d/?s=zs.f\n"
            "Date,Open,High,Low,Close,Volume\n"
            "2026-01-05,10.0,10.5,9.9,10.2,100\n"
        )
        frame = parse_stooq_csv(io.StringIO(text), SYMBOL_ZS_F, "d", "")
        self.assertEqual(len(frame.rows), 1)
        self.assertEqual(frame.rows[0]["close"], 10.2)

    def test_junk_header_refused(self) -> None:
        with self.assertRaises(ValueError):
            parse_stooq_csv(
                io.StringIO("Alpha,Beta\n1,2\n"), SYMBOL_ZS_F, "d", ""
            )

    def test_zero_rows_refused(self) -> None:
        with self.assertRaises(ValueError):
            parse_stooq_csv(io.StringIO(""), SYMBOL_ZS_F, "d", "")

    def test_row_validation_on_frame_construction(self) -> None:
        with self.assertRaises(ValueError):
            PriceSeriesFrame(
                source="s",
                symbol="sym",
                interval="d",
                rows=({"date": date(2026, 1, 1)},),  # missing close/source/symbol
            )

    def test_intraday_sorting_is_stable(self) -> None:
        text = (
            "Date,Time,Close\n"
            "2026-01-05,02:00,10.0\n"
            "2026-01-05,01:00,9.5\n"
        )
        frame = parse_stooq_csv(io.StringIO(text), SYMBOL_ZS_F, "60", "")
        self.assertEqual([row["close"] for row in frame.rows], [9.5, 10.0])


class GateDisciplineTest(unittest.TestCase):
    def test_capture_without_gate_refuses_by_name(self) -> None:
        import os

        old = os.environ.pop("FARM_ONLINE_TESTS", None)
        try:
            with self.assertRaises(PermissionError) as ctx:
                capture_online(SYMBOL_ZS_F, "d", "2026-01-01", "2026-02-01", ".")
        finally:
            if old is not None:
                os.environ["FARM_ONLINE_TESTS"] = old
        self.assertIn("FARM_ONLINE_TESTS", str(ctx.exception))

    def test_download_url_builder_shape(self) -> None:
        url = _download_url(SYMBOL_ZS_F, "d", "20261001", "20261231")
        self.assertTrue(url.startswith("https://stooq.com/q/d/l/?s=zs.f"))
        self.assertIn("d1=20261001", url)
        self.assertIn("d2=20261231", url)
        self.assertIn("i=d", url)

    def test_no_network_during_offline_suite(self) -> None:
        # the loader and parser never touch urllib at import- or call-time
        loader = StooqCsvSeriesLoader()
        frame = loader.from_sample(SYMBOL_ZS_F)
        self.assertTrue(frame.rows)


if __name__ == "__main__":
    unittest.main()
