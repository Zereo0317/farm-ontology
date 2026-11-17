"""Finance gate. It does not fetch, and it stores no price, yield, or trade.

The gate returns closed unless three records all exist: a license page
that loaded (HTTP success, not a 403 body), license text that permits
storing settlement prices, and one settlement print with a citation_url.
None of those records exist. permits_financial_use stays false. Class C
stays closed. This module does not request a license PDF.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

OPEN_CONDITION = (
    "The gate returns open only when three records all exist: "
    "a license page that loaded (HTTP success, not a 403 body), "
    "license text that permits storing settlement prices, "
    "and one settlement print with a citation_url."
)

_403_BODY_MARKERS = (
    "403 forbidden",
    "http 403",
    "status code 403",
    "<title>403",
)


def _license_page_loaded(record) -> bool:
    if not isinstance(record, dict):
        return False
    status = record.get("http_status")
    if not isinstance(status, int) or status < 200 or status > 299:
        return False
    body = record.get("body")
    if not isinstance(body, str) or body.strip() == "":
        return False
    folded = " ".join(body.split()).lower()
    return not any(marker in folded for marker in _403_BODY_MARKERS)


def _license_text_permits(record) -> bool:
    if not isinstance(record, dict):
        return False
    text = record.get("text")
    if not isinstance(text, str) or text.strip() == "":
        return False
    return record.get("permits_storing_settlement_prices") is True


def _settlement_print(record) -> bool:
    if not isinstance(record, dict):
        return False
    if record.get("kind") != "settlement":
        return False
    citation = record.get("citation_url")
    return isinstance(citation, str) and citation.strip() != ""


def gate_status(records=None) -> str:
    """Return open only when all three records exist. Otherwise return closed."""

    if not isinstance(records, dict):
        return "closed"
    loaded = _license_page_loaded(records.get("license_page"))
    permitted = _license_text_permits(records.get("license_text"))
    printed = _settlement_print(records.get("settlement"))
    if loaded and permitted and printed:
        return "open"
    return "closed"


def record_finance_gate(
    path: Path,
    records=None,
    *,
    price: object = None,
    yield_value: object = None,
    trade: object = None,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> dict:
    """Write the closed gate, or write nothing when asked to store a figure."""

    if any(item is not None for item in (price, yield_value, trade)):
        raise ValueError("the finance gate writes no price, yield, or trade")
    if label is not None and label.strip().lower() in {"price", "yield", "trade", "settlement"}:
        raise ValueError("the finance gate writes no price, yield, or trade")
    if permits_financial_use not in (None, False):
        raise ValueError("permits_financial_use stays false")
    if class_c_policy not in (None, CLASS_C_POLICY):
        raise ValueError("Class C stays closed")
    body = {
        "gate": gate_status(records),
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(body, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return body
