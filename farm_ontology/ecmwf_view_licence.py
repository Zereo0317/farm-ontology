"""ECMWF open-data redistribution sentence and View licence name.

The stored citation stays on
https://www.ecmwf.int/en/forecasts/datasets/open-data.
That page prints: This means that the data may be redistributed and
used commercially, subject to appropriate attribution.
Its View licence target is
http://apps.ecmwf.int/datasets/licences/general.
Opening that target follows to the same licence page. The licence
statement there prints the name Creative Commons Attribution 4.0
International (CC BY 4.0). The stored record is that sentence and that
name. A GRIB file, a forecast file, the Service Charges page, and the
Service Agreement page were not opened. No forecast value is stored.
A forecast is not a completed harvest and not a trade. Commercial
redistribution is not a right to trade. permits_financial_use stays
false. Class C stays closed. This module is not called from a field save.
"""

from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path

from farm_ontology.ecmwf_open_data import ECMWF_OPEN_DATA_URL
from farm_ontology.policy import CLASS_C_POLICY

VIEW_LICENCE_URL = "http://apps.ecmwf.int/datasets/licences/general"
_ACCEPTED_LICENCE_URLS = frozenset(
    {
        VIEW_LICENCE_URL,
        "https://apps.ecmwf.int/datasets/licences/general/",
        "https://apps.ecmwf.int:443/datasets/licences/general/",
    }
)
_SENTENCE = re.compile(
    r"[^.]*redistributed and used commercially[^.]*attribution[^.]*\."
)
_LICENCE_NAME = re.compile(r"published under a (.+?\))")
_LICENCE_NAME_PLAIN = re.compile(r"published under a ([^.]+)")
FORBIDDEN_LABELS = frozenset(
    {
        "trade",
        "completed harvest",
        "harvest",
        "forecast",
        "forecast value",
        "settlement",
        "yield",
        "price",
    }
)


_EXACT_SENTENCE = (
    "This means that the data may be redistributed and used commercially, "
    "subject to appropriate attribution."
)


def _plain(body: str) -> str:
    text = unescape(body).replace("\xa0", " ")
    text = re.sub(r"<[^>]+>", " ", text)
    text = " ".join(text.split())
    return re.sub(r"\s+([.,;:])", r"\1", text)


def _printed_sentence(body: str) -> str:
    plain = _plain(body)
    if _EXACT_SENTENCE in plain:
        return _EXACT_SENTENCE
    match = _SENTENCE.search(plain)
    if match is None or '"' in match.group(0):
        raise ValueError("the open-data page prints no redistribution sentence")
    return match.group(0).strip()


def _printed_licence_name(body: str) -> str:
    plain = _plain(body)
    match = _LICENCE_NAME.search(plain) or _LICENCE_NAME_PLAIN.search(plain)
    if match is None:
        raise ValueError("the View licence page prints no licence name")
    return match.group(1).strip()


def record_view_licence(
    path: Path,
    citation_url: str | None,
    overview: str | None = None,
    licence_body: str | None = None,
    *,
    licence_url: str | None = None,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed sentence and licence name, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("the sentence is not stored without the open-data page")
    if citation_url != ECMWF_OPEN_DATA_URL:
        raise ValueError("the sentence is not stored for a different citation")
    if licence_url not in _ACCEPTED_LICENCE_URLS:
        raise ValueError("only the View licence target is opened")
    if overview is None or overview.strip() == "":
        raise ValueError("the open-data page prints no redistribution sentence")
    if licence_body is None or licence_body.strip() == "":
        raise ValueError("the View licence page prints no licence name")
    if label is not None and (
        label.strip().lower() in FORBIDDEN_LABELS
        or any(character.isdigit() for character in label)
    ):
        raise ValueError(
            "a forecast is not a completed harvest and not a trade"
        )
    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    stored = {
        "sentence": _printed_sentence(overview),
        "licence_name": _printed_licence_name(licence_body),
        "citation_url": ECMWF_OPEN_DATA_URL,
        "licence_page": VIEW_LICENCE_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
