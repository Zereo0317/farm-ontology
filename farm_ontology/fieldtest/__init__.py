"""Field-test rehearsals (QA) — registry, harness, doctrine-lane drills.

Finder-only discipline lives here: ``run_site``/``run_matrix`` drive the
multi-site agronomy matrix and collect
:class:`~farm_ontology.fieldtest.harness.DefectRow` findings, while
``arb_rehearsal`` walks the doctrine lanes end-to-end — both soften
nothing, change no engine configuration, and record every defect with a
named remedy. Standing verdicts:
``reports/arb-rehearsal-REPORT.md`` and
``reports/fieldtest-multisite-REPORT.md``.
"""

from farm_ontology.fieldtest.harness import (
    DEFAULT_DRIVE_DAYS,
    DECLARED_NATIVE_RESOLUTION_KM,
    SEVERITIES,
    DefectRow,
    SiteRunResult,
    adapt_fixture,
    fetch_site_year,
    fixture_path,
    load_site_fixture,
    run_matrix,
    run_site,
    save_site_fixture,
)
from farm_ontology.fieldtest.sites import SITES, SiteSpec, get_site

__all__ = [
    "DEFAULT_DRIVE_DAYS",
    "DECLARED_NATIVE_RESOLUTION_KM",
    "SEVERITIES",
    "DefectRow",
    "SiteRunResult",
    "adapt_fixture",
    "fetch_site_year",
    "fixture_path",
    "load_site_fixture",
    "run_matrix",
    "run_site",
    "save_site_fixture",
    "SITES",
    "SiteSpec",
    "get_site",
]
