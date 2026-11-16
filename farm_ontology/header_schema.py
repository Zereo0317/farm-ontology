"""Schemas for reading one stored header.

The reader returns the kind already stored on the header. It does not
fetch the network and it does not invent a number. A forecast is not a
completed harvest. An index is not a quantity of goods.
permits_financial_use stays false.
"""

from __future__ import annotations

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
_TEXT_FIELDS = HEADER_FIELDS[:-1]
_REFUSED = frozenset({"yield", "price", "trade"})
FORECAST_SENTENCE = "A forecast is not a completed harvest."
INDEX_SENTENCE = "An index is not a quantity of goods."

STORED_HEADER_SCHEMA = {
    "type": "object",
    "description": (
        "A stored header. The reader returns the stored kind. "
        + FORECAST_SENTENCE
        + " "
        + INDEX_SENTENCE
        + " permits_financial_use stays false."
    ),
    "required": list(HEADER_FIELDS),
    "properties": {
        "publisher": {"type": "string"},
        "product": {"type": "string"},
        "period": {"type": "string"},
        "unit": {"type": "string"},
        "administrative_area": {"type": "string"},
        "citation_url": {"type": "string"},
        "kind": {"type": "string"},
        "permits_financial_use": {"type": "boolean", "const": False},
    },
    "additionalProperties": True,
}

STORED_KIND_SCHEMA = {
    "type": "object",
    "description": FORECAST_SENTENCE + " " + INDEX_SENTENCE,
    "additionalProperties": False,
    "required": ["kind", "permits_financial_use", "statement"],
    "properties": {
        "kind": {"type": "string"},
        "permits_financial_use": {"type": "boolean", "const": False},
        "statement": {"type": "string"},
    },
}

PAGE_API_SCHEMA = {
    "read_header": {
        "description": (
            "Read a stored header and return its stored kind. "
            + FORECAST_SENTENCE
            + " "
            + INDEX_SENTENCE
        ),
        "input": {
            "type": "object",
            "additionalProperties": False,
            "required": ["op", "header"],
            "properties": {
                "op": {"const": "read_header"},
                "header": STORED_HEADER_SCHEMA,
            },
        },
        "output": STORED_KIND_SCHEMA,
    },
    "stored_header": STORED_HEADER_SCHEMA,
    "stored_kind": STORED_KIND_SCHEMA,
}


def read_stored_header(header) -> dict:
    if not isinstance(header, dict):
        raise ValueError("a stored header is required")
    refused = [key for key in header if str(key).strip().lower() in _REFUSED]
    if refused:
        raise ValueError("a yield, a price, or a trade is not stored")
    missing = [name for name in HEADER_FIELDS if name not in header]
    if missing:
        raise ValueError("a stored header field is missing")
    if header["permits_financial_use"] is not False:
        raise ValueError("permits_financial_use stays false")
    for name in _TEXT_FIELDS:
        value = header[name]
        if not isinstance(value, str) or value.strip() == "":
            raise ValueError("a stored header field is missing")
    kind = header["kind"]
    return {
        "kind": kind,
        "permits_financial_use": False,
        "statement": f"{kind}. {FORECAST_SENTENCE} {INDEX_SENTENCE}",
    }
