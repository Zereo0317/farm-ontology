"""Multi-site registry for the WS3 engine field test (QA campaign).

Five pilot sites: four Hokkaido soybean venues plus one Honshu control.
Every agronomic expectation in this module is VERIFY-tagged: these are
published-norm envelopes for the region, NOT local trial calibrations, and
they exist so the field-test harness can distinguish "engine disagrees
with the region" from "engine agrees with reality" loudly. Nothing here is
an acceptance criterion for the engine's maths — it is the net the engine
should fail into if its assumptions drift.

House rules inherited from the engine (``farm_ontology.agronomy``):
stdlib-only, frozen dataclasses, no wall-clock reads, no network.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SiteSpec:
    """One field-test site and the agronomic sanity envelope around it.

    ``verify_tags`` names every VERIFY-marked claim this registry carries
    (sowing-window norms, GDD bands, station anchors) so a future agent
    can chase each tag against its published source.
    """

    site_id: str
    label: str
    latitude: float
    longitude: float
    is_control: bool = False
    #: Regional context note (climate/terrain factors the report should read).
    context_note: str = ""
    #: VERIFY [SOW-HOKKAIDO]: Hokkaido soybean sowing norm, Yukihomare /
    #: Ryuho class varieties: establishment after late-frost risk, typically
    #: mid-May through the first week of June. Formatted MM-DD strings.
    sow_window_start_md: str = "05-10"
    sow_window_end_md: str = "06-10"
    #: VERIFY [GDD-SANITY-BAND]: plausible cumulative GDD (base 10 C, cap-30)
    #: accumulated by the END of the driven season window for this region,
    #: sown inside the window above. Breaching the band is a ROUGH defect
    #: (engine-vs-region disagreement), not an engine correctness verdict.
    season_gdd_band_low: float = 0.0
    season_gdd_band_high: float = 0.0
    #: Cumulative GDD by 2026-10-15 at which R7 (1850) should be at risk of
    #: NOT being reached in this climate; also used for the R7-miss check.
    gdd_expect_oct15_low: float = 0.0
    #: Nearest AMeDAS observatory number (JMA), VERIFY-RESOLVE tagged:
    #: only values cross-checked against public JMA listings during authoring
    #: are non-None; ``jma_block_note`` says the confidence level.
    jma_block: str | None = None
    jma_block_note: str = ""
    #: 2026 default sowing instants (JST, 09:00 local) used as INJECTED
    #: engine anchors; per-site differentiation is intentional (coastal
    #: Nemuro sows late) and VERIFY [SOW-HOKKAIDO] bounded.
    sow_default_2026: str = "2026-05-20T09:00:00+09:00"
    verify_tags: tuple[str, ...] = ()

    @property
    def sow_window_2027(self) -> tuple[str, str]:
        return (f"2027-{self.sow_window_start_md}", f"2027-{self.sow_window_end_md}")


VERIFY_SOW = "VERIFY [SOW-HOKKAIDO]: Hokkaido soybean sowing norm, mid-May "
"to early June for Yukihomare/Ryuho-class varieties (establishment after "
"late-frost risk; Ryuho grown slightly later/planted marginally later in "
"practice). Recalibrate per JA guidance before any agronomic reliance."

_VERIFY_TAGS_COMMON = (
    "VERIFY [SOW-HOKKAIDO]",
    "VERIFY [GDD-SANITY-BAND]",
    "VERIFY [SOY-GDD-BASE] (inherited from engine)",
    "VERIFY [SOY-GDD-TABLE] (inherited from engine)",
)

# Sanity bands (VERIFY [GDD-SANITY-BAND]): the engine's coarse stage table
# puts R8 at 2100 GDD. Regions differ: Tokachi/Central Highlands routinely
# accumulate 1500-2300 GDD May-Oct (R6-R8 attainable for short-season
# varieties), Nemuro's cool maritime shoulder often lands 1200-1900 (R6-R7),
# and the warm Shonai control typically overshoots 1800-2600 (R7/R8 well
# within reach, often excessing R8). Bands are deliberately WIDE: a breach
# signals an engine/climate disagreement worth investigating, not proof.
_BANDS = {
    "biratori-hidaka": (1250.0, 2450.0, 1500.0),
    "obihiro-tokachi": (1350.0, 2500.0, 1600.0),
    "nakafurano-kamikawa": (1250.0, 2450.0, 1450.0),
    "nemuro-hanasaki": (1050.0, 2150.0, 1200.0),
    "tsuruoka-shonai": (1650.0, 2850.0, 1850.0),
}


def _site(site_id: str, **kw) -> SiteSpec:
    low, high, oct15 = _BANDS[site_id]
    kw.setdefault("season_gdd_band_low", low)
    kw.setdefault("season_gdd_band_high", high)
    kw.setdefault("gdd_expect_oct15_low", oct15)
    kw.setdefault("verify_tags", _VERIFY_TAGS_COMMON)
    return SiteSpec(site_id=site_id, **kw)


#: The five-site matrix (Hokkaido quartet + Honshu control).
SITES: tuple[SiteSpec, ...] = (
    _site(
        "biratori-hidaka",
        label="Biratori / Hidaka (campaign home anchor)",
        latitude=42.7018,
        longitude=142.4071,
        context_note=(
            "Saru-river valley agri belt; the farm the record anchors on. "
            "Inland Hokkaido warm pocket with cold drainage nights."
        ),
        jma_block="1423",
        jma_block_note=(
            "AMeDAS Hiratori 1423 — plausibly the nearest observatory; "
            "VERIFY-RESOLVE against the JMA station listing before feed use."
        ),
        sow_default_2026="2026-05-20T09:00:00+09:00",
    ),
    _site(
        "obihiro-tokachi",
        label="Obihiro / Tokachi (megafarm soybelt)",
        latitude=42.85,
        longitude=143.20,
        context_note=(
            "Tokachi plain — Hokkaido's largest dry-field basin; the "
            "production reality the record must eventually speak to."
        ),
        jma_block="1408",
        jma_block_note=(
            "AMeDAS Obihiro 1408 — high-confidence anchor (major JMA "
            "observatory); still VERIFY-RESOLVE before feed use."
        ),
        sow_default_2026="2026-05-15T09:00:00+09:00",
    ),
    _site(
        "nakafurano-kamikawa",
        label="Nakafurano / Kamikawa (higher-latitude inland)",
        latitude=43.48,
        longitude=142.54,
        context_note=(
            "Furano basin; higher latitude inland, sharper continentality, "
            "famous for flower farming — soy suitability is the edge case."
        ),
        jma_block=None,
        jma_block_note=(
            "Nearest AMeDAS candidates are Furano and Asahikawa; block "
            "numbers NOT confirmed during authoring — left None (a gap, "
            "not a guess). VERIFY-RESOLVE before feed use."
        ),
        sow_default_2026="2026-05-25T09:00:00+09:00",
    ),
    _site(
        "nemuro-hanasaki",
        label="Nemuro / Hanasaki (eastern maritime cool shoulder)",
        latitude=43.30,
        longitude=145.55,
        context_note=(
            "Easternmost maritime site; sea-ice cooled springs, fierce "
            "coastal winds — the stress test for spray-window logic and "
            "the coldest GDD regime in the matrix."
        ),
        jma_block="1420",
        jma_block_note=(
            "AMeDAS Nemuro 1420 — high-confidence anchor (major JMA "
            "observatory); still VERIFY-RESOLVE before feed use."
        ),
        sow_default_2026="2026-05-28T09:00:00+09:00",
    ),
    _site(
        "tsuruoka-shonai",
        label="Tsuruoka / Shonai (Honshu warm control)",
        latitude=38.72,
        longitude=139.85,
        is_control=True,
        context_note=(
            "Warm Shonai-plain control OUTSIDE Hokkaido: if the engine "
            "behaves identically here and in Nemuro, its climate response "
            "is broken. Excess GDD and earlier maturity are EXPECTED and "
            "not defects on this control line."
        ),
        jma_block="1216",
        jma_block_note=(
            "AMeDAS Tsuruoka 1216 — plausibly correct; VERIFY-RESOLVE "
            "against the JMA station listing before feed use."
        ),
        sow_default_2026="2026-05-15T09:00:00+09:00",
    ),
)

_SITE_INDEX = {spec.site_id: spec for spec in SITES}


def get_site(site_id: str) -> SiteSpec:
    """Registry lookup; an unknown id raises KeyError (loud, not silent)."""
    return _SITE_INDEX[site_id]


__all__ = [
    "SiteSpec",
    "SITES",
    "get_site",
    "VERIFY_SOW",
]
