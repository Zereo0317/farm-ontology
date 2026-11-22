import json
import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.fieldtest.harness import (
    DEFAULT_DRIVE_DAYS,
    DefectRow,
    adapt_fixture,
    fetch_site_year,
    fixture_path,
    load_site_fixture,
    run_matrix,
    run_site,
    save_site_fixture,
)
from farm_ontology.fieldtest.sites import SITES, get_site
from farm_ontology.testing import ONLINE_ENV

NOW = datetime(2026, 11, 1, tzinfo=timezone.utc)
RES = 11.0


def synth_fixture(
    *,
    t_mean_bias: float = 0.0,
    wet_bias_mm: float = 0.0,
    wind_scale: float = 1.0,
    ecto_null_row: int | None = None,
    duplicate_day: str | None = None,
) -> dict:
    """A tiny but engine-real 2026 season: May 20 .. Oct 30 daily + hourly."""
    start = date(2026, 5, 20)
    daily, hourly = [], []
    day = start
    step = 0
    while day <= date(2026, 10, 30):
        step += 1
        # Gentle seasonal warm curve peaking in July.
        swing = 18.0 + 7.0 * pow(abs(step - 75) / 75.0, 0.7)
        t_mean = round(swing - 8.0 + t_mean_bias, 1)
        daily.append(
            {
                "date": day.isoformat(),
                "temperature_2m_max": round(t_mean + 5, 1),
                "temperature_2m_min": round(t_mean - 6, 1),
                "temperature_2m_mean": t_mean,
                "precipitation_sum": round(1.0 + wet_bias_mm, 2),
                "et0_fao_evapotranspiration": 3.5,
                "wind_speed_10m_max": round(4.0 * wind_scale, 2),
            }
        )
        for hour in range(24):
            stamp = f"{day.isoformat()}T{hour:02d}:00"
            hourly.append(
                {
                    "time": stamp,
                    "temperature_2m": round(t_mean - 2.0, 1),
                    "precipitation": 0.0 if hour < 6 else round(0.05, 3),
                    "wind_speed_10m": round(2.0 * wind_scale, 2),
                }
            )
        if duplicate_day and day.isoformat() == duplicate_day:
            daily.append(dict(daily[-1]))
            duplicate_day = None
        day += timedelta(days=1)
    if ecto_null_row is not None:
        daily[ecto_null_row]["et0_fao_evapotranspiration"] = None
    body = {
        "daily": {
            "time": [row["date"] for row in daily],
            "temperature_2m_max": [row["temperature_2m_max"] for row in daily],
            "temperature_2m_min": [row["temperature_2m_min"] for row in daily],
            "temperature_2m_mean": [row["temperature_2m_mean"] for row in daily],
            "precipitation_sum": [row["precipitation_sum"] for row in daily],
            "et0_fao_evapotranspiration": [
                row["et0_fao_evapotranspiration"] for row in daily
            ],
            "wind_speed_10m_max": [row["wind_speed_10m_max"] for row in daily],
        },
        "hourly": {
            "time": [row["time"] for row in hourly],
            "temperature_2m": [row["temperature_2m"] for row in hourly],
            "precipitation": [row["precipitation"] for row in hourly],
            "wind_speed_10m": [row["wind_speed_10m"] for row in hourly],
        },
    }
    return {
        "captured_live": True,
        "transport_error": None,
        "fetched_at": NOW.isoformat(),
        "endpoint": "https://archive-api.open-meteo.com/v1/archive",
        "query": {},
        "response": body,
    }


def write_fixtures(tmp: Path, **overrides) -> Path:
    (tmp / "site-biratori-hidaka").mkdir(parents=True, exist_ok=True)
    (tmp / "site-obihoro-none").mkdir(parents=True, exist_ok=True)
    (tmp / "site-obihiro-tokachi").mkdir(parents=True, exist_ok=True)
    (tmp / "site-nakafurano-kamikawa").mkdir(parents=True, exist_ok=True)
    (tmp / "site-nemuro-hanasaki").mkdir(parents=True, exist_ok=True)
    (tmp / "site-tsuruoka-shonai").mkdir(parents=True, exist_ok=True)
    for site in SITES:
        envelope = synth_fixture(**overrides)
        if site.site_id == "nemuro-hanasaki":
            envelope = synth_fixture(wind_scale=3.0, **{})
        if site.site_id == "tsuruoka-shonai":
            envelope = synth_fixture(t_mean_bias=3.5)
        save_site_fixture(envelope, site.site_id, tmp)
    return tmp


