"""Argus Media website terms header.

One terms record from the page that was already opened. The stored
record is the printed header. The publisher is Argus Media Limited. The
product is Argus Media Website Terms of Use. The kind is Terms of Use.
The citation stays on
https://www.argusmedia.com/en/policies/terms-of-use.
https://www.argusmedia.com/ is not the citation.
https://www.argusmedia.com/en is not the citation.
14 May 2024 is the terms update date, not a data period.
The Copyright Policy named on the page was not opened.
The link Key commodity prices was not opened.
The London registered office is not an administrative area.
Period, unit, and administrative area were not opened.
No intellectual property is transferred.
The content does not constitute advice or recommendations.
No part, including single prices, graphs, or news, may be copied or reproduced without the prior written consent of the publisher.
© 2026 Argus Media group. All rights reserved. is a copyright line, not public domain.
No price, assessment, spread, or trade is stored.
The terms are not marked public domain.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

ARGUS_TERMS_URL = "https://www.argusmedia.com/en/policies/terms-of-use"

PUBLISHER = "Argus Media Limited"
PRODUCT = "Argus Media Website Terms of Use"
NOT_OPENED = "the field was not opened"
KIND = "Terms of Use"
UPDATE_DATE = "14 May 2024"
COPYRIGHT_LINE = "© 2026 Argus Media group. All rights reserved."
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "forecast",
    "observation",
    "completed harvest",
    "public domain",
    "benchmark",
    "price",
    "assessment",
    "spread",
    "single prices",
    "figure",
})


def _stores_figure(label) -> bool:
    return any(character.isdigit() for character in str(label))


def record_series_header(
    directory,
    *,
    citation_url=None,
    label=None,
    period=None,
    unit=None,
    administrative_area=None,
    value=None,
) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and (
        str(label).strip().lower() in FORBIDDEN_LABELS or _stores_figure(label)
    ):
        raise ValueError(
            "website terms are not a settlement, a yield, a trade, a "
            "forecast, an observation, a completed harvest, or a benchmark, "
            "and a price, assessment, spread, or figure is not stored"
        )
    if period is not None or unit is not None or administrative_area is not None:
        raise ValueError("period, unit, and administrative_area were not opened")
    if value is not None:
        raise ValueError("a figure is not stored")
    citation = str(citation_url).strip()
    if citation != ARGUS_TERMS_URL:
        raise ValueError("citation_url is not the opened terms page")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": NOT_OPENED,
        "unit": NOT_OPENED,
        "administrative_area": NOT_OPENED,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "argus-terms.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
