"""Multi-site field test (QA campaign) — registry, harness, findings.

Finder-only discipline lives here: run_site and run_matrix collect
:class:`~farm_ontology.fieldtest.harness.DefectRow` findings; they never
change engine configuration and never patch engine behaviour.
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
