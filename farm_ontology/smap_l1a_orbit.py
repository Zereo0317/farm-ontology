"""SMAP L1A orbit times from the cited ISO metadata.

The citation is the ISO XML already cited.
https://nsidc.org/data/smap is not the citation.
https://smap.jpl.nasa.gov/ is not the citation.
The cited URL returns 303.
The followed body is the ISO XML.
The redirect URL is not stored.
halfOrbitStartDateTime prints 2026-11-16T22:00:29.000Z.
halfOrbitEndDateTime prints 2026-11-16T22:49:43.000Z.
gml:beginPosition prints 2026-11-16T21:58:29.862Z.
gml:endPosition prints 2026-11-16T22:51:51.299Z.
The temporal extent is not the orbit time.
A soil-moisture pixel is not stored.
No brightness temperature is stored.
permits_financial_use stays false.
Class C stays closed.
A missing citation writes nothing.
A body with no orbit time writes nothing.
This module is not called from a field save.
"""

from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

SMAP_L1A_ORBIT_URL = (
    "https://data.nsidc.earthdatacloud.nasa.gov/nsidc-cumulus-prod-public/"
    "SMAP/SPL1AP/002/2026/11/16/"
    "SMAP_L1A_RADIOMETER_62995_D_20261116T215830_R19240_001.h5.iso.xml"
)

ORBIT_START_NAME = "halfOrbitStartDateTime"
ORBIT_END_NAME = "halfOrbitEndDateTime"
ORBIT_START = "2026-11-16T22:00:29.000Z"
ORBIT_END = "2026-11-16T22:49:43.000Z"
TEMPORAL_BEGIN = "2026-11-16T21:58:29.862Z"
TEMPORAL_END = "2026-11-16T22:51:51.299Z"
_TIME = re.compile(r"\d{4}-\d{2}-\d{2}T")
FORBIDDEN_LABELS = frozenset({
    "pixel",
    "soil moisture",
    "soil-moisture pixel",
    "brightness temperature",
    "yield",
    "price",
    "trade",
    "settlement",
    "harvest",
    "completed harvest",
})


def _open(request):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_default_certs()
    return urllib.request.urlopen(request, timeout=90, context=context)


def _value_follows(text: str, name: str, value: str) -> bool:
    marker = f">{name}<"
    index = text.find(marker)
    if index < 0:
        return False
    found = text.find(value, index)
    if found < 0:
        return False
    between = text[index:found]
    if _TIME.search(between):
        return False
    needle = f"<gco:CharacterString>{value}</gco:CharacterString>"
    return needle in text[found - len("<gco:CharacterString>"):found + len(value) + 32]


def _position_prints(text: str, tag: str, value: str) -> bool:
    return f">{value}</gml:{tag}>" in text


def fetch_orbit_xml(citation_url: str) -> bytes:
    request = urllib.request.Request(
        citation_url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/xml,text/xml,*/*",
        },
    )
    try:
        with _open(request) as response:
            status = response.status
            body = response.read()
    except urllib.error.HTTPError as error:
        raise ValueError("the orbit time was not stored") from error
    if status != 200 or not body.startswith(b"<?xml"):
        raise ValueError("the orbit time was not stored")
    text = body.decode("utf-8")
    if not _value_follows(text, ORBIT_START_NAME, ORBIT_START):
        raise ValueError("the orbit time was not stored")
    if not _value_follows(text, ORBIT_END_NAME, ORBIT_END):
        raise ValueError("the orbit time was not stored")
    if not _position_prints(text, "beginPosition", TEMPORAL_BEGIN):
        raise ValueError("the temporal extent was not stored")
    if not _position_prints(text, "endPosition", TEMPORAL_END):
        raise ValueError("the temporal extent was not stored")
    return body


def record_orbit_times(
    directory,
    *,
    citation_url=None,
    label=None,
    orbit_start=None,
    orbit_end=None,
    temporal_begin=None,
    temporal_end=None,
    permits_financial_use=None,
    class_c_policy=None,
    pixel=None,
    soil_moisture=None,
) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("an orbit time is not a soil-moisture pixel")
    if pixel is not None or soil_moisture is not None:
        raise ValueError("a soil-moisture pixel is not stored")
    if permits_financial_use is not None:
        raise ValueError("permits_financial_use stays false")
    if class_c_policy is not None:
        raise ValueError("class C stays closed")
    if orbit_start is not None or orbit_end is not None:
        raise ValueError("an orbit time is not replaced")
    if temporal_begin is not None or temporal_end is not None:
        raise ValueError("a temporal extent is not replaced")
    citation = str(citation_url).strip()
    if citation != SMAP_L1A_ORBIT_URL:
        raise ValueError("citation_url is not the cited ISO XML")
    fetch_orbit_xml(citation)
    header = {
        "citation_url": citation,
        "orbit_start": ORBIT_START,
        "orbit_end": ORBIT_END,
        "temporal_begin": TEMPORAL_BEGIN,
        "temporal_end": TEMPORAL_END,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "smap-l1a-orbit.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
