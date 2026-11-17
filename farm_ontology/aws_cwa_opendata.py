"""AWS open-data registry header for CWA.

The page https://registry.opendata.aws/cwa_opendata/ was fetched.
The final URL is https://registry.opendata.aws/cwa_opendata/.
The citation is the URL that was fetched.
https://registry.opendata.aws/cwa_opendata is not the citation.
https://registry.opendata.aws/ is not the citation.
http://data.gov.tw/license is not the citation.
https://data.gov.tw/dataset/58977 is not the citation.
The publisher is Central Weather Administration.
Registry of Open Data on AWS is the site name, not the publisher.
The product is Central Weather Administration OpenData.
The document title appends Registry of Open Data on AWS.
Various kinds of weather raw data and charts is the description, not one kind.
climate, earth observation, earthquakes, satellite imagery, and weather are tags, not a kind.
Kind was not printed.
Data is updated as soon as newer one is available. That sentence is the update frequency, not the period.
DATE is a placeholder, not a period.
Period was not printed.
Unit was not printed.
ap-northeast-1 is the bucket region, not an area.
Area was not printed.
The licence is http://data.gov.tw/license.
The licence page was not opened.
CWA data lake is a resource description, not the product.
S3 Bucket is a resource type, not the kind.
The ARN arn:aws:s3:::cwaopendata is not stored.
This page is not the data.gov.tw WRF header.
Do not store a rainfall amount.
Do not store a temperature.
Do not store a yield.
Do not store a price.
Do not store a trade.
A forecast is not a completed harvest.
permits_financial_use stays false.
Class C stays closed.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

AWS_CWA_OPENDATA_URL = "https://registry.opendata.aws/cwa_opendata/"

PUBLISHER = "Central Weather Administration"
PRODUCT = "Central Weather Administration OpenData"
LICENCE = "http://data.gov.tw/license"
FORBIDDEN_LABELS = frozenset({
    "yield",
    "price",
    "trade",
    "rainfall",
    "rainfall amount",
    "temperature",
    "completed harvest",
    "forecast",
    "date",
    "settlement",
})


def _stores_figure(label) -> bool:
    return any(character.isdigit() for character in str(label))


def record_series_header(
    directory,
    *,
    citation_url=None,
    label=None,
    period=None,
    unit=None,
    administrative_area=None,
    kind=None,
    licence=None,
    value=None,
    permits_financial_use=None,
    class_c_policy=None,
) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and (
        str(label).strip().lower() in FORBIDDEN_LABELS or _stores_figure(label)
    ):
        raise ValueError(
            "a catalog header is not a yield, a price, a trade, a "
            "rainfall amount, a temperature, or a completed harvest, "
            "and a figure is not stored"
        )
    if period is not None:
        raise ValueError("period was not printed")
    if unit is not None:
        raise ValueError("unit was not printed")
    if administrative_area is not None:
        raise ValueError("area was not printed")
    if kind is not None:
        raise ValueError("kind was not printed")
    if licence is not None:
        raise ValueError("licence is not replaced")
    if value is not None:
        raise ValueError("a figure is not stored")
    if permits_financial_use is not None:
        raise ValueError("permits_financial_use stays false")
    if class_c_policy is not None:
        raise ValueError("class C stays closed")
    citation = str(citation_url).strip()
    if citation != AWS_CWA_OPENDATA_URL:
        raise ValueError("citation_url is not the fetched page")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "citation_url": citation,
        "licence": LICENCE,
        "permits_financial_use": False,
        "class_c_policy": "closed",
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "aws-cwa-opendata.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
