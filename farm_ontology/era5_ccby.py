"""ERA5-Land CC-BY sentence.

The overview page

https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=overview

was refetched. Its CC-BY licence button opens

https://object-store.os-api.cci2.ecmwf.int:443/cci2-prod-catalogue/licences/cc-by/cc-byv1_2b61eb0b42e053566cb9447c1d2847a69a275c095e00fca00bad1bf5326a9432.md

That page still prints: This dataset is released for use under the CC-BY
licence. The stored record is that sentence. The wording on the page is
what is stored. No weather value is stored. A data download, a GRIB
file, and the Confluence page were not opened. A reanalysis is not a
completed harvest and not a trade. permits_financial_use stays false.
Class C stays closed. This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.era5_land import ERA5_LAND_URL
from farm_ontology.policy import CLASS_C_POLICY

LICENCE_URL = (
    "https://object-store.os-api.cci2.ecmwf.int:443/cci2-prod-catalogue/"
    "licences/cc-by/cc-byv1_2b61eb0b42e053566cb9447c1d2847a69a275c095e00"
    "fca00bad1bf5326a9432.md"
)
FORBIDDEN_LABELS = frozenset(
    {
        "trade",
        "completed harvest",
        "harvest",
        "weather",
        "temperature",
        "settlement",
        "yield",
    }
)


def _printed_sentence(body: str) -> str:
    for line in body.splitlines():
        sentence = line.strip()
        if sentence:
            return sentence
    raise ValueError("the licence page prints no sentence")


def record_ccby_sentence(
    path: Path,
    citation_url: str | None,
    body: str | None = None,
    *,
    licence_url: str | None = None,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the sentence the licence page prints, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("a licence sentence is not stored without the overview")
    if citation_url != ERA5_LAND_URL:
        raise ValueError("a licence sentence is not stored for a different citation")
    if licence_url not in (None, LICENCE_URL):
        raise ValueError("a licence sentence is not stored for a different page")
    if body is None or body.strip() == "":
        raise ValueError("the licence page prints no sentence")
    if label is not None and (
        label.strip().lower() in FORBIDDEN_LABELS
        or any(character.isdigit() for character in label)
    ):
        raise ValueError("a reanalysis is not a completed harvest and not a trade")
    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    stored = {
        "sentence": _printed_sentence(body),
        "citation_url": ERA5_LAND_URL,
        "licence_page": LICENCE_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
