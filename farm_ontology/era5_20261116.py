"""ERA5-Land image 20261116 was not found.

The compute for ECMWF/ERA5_LAND/DAILY_AGGR/20261116 returned HTTP 400.
The printed error says that image was not found.
Temperature was not printed.
Wind was not printed.
Dewpoint was not printed.
Relative humidity was not calculated.
The 20261108 values are not stored.
A missing image is not a completed harvest.
permits_financial_use stays false.
Class C stays closed.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

HTTP_STATUS = 400
ERROR = (
    "Image.load: Image asset 'ECMWF/ERA5_LAND/DAILY_AGGR/20261116' "
    "not found (does not exist or caller does not have access)."
)


def record_missing_image(
    directory,
    *,
    http_status=None,
    error=None,
    value=None,
    permits_financial_use=None,
    class_c_policy=None,
) -> dict:
    if http_status != HTTP_STATUS:
        raise ValueError("http_status is not the printed status")
    if error != ERROR:
        raise ValueError("error is not the printed error")
    if value is not None:
        raise ValueError("a missing image has no band value")
    if permits_financial_use is not None:
        raise ValueError("permits_financial_use stays false")
    if class_c_policy is not None:
        raise ValueError("class C stays closed")
    header = {
        "http_status": HTTP_STATUS,
        "error": ERROR,
        "permits_financial_use": False,
        "class_c_policy": "closed",
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "era5-20261116.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
