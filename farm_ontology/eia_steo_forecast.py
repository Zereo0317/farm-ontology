"""One printed EIA Short-Term Energy Outlook forecast figure.

The citation already stored in the tests is:

https://www.eia.gov/outlooks/steo/

The Notable Forecast Changes table prints OPEC total liquid fuels
production, in million barrels per day, at 24.5 under the 2026 column.
That cell is a published forecast. It is not completed supply, an
observation, or a settlement. The 2027 cell and the previous forecast
are not this figure.

permits_financial_use stays false. Class C stays closed. A missing
citation writes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

STEO_URL = "https://www.eia.gov/outlooks/steo/"

SERIES = "OPEC total liquid fuels production"
PERIOD = "2026"
VALUE = "24.5"
UNIT = "million barrels per day"
KIND = "published forecast"

FORBIDDEN_LABELS = frozenset(
    {
        "settlement",
        "observation",
        "completed supply",
        "trade",
        "yield",
    }
)


def record_eia_steo_forecast(
    path: Path,
    citation_url: str | None,
    *,
    series: str | None = None,
    period: str | None = None,
    value: object = None,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed forecast cell, or write nothing."""

    if citation_url is None or citation_url.strip() == "":
        raise ValueError("a forecast figure is not stored without a citation_url")
    if citation_url != STEO_URL:
        raise ValueError("a forecast figure is not stored for a different citation")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "a forecast figure is not completed supply, an observation, or a settlement"
        )
    if any(
        item is not None
        for item in (series, period, value, permits_financial_use, class_c_policy)
    ):
        raise ValueError("a forecast figure is not stored with a different value")
    header = {
        "series": SERIES,
        "period": PERIOD,
        "value": VALUE,
        "unit": UNIT,
        "kind": KIND,
        "citation_url": STEO_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
