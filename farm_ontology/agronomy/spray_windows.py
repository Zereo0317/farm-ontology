"""Spray-window adviser v0 (WS3.3) — 48 h scan over hourly rows.

INPUTS
------
Hourly rows, each ``{time, wind_ms, precip_mm, temp_c,
native_resolution_km}``, timestamps timezone-aware ISO-8601, strictly
hourly, no holes; the series must cover the scan context ``at`` and begin
no more than :data:`CONTEXT_BACK_HOURS` before it (context hours are
legitimate, a stale archive is not). A hole, a dup, a missing field, a
naive stamp, or a series that misses ``now`` is a named
:class:`AgronomyGap`.

RULE TABLE (CONFIG, VERIFY-tagged sources)
------------------------------------------
For a contiguous candidate run of hours, with the "rainfast tail" being
the ``RAINFAST_HOURS`` immediately AFTER the run:

==========  ==============================  ==============================  ==========
rule        NO-GO                           CAUTION                         GO
==========  ==============================  ==============================  ==========
wind        hourly wind > WIND_MAX_MS       none — wind between             every hour
            (loose: also excludes the       WIND_CONSERVATIVE_MS and        ≤ WIND_
            run entirely)                   WIND_MAX_MS still yields GO     MAX_MS
                                            but never the conservative tag  (≤CONS:
                                                                            conservative)
precip      any rain inside the run, or     the rainfast tail is not        run and
            inside a verifiable tail        fully inside the data — the     tail rain-
            (systemic uptake needs a dry    verdict drops to CAUTION with   free
            rainfast window)                evidence ``rainfast-window-     verified
                                            unverifiable`` — a published
                                            doubt, never a silent pass
temperature hourly temp outside               hourly temp in [TEMP_ABS_MIN,   every hour
            TEMP_ABS_MIN..TEMP_ABS_MAX      TEMP_GO_MIN) or (TEMP_GO_MAX,   in [10, 25]
                                            TEMP_ABS_MAX] — sprayable but
                                            flagged; stage-appropriate
            ==============================  ==============================
                                          GO wants the GLYPHOSATE-TYPE
                                          SYSTEMIC band [10, 25] °C
============ ============================== ============================== ==========

A candidate run is a maximal contiguous stretch where the LOOSE bounds
hold (wind ≤ 3, precip == 0, temp within absolute bounds). Its verdict is
GO only when every STRICT bound holds over the run AND the rainfast tail
is verifiably dry; otherwise CAUTION; NO-GO when the verdict-level rain
failure (wet tail) poisons an otherwise-valid run. Hours that belong to
no candidate are listed in the scan's ``unusable_spans`` with the rule
that disqualified them — the report explains its silences.

Wind limits per Japanese spray-window norms: ≤3 m/s for low-drift ground
sprayers, ≤2 m/s conservative flag; the 10–25 °C band is the guideline
uptake window for glyphosate-type systemics. VERIFY [SPRAY-WINDOW].

Every window carries its evidence: which rule fired, at which bound, with
which worst observed hour. Verdicts are advice stamps, not instructions:
the human signer disposes. Offline, deterministic, injected ``at``.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from datetime import datetime, timedelta
from typing import Sequence

from farm_ontology.agronomy.common import (
    CONFIG_VERSION,
    AgronomyGap,
    SupportDeclaration,
)
from farm_ontology.timeutil import ensure_utc

# Rule table (CONFIG). VERIFY [SPRAY-WINDOW]: Japanese low-drift ground
# spraying norm wind ≤3 m/s (conservative flag ≤2 m/s); systemic herbicide
# uptake guideline 10–25 °C; rainfast treated as 6 h for systemic
# glyphosate-type products (label-dependent; the label governs in reality).
WIND_CONSERVATIVE_MS = 2.0
WIND_MAX_MS = 3.0
TEMP_GO_MIN_C = 10.0
TEMP_GO_MAX_C = 25.0
TEMP_ABS_MIN_C = 5.0
TEMP_ABS_MAX_C = 30.0
RAINFAST_HOURS = 6
MIN_RUN_HOURS = 2

#: How far before the scan context the supplied series may begin.
CONTEXT_BACK_HOURS = 24

SPRAY_CONFIG = {
    "wind_conservative_ms": WIND_CONSERVATIVE_MS,
    "wind_max_ms": WIND_MAX_MS,
    "temp_go_min_c": TEMP_GO_MIN_C,
    "temp_go_max_c": TEMP_GO_MAX_C,
    "temp_abs_min_c": TEMP_ABS_MIN_C,
    "temp_abs_max_c": TEMP_ABS_MAX_C,
    "rainfast_hours": RAINFAST_HOURS,
    "min_run_hours": MIN_RUN_HOURS,
}

SPRAY_SOURCE_NOTE = (
    "VERIFY [SPRAY-WINDOW]: Japanese low-drift ground-sprayer norms "
    "(wind ≤3 m/s, conservative ≤2 m/s); glyphosate-type systemic uptake "
    "guideline 10-25 °C; rainfast 6 h is a conservative stand-in for the "
    "product label, which governs in reality. Weather screening only; no "
    "product or application method is verified, and no operation is approved."
)


class Verdict:
    # Weather-only screening cannot authorize a pesticide application.
    SCREENING = "WEATHER-SCREENING-ONLY"
    GO = "GO"  # legacy constant; never emitted by this screening interface
    CAUTION = "CAUTION"
    NO_GO = "NO-GO"


@dataclass(frozen=True)
class SprayWindow:
    """One candidate run with its verdict and its full evidence trail."""

    start: str                      # ISO-8601 UTC
    end: str                        # ISO-8601 UTC, run-exclusive
    hours: int
    verdict: str                    # a Verdict value
    evidence: tuple[dict, ...]
    support: SupportDeclaration
    use_class: str = "weather-screening"
    config_version: str = CONFIG_VERSION

    def __post_init__(self) -> None:
        if self.use_class != "weather-screening" or self.verdict not in (
            Verdict.SCREENING, Verdict.CAUTION, Verdict.NO_GO
        ):
            raise ValueError("spray windows are unapproved weather screening only")

    def to_payload(self) -> dict:
        return {
            "start": self.start,
            "end": self.end,
            "hours": self.hours,
            "verdict": self.verdict,
            "operational_approval": False,
            "evidence": [dict(item) for item in self.evidence],
            "support": self.support.to_payload(),
            "use_class": self.use_class,
            "config_version": self.config_version,
        }


def _parse_hour(value: object, index: int) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise AgronomyGap(
            "malformed-hour",
            f"hour row {index}: 'time' must be an ISO-8601 string",
            missing=(f"hour[{index}].time",),
        )
    try:
        return ensure_utc(
            datetime.fromisoformat(value.replace("Z", "+00:00")), f"hour[{index}].time"
        )
    except ValueError as error:
        raise AgronomyGap(
            "malformed-hour",
            f"hour row {index}: unparseable time {value!r}: {error}",
        ) from error


def _field(row: Sequence | dict, key: str, index: int) -> float:
    if not isinstance(row, dict) or key not in row:
        raise AgronomyGap(
            "missing-hour-field",
            f"hour row {index} lacks '{key}'",
            missing=(f"hour[{index}].{key}",),
        )
    value = row[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AgronomyGap(
            "missing-hour-field",
            f"hour row {index}: '{key}' must be a number, got {value!r}",
            missing=(f"hour[{index}].{key}",),
        )
    value = float(value)
    if not math.isfinite(value) or (key in {"wind_ms", "precip_mm"} and value < 0):
        raise AgronomyGap(
            "invalid-hour-field",
            f"hour row {index}: {key!r} must be finite and non-negative when applicable",
            missing=(f"hour[{index}].{key}",),
        )
    return value


def scan_spray_windows(
    hourly_rows: Sequence[dict],
    *,
    at: datetime,
) -> tuple[tuple[SprayWindow, ...], dict]:
    """Scan the hourly rows and return ``(windows, summary)``.

    ``summary`` names the honest leftovers: any gap-opening condition
    (short data, unusable spans with the disqualifying rule, the rule
    table version). The scan NEVER pads short data with hope: fewer than
    ``MIN_RUN_HOURS`` viable hours yields an empty window set and a
    summary note — a published nothing, not a fabricated window.
    """
    moment = ensure_utc(at, "at")
    if not hourly_rows:
        raise AgronomyGap(
            "no-usable-rows",
            "no hourly rows were supplied for the 48 h scan",
            missing=("hourly_rows",),
        )
    from farm_ontology.agronomy.phenology import _require_native_resolution

    resolution_km = _require_native_resolution(hourly_rows)

    stamps: list[datetime] = []
    for index, row in enumerate(hourly_rows):
        stamps.append(_parse_hour(row.get("time"), index))
    for index in range(1, len(stamps)):
        if stamps[index] - stamps[index - 1] != timedelta(hours=1):
            raise AgronomyGap(
                "hour-sequence-hole",
                f"hour rows {index - 1}->{index} are not a 1-hour step "
                f"({stamps[index - 1].isoformat()} -> {stamps[index].isoformat()})",
            )
    # Series-containment rule: the supplied series must COVER the scan
    # context (`at` lies inside it) and may reach at most CONTEXT_BACK
    # into the past — enough context hours to judge runs that begin
    # before `at`, never so much past that a stale archive masquerades
    # as a "next 48 h" scan.
    context_back = timedelta(hours=CONTEXT_BACK_HOURS)
    if stamps[0] > moment:
        raise AgronomyGap(
            "series-misses-now",
            f"the hourly series starts {stamps[0].isoformat()}, after the "
            f"scan context {moment.isoformat()}; a 'next 48 h' scan refuses "
            "a purely future (possibly stale-cached) series",
        )
    if stamps[-1] < moment:
        raise AgronomyGap(
            "stale-hours",
            f"the hourly series ends {stamps[-1].isoformat()}, before the "
            f"scan context {moment.isoformat()}; nothing 'next' to scan",
        )
    if stamps[0] < moment - context_back:
        raise AgronomyGap(
            "stale-hours",
            f"the hourly series begins {stamps[0].isoformat()}, more than "
            f"{CONTEXT_BACK_HOURS} h before the scan context; trim the rows "
            "to the operational window",
        )

    wind = [_field(row, "wind_ms", i) for i, row in enumerate(hourly_rows)]
    precip = [_field(row, "precip_mm", i) for i, row in enumerate(hourly_rows)]
    temp = [_field(row, "temp_c", i) for i, row in enumerate(hourly_rows)]

    # Loose viability per hour; remember WHY each failed hour failed.
    viable: list[bool] = []
    disqualification: list[str | None] = []
    for index in range(len(stamps)):
        reasons: list[str] = []
        if wind[index] > WIND_MAX_MS:
            reasons.append(f"wind>{WIND_MAX_MS:g}m/s")
        if precip[index] > 0:
            reasons.append("precip>0")
        if not (TEMP_ABS_MIN_C <= temp[index] <= TEMP_ABS_MAX_C):
            reasons.append(f"temp outside [{TEMP_ABS_MIN_C:g},{TEMP_ABS_MAX_C:g}]")
        viable.append(not reasons)
        disqualification.append("+".join(reasons) if reasons else None)

    # Maximal loose runs.
    runs: list[tuple[int, int]] = []  # inclusive start, exclusive end
    index = 0
    while index < len(viable):
        if viable[index]:
            end = index
            while end < len(viable) and viable[end]:
                end += 1
            if end - index >= MIN_RUN_HOURS:
                runs.append((index, end))
            index = end
        else:
            index += 1

    windows: list[SprayWindow] = []
    for start, end in runs:
        # Only full hours starting at or after the query are actionable.
        # Past context helps verify input continuity, not create past GO windows.
        while start < end and stamps[start] < moment:
            start += 1
        if end - start < MIN_RUN_HOURS:
            continue
        evidence: list[dict] = []
        run_wind = max(wind[start:end])
        run_temp_bad = [
            (i, temp[i])
            for i in range(start, end)
            if not (TEMP_GO_MIN_C <= temp[i] <= TEMP_GO_MAX_C)
        ]
        run_wet_inside = [
            (i, precip[i]) for i in range(start, end) if precip[i] > 0
        ]  # impossible by construction; kept as belt-and-braces evidence
        tail_indexes = list(range(end, min(len(stamps), end + RAINFAST_HOURS)))
        tail_wet = [(i, precip[i]) for i in tail_indexes if precip[i] > 0]
        tail_verifiable = len(tail_indexes) == RAINFAST_HOURS

        evidence.append(
            {
                "rule": "wind<=max",
                "bound_ms": WIND_MAX_MS,
                "worst_observed_ms": run_wind,
                "conservative_eligible": run_wind <= WIND_CONSERVATIVE_MS,
                "fired": True,
            }
        )
        if run_temp_bad:
            evidence.append(
                {
                    "rule": "temp-in-go-band",
                    "bound_c": [TEMP_GO_MIN_C, TEMP_GO_MAX_C],
                    "violating_hours": [
                        (stamps[i].isoformat(), value) for i, value in run_temp_bad
                    ],
                    "severity": "caution",
                    "fired": True,
                }
            )
        if run_wet_inside:
            evidence.append(
                {
                    "rule": "no-precip-in-run",
                    "wet_hours": [
                        (stamps[i].isoformat(), value) for i, value in run_wet_inside
                    ],
                    "fired": True,
                }
            )
        if tail_wet:
            evidence.append(
                {
                    "rule": "rainfast-tail-wet",
                    "rainfast_hours": RAINFAST_HOURS,
                    "wet_tail_hours": [
                        (stamps[i].isoformat(), value) for i, value in tail_wet
                    ],
                    "fired": True,
                }
            )
        elif not tail_verifiable:
            evidence.append(
                {
                    "rule": "rainfast-window-unverifiable",
                    "needed_hours": RAINFAST_HOURS,
                    "available_hours": len(tail_indexes),
                    "fired": True,
                    "note": "the data ends before the rainfast tail can be "
                    "checked; the window is published as CAUTION, not GO",
                }
            )

        if tail_wet or run_wet_inside:
            verdict = Verdict.NO_GO
        elif run_temp_bad or not tail_verifiable:
            verdict = Verdict.CAUTION
        else:
            verdict = Verdict.SCREENING

        evidence.append({
            "rule": "product-label-and-method-unverified",
            "fired": True,
            "note": "Weather screening only; no pesticide application is approved. "
                    "The product label, method, and authoritative requirements have not been verified.",
        })
        end_stamp = (
            stamps[end] if end < len(stamps) else stamps[end - 1] + timedelta(hours=1)
        )
        windows.append(
            SprayWindow(
                start=stamps[start].isoformat(),
                end=end_stamp.isoformat(),
                hours=end - start,
                verdict=verdict,
                evidence=tuple(evidence),
                support=SupportDeclaration(
                    base=f"grid-support (native {resolution_km:g} km)",
                    notes=(SPRAY_SOURCE_NOTE,),
                ),
            )
        )

    unusable = [
        {"time": stamps[i].isoformat(), "failed": disqualification[i]}
        for i in range(len(stamps))
        if disqualification[i] is not None
    ]
    summary = {
        "rule_table": SPRAY_CONFIG,
        "use_class": "weather-screening",
        "operational_approval": False,
        "label_status": "unverified",
        "config_version": CONFIG_VERSION,
        "source_note": SPRAY_SOURCE_NOTE,
        "hours_scanned": len(stamps),
        "scan_context": moment.isoformat(),
        "unusable_spans": unusable,
    }
    deterministic = tuple(
        sorted(windows, key=lambda window: (window.start, window.end))
    )
    return deterministic, summary


__all__ = [
    "SPRAY_CONFIG",
    "SPRAY_SOURCE_NOTE",
    "RAINFAST_HOURS",
    "MIN_RUN_HOURS",
    "Verdict",
    "SprayWindow",
    "scan_spray_windows",
]
