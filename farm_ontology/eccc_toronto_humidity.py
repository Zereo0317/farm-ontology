"""Toronto climate-normal relative humidity, copied from the live page.

The page opened on 17 Nov 2026 is the 1991 to 2020 Canadian Climate Normals
station page for TORONTO (CITY), ONTARIO:

https://climate.weather.gc.ca/climate_normals/results_1991_2020_e.html?searchType=stnName_1991&txtStationName_1991=Toronto&searchMethod=begins&txtCentralLatMin=0&txtCentralLatSec=0&txtCentralLongMin=0&txtCentralLongSec=0&climate_id=6158350&dispBack=0

The row "Average Relative Humidity - 0600LST (%)" prints 77.5 in the Jan
column. Its code cell prints D, and the legend prints "D = At least 15 years".
The other month columns on that row, and the month columns on
"Average Relative Humidity - 1500LST (%)", are stored as the percents the
page prints, with the month labels the table prints. The Year column is not
stored. Vapour pressure is not stored.

This is a climate normal, not a Biratori observation, and not a current
reading. It is not calculated from temperature or dewpoint. It is not farm
humidity. It is not a completed harvest.

permits_financial_use stays false. Class C stays closed. A missing citation
writes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

ECCC_TORONTO_HUMIDITY_URL = (
    "https://climate.weather.gc.ca/climate_normals/results_1991_2020_e.html"
    "?searchType=stnName_1991&txtStationName_1991=Toronto&searchMethod=begins"
    "&txtCentralLatMin=0&txtCentralLatSec=0&txtCentralLongMin=0"
    "&txtCentralLongSec=0&climate_id=6158350&dispBack=0"
)

STATION = "TORONTO (CITY)"
PROVINCE = "ONTARIO"
PRODUCT = "1991 to 2020 Canadian Climate Normals Data"
PERIOD = "1991 to 2020"
CODE = "D"
CODE_LEGEND = "D = At least 15 years"
MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)
ROW_0600 = "Average Relative Humidity - 0600LST (%)"
PERCENTS_0600 = (
    77.5,
    76.3,
    73.4,
    70.4,
    73.3,
    76.9,
    79.0,
    82.4,
    84.1,
    82.6,
    78.9,
    79.3,
)
ROW_1500 = "Average Relative Humidity - 1500LST (%)"
PERCENTS_1500 = (
    68.0,
    65.4,
    58.5,
    53.4,
    53.1,
    55.2,
    54.3,
    56.7,
    59.6,
    65.0,
    67.1,
    70.9,
)

FORBIDDEN_LABELS = frozenset(
    {
        "farm humidity",
        "biratori",
        "current reading",
        "dewpoint",
        "temperature",
        "yield",
        "price",
        "trade",
        "harvest",
        "completed harvest",
    }
)


def _row(label: str, percents: tuple[float, ...]) -> dict[str, object]:
    return {
        "label": label,
        "code": CODE,
        "code_legend": CODE_LEGEND,
        "months": [
            {"month": month, "percent": percent}
            for month, percent in zip(MONTHS, percents, strict=True)
        ],
    }


def record_eccc_toronto_humidity(
    path: Path,
    citation_url: str | None,
    *,
    station: str | None = None,
    province: str | None = None,
    product: str | None = None,
    period: str | None = None,
    rows: object = None,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed humidity percents, or write nothing."""

    if citation_url is None or citation_url.strip() == "":
        raise ValueError("a climate-normal humidity percent is not stored without a citation_url")
    if citation_url != ECCC_TORONTO_HUMIDITY_URL:
        raise ValueError("a climate-normal humidity percent is not stored for a different citation")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a climate-normal humidity percent is not farm humidity")
    if any(
        value is not None
        for value in (
            station,
            province,
            product,
            period,
            rows,
            permits_financial_use,
            class_c_policy,
        )
    ):
        raise ValueError("a climate-normal humidity percent is not stored with a different value")
    header = {
        "station": STATION,
        "province": PROVINCE,
        "product": PRODUCT,
        "period": PERIOD,
        "rows": [_row(ROW_0600, PERCENTS_0600), _row(ROW_1500, PERCENTS_1500)],
        "citation_url": ECCC_TORONTO_HUMIDITY_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
