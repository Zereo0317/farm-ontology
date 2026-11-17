"""Latest FAO Food Price Index from the cited page.

The refetch of

https://www.fao.org/worldfoodsituation/foodpricesindex/en/

returned HTTP 200. The page prints that the FAO Food Price Index
(FFPI) averaged 133.9 points in October 2026. The index is not a
traded price. A request that fails, or a page with no index value,
writes nothing. An index value is not invented.
permits_financial_use stays false. Class C stays closed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

FAO_FFPI_URL = "https://www.fao.org/worldfoodsituation/foodpricesindex/en/"

FORBIDDEN_LABELS = frozenset(
    {
        "trade",
        "traded price",
        "settlement",
        "yield",
        "harvest",
        "completed harvest",
    }
)


def _plain(body: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", body).split())


def _index(body: str) -> dict:
    text = _plain(body)
    match = re.search(
        r"FAO Food Price Index \(FFPI\s*\)\s*\*?\s*averaged\s+"
        r"(\d+(?:\.\d+)?)\s+points in ([A-Z][a-z]+ \d{4})",
        text,
    )
    if match is None:
        raise ValueError("the page has no index value")
    token = match.group(1)
    number = float(token) if "." in token else int(token)
    if json.dumps(number) != token:
        number = token
    return {
        "index": "FAO Food Price Index",
        "month": match.group(2),
        "value": number,
        "unit": "points",
    }


def record_fao_ffpi_current(
    path: Path,
    citation_url: str | None,
    body: str | None = None,
    *,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed food price index, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("an index is not stored without a response")
    if citation_url != FAO_FFPI_URL:
        raise ValueError("an index is not stored for a different citation")
    if body is None or body.strip() == "":
        raise ValueError("the page has no index value")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("the index is not a traded price")
    if permits_financial_use not in (None, False) or class_c_policy not in (None, CLASS_C_POLICY):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    stored = _index(body)
    stored["citation_url"] = FAO_FFPI_URL
    stored["permits_financial_use"] = False
    stored["class_c_policy"] = CLASS_C_POLICY
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
