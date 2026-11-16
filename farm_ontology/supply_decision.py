"""Decision from stored supply headers.

The statement uses header records this package already stores. It reads
publisher, product, administrative_area, citation_url, kind, and
permits_financial_use. Period and unit are copied when the stored
header has them and are not invented when it does not. It does not
fetch the network and it does not invent a number. A forecast is not a completed harvest. An
index is not a quantity of goods. A licence, terms, disclaimer, or
methodology header is not a right to trade. permits_financial_use stays
false. This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

HEADER_FIELDS = (
    "publisher",
    "product",
    "period",
    "unit",
    "administrative_area",
    "citation_url",
    "kind",
    "permits_financial_use",
)
_OPTIONAL_FIELDS = frozenset({"period", "unit"})
SUBJECTS = (
    "food supply",
    "oil supply",
    "manufacturing supply",
    "farmer",
)
REFUSED_ASKS = frozenset({
    "yield",
    "price",
    "trade",
    "hedge",
    "position",
})
_RIGHT_TO_TRADE = (
    "A licence, terms, disclaimer, or methodology header is not a right to trade."
)


def _stored_header(header) -> dict:
    if not isinstance(header, dict):
        raise ValueError("a stored header is required")
    missing = [
        name
        for name in HEADER_FIELDS
        if name not in header and name not in _OPTIONAL_FIELDS
    ]
    if missing:
        raise ValueError("a stored header field is missing")
    stored = {name: header[name] for name in HEADER_FIELDS if name in header}
    if stored["permits_financial_use"] is not False:
        raise ValueError("permits_financial_use stays false")
    return stored


def _rule(kind) -> str:
    text = str(kind).strip().lower()
    if text == "forecast":
        return "A forecast is not a completed harvest."
    if text == "index":
        return "An index is not a quantity of goods."
    if any(word in text for word in ("licence", "license", "terms", "disclaimer", "methodology")):
        return _RIGHT_TO_TRADE
    return ""


def decision_text(records) -> str:
    lines = []
    for record in records:
        header = record["header"]
        subject = record["subject"]
        line = (
            f"{subject}: {header['publisher']}; {header['product']}; "
            f"kind {header['kind']}."
        )
        if subject == "farmer":
            line += f" administrative_area {header['administrative_area']}."
        rule = _rule(header["kind"])
        if rule:
            line += f" {rule}"
        line += " permits_financial_use is false."
        lines.append(line)
    lines.append(
        "A forecast is not a completed harvest. "
        "An index is not a quantity of goods. "
        + _RIGHT_TO_TRADE
    )
    lines.append("permits_financial_use is false.")
    return "\n".join(lines) + "\n"


def record_supply_decision(directory, *, records, ask=None) -> dict:
    if ask is not None and str(ask).strip().lower() in REFUSED_ASKS:
        raise ValueError(
            "a yield, a price, a trade, a hedge, or a position is not stored"
        )
    if not records:
        raise ValueError(
            "the decision is for food supply, oil supply, manufacturing supply, and a farmer"
        )
    stored_records = []
    for record in records:
        subject = record.get("subject")
        if subject not in SUBJECTS:
            raise ValueError(
                "the decision is for food supply, oil supply, manufacturing supply, and a farmer"
            )
        stored_records.append({
            "subject": subject,
            "header": _stored_header(record.get("header")),
        })
    seen = {record["subject"] for record in stored_records}
    if set(SUBJECTS) != seen:
        raise ValueError(
            "the decision is for food supply, oil supply, manufacturing supply, and a farmer"
        )
    text = decision_text(stored_records)
    body = {
        "decision": text,
        "permits_financial_use": False,
        "records": stored_records,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "supply-decision.json"
    path.write_text(
        json.dumps(body, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "decision": text, "permits_financial_use": False}
