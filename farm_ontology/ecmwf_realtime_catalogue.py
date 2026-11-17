"""ECMWF real-time catalogue.

The open-data page

https://www.ecmwf.int/en/forecasts/datasets/open-data

links one catalogue, Catalogue of ECMWF Real-time Products:

https://www.ecmwf.int/en/forecasts/datasets/catalogue-ecmwf-real-time-products

That catalogue lists product sets and forecast horizons. It does not
print a parameter, a time, and an area together with a forecast value.
A GRIB file and a forecast file were not opened. A latitude or
longitude is not chosen. A forecast value is stored only when the
catalogue page itself prints those four together, and only then with
the attribution sentence the open-data page prints. A forecast is not
a completed harvest and not a trade. Commercial redistribution is not
a right to trade. permits_financial_use stays false. Class C stays
closed. This module is not called from a field save.
"""

from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path

from farm_ontology.ecmwf_open_data import ECMWF_OPEN_DATA_URL
from farm_ontology.policy import CLASS_C_POLICY

CATALOGUE_URL = (
    "https://www.ecmwf.int/en/forecasts/datasets/"
    "catalogue-ecmwf-real-time-products"
)
ATTRIBUTION_SENTENCE = (
    "This means that the data may be redistributed and used commercially, "
    "subject to appropriate attribution."
)
FORBIDDEN_LABELS = frozenset(
    {
        "trade",
        "completed harvest",
        "harvest",
        "settlement",
        "yield",
        "price",
    }
)
_PARAMETER = re.compile(
    r"\b((?:2\s*m\s+)?(?:temperature|precipitation|wind|pressure|humidity))\b",
    re.IGNORECASE,
)
_TIME = re.compile(
    r"\b(\d{1,2}:\d{2}\s*UTC(?:\s+on\s+\d{1,2}\s+"
    r"(?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+\d{4})?)\b",
    re.IGNORECASE,
)
_AREA = re.compile(r"\b(?:for|over|in)\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)\b")
_VALUE = re.compile(r"\b(\d+(?:\.\d+)?)\s*(°C|m/s|mm|hPa)\b")
_LATLON = re.compile(r"\b\d+(?:\.\d+)?\s*[NSEW]\b")


def _plain(body: str) -> str:
    text = unescape(body).replace("\xa0", " ")
    text = re.sub(r"<[^>]+>", " ", text)
    text = " ".join(text.split())
    return re.sub(r"\s+([.,;:])", r"\1", text)


def _sentences(plain: str) -> list[str]:
    protected = re.sub(r"(\d)\.(\d)", r"\1§\2", plain)
    parts = re.split(r"(?<=[.!?])\s+", protected)
    return [part.replace("§", ".").strip() for part in parts if part.strip()]


def _printed_forecasts(body: str) -> list[dict[str, str]]:
    found = []
    for sentence in _sentences(_plain(body)):
        if _LATLON.search(sentence):
            continue
        parameters = list(_PARAMETER.finditer(sentence))
        times = list(_TIME.finditer(sentence))
        areas = list(_AREA.finditer(sentence))
        values = list(_VALUE.finditer(sentence))
        if not (len(parameters) == 1 and len(times) == 1 and len(areas) == 1 and len(values) == 1):
            continue
        area = areas[0].group(1).strip()
        if any(character.isdigit() for character in area):
            continue
        number, unit = values[0].group(1), values[0].group(2)
        found.append(
            {
                "parameter": parameters[0].group(1),
                "time": times[0].group(1),
                "area": area,
                "value": f"{number} {unit}",
            }
        )
    return found


def record_catalogue_forecast(
    path: Path,
    citation_url: str | None,
    overview: str | None = None,
    catalogue_body: str | None = None,
    *,
    catalogue_url: str | None = None,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write one printed forecast with the attribution sentence, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("a forecast is not stored without the open-data page")
    if citation_url != ECMWF_OPEN_DATA_URL:
        raise ValueError("a forecast is not stored for a different citation")
    if catalogue_url != CATALOGUE_URL:
        raise ValueError("only the linked catalogue page is opened")
    if overview is None or catalogue_body is None:
        raise ValueError("the catalogue page prints no forecast value")
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
    forecasts = _printed_forecasts(catalogue_body)
    if len(forecasts) != 1:
        raise ValueError("the catalogue page prints no forecast value")
    if ATTRIBUTION_SENTENCE not in _plain(overview):
        raise ValueError("the attribution sentence is not printed")
    forecast = forecasts[0]
    stored = {
        "sentence": ATTRIBUTION_SENTENCE,
        "parameter": forecast["parameter"],
        "time": forecast["time"],
        "area": forecast["area"],
        "value": forecast["value"],
        "kind": "published_forecast",
        "citation_url": ECMWF_OPEN_DATA_URL,
        "catalogue_page": CATALOGUE_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