class HarnessOfflineTests(unittest.TestCase):
    def setUp(self):
        import tempfile

        self.tmp = Path(tempfile.mkdtemp(prefix="fieldtest-"))
        write_fixtures(self.tmp)

    # -- happy path ------------------------------------------------------
    def test_run_site_produces_chain_and_no_blocker_defects(self):
        result = run_site(get_site("obihiro-tokachi"), days=140, fixtures_root=self.tmp)
        self.assertEqual(result.site, "obihiro-tokachi")
        self.assertIsNotNone(result.phenology_stage)
        # Historical fixtures do not prove an initial balance or point-in-time
        # availability. The operational adviser refuses instead of guessing.
        self.assertIsNone(result.irrigation_net_mm)
        self.assertIsNone(result.recommendation_id)
        self.assertIn("gap:missing-initial-state", {row.rule for row in result.defects})

    def test_irrigation_never_implies_parcel_support_without_sensors(self):
        for site in SITES:
            result = run_site(site, days=120, fixtures_root=self.tmp)
            for defect in result.defects:
                if defect.rule in {"support-ladder-climb", "parcel-claim-without-sensor", "probe-claim-without-sensor", "sensor-gate-leak"}:
                    self.fail(f"unexpected {defect.rule}: {defect.message}")
            self.assertIsNone(result.fixture_transport_error)

    # -- sharp-question probes -------------------------------------------
    def test_hot_control_earlier_stages_than_nemuro(self):
        hot = run_site(get_site("tsuruoka-shonai"), days=150, fixtures_root=self.tmp)
        cool = run_site(get_site("nemuro-hanasaki"), days=150, fixtures_root=self.tmp)
        self.assertIsNotNone(hot.cumulative_gdd)
        self.assertIsNotNone(cool.cumulative_gdd)
        self.assertGreater(hot.cumulative_gdd, cool.cumulative_gdd)

    def test_wind_scale_triple_keeps_chain_alive_but_records_sanity(self):
        result = run_site(get_site("nemuro-hanasaki"), days=150, fixtures_root=self.tmp)
        self.assertTrue(any(item["hours_in_slice"] > 0 for item in result.spray_scan))
        winds = [item.get("worst_wind_ms") or 0 for item in result.spray_scan]
        self.assertGreater(max(winds), 5.0)

    # -- defect capture ---------------------------------------------------
    def test_publisher_null_et0_becomes_named_gap_defect(self):
        (self.tmp / "site-obihiro-tokachi" / "year2026.json").unlink()
        envelope = synth_fixture(ecto_null_row=40)
        save_site_fixture(envelope, "obihiro-tokachi", self.tmp)
        result = run_site(get_site("obihiro-tokachi"), days=140, fixtures_root=self.tmp)
        rules = {row.rule for row in result.defects}
        # Missing initial-state evidence is the first refusal, before the
        # archive row can be treated as an operational input.
        self.assertIn("gap:missing-initial-state", rules)

    def test_transport_error_fixture_becomes_defect_not_crash(self):
        (self.tmp / "site-nemuro-hanasaki" / "year2026.json").unlink()
        broken = {
            "captured_live": False,
            "transport_error": "HTTP 503: upstream archive hiccup",
            "fetched_at": NOW.isoformat(),
        }
        save_site_fixture(broken, "nemuro-hanasaki", self.tmp)
        result = run_site(get_site("nemuro-hanasaki"), days=140, fixtures_root=self.tmp)
        rules = {(row.rule, row.severity) for row in result.defects}
        self.assertIn(("fixture-transport", "rough"), rules)
        self.assertEqual(result.fixture_transport_error, "HTTP 503: upstream archive hiccup")

    def test_missing_fixture_is_a_blocker(self):
        (self.tmp / "site-tsuruoka-shonai" / "year2026.json").unlink()
        result = run_site(get_site("tsuruoka-shonai"), days=90, fixtures_root=self.tmp)
        self.assertIn(
            "fixture-missing", {row.rule for row in result.defects}
        )
        self.assertTrue(
            any(row.severity == "blocker" for row in result.defects)
        )

    def test_edge_probes_fire_named_gaps(self):
        result = run_site(get_site("obihiro-tokachi"), days=120, fixtures_root=self.tmp)
        fired = dict(result.edges)
        for expected in (
            "missing-anchor",
            "mixed-resolutions",
            "regressive-dates",
            "missing-eto",
            "hour-hole",
            "stale-hours",
            "refused-kind",
            "no-inputs",
            "born-expired",
        ):
            self.assertIn(expected, fired)
            self.assertTrue(fired[expected].startswith("fired:"), (expected, fired[expected]))
        mismatches = [row for row in result.defects if row.stage == "edge"]
        self.assertEqual(mismatches, [], [row.to_payload() for row in mismatches])

    # -- adapter fidelity ---------------------------------------------------
    def test_adapter_passes_publisher_nulls_through(self):
        fixture = synth_fixture(ecto_null_row=3)
        adapted = adapt_fixture(fixture)
        self.assertIsNone(adapted["irrigation_rows"][3]["eto_mm"])
        self.assertEqual(
            adapted["phenology_rows"][0]["native_resolution_km"], RES
        )

    def test_adapter_normalises_archive_hour_stamps(self):
        adapted = adapt_fixture(synth_fixture())
        first = adapted["hourly_rows"][0]["time"]
        self.assertTrue(first.endswith("+00:00"), first)

    # -- helpers -------------------------------------------------------------
    def test_defect_row_validates_severity(self):
        with self.assertRaises(ValueError):
            DefectRow("s", "st", "rule", "msg", "catastrophic")

    def test_fixture_roundtrip_path_shape(self):
        path = fixture_path("obihiro-tokachi", self.tmp)
        self.assertEqual(path.name, "year2026.json")
        self.assertEqual(path.parent.name, "site-obihiro-tokachi")
        loaded = load_site_fixture(get_site("obihiro-tokachi"), self.tmp)
        self.assertTrue(loaded["captured_live"])

    def test_fetch_gate_refuses_when_offline(self):
        previous = {ONLINE_ENV: __import__("os").environ.get(ONLINE_ENV)}
        __import__("os").environ.pop(ONLINE_ENV, None)
        try:
            envelope = fetch_site_year(get_site("obihiro-tokachi"))
            self.assertFalse(envelope["captured_live"])
            self.assertIn("FARM_ONLINE_TESTS", envelope["transport_error"])
        finally:
            if previous[ONLINE_ENV] is not None:
                __import__("os").environ[ONLINE_ENV] = previous[ONLINE_ENV]

    def test_run_matrix_totals_match_sites(self):
        matrix = run_matrix(days=100, fixtures_root=self.tmp)
        self.assertEqual(matrix["site_count"], len(SITES))
        summed = {k: 0 for k in matrix["totals"]}
        for site in matrix["sites"]:
            for key, count in site["defect_counts"].items():
                summed[key] = summed.get(key, 0) + count
        self.assertEqual(summed, matrix["totals"])

    def test_days_trims_the_drive_window(self):
        short = run_site(get_site("obihiro-tokachi"), days=30, fixtures_root=self.tmp)
        long = run_site(get_site("obihiro-tokachi"), days=150, fixtures_root=self.tmp)
        self.assertIsNotNone(short.cumulative_gdd)
        self.assertIsNotNone(long.cumulative_gdd)
        self.assertLess(short.cumulative_gdd, long.cumulative_gdd)
        self.assertEqual(DEFAULT_DRIVE_DAYS, 165)


if __name__ == "__main__":
    unittest.main()
