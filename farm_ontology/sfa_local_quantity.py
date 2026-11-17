"""No local quantity from the stored Singapore Food Statistics citation.

The citation already stored in the tests is:

https://www.sfa.gov.sg/docs/default-source/publication/sg-food-statistics/sgfs-2025-publication_060526-fa.pdf

Refetched on 17 Nov 2026, that exact URL returned HTTP 301. The body
was not a PDF and printed no local quantity for vegetables,
beansprouts, mushrooms, eggs, or seafood. The other address was not
opened. Nothing is stored. Singapore is not a farm. It is not a trade.
A soybean crop, a farm yield, and an import share are not stored.

permits_financial_use stays false. Class C stays closed.
"""

from __future__ import annotations

from pathlib import Path


SFA_URL = (
    "https://www.sfa.gov.sg/docs/default-source/publication/sg-food-statistics/"
    "sgfs-2025-publication_060526-fa.pdf"
)


def record_sfa_local_quantity(
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
    """Write nothing. The exact citation printed no local quantity."""

    del path, citation_url, series, period, value, label
    del permits_financial_use, class_c_policy
    raise ValueError("the exact citation printed no local quantity")
