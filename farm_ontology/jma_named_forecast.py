"""JMA forecast for a link that names 平取 or 日高.

The start page is the local-information citation. A link is followed
only when that page prints the name 平取 or 日高 on the link. The English
region name Hidaka and an area code are not that link. A forecast is
stored only when the followed page prints one value for that named area
together with a period. No temperature, rainfall amount, or area code
is invented. A forecast is not a completed harvest and not a trade.
permits_financial_use stays false. permits_financial_use_test is not
set. Class C stays closed. This module does not change the header
function that rejects a figure. This module is not called from a field
save.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from farm_ontology.jma_local import JMA_LOCAL_URL
from farm_ontology.policy import CLASS_C_POLICY

_AREA = "平取|日高"
_ANCHOR = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.IGNORECASE | re.DOTALL)
_HREF = re.compile(r"""href=["']([^"']+)["']""", re.IGNORECASE)
_FORECAST = re.compile(
    rf"({_AREA})\s+forecast is (\d{{1,2}}(?:\.\d+)?)\s+for\s+"
    r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{4})"
)
FORBIDDEN_LABELS = frozenset(
    {
        "trade",
        "completed harvest",
        "harvest",
        "yield",
        "temperature",
        "rainfall amount",
        "area code",
    }
)


def _plain(body: str) -> str:
    text = re.sub(r"<[^>]+>", " ", body.replace("\xa0", " "))
    return " ".join(text.split())


def _named_links(body: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for match in _ANCHOR.finditer(body):
        attrs, inner = match.group(1), match.group(2)
        href_match = _HREF.search(attrs)
        href = href_match.group(1) if href_match else ""
        area = None
        for name in ("平取", "日高"):
            if name in inner or name in href:
                area = name
                break
        if area and href:
            found.append((href, area))
    return found


def _one_forecast(body: str, area: str) -> tuple[str, str]:
    found = [item for item in _FORECAST.findall(_plain(body)) if item[0] == area]
    if len(found) != 1:
        raise ValueError("the page prints no forecast value for the named area")
    _area, value, period = found[0]
    if len(value) >= 5:
        raise ValueError("an area code is not a forecast value")
    return value, period


def record_named_forecast(
    path: Path,
    citation_url: str | None,
    body: str | None = None,
    *,
    followed_url: str | None = None,
    followed_body: str | None = None,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    permits_financial_use_test: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write one printed forecast, or write nothing."""

    if citation_url != JMA_LOCAL_URL:
        raise ValueError("the start page is the local-information citation")
    if body is None or body.strip() == "":
        raise ValueError("the page prints no link naming 平取 or 日高")
    if label is not None and (
        label.strip().lower() in FORBIDDEN_LABELS
        or any(character.isdigit() for character in label)
    ):
        raise ValueError("a forecast is not a completed harvest and not a trade")
    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    if permits_financial_use_test is not None:
        raise ValueError("permits_financial_use_test is not set")
    links = _named_links(body)
    if len(links) != 1:
        raise ValueError("the page prints no link naming 平取 or 日高")
    href, area = links[0]
    if followed_url != href or followed_body is None or followed_body.strip() == "":
        raise ValueError("the named page was not opened")
    value, period = _one_forecast(followed_body, area)
    stored = {
        "value": value,
        "area": area,
        "period": period,
        "citation_url": href,
        "kind": "forecast",
        "label": "forecast",
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
