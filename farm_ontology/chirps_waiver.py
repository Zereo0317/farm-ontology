"""CHIRPS public-domain waiver.

The stored citation is

https://www.chc.ucsb.edu/data/chirps.

That page prints: To the extent possible under the law, Pete Peterson
has waived all copyright and related or neighboring rights to CHIRPS.
CHIRPS data is in the public domain as registered with Creative Commons.
The stored record is that sentence. The CHIRPS v3 page was not opened.
A data file was not opened. No rainfall amount is stored. A
public-domain waiver is not a right to trade. The Regents copyright
line is not a grant of financial use. A rainfall estimate is not a
completed harvest. permits_financial_use stays false. Class C stays
closed. This module is not called from a field save.
"""

from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path

from farm_ontology.chirps_rainfall import CHIRPS_RAINFALL_URL
from farm_ontology.policy import CLASS_C_POLICY

WAIVER_SENTENCE = (
    "To the extent possible under the law, Pete Peterson has waived all "
    "copyright and related or neighboring rights to CHIRPS. CHIRPS data is "
    "in the public domain as registered with Creative Commons."
)
_OTHER_WORDING = re.compile(
    r"[^.]*waived all copyright and related or neighboring rights to CHIRPS\.\s+"
    r"[^.]*public domain as registered with Creative Commons\."
)
FORBIDDEN_LABELS = frozenset(
    {
        "trade",
        "completed harvest",
        "harvest",
        "rainfall",
        "rainfall amount",
        "settlement",
        "yield",
        "price",
    }
)


def _plain(body: str) -> str:
    text = unescape(body).replace("\xa0", " ")
    text = re.sub(r"<[^>]+>", " ", text)
    text = " ".join(text.split())
    return re.sub(r"\s+([.,;:])", r"\1", text)


def _printed_sentence(body: str) -> str:
    plain = _plain(body)
    if WAIVER_SENTENCE in plain:
        return WAIVER_SENTENCE
    match = _OTHER_WORDING.search(plain)
    if match is None:
        raise ValueError("the page prints no waiver sentence")
    return match.group(0).strip()


def record_waiver_sentence(
    path: Path,
    citation_url: str | None,
    body: str | None = None,
    *,
    source_url: str | None = None,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the waiver sentence the data page prints, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("a waiver sentence is not stored without the data page")
    if citation_url != CHIRPS_RAINFALL_URL:
        raise ValueError("a waiver sentence is not stored for a different citation")
    if source_url not in (None, CHIRPS_RAINFALL_URL):
        raise ValueError("the CHIRPS v3 page and a data file are not opened")
    if body is None or body.strip() == "":
        raise ValueError("the page prints no waiver sentence")
    if label is not None and (
        label.strip().lower() in FORBIDDEN_LABELS
        or any(character.isdigit() for character in label)
    ):
        raise ValueError("a rainfall estimate is not a completed harvest")
    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    stored = {
        "sentence": _printed_sentence(body),
        "citation_url": CHIRPS_RAINFALL_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
