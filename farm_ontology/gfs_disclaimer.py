"""GFS disclaimer sentence.

The stored citation is

https://www.emc.ncep.noaa.gov/emc/pages/numerical_forecast_systems/gfs.php.

That page links one disclaimer,

https://www.weather.gov/disclaimer.

Under Use of NOAA/NWS Data and Products, that page prints: The
information on National Weather Service (NWS) Web pages are in the
public domain, unless specifically noted otherwise, and may be used
without charge for any lawful purpose so long as you do not claim it
as your own, imply an endorsement, or modify it and present it as
official government material. The stored record is that sentence.
Third-party licence sentences are not stored. No forecast value, grid,
temperature, wind speed, or rainfall amount is stored. A forecast is
not a completed harvest. A public-domain sentence is not a right to
trade. permits_financial_use stays false. Class C stays closed. This
module does not change the header function that rejects a figure. This
module is not called from a field save.
"""

from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path

from farm_ontology.gfs_forecast import GFS_FORECAST_URL
from farm_ontology.policy import CLASS_C_POLICY

DISCLAIMER_URL = "https://www.weather.gov/disclaimer"
DISCLAIMER_SENTENCE = (
    "The information on National Weather Service (NWS) Web pages are in "
    "the public domain, unless specifically noted otherwise, and may be "
    "used without charge for any lawful purpose so long as you do not: "
    "1) claim it is your own (e.g., by claiming copyright for NWS "
    "information -- see below), 2) use it in a manner that implies an "
    "endorsement or affiliation with NOAA/NWS, or 3) modify its content "
    "and then present it as official government material."
)
_OTHER = re.compile(
    r"[^.?!]*\b(?:public domain|under licen[cs]e)\b[^.?!]*[.?!]",
    re.IGNORECASE,
)
FORBIDDEN_LABELS = frozenset(
    {
        "trade",
        "completed harvest",
        "harvest",
        "forecast value",
        "temperature",
        "wind",
        "wind speed",
        "rainfall",
        "rainfall amount",
        "grid",
    }
)


def _plain(body: str) -> str:
    text = unescape(body).replace("\xa0", " ")
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.split())


def _printed_sentence(body: str) -> str:
    plain = _plain(body)
    if DISCLAIMER_SENTENCE in plain:
        return DISCLAIMER_SENTENCE
    found = [match.group(0).strip() for match in _OTHER.finditer(plain)]
    if len(found) != 1:
        raise ValueError("the disclaimer prints no single licence sentence")
    return found[0]


def record_disclaimer_sentence(
    path: Path,
    citation_url: str | None,
    body: str | None = None,
    *,
    disclaimer_url: str | None = None,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the disclaimer sentence, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("a disclaimer sentence is not stored without the forecast page")
    if citation_url != GFS_FORECAST_URL:
        raise ValueError("a disclaimer sentence is not stored for a different citation")
    if disclaimer_url != DISCLAIMER_URL:
        raise ValueError("only the linked disclaimer page is opened")
    if body is None or body.strip() == "":
        raise ValueError("the disclaimer prints no licence sentence")
    if label is not None and (
        label.strip().lower() in FORBIDDEN_LABELS
        or any(character.isdigit() for character in label)
    ):
        raise ValueError("a forecast is not a completed harvest")
    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    stored = {
        "sentence": _printed_sentence(body),
        "citation_url": GFS_FORECAST_URL,
        "disclaimer_page": DISCLAIMER_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
