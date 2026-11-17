"""Current USGS instantaneous streamflow for the site cited in the Potomac record.

The refetch of

https://waterservices.usgs.gov/nwis/iv/?format=json&sites=01646500&parameterCd=00060,00065&siteStatus=all

returned HTTP 200. Parameter 00060 prints value 1600, unit ft3/s, and
time 2026-11-16T20:50:00.000-05:00 for POTOMAC RIVER NEAR WASH, DC
LITTLE FALLS PUMP STA. The stored reading is that printed value, unit,
and time. A request that fails, or a body with no value, unit, or time,
writes nothing. No second site is added.
permits_financial_use stays false. Class C stays closed.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

USGS_URL = (
    "https://waterservices.usgs.gov/nwis/iv/?format=json&sites=01646500"
    "&parameterCd=00060,00065&siteStatus=all"
)
SITE_CODE = "01646500"
PARAMETER = "00060"

FORBIDDEN_LABELS = frozenset(
    {
        "settlement",
        "trade",
        "yield",
        "price",
        "harvest",
        "completed harvest",
    }
)


def _printed_value(text: str):
    if text.isdigit():
        return int(text)
    return text


def _streamflow(body: str) -> dict:
    try:
        payload = json.loads(body)
        series = payload["value"]["timeSeries"]
    except (TypeError, KeyError, json.JSONDecodeError) as exc:
        raise ValueError("the response body has no streamflow value") from exc
    found = None
    for item in series:
        site_codes = item.get("sourceInfo", {}).get("siteCode") or []
        if not site_codes or site_codes[0].get("value") != SITE_CODE:
            continue
        variable_codes = item.get("variable", {}).get("variableCode") or []
        if not variable_codes or variable_codes[0].get("value") != PARAMETER:
            continue
        unit = (item.get("variable", {}).get("unit") or {}).get("unitCode")
        readings = (item.get("values") or [{}])[0].get("value") or []
        if not readings:
            continue
        latest = readings[-1]
        value = str(latest.get("value") or "").strip()
        observed_at = str(latest.get("dateTime") or "").strip()
        if value == "" or not unit or observed_at == "":
            continue
        found = {
            "site": item.get("sourceInfo", {}).get("siteName"),
            "parameter": PARAMETER,
            "value": _printed_value(value),
            "unit": unit,
            "observed_at": observed_at,
        }
    if found is None or not found.get("site"):
        raise ValueError("the response body has no streamflow value")
    return found


def record_usgs_current(
    path: Path,
    citation_url: str | None,
    body: str | None = None,
    *,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed current reading, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("a reading is not stored without a response")
    if citation_url != USGS_URL:
        raise ValueError("a reading is not stored for a different citation")
    if body is None or body.strip() == "":
        raise ValueError("the response body has no streamflow value")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a streamflow reading is not a settlement or a trade")
    if permits_financial_use not in (None, False) or class_c_policy not in (None, CLASS_C_POLICY):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    reading = _streamflow(body)
    reading["citation_url"] = USGS_URL
    reading["permits_financial_use"] = False
    reading["class_c_policy"] = CLASS_C_POLICY
    path.write_text(
        json.dumps(reading, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
