"""Offline tests for the markets point-in-time dataset builder.

Only the repo's recorded fixtures are used. Nothing in this module, or
in what it exercises, opens a socket, calls an endpoint, or touches the
network.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from farm_ontology.markets import pit_dataset as pit
from farm_ontology.markets.pit_dataset import MarketFact, PurgeTrim


def _fact_factory(base_kwargs):
    def factory(**overrides):
        kwargs = dict(base_kwargs)
        kwargs.update(overrides)
        return MarketFact(**kwargs)

    return factory


BASE = dict(
    feed="ams_soybean_bid",
    group="usda_mnreports",
    subject="test:subject",
    metric="test_metric",
    recorded_act="recorded act text",
    publication_basis="printed basis text",
)


class CaptureConstantsTest(unittest.TestCase):
    def test_capture_times_are_pinned(self) -> None:
        utc = timezone.utc
        self.assertEqual(
            pit.CAPTURE_UTC[pit.FEED_USDA_WASDE],
            datetime(2026, 11, 16, 16, 15, 11, tzinfo=utc),
        )
        self.assertEqual(
            pit.CAPTURE_UTC[pit.FEED_AMS_SOYBEAN_BID],
            datetime(2026, 11, 17, 1, 59, 46, tzinfo=utc),
        )
        self.assertEqual(
            pit.CAPTURE_UTC[pit.FEED_FAO_FPI],
            datetime(2026, 11, 16, 16, 6, 25, tzinfo=utc),
        )
        self.assertEqual(
            pit.CAPTURE_UTC[pit.FEED_IMF_PCPS],
            datetime(2026, 11, 16, 16, 30, 12, tzinfo=utc),
        )
        self.assertEqual(
            pit.CAPTURE_UTC[pit.FEED_PINK_SHEET],
            datetime(2026, 11, 16, 15, 16, 44, tzinfo=utc),
        )

    def test_captures_are_timezone_aware(self) -> None:
        for feed in pit.FEEDS:
            self.assertIsNotNone(pit.CAPTURE_UTC[feed].tzinfo)


class FactIntegrityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = pit.all_facts()

    def test_row_count_and_shapes(self) -> None:
        by_feed: dict[str, int] = {}
        for row in self.rows:
            by_feed[row.feed] = by_feed.get(row.feed, 0) + 1
        self.assertEqual(by_feed[pit.FEED_AMS_SOYBEAN_BID], 4)
        self.assertEqual(by_feed[pit.FEED_USDA_WASDE], 4)
        self.assertEqual(by_feed[pit.FEED_FAO_FPI], 4)
        self.assertEqual(by_feed[pit.FEED_IMF_PCPS], 4)
        self.assertEqual(by_feed[pit.FEED_PINK_SHEET], 3)

    def test_every_quantitative_fact_has_a_unit(self) -> None:
        for row in self.rows:
            if row.quantitative:
                self.assertTrue(row.unit, row.metric)

    def test_only_ams_carries_values(self) -> None:
        valued = {row.feed for row in self.rows if row.quantitative}
        self.assertEqual(valued, {pit.FEED_AMS_SOYBEAN_BID})

    def test_storage_scope_rows_exist_and_store_none(self) -> None:
        for feed, subject in (
            (pit.FEED_USDA_WASDE, pit.SUBJECT_WASDE),
            (pit.FEED_FAO_FPI, pit.SUBJECT_FAO),
            (pit.FEED_IMF_PCPS, pit.SUBJECT_IMF),
            (pit.FEED_PINK_SHEET, pit.SUBJECT_PINK_CRUDE),
        ):
            scoped = [row for row in self.rows if row.subject == subject and row.metric == "storage_scope"]
            self.assertEqual(len(scoped), 1, subject)
            self.assertIsNone(scoped[0].value)
            self.assertTrue(scoped[0].value_text)

    def test_ams_printed_values_survive(self) -> None:
        rows = {(row.metric,): row for row in self.rows if row.feed == pit.FEED_AMS_SOYBEAN_BID}
        self.assertEqual(rows[("cash_bid_average",)].value, 11.16)
        self.assertEqual(rows[("cash_bid_range_low",)].value, 10.79)
        self.assertEqual(rows[("cash_bid_range_high",)].value, 11.34)
        self.assertEqual(rows[("cash_bid_average",)].unit, "$/Bu")

    def test_permits_financial_use_is_false_everywhere(self) -> None:
        for row in self.rows:
            self.assertFalse(row.permits_financial_use)

    def test_citations_match_recorded_constants(self) -> None:
        for row in self.rows:
            self.assertEqual(row.citation_url, pit.CITATIONS[row.feed])


class MatrixVisibilityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = pit.all_facts()

    def test_nothing_before_any_recording_act(self) -> None:
        early = datetime(2026, 11, 16, 15, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(pit.matrix(early, self.rows), [])

    def test_progressive_visibility_chronology(self) -> None:
        t0 = datetime(2026, 11, 16, 15, 20, tzinfo=timezone.utc)  # after pink
        t1 = datetime(2026, 11, 16, 17, 0, tzinfo=timezone.utc)  # after fao+wasde+imf
        t2 = datetime(2026, 11, 17, 2, 0, tzinfo=timezone.utc)  # after ams
        self.assertEqual(len(pit.matrix_row_keys(t0, self.rows)), 3)
        self.assertEqual(len(pit.matrix_row_keys(t1, self.rows)), 15)
        self.assertEqual(len(pit.matrix_row_keys(t2, self.rows)), 19)

    def test_naive_as_of_raises(self) -> None:
        with self.assertRaises(ValueError):
            pit.visible_facts(self.rows, datetime(2026, 11, 17))

    def test_matrix_columns_complete(self) -> None:
        late = datetime(2026, 11, 18, tzinfo=timezone.utc)
        row = pit.matrix(late, self.rows)[0]
        for column in (
            "feed",
            "group",
            "subject",
            "metric",
            "fact_time",
            "publication_time",
            "publication_basis",
            "value",
            "value_text",
            "unit",
            "recorded_act",
            "citation_url",
            "permits_financial_use",
            "capture_commit",
        ):
            self.assertIn(column, row)

    def test_matrix_is_deterministic(self) -> None:
        late = datetime(2026, 11, 18, tzinfo=timezone.utc)
        first = pit.matrix(late, self.rows)
        second = pit.matrix(late, self.rows)
        self.assertEqual(first, second)


class LatestRevisionTest(unittest.TestCase):
    def make(self, **overrides) -> MarketFact:
        kwargs = dict(BASE)
        kwargs["fact_time"] = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
        kwargs.update(overrides)
        return MarketFact(**kwargs)

    def test_latest_known_at_wins_per_metric(self) -> None:
        old = self.make(value=10.0, unit="$/Bu")
        new = self.make(
            fact_time=datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc),
            value=12.5,
            unit="$/Bu",
        )
        early = datetime(2026, 11, 17, 13, 0, tzinfo=timezone.utc)
        rows = pit.latest_per_metric(pit.visible_facts([old, new], early))
        self.assertEqual([row.value for row in rows], [10.0])
        late = datetime(2026, 11, 18, 13, 0, tzinfo=timezone.utc)
        rows = pit.latest_per_metric(pit.visible_facts([old, new], late))
        self.assertEqual([row.value for row in rows], [12.5])

    def test_future_revision_never_leaks_backward(self) -> None:
        leaked = self.make(
            fact_time=datetime(2026, 12, 1, tzinfo=timezone.utc),
            value=99.0,
            unit="$/Bu",
        )
        past = datetime(2026, 11, 19, tzinfo=timezone.utc)
        self.assertEqual(pit.visible_facts([leaked], past), ())
        # matrix reproduces only the knowable record
        self.assertEqual(
            [row for row in pit.matrix(past, [leaked])],
            [],
        )


class PurgeOverlapTest(unittest.TestCase):
    def two_group_case(self, later_value: float = 12.0):
        factory = _fact_factory(BASE)
        a1 = factory(
            metric="k",
            fact_time=datetime(2026, 11, 17, tzinfo=timezone.utc),
            value=10.0,
            unit="$/Bu",
        )
        b1 = factory(
            feed="pink_sheet",
            group="world_bank_pink",
            metric="k",
            fact_time=datetime(2026, 11, 19, tzinfo=timezone.utc),
            value=later_value,
            unit="$/Bu",
        )
        return a1, b1

    def test_later_published_group_wins_forward(self) -> None:
        a1, b1 = self.two_group_case()
        trims = {trim.fact.feed: trim for trim in pit.purge_overlapping([a1, b1])}
        self.assertEqual(trims["ams_soybean_bid"].until, b1.fact_time)
        self.assertIsNone(trims["pink_sheet"].until)

    def test_purged_matrix_switches_sources_at_the_seam(self) -> None:
        a1, b1 = self.two_group_case(later_value=12.0)
        between = datetime(2026, 11, 18, tzinfo=timezone.utc)
        after = datetime(2026, 11, 20, tzinfo=timezone.utc)
        before = datetime(2026, 11, 16, tzinfo=timezone.utc)
        self.assertEqual([row["feed"] for row in pit.purged_matrix(between, [a1, b1])], ["ams_soybean_bid"])
        self.assertEqual([row["feed"] for row in pit.purged_matrix(after, [a1, b1])], ["pink_sheet"])
        self.assertEqual(pit.purged_matrix(before, [a1, b1]), [])

    def test_equal_instants_do_not_trim_each_other(self) -> None:
        factory = _fact_factory(BASE)
        moment = datetime(2026, 11, 18, tzinfo=timezone.utc)
        a = factory(metric="k", fact_time=moment, value=10.0, unit="$/Bu")
        b = factory(feed="pink_sheet", group="world_bank_pink", metric="k", fact_time=moment, value=11.0, unit="$/Bu")
        for trim in pit.purge_overlapping([a, b]):
            self.assertIsNone(trim.until)
            self.assertFalse(trim.dropped_entirely)

    def test_same_group_dupes_collapse(self) -> None:
        factory = _fact_factory(BASE)
        t1 = datetime(2026, 11, 18, tzinfo=timezone.utc)
        t2 = t1 + timedelta(hours=1)
        first = factory(metric="k", fact_time=t1, value=10.0, unit="$/Bu")
        dup = factory(metric="k", fact_time=t1, value=10.0, unit="$/Bu")
        chained = factory(metric="k", fact_time=t2, value=11.0, unit="$/Bu")
        trims = pit.purge_overlapping([first, dup, chained])
        collapsed = [trim for trim in trims if trim.dropped_entirely]
        self.assertEqual(len(collapsed), 1)
        self.assertEqual(collapsed[0].fact.fact_time, t1)
        survivor = [trim for trim in trims if not trim.dropped_entirely]
        self.assertEqual({trim.fact.fact_time for trim in survivor}, {t1, t2})

    def test_group_of_fusion_trims_across_feeds(self) -> None:
        factory = _fact_factory(BASE)
        a = factory(metric="k", fact_time=datetime(2026, 11, 17, tzinfo=timezone.utc), value=10.0, unit="$/Bu")
        w = factory(
            feed="usda_wasde",
            group="usda_waob",
            metric="k",
            fact_time=datetime(2026, 11, 20, tzinfo=timezone.utc),
            value=11.0,
            unit="$/Bu",
        )
        fused = {"ams_soybean_bid": "combined", "usda_wasde": "combined"}
        trims = {trim.fact.feed: trim for trim in pit.purge_overlapping([a, w], group_of=fused)}
        self.assertEqual(trims["ams_soybean_bid"].until, w.fact_time)


class ConstructionGuardsTest(unittest.TestCase):
    def test_valueless_fact_requires_explicit_text(self) -> None:
        with self.assertRaises(ValueError):
            MarketFact(
                **{
                    **BASE,
                    "fact_time": datetime(2026, 11, 17, tzinfo=timezone.utc),
                    "metric": "empty",
                }
            )

    def test_quantitative_fact_requires_unit(self) -> None:
        with self.assertRaises(ValueError):
            MarketFact(
                **{
                    **BASE,
                    "fact_time": datetime(2026, 11, 17, tzinfo=timezone.utc),
                    "metric": "no_unit",
                    "value": 5.0,
                }
            )

    def test_unknown_feed_rejected(self) -> None:
        with self.assertRaises(ValueError):
            pit.facts_for_feed("does_not_exist")

    def test_helpful_attribute_touch_allowed(self) -> None:
        # purge helper exposes its result type for callers
        self.assertTrue(hasattr(pit, "PurgeTrim"))
        self.assertTrue(isinstance(PurgeTrim.__dataclass_fields__["until"], object))


if __name__ == "__main__":
    unittest.main()
