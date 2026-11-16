"""IMF Primary Commodity Price System header.

One compilation from the FAQ page that was already opened. The stored
record is the printed header plus the copyright note that the special
terms were only partly rendered. Those terms are not permission to
trade. The series is not given a public-domain label. The FAQ says the
IMF does not report futures prices in this file. Prices are period
averages, are not seasonally adjusted, and are revised when sources
revise, usually the latest few months. Where a release lags, the IMF
inserts a random-walk estimate and later replaces it; that fill is not
stored as an observation. Two-year price projections are in the World
Economic Outlook, not in this price file, and they are not stored or
scored. The IMF's own phrase "benchmark prices" stays in the unit
text. This record is not a financial benchmark. It does not store a
price or an index level. This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

IMF_PCPS_URL = "https://www.imf.org/external/np/res/commod/faq/index.htm"

PUBLISHER = "International Monetary Fund"
PRODUCT = "Primary Commodity Price System"
PERIOD = (
    "the FAQ, last updated 21 November 2025, says tables are annual, "
    "quarterly, monthly, and weekly; monthly figures are updated in the "
    "first full week of the month; the FAQ says some prices start in 1980 "
    "and index coverage starts in 1992; the technical note says the "
    "all-commodity index starts in January 1992"
)
UNIT = (
    "benchmark prices and indexes for energy, agriculture, fertilizers, and "
    "metals, as the IMF names them; the all-commodity index is monthly, "
    "quarterly, and annual, weighted by 2014-2016 world import shares, and "
    "is 2016=100; group indexes include food, agricultural raw materials, "
    "industrial inputs (agricultural raw materials and metals), and fuel; "
    "the petroleum index is the simple average of Dated Brent, West Texas "
    "Intermediate, and Dubai Fateh; no price and no index level is stored"
)
ADMINISTRATIVE_AREA = (
    "the published commodity indexes; the FAQ also describes a commodity "
    "terms-of-trade database for 182 economies from 1962, and that database "
    "is not stored here"
)
KIND = "compilation"
COPYRIGHT_STATEMENT = (
    "The copyright page effective 11 October 2024 says Primary Commodity "
    "Prices are among the statistical data covered by special terms. Those "
    "terms, in the portion rendered, allow users to download, extract, copy, "
    "create derivative works, publish, distribute, and use that data, subject "
    "to conditions the fetch did not fully display. The same page says "
    "systematic reuse of other IMF content needs permission, bulk automated "
    "download is prohibited without permission, and IMF content may not be "
    "used to train large language models without permission. Some statistical "
    "products incorporate third-party information with separate terms. The "
    "special terms were only partly rendered."
)
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "forecast",
    "observation",
    "completed harvest",
    "public domain",
    "benchmark",
})


def record_series_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "a Primary Commodity Price System figure is not a settlement, "
            "a yield, a trade, a forecast, an observation, a completed "
            "harvest, or a benchmark"
        )
    citation = str(citation_url).strip()
    if citation != IMF_PCPS_URL:
        raise ValueError("citation_url is not the opened Primary Commodity Price System FAQ")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "unit": UNIT,
        "administrative_area": ADMINISTRATIVE_AREA,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
        "copyright_statement": COPYRIGHT_STATEMENT,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "pcps.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
