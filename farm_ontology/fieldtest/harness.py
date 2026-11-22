"""Field-test harness (QA campaign) — the finder, never the fixer.

Runs the full WS3 chain (phenology → irrigation scan → spray windows →
RecommendationRecord) per site on 2026 season fixtures and COLLECTS every
gap, refusal, exception, and sanity breach as a :class:`DefectRow`. This
module changes nothing about the engine under test: no config overrides,
no monkey-patching, no weakened assertions. Engine failures land in the
defect ledger exactly as thrown.

Offline discipline: everything here is deterministic and offline. The ONE
sanctioned live-fetch body (:func:`fetch_site_year`, reachable via
``python -m farm_ontology.fieldtest.harness --fetch``) is gated by
``FARM_ONLINE_TESTS=1`` mirroring :mod:`farm_ontology.testing`; it captures
the raw archive response ONCE per site into
``fixtures/fieldtest/site-<id>/year2026.json`` with ``captured_live`` and
``fetched_at`` recorded. Transport failures become defect rows, never
crashes (a Nemuro coastal quirk is a finding, not an exception).

Clocks: every datetime handed to the engine is INJECTED from the site
spec's 2026 sowing defaults and the season window; there is no wall-clock
read in the matrix path.

Usage::

    python -m farm_ontology.fieldtest.harness --fetch          # sanctioned capture
    python -m farm_ontology.fieldtest.harness [--days 165]     # matrix -> JSON on stdout
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from farm_ontology.agronomy.common import (
    AgronomyError,
    AgronomyGap,
    AgronomyRefusal,
)
from farm_ontology.agronomy.irrigation import (
    CoverageLevel,
    irrigation_advisory,
)
from farm_ontology.agronomy.phenology import (
    daily_gdd_contribution,
    phenology_reading,
)
from farm_ontology.agronomy.recommendation import (
    InputRef,
    RationaleStep,
    draft_recommendation,
)
from farm_ontology.agronomy.spray_windows import scan_spray_windows
from farm_ontology.fieldtest.sites import SITES, SiteSpec, get_site
from farm_ontology.timeutil import parse_time
from farm_ontology.testing import ONLINE_ENV

SEVERITIES = frozenset({"blocker", "rough", "cosmetic"})

#: Declared grid support of the 2026 archive fixtures. Open-Meteo's archive
#: best-match mixes ERA5 (~25 km) and ERA5-Land (~9-11 km); the harness
#: declares ONE uniform support for every row so the engine's no-blending
#: rule is exercised on TRUE inputs rather than adapter sloppiness.
#: VERIFY [ARCHIVE-GRID] against open-meteo's era5/API pages.
DECLARED_NATIVE_RESOLUTION_KM = 11.0

#: Days after the sowing anchor the harness drives. 165 days from a
#: 2026-05-20 sowing lands on 2026-11-01 — past the R7/R8 question window.
DEFAULT_DRIVE_DAYS = 165

#: Midday-JST (GMT 03:00) spray-scan instants.
SCAN_INSTANT_DATES: tuple[str, ...] = (
    "2026-06-15",
    "2026-07-15",
    "2026-08-15",
    "2026-09-15",
    "2026-09-30",
    "2026-10-05",
)

_SPRAY_BACK_HOURS = 12
_SPRAY_FORWARD_HOURS = 35
_ARCHIVE_ENDPOINT = "https://archive-api.open-meteo.com/v1/archive"
_DAILY_VARS = ",".join(
    (
        "temperature_2m_max",
        "temperature_2m_min",
        "temperature_2m_mean",
        "precipitation_sum",
        "et0_fao_evapotranspiration",
        "wind_speed_10m_max",
    )
)
_HOURLY_VARS = "temperature_2m,precipitation,wind_speed_10m"
_FETCH_WINDOW = ("2026-05-01", "2026-10-31")

_CAMPAIGN = "field-multisite-2026"


# ---------------------------------------------------------------------------
# Findings.


@dataclass(frozen=True)
class DefectRow:
    """One finding. The field order (site, stage, rule, message, severity)
    is the campaign contract."""

    site: str
    stage: str
    rule: str
    message: str
    severity: str

    def __post_init__(self) -> None:
        if self.severity not in SEVERITIES:
            raise ValueError(
                f"severity must be one of {sorted(SEVERITIES)}, got {self.severity!r}"
            )

    def to_payload(self) -> dict:
        return {
            "site": self.site,
            "stage": self.stage,
            "rule": self.rule,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class SiteRunResult:
    """Everything one site's run learned. Findings only; fixes never."""

    site: str
    sowing: str
    days: int
    phenology_stage: str | None
    cumulative_gdd: float | None
    gdd_oct15: float | None
    irrigation_recommend: bool | None
    irrigation_net_mm: float | None
    irrigation_coverage_level: str | None
    support_rendered: str | None
    spray_scan: tuple[dict, ...]
    recommendation_id: str | None
    recommendation_permits_financial_use: bool | None
    recommendation_requires_signoff: bool | None
    edges: tuple[tuple[str, str], ...]
    defects: tuple[DefectRow, ...]
    fixture_transport_error: str | None

    @property
    def defect_counts(self) -> dict[str, int]:
        counts = {severity: 0 for severity in sorted(SEVERITIES)}
        for row in self.defects:
            counts[row.severity] += 1
        return counts

    def to_payload(self) -> dict:
        return {
            "site": self.site,
            "sowing": self.sowing,
            "days": self.days,
            "phenology_stage": self.phenology_stage,
            "cumulative_gdd": self.cumulative_gdd,
            "gdd_oct15": self.gdd_oct15,
            "irrigation_recommend": self.irrigation_recommend,
            "irrigation_net_mm": self.irrigation_net_mm,
            "irrigation_coverage_level": self.irrigation_coverage_level,
            "support_rendered": self.support_rendered,
            "spray_scan": [dict(item) for item in self.spray_scan],
            "recommendation_id": self.recommendation_id,
            "recommendation_permits_financial_use": (
                self.recommendation_permits_financial_use
            ),
            "recommendation_requires_signoff": self.recommendation_requires_signoff,
            "edges": [[name, outcome] for name, outcome in self.edges],
            "defects": [row.to_payload() for row in self.defects],
            "defect_counts": self.defect_counts,
            "fixture_transport_error": self.fixture_transport_error,
        }


