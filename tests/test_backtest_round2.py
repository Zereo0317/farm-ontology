# -*- coding: utf-8 -*-
"""Round-2 residual producer tests (correctly-structured rewrite).

(1) D-R2-1: a gappy multi-season frame must not have THIS season's
    unfired-leg coverage waived by its global tail.
(2) D-R2-2 covered by the module's own render tests.
"""

import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.markets import backtest as bt
from farm_ontology.markets import real_backtest as rb


def make_row(day: str, cents: float) -> rb.RealPriceRow:
    return rb.RealPriceRow(
        session_date=date.fromisoformat(day),
        close=cents,
        source="yahoo",
        symbol="ZS=F",
        interval="1d",
        captured_at=datetime(2026, 11, 20, tzinfo=timezone.utc),
        unit_note=rb.YAHOO_UNIT_NOTE_CENTS,
    )


class WindowScopedCoverage(unittest.TestCase):
    def test_gap_multi_season_frame_refuses_short_window_despite_global_tail(self):
        """A frame whose GLOBAL last row sits past this season's window_end
        must not waive THIS season's unfired-leg coverage (old code read
        rows[-1] globally and wrongly accepted)."""
        season = "2021"
        rows = []
        cursor = date.fromisoformat("2021-09-01")
        while cursor < date.fromisoformat("2021-11-20"):
            if cursor.weekday() < 5:
                rows.append(make_row(cursor.isoformat(), 1100.0))
            cursor += timedelta(days=1)
        late = date.fromisoformat("2025-12-01")
        while late < date.fromisoformat("2025-12-11"):
            if late.weekday() < 5:
                rows.append(make_row(late.isoformat(), 1200.0))
            late += timedelta(days=1)
        frame = rb.RealPriceFrame(
            symbol="ZS=F",
            source="yahoo",
            interval="1d",
            citation_url="test://gap-frame",
            unit_note=rb.YAHOO_UNIT_NOTE_CENTS,
            captured_at=datetime(2026, 11, 20, tzinfo=timezone.utc),
            rows=tuple(rows),
        )
        with self.assertRaises(ValueError) as ctx:
            rb.run_season(season, frame)
        self.assertIn("window coverage stops at", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
