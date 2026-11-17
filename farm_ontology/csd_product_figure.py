"""C&SD product-line index figure.

The subject page prints one parenthetical figure on the product line:
Index of Industrial Production for Manufacturing and Waste Management
Sectors (Year 2015=100). The stored figure is 100. Year 2015 is printed
next to that figure, so the period is Year 2015. No unit and no area
are printed next to the figure, so neither is stored. The web table and
a bulk file were not opened. An index is not a quantity of goods and
not a trade. permits_financial_use stays false.
permits_financial_use_test is not set. Class C stays closed. This
module does not change the header function that rejects a figure. This
module is not called from a field save.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from farm_ontology.csd_industrial import CSD_INDUSTRIAL_URL, PRODUCT
from farm_ontology.policy import CLASS_C_POLICY

_FIGURE = re.compile(
    r"Index of Industrial Production for Manufacturing and Waste Management "
    r"Sectors \(Year (\d{4})=(\d+)\)"
)
FORBIDDEN_LABELS = frozenset(
    {
        "trade",
        "completed harvest",
        "harvest",
        "quantity of goods",
        "trading right",
        "settlement",
        "settlement price",
        "price",
    }
)
def _plain(body: str) -> str:
    text = re.sub(r"<[^>]+>", " ", body.replace("\xa0", " "))
    return " ".join(text.split())


def _printed_figure(body: str) -> tuple[str, str]:
    found = _FIGURE.findall(_plain(body))
    if len(found) != 1:
        raise ValueError("the page prints no single index figure")
    year, figure = found[0]
    return figure, f"Year {year}"


def record_product_figure(
    path: Path,
    citation_url: str | None,
    body: str | None = None,
    *,
    source_url: str | None = None,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    permits_financial_use_test: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed product-line index figure, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("a figure is not stored without the subject page")
    if citation_url != CSD_INDUSTRIAL_URL:
        raise ValueError("a figure is not stored for a different citation")
    if source_url not in (None, CSD_INDUSTRIAL_URL):
        raise ValueError("the web table and a bulk file are not opened")
    if body is None or body.strip() == "":
        raise ValueError("the page prints no single index figure")
    if label is not None and (
        label.strip().lower() in FORBIDDEN_LABELS
        or any(character.isdigit() for character in label)
    ):
        raise ValueError("an index is not a quantity of goods and not a trade")
    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    if permits_financial_use_test is not None:
        raise ValueError("permits_financial_use_test is not set")
    figure, period = _printed_figure(body)
    stored = {
        "value": figure,
        "period": period,
        "product": PRODUCT,
        "kind": "index",
        "citation_url": CSD_INDUSTRIAL_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