# ---------------------------------------------------------------------------
# Sanctioned live capture (gated).


def _online_enabled() -> bool:
    return os.environ.get(ONLINE_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def fetch_site_year(spec: SiteSpec) -> dict:
    """ONE gated network request per site; the raw response is preserved.

    Returns the fixture envelope with ``captured_live: True`` or with a
    ``transport_error`` string — it never raises for network trouble.
    """
    if not _online_enabled():
        return {
            "captured_live": False,
            "transport_error": (
                f"live fetch refused: set {ONLINE_ENV}=1 (mirrors farm_ontology.testing)"
            ),
            "fetched_at": None,
        }
    query = {
        "latitude": spec.latitude,
        "longitude": spec.longitude,
        "start_date": _FETCH_WINDOW[0],
        "end_date": _FETCH_WINDOW[1],
        "timezone": "GMT",
        "daily": _DAILY_VARS,
        "hourly": _HOURLY_VARS,
        "wind_speed_unit": "ms",
    }
    url = _ARCHIVE_ENDPOINT + "?" + urlencode(query)
    fetched_at = datetime.now(timezone.utc).isoformat()
    try:
        request = Request(
            url, headers={"User-Agent": "farm-ontology-fieldtest/0.1 (qa matrix)"}
        )
        with urlopen(request, timeout=180) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        try:
            detail = error.read().decode("utf-8", "replace")[:400]
        except OSError:
            detail = ""
        return {
            "captured_live": False,
            "transport_error": f"HTTP {error.code}: {detail}",
            "fetched_at": fetched_at,
            "endpoint": _ARCHIVE_ENDPOINT,
            "query": query,
        }
    except (URLError, TimeoutError, OSError) as error:
        return {
            "captured_live": False,
            "transport_error": f"{type(error).__name__}: {error}",
            "fetched_at": fetched_at,
            "endpoint": _ARCHIVE_ENDPOINT,
            "query": query,
        }
    return {
        "captured_live": True,
        "transport_error": None,
        "fetched_at": fetched_at,
        "endpoint": _ARCHIVE_ENDPOINT,
        "query": query,
        "declared_native_resolution_note": (
            "ERA5/ERA5-Land mixed archive; harness declares "
            f"{DECLARED_NATIVE_RESOLUTION_KM:g} km uniformly. VERIFY [ARCHIVE-GRID]"
        ),
        "response": body,
    }


def _default_fixtures_root() -> Path:
    return Path(__file__).resolve().parents[2] / "fixtures" / "fieldtest"


def fixture_path(site_id: str, fixtures_root: Path | None = None) -> Path:
    root = fixtures_root if fixtures_root is not None else _default_fixtures_root()
    return root / f"site-{site_id}" / "year2026.json"


def save_site_fixture(envelope: Mapping, site_id: str, fixtures_root: Path) -> Path:
    path = fixture_path(site_id, fixtures_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(envelope), ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return path


def load_site_fixture(spec: SiteSpec, fixtures_root: Path | None = None) -> dict:
    path = fixture_path(spec.site_id, fixtures_root)
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Fixture adaptation: raw archive body -> engine row vocabularies.


def _iso_gmt(stamp: object) -> str | None:
    if not isinstance(stamp, str) or len(stamp) < 10:
        return None
    text = stamp.replace("Z", "+00:00")
    if len(text) == 16:  # "YYYY-MM-DDTHH:MM" — the GMT archive convention
        text += ":00+00:00"
    return text


def _column(body: Mapping, section: str, key: str) -> list:
    data = body.get(section)
    if not isinstance(data, Mapping):
        return []
    values = data.get(key)
    return list(values) if isinstance(values, list) else []


def adapt_fixture(fixture: Mapping) -> dict:
    """Map the captured archive into the engine's row vocabularies.

    Publisher values pass through VERBATIM: a None the archive shipped
    stays a None and becomes the engine's own named gap — faithful history,
    not adapter repair.
    """
    response = fixture.get("response")
    body = response if isinstance(response, Mapping) else {}
    daily_dates = _column(body, "daily", "time")
    phenology_rows = [
        {
            "date": day,
            "t_mean_c": value,
            "native_resolution_km": DECLARED_NATIVE_RESOLUTION_KM,
        }
        for day, value in zip(daily_dates, _column(body, "daily", "temperature_2m_mean"))
    ]
    irrigation_rows = [
        {
            "date": day,
            "eto_mm": eto,
            "rain_mm": rain,
            "t_max_c": t_hi,
            "t_min_c": t_lo,
            "wind_max_ms": wind_peak,
            "native_resolution_km": DECLARED_NATIVE_RESOLUTION_KM,
        }
        for day, eto, rain, t_hi, t_lo, wind_peak in zip(
            daily_dates,
            _column(body, "daily", "et0_fao_evapotranspiration"),
            _column(body, "daily", "precipitation_sum"),
            _column(body, "daily", "temperature_2m_max"),
            _column(body, "daily", "temperature_2m_min"),
            _column(body, "daily", "wind_speed_10m_max"),
        )
    ]
    hourly_rows = [
        {
            "time": _iso_gmt(stamp),
            "temp_c": temp,
            "precip_mm": precip,
            "wind_ms": wind,
            "native_resolution_km": DECLARED_NATIVE_RESOLUTION_KM,
        }
        for stamp, temp, precip, wind in zip(
            _column(body, "hourly", "time"),
            _column(body, "hourly", "temperature_2m"),
            _column(body, "hourly", "precipitation"),
            _column(body, "hourly", "wind_speed_10m"),
        )
    ]
    return {
        "phenology_rows": phenology_rows,
        "irrigation_rows": irrigation_rows,
        "hourly_rows": hourly_rows,
    }


# ---------------------------------------------------------------------------
# Capture of engine failures.


def _capture(defects: list[DefectRow], site_id: str, stage: str):
    """Record engine failures as defect rows and neutralise them.

    AgronomyGap / AgronomyRefusal are the engine's DESIGNED, NAMED
    failures — they land as ``rough`` with the exact gap/refusal name.
    Anything else escaped the design envelope and lands as ``blocker``.
    """

    class _Ctx:
        gap: str | None = None
        refusal: str | None = None
        exception: str | None = None
        ok: bool = False

        def __enter__(ctx) -> "_Ctx":
            return ctx

        def __exit__(ctx, exc_type, exc, tb) -> bool:
            if exc is None:
                ctx.ok = True
                return False
            if isinstance(exc, AgronomyGap):
                ctx.gap = exc.gap
                defects.append(
                    DefectRow(site_id, stage, f"gap:{exc.gap}", exc.detail, "rough")
                )
                return True
            if isinstance(exc, AgronomyRefusal):
                ctx.refusal = exc.refusal
                defects.append(
                    DefectRow(
                        site_id, stage, f"refusal:{exc.refusal}", exc.detail, "rough"
                    )
                )
                return True
            if isinstance(exc, AgronomyError):
                ctx.exception = f"{type(exc).__name__}: {exc}"
                defects.append(
                    DefectRow(
                        site_id,
                        stage,
                        f"error:{type(exc).__name__}",
                        str(exc),
                        "rough",
                    )
                )
                return True
            ctx.exception = f"{type(exc).__name__}: {exc}"
            defects.append(
                DefectRow(
                    site_id,
                    stage,
                    f"exception:{type(exc).__name__}",
                    str(exc),
                    "blocker",
                )
            )
            return True

    return _Ctx()


# ---------------------------------------------------------------------------
# Row trimming.


def _row_day(row: Mapping, key: str) -> date | None:
    stamp = row.get(key)
    if not isinstance(stamp, str) or len(stamp) < 10:
        return None
    try:
        return date.fromisoformat(stamp[:10])
    except ValueError:
        return None


def _trim_rows_by_date(
    rows: Sequence[Mapping], key: str, start: date, end: date
) -> list[Mapping]:
    trimmed: list[Mapping] = []
    for row in rows:
        day = _row_day(row, key)
        if day is None or start <= day <= end:
            # Malformed stamps pass through: the ENGINE names them.
            trimmed.append(row)
    return trimmed


# ---------------------------------------------------------------------------
# The chain.


def _cumulative_by(p_rows: Sequence[Mapping], cutoff: date) -> float:
    cumulative = 0.0
    for row in p_rows:
        day = _row_day(row, "date")
        if day is not None and day <= cutoff:
            value = row.get("t_mean_c")
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                cumulative += daily_gdd_contribution(float(value))
    return round(cumulative, 1)


def _slice_hourly(
    hourly_rows: Sequence[Mapping], moment: datetime
) -> list[Mapping]:
    """Timestamp-exact slice: [moment - back, moment + forward].

    Date-boundary trimming would smuggle in up to a day of extra context
    hours and the engine would rightly refuse the slice with
    ``stale-hours`` (its context window is CONTEXT_BACK_HOURS = 24 h).
    """
    low = moment - timedelta(hours=_SPRAY_BACK_HOURS)
    high = moment + timedelta(hours=_SPRAY_FORWARD_HOURS)
    sliced: list[Mapping] = []
    for row in hourly_rows:
        stamp = row.get("time")
        if not isinstance(stamp, str) or not stamp:
            sliced.append(row)  # malformed: the engine names it
            continue
        try:
            moment_row = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except ValueError:
            sliced.append(row)
            continue
        if moment_row.tzinfo is None:
            moment_row = moment_row.replace(tzinfo=timezone.utc)
        if low <= moment_row <= high:
            sliced.append(row)
    return sliced


def run_site(
    spec: SiteSpec,
    days: int = DEFAULT_DRIVE_DAYS,
    *,
    fixtures_root: Path | None = None,
) -> SiteRunResult:
    """Drive the full chain for one site; collect findings. Finder only."""
    defects: list[DefectRow] = []
    edges: list[tuple[str, str]] = []
    spray_scan: list[dict] = []

    site_id = spec.site_id

    # ---- fixture -------------------------------------------------------
    transport_error: str | None = None
    try:
        fixture = load_site_fixture(spec, fixtures_root)
    except (OSError, ValueError) as error:
        defects.append(
            DefectRow(
                site_id,
                "fixture",
                "fixture-missing",
                f"could not load {fixture_path(site_id, fixtures_root)}: {error}",
                "blocker",
            )
        )
        return _result(spec, days, defects, edges, spray_scan, None)
    transport_error = fixture.get("transport_error") or None
    if transport_error:
        defects.append(
            DefectRow(
                site_id,
                "fixture",
                "fixture-transport",
                str(transport_error),
                "rough",
            )
        )
    if not fixture.get("captured_live"):
        defects.append(
            DefectRow(
                site_id,
                "fixture",
                "fixture-not-live",
                "fixture is not a captured_live capture",
                "cosmetic",
            )
        )
    if not fixture.get("fetched_at"):
        defects.append(
            DefectRow(site_id, "fixture", "fixture-metadata", "fetched_at missing", "cosmetic")
        )
    adapted = adapt_fixture(fixture)

    # ---- injected anchors ----------------------------------------------
    sowing = parse_time(spec.sow_default_2026)          # injected, per spec
    fixture_daily_dates = [
        _row_day(row, "date")
        for row in adapted["phenology_rows"]
        if _row_day(row, "date") is not None
    ]
    last_fixture_day = max(fixture_daily_dates) if fixture_daily_dates else None
    drive_end = sowing.date() + timedelta(days=days)
    if last_fixture_day is not None:
        drive_end = min(drive_end, last_fixture_day)
    # The assessment instant: end of the drive, 03:00 UTC (noon JST).
    at_final = datetime.combine(
        drive_end - timedelta(days=1), time(hour=3), tzinfo=timezone.utc
    )

    p_rows = _trim_rows_by_date(adapted["phenology_rows"], "date", sowing.date(), drive_end)
    i_rows = _trim_rows_by_date(adapted["irrigation_rows"], "date", sowing.date(), drive_end)
    h_rows = _trim_rows_by_date(adapted["hourly_rows"], "time", sowing.date(), drive_end)

    reading = None
    advice = None
    cumulative: float | None = None
    gdd_oct15: float | None = None

    # ---- stage: phenology ----------------------------------------------
    with _capture(defects, site_id, "phenology") as ctx:
        reading = phenology_reading(p_rows, sowing=sowing, emergence=None, at=at_final)
    if reading is not None:
        cumulative = reading.cumulative_gdd
        gdd_oct15 = _cumulative_by(p_rows, date(2026, 10, 15))
        if reading.anchor_conflict:
            defects.append(
                DefectRow(
                    site_id,
                    "sanity",
                    "anchor-conflict",
                    "sowing/emergence credit mismatch flagged by the engine reading",
                    "cosmetic",
                )
            )
        band_low, band_high = spec.season_gdd_band_low, spec.season_gdd_band_high
        if not band_low <= cumulative <= band_high:
            defects.append(
                DefectRow(
                    site_id,
                    "sanity",
                    "gdd-band-breach",
                    f"season cumulative {cumulative:g} GDD outside the VERIFY sanity "
                    f"band [{band_low:g},{band_high:g}] for {site_id}",
                    "rough",
                )
            )
        if not spec.is_control:
            # Sharp question 1: R7 (1850) reached for Hokkaido by mid-Oct?
            if gdd_oct15 < 1850.0:
                defects.append(
                    DefectRow(
                        site_id,
                        "sanity",
                        "r7-not-reached-by-oct15",
                        f"cumulative GDD by 2026-10-15 is {gdd_oct15:g} "
                        "(R7 threshold 1850); Hokkaido short-season norms "
                        "expect R7 within late-Sep–Oct (VERIFY [SOY-GDD-TABLE])",
                        "rough",
                    )
                )
            if reading.stage not in {"R6", "R7", "R8"}:
                defects.append(
                    DefectRow(
                        site_id,
                        "sanity",
                        "stage-below-r6-at-drive-end",
                        f"final announced stage {reading.stage!r} at drive end "
                        "is below full-seed; the season model never ripened",
                        "rough",
                    )
                )
            if gdd_oct15 is not None and gdd_oct15 >= 2100.0 and reading.stage == "R8":
                cum_sep15 = _cumulative_by(p_rows, date(2026, 9, 15))
                if cum_sep15 >= 2100.0:
                    defects.append(
                        DefectRow(
                            site_id,
                            "sanity",
                            "implausible-precocity",
                            f"R8-level GDD ({cum_sep15:g}) already banked by "
                            "2026-09-15 — agronomically implausible for "
                            "Hokkaido norms (VERIFY [GDD-SANITY-BAND])",
                            "rough",
                        )
                    )
        else:
            # Control: warm Shonai is EXPECTED to run hot; record the gulf
            # the record must speak to, not as a defect.
            pass

    # ---- stage: irrigation scan -----------------------------------------
    with _capture(defects, site_id, "irrigation") as ctx:
        advice = irrigation_advisory(
            i_rows, reading=reading, sensor_rows=(), parcel=None, at=at_final
        )
    if advice is not None:
        coverage_level = advice.coverage.level
        support_payload = advice.support.to_payload()
        if coverage_level != CoverageLevel.NONE:
            defects.append(
                DefectRow(
                    site_id,
                    "irrigation",
                    "support-ladder-climb",
                    f"coverage level {coverage_level!r} without any sensor rows "
                    "passed — the adviser climbed the ladder unevidence",
                    "blocker",
                )
            )
        extras = support_payload.get("extras") or []
        for extra in extras:
            if "parcel-support" in extra:
                defects.append(
                    DefectRow(
                        site_id,
                        "irrigation",
                        "parcel-claim-without-sensor",
                        f"support extras carry a parcel claim: {extra!r}",
                        "blocker",
                    )
                )
            if "probe-support" in extra:
                defects.append(
                    DefectRow(
                        site_id,
                        "irrigation",
                        "probe-claim-without-sensor",
                        f"support extras carry a probe claim: {extra!r}",
                        "blocker",
                    )
                )
        if advice.net_irrigation_requirement_mm > 400.0:
            defects.append(
                DefectRow(
                    site_id,
                    "sanity",
                    "implausible-deficit",
                    f"net irrigation requirement {advice.net_irrigation_requirement_mm:g} mm "
                    "exceeds a plausible season demand envelope for the crop",
                    "rough",
                )
            )
        # Design probe: the v0 balance holds the BASAL COEFFICIENT at the
        # season-FINAL stage's value for every day of the trace (Kcb is
        # driven by the single final reading's cumulative GDD, not by each
        # day's running total). On a Hokkaido-length season that tariffs
        # the vegetative weeks at pod-fill water use — a declared-ish but
        # consequence-heavy modelling artefact worth publishing.
        trace = advice.daily_trace
        if len(trace) > 30 and reading is not None and reading.stage_index >= 2:
            kcbs = {row.get("kcb") for row in trace}
            if len(kcbs) == 1:
                defects.append(
                    DefectRow(
                        site_id,
                        "irrigation",
                        "kcb-static-across-season",
                        f"Kcb held constant at {next(iter(kcbs)):g} across "
                        f"{len(trace)} daily rows while the season-spanning "
                        f"curve should have traversed several anchors "
                        f"(final stage {reading.stage}); vegetative weeks "
                        "tariffed at reproductive water use — v0 artefact, "
                        "biases ETc and the deficit upward",
                        "rough",
                    )
                )

    # ---- stage: sensor gates (the ladder must hold both ways) -----------
    parcel_demo = f"fixture:fieldtest/{site_id}/boundary-demo"
    sensor_probe_end = at_final
    uncertified_row = {
        "sensor_iri": "sensor/demo-probe-uncertified",
        "parcel_iri": parcel_demo,
        "value": 30.0,
        "phenomenon_end": sensor_probe_end.isoformat(),
    }
    certified_row = {
        "sensor_iri": "sensor/demo-probe-certified",
        "parcel_iri": parcel_demo,
        "value": 28.0,
        "phenomenon_end": sensor_probe_end.isoformat(),
        "calibration_activity": "activity/fieldtest-2026",
        "recalibration_due": "2027-06-01T00:00:00+00:00",
        "probe_radius_m": 2.0,
    }
    area_row = {
        **certified_row,
        "sensor_iri": "sensor/demo-probe-area",
        "coverage_area_ha": 0.4,
    }
    expired_row = {
        **certified_row,
        "sensor_iri": "sensor/demo-probe-expired",
        "recalibration_due": "2026-01-01T00:00:00+00:00",
    }

    from farm_ontology.agronomy.irrigation import has_calibrated_coverage

    for label, row, adopt_expected in (
        ("uncertified", uncertified_row, False),
        ("certified-probe", certified_row, True),
        ("certified-area", area_row, True),
        ("expired-cert", expired_row, False),
    ):
        outcome = has_calibrated_coverage([row], parcel_demo, at_final)
        adopted = bool(outcome.supporting_sensor_iris)
        if adopt_expected and not adopted:
            defects.append(
                DefectRow(
                    site_id,
                    "sensor-gate",
                    "ladder-underclaim",
                    f"{label} sensor row was refused coverage although it "
                    "carried a live certificate and fresh phenomena",
                    "rough",
                )
            )
        elif (not adopt_expected) and adopted:
            defects.append(
                DefectRow(
                    site_id,
                    "sensor-gate",
                    "sensor-gate-leak",
                    f"{label} sensor row was ADOPTED although its certificate "
                    f"story forbids it (excluded={ [dict(i) for i in outcome.excluded] })",
                    "blocker",
                )
            )
        edges.append((f"sensor-gate:{label}", f"adopted={adopted}"))

    # The adviser with a certified parcel-linked row: the ladder must
    # climb THROUGH the whole adviser, and the NUMBER must not move
    # (v0 sensors never change the grid-derived balance).
    if advice is not None:
        with _capture(defects, site_id, "irrigation-with-sensor") as ctx:
            advice_sensed = irrigation_advisory(
                i_rows,
                reading=reading,
                sensor_rows=[area_row],
                parcel=parcel_demo,
                at=at_final,
            )
        if getattr(ctx, "ok", False) and advice_sensed is not None:
            sensed_support = advice_sensed.support.to_payload()
            extras_sensed = sensed_support.get("extras") or []
            if not any("parcel-support" in extra for extra in extras_sensed):
                defects.append(
                    DefectRow(
                        site_id,
                        "sensor-gate",
                        "advisor-ladder-disconnect",
                        "a sensor-declared parcel area did not surface as "
                        "parcel-support through the adviser",
                        "rough",
                    )
                )
            if (
                advice_sensed.net_irrigation_requirement_mm
                != advice.net_irrigation_requirement_mm
            ):
                defects.append(
                    DefectRow(
                        site_id,
                        "sensor-gate",
                        "sensor-altered-balance",
                        "adding a sensor row changed the v0 grid-derived "
                        "balance; v0 promises divergence NOTES, not new numbers",
                        "blocker",
                    )
                )

    # ---- stage: spray windows --------------------------------------------
    for instant_date in SCAN_INSTANT_DATES:
        moment = datetime.combine(
            date.fromisoformat(instant_date), time(hour=3), tzinfo=timezone.utc
        )
        if moment > at_final + timedelta(hours=6):
            continue
        slice_rows = _slice_hourly(h_rows, moment)
        metric: dict = {
            "instant": moment.isoformat(),
            "hours_in_slice": len(slice_rows),
            "go": 0,
            "caution": 0,
            "nogo": 0,
            "no_windows_gap": None,
            "worst_wind_ms": None,
        }
        winds = [
            row.get("wind_ms")
            for row in slice_rows
            if isinstance(row.get("wind_ms"), (int, float))
        ]
        if winds:
            metric["worst_wind_ms"] = round(max(winds), 2)
        if not slice_rows:
            continue
        with _capture(defects, site_id, "spray") as ctx:
            windows, summary = scan_spray_windows(slice_rows, at=moment)
        if getattr(ctx, "ok", False):
            for window in windows:
                verdict = window.verdict
                if verdict.startswith("GO"):
                    metric["go"] += 1
                elif verdict == "CAUTION":
                    metric["caution"] += 1
                elif verdict == "NO-GO":
                    metric["nogo"] += 1
            metric["unusable_hours"] = len(summary.get("unusable_spans") or [])
        else:
            metric["no_windows_gap"] = (
                getattr(ctx, "gap", None) or getattr(ctx, "refusal", None)
            )
        spray_scan.append(metric)
    if spray_scan and all(item.get("hours_in_slice", 0) == 0 for item in spray_scan):
        defects.append(
            DefectRow(
                site_id,
                "spray",
                "no-spray-slices",
                "no scan instant had any hourly coverage",
                "rough",
            )
        )
    if site_id == "nemuro-hanasaki" and spray_scan:
        worst = max(
            (item.get("worst_wind_ms") or 0.0) for item in spray_scan
        )
        go_total = sum(item.get("go", 0) for item in spray_scan)
        if worst >= 8.0 and go_total > 0:
            # Not wrong per se — but with ≥8 m/s peaks dominating, an
            # abundance of GO windows deserves the squint.
            if go_total >= 6:
                defects.append(
                    DefectRow(
                        site_id,
                        "sanity",
                        "nemuro-wind-suspicious",
                        f"Nemuro slice winds peaked at {worst:g} m/s yet "
                        f"{go_total} GO windows appeared across "
                        f"{len(spray_scan)} scans — plausible only if the "
                        "gusts sat outside the scanned runs; verify against "
                        "the site's maritime climatology",
                        "rough",
                    )
                )

    # ---- stage: recommendation -------------------------------------------
    rec = None
    if advice is not None:
        inputs = (
            InputRef(
                iri=f"fixture:fieldtest/{site_id}/year2026",
                native_support="grid-cell",
                observed_property="open-meteo-archive:daily+hourly",
                availability_iso=str(fixture.get("fetched_at") or "fixture:not-live"),
                is_forecast=False,
                licence_instrument=(
                    "open-meteo CC-BY-4.0 (recorded fixture, attribution in file)"
                ),
                licence_permits_financial_use=False,
                licence_permits_redistribution=True,
                licence_expiry="none stated",
            ),
        )
        rationale = (
            RationaleStep(
                rule_id="ft-irrigation-summary",
                detail=(
                    f"grid-model root depletion {advice.root_depletion_mm:g} mm vs "
                    f"RAW {advice.raw_mm:g} mm; recommendation {advice.recommend}"
                ),
                triggered=bool(advice.recommend),
                evidence=(
                    ("net_mm", advice.net_irrigation_requirement_mm),
                    ("stage", advice.stage),
                ),
            ),
        )
        payload = {
            "site": site_id,
            "campaign": _CAMPAIGN,
            "net_irrigation_requirement_mm": advice.net_irrigation_requirement_mm,
            "recommend": bool(advice.recommend),
            "stage": advice.stage,
            "cumulative_gdd": cumulative if cumulative is not None else 0.0,
            "support": advice.support.to_payload(),
            "coverage": advice.coverage.to_payload(),
        }
        with _capture(defects, site_id, "recommendation") as ctx:
            rec = draft_recommendation(
                kind="irrigation",
                inputs=inputs,
                rationale=rationale,
                payload=payload,
                drafted_at=at_final,
                expires_at=at_final + timedelta(hours=48),
                uncertainty={
                    "basis": "engine-v0-fixtures",
                    "campaign": _CAMPAIGN,
                    "drive_days": days,
                },
            )
        if rec is not None:
            if rec.permits_financial_use:
                defects.append(
                    DefectRow(
                        site_id,
                        "recommendation",
                        "rec-financial-use-flipped",
                        "the record carries permits_financial_use True",
                        "blocker",
                    )
                )
            if not rec.requires_human_signoff:
                defects.append(
                    DefectRow(
                        site_id,
                        "recommendation",
                        "rec-signoff-missing",
                        "the record lost requires_human_signoff",
                        "blocker",
                    )
                )

    # ---- stage: edge probes -----------------------------------------------
    edges.extend(
        _probe_edges(spec, adapted, sowing=sowing, at=at_final, reading=reading, defects=defects)
    )

    return SiteRunResult(
        site=site_id,
        sowing=spec.sow_default_2026,
        days=days,
        phenology_stage=(reading.stage if reading is not None else None),
        cumulative_gdd=cumulative,
        gdd_oct15=gdd_oct15,
        irrigation_recommend=(advice.recommend if advice is not None else None),
        irrigation_net_mm=(advice.net_irrigation_requirement_mm if advice is not None else None),
        irrigation_coverage_level=(
            advice.coverage.level if advice is not None else None
        ),
        support_rendered=(
            advice.support.render() if advice is not None else None
        ),
        spray_scan=tuple(spray_scan),
        recommendation_id=(rec.recommendation_id if rec is not None else None),
        recommendation_permits_financial_use=(
            rec.permits_financial_use if rec is not None else None
        ),
        recommendation_requires_signoff=(
            rec.requires_human_signoff if rec is not None else None
        ),
        edges=tuple(edges),
        defects=tuple(defects),
        fixture_transport_error=transport_error,
    )


def _result(
    spec: SiteSpec,
    days: int,
    defects: list[DefectRow],
    edges: list[tuple[str, str]],
    spray_scan: list[dict],
    transport_error: str | None,
) -> SiteRunResult:
    return SiteRunResult(
        site=spec.site_id,
        sowing=spec.sow_default_2026,
        days=days,
        phenology_stage=None,
        cumulative_gdd=None,
        gdd_oct15=None,
        irrigation_recommend=None,
        irrigation_net_mm=None,
        irrigation_coverage_level=None,
        support_rendered=None,
        spray_scan=tuple(spray_scan),
        recommendation_id=None,
        recommendation_permits_financial_use=None,
        recommendation_requires_signoff=None,
        edges=tuple(edges),
        defects=tuple(defects),
        fixture_transport_error=transport_error,
    )


# ---------------------------------------------------------------------------
# Edge probes (designed failures must fire with their OWN names).


def _probe_edges(
    spec: SiteSpec,
    adapted: Mapping,
    *,
    sowing: datetime,
    at: datetime,
    reading,
    defects: list[DefectRow],
) -> list[tuple[str, str]]:
    site_id = spec.site_id
    outcomes: list[tuple[str, str]] = []

    def expect(name: str, expected: str, action: Callable[[], None]) -> None:
        try:
            action()
        except AgronomyGap as gap:
            if gap.gap == expected:
                outcomes.append((name, f"fired:{gap.gap}"))
            else:
                outcomes.append((name, f"MISMATCH:{gap.gap}"))
                defects.append(
                    DefectRow(
                        site_id,
                        "edge",
                        "edge-name-mismatch",
                        f"{name}: fired gap {gap.gap!r}, expected {expected!r}",
                        "blocker",
                    )
                )
        except AgronomyRefusal as refusal:
            outcomes.append((name, f"MISMATCH:refusal-{refusal.refusal}"))
            defects.append(
                DefectRow(
                    site_id,
                    "edge",
                    "edge-name-mismatch",
                    f"{name}: refusal {refusal.refusal!r}, expected gap {expected!r}",
                    "blocker",
                )
            )
        except Exception as error:  # noqa: BLE001 — recorded, never silenced
            outcomes.append((name, f"EXCEPTION:{type(error).__name__}"))
            defects.append(
                DefectRow(
                    site_id,
                    "edge",
                    "edge-exception",
                    f"{name}: unexpected {type(error).__name__}: {error}",
                    "blocker",
                )
            )
        else:
            outcomes.append((name, "MISSED"))
            defects.append(
                DefectRow(
                    site_id,
                    "edge",
                    "edge-missed",
                    f"{name}: expected gap {expected!r} never fired",
                    "blocker",
                )
            )

    def expect_refusal(name: str, expected: str, action: Callable[[], None]) -> None:
        try:
            action()
        except AgronomyRefusal as refusal:
            if refusal.refusal == expected:
                outcomes.append((name, f"fired:{refusal.refusal}"))
            else:
                outcomes.append((name, f"MISMATCH:{refusal.refusal}"))
                defects.append(
                    DefectRow(
                        site_id,
                        "edge",
                        "edge-name-mismatch",
                        f"{name}: refusal {refusal.refusal!r}, expected {expected!r}",
                        "blocker",
                    )
                )
        except AgronomyGap as gap:
            outcomes.append((name, f"MISMATCH:gap-{gap.gap}"))
            defects.append(
                DefectRow(
                    site_id,
                    "edge",
                    "edge-name-mismatch",
                    f"{name}: gap {gap.gap!r}, expected refusal {expected!r}",
                    "blocker",
                )
            )
        except Exception as error:  # noqa: BLE001
            outcomes.append((name, f"EXCEPTION:{type(error).__name__}"))
            defects.append(
                DefectRow(
                    site_id,
                    "edge",
                    "edge-exception",
                    f"{name}: unexpected {type(error).__name__}: {error}",
                    "blocker",
                )
            )
        else:
            outcomes.append((name, "MISSED"))
            defects.append(
                DefectRow(
                    site_id,
                    "edge",
                    "edge-missed",
                    f"{name}: expected refusal {expected!r} never fired",
                    "blocker",
                )
            )

    # E1: no anchor at all.
    expect(
        "missing-anchor",
        "missing-sowing-anchor",
        lambda: phenology_reading([], sowing=None, emergence=None),
    )
    # E2: mixed native resolutions in the phenology rows.
    def _e2() -> None:
        phenology_reading(
            [
                {"date": "2026-07-01", "t_mean_c": 20.0, "native_resolution_km": 11.0},
                {"date": "2026-07-02", "t_mean_c": 21.0, "native_resolution_km": 5.0},
            ],
            sowing=sowing,
            emergence=None,
            at=at,
        )

    expect("mixed-resolutions", "grid-resolution-mixed", _e2)
    # E3: regressive dates.
    def _e3() -> None:
        phenology_reading(
            [
                {"date": "2026-07-01", "t_mean_c": 20.0, "native_resolution_km": 11.0},
                {"date": "2026-06-30", "t_mean_c": 21.0, "native_resolution_km": 11.0},
            ],
            sowing=sowing,
            emergence=None,
            at=at,
        )

    expect("regressive-dates", "regressive-dates", _e3)
    # E4: irrigation row missing eto (None passes through from archives too).
    # When the happy-path reading failed earlier, the engine's first refusal
    # becomes missing-stage — the probe expects whichever fires honestly.
    def _e4() -> None:
        irrigation_advisory(
            [
                {
                    "date": "2026-07-01",
                    "eto_mm": None,
                    "rain_mm": 1.0,
                    "native_resolution_km": 11.0,
                }
            ],
            reading=reading,
            parcel=None,
            at=at,
        )

    expect(
        "missing-eto",
        "missing-initial-state" if reading is not None else "missing-stage",
        _e4,
    )
    # E5: a hole in the hourly series.
    def _e5() -> None:
        scan_spray_windows(
            [
                {
                    "time": (at - timedelta(hours=3)).isoformat(),
                    "wind_ms": 1.0,
                    "precip_mm": 0.0,
                    "temp_c": 20.0,
                    "native_resolution_km": 11.0,
                },
                {
                    "time": (at - timedelta(hours=1)).isoformat(),
                    "wind_ms": 1.0,
                    "precip_mm": 0.0,
                    "temp_c": 20.0,
                    "native_resolution_km": 11.0,
                },
            ],
            at=at,
        )

    expect("hour-hole", "hour-sequence-hole", _e5)
    # E6: stale series — strictly hourly (no holes: the engine checks
    # those first), stretching beyond the 24 h context window and ending
    # before `at`, so the containment rule and not the hole rule fires.
    def _e6() -> None:
        rows = [
            {
                "time": (at - timedelta(hours=offset)).isoformat(),
                "wind_ms": 1.0,
                "precip_mm": 0.0,
                "temp_c": 20.0,
                "native_resolution_km": 11.0,
            }
            for offset in range(30, 5, -1)
        ]
        scan_spray_windows(rows, at=at)

    expect("stale-hours", "stale-hours", _e6)
    # E7: recommendation refusing a class-C-shaped kind outright.
    input_ref = InputRef(
        iri=f"fixture:fieldtest/{site_id}/edge-input",
        native_support="grid-cell",
        observed_property=None,
        availability_iso=None,
        is_forecast=False,
        licence_instrument="none",
        licence_permits_financial_use=False,
        licence_permits_redistribution=False,
        licence_expiry="none",
    )
    expect_refusal(
        "refused-kind",
        "refused-use",
        lambda: draft_recommendation(
            kind="hedge",
            inputs=(input_ref,),
            rationale=(RationaleStep(rule_id="ft-edge", detail="x", triggered=True),),
            payload={},
            drafted_at=at,
            expires_at=at + timedelta(hours=48),
        ),
    )
    # E8: a recommendation without inputs.
    expect(
        "no-inputs",
        "no-inputs",
        lambda: draft_recommendation(
            kind="irrigation",
            inputs=(),
            rationale=(RationaleStep(rule_id="ft-edge", detail="x", triggered=True),),
            payload={},
            drafted_at=at,
            expires_at=at + timedelta(hours=48),
        ),
    )
    # E9: born expired.
    expect_refusal(
        "born-expired",
        "born-expired",
        lambda: draft_recommendation(
            kind="irrigation",
            inputs=(input_ref,),
            rationale=(RationaleStep(rule_id="ft-edge", detail="x", triggered=True),),
            payload={},
            drafted_at=at,
            expires_at=at - timedelta(hours=1),
        ),
    )
    return outcomes


# ---------------------------------------------------------------------------
# Matrix + entry points.


def run_matrix(days: int = DEFAULT_DRIVE_DAYS, fixtures_root: Path | None = None) -> dict:
    results = [run_site(get_site(spec.site_id), days, fixtures_root=fixtures_root) for spec in SITES]
    totals = {severity: 0 for severity in sorted(SEVERITIES)}
    for result in results:
        for severity, count in result.defect_counts.items():
            totals[severity] = totals.get(severity, 0) + count
    return {
        "campaign": _CAMPAIGN,
        "generated_from": "fixtures/fieldtest (2026 open-meteo archive captures)",
        "days": days,
        "declared_native_resolution_km": DECLARED_NATIVE_RESOLUTION_KM,
        "sites": [result.to_payload() for result in results],
        "totals": totals,
        "site_count": len(results),
    }


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--fetch" in argv:
        if not _online_enabled():
            print(
                json.dumps(
                    {
                        "error": f"refusing: set {ONLINE_ENV}=1 to sanction the fetch",
                        "fetched": [],
                    }
                )
            )
            return 2
        fixtures_root = _default_fixtures_root()
        report = []
        for spec in SITES:
            envelope = fetch_site_year(spec)
            path = save_site_fixture(envelope, spec.site_id, fixtures_root)
            report.append(
                {
                    "site": spec.site_id,
                    "captured_live": envelope.get("captured_live"),
                    "transport_error": envelope.get("transport_error"),
                    "written": str(path),
                }
            )
        print(json.dumps({"fetched": report}, ensure_ascii=False, indent=2))
        return 0
    days = DEFAULT_DRIVE_DAYS
    if "--days" in argv:
        index = argv.index("--days")
        days = int(argv[index + 1])
    print(json.dumps(run_matrix(days=days), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
