"""Refusal for the Biratori bundle.

The bundle records dataset, image id, date, band, and value.
It has no citation_url on any record.
A record without a citation_url is not stored.
Do not invent a catalog URL.
permits_financial_use stays false.
No yield, price, or trade is stored.
This module is not called from a field save.
"""

from __future__ import annotations


def record_bundle_observations(directory, records) -> dict:
    del directory
    if not isinstance(records, list) or not records:
        raise ValueError("citation_url is required")
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("citation_url is required")
        citation = record.get("citation_url")
        if citation is None or str(citation).strip() == "":
            raise ValueError("citation_url is required")
    raise ValueError("a bundle value is not stored")
