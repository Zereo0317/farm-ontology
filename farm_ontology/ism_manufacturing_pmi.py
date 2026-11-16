"""ISM Manufacturing PMI header.

One survey from the terms PDF that was already opened. The stored record
is the printed header plus two license statements that were not
reconciled by logging in. They are stored separately and are not one
permission. The citation stays on
https://www.ismworld.org/globalassets/738-terms-and-conditions.pdf.
The branding note that was opened is
https://www.ismworld.org/supply-management-news-and-reports/news-publications/releases/2025/institute-for-supply-management-updates-monthly-economic-indicators-branding-ism-pmi-reports/.
The 2014 subscription announcement is
https://www.prnewswire.com/news-releases/institute-for-supply-management-to-offer-subscription-access-to-historical-and-recent-ism-manufacturing-and-non-manufacturing-report-on-business-starting-march-1-245203881.html.
The 2022 license text is
https://www.prnewswire.com/news-releases/ism-makes-annual-adjustments-to-seasonal-factors-for-manufacturing-pmi-services-pmi-and-diffusion-indexes-301464999.html.
The 1948 span is not stored as a redistributable history. The survey is
not a quantity of manufactured goods and is not a trading right. It
does not store an index value. This module is not called from a field
save.
"""

from __future__ import annotations

import json
from pathlib import Path

ISM_MANUFACTURING_PMI_URL = (
    "https://www.ismworld.org/globalassets/738-terms-and-conditions.pdf"
)

PUBLISHER = "Institute for Supply Management"
PRODUCT = "Manufacturing PMI"
PERIOD = (
    "monthly; a February 2014 announcement said a paid historical "
    "subscription would include Report on Business information dating as far "
    "back as 1948 and stated an expected annual price of $2,500; that price "
    "was not re-checked; a January 2022 seasonal-factor release still points "
    "readers to a historical-data subscription; the 1948 span is not an open "
    "file"
)
UNIT = (
    "monthly diffusion index from a survey of U.S. purchasing and supply "
    "executives; the September 2025 branding note says the "
    "expansion/contraction baseline of 50.0 is unchanged and that "
    "seasonal-adjustment practice is unchanged; no index value is stored; a "
    "diffusion index is not a quantity of manufactured goods"
)
ADMINISTRATIVE_AREA = (
    "the United States survey of purchasing and supply executives; not a "
    "stored quantity of goods"
)
KIND = "survey"
RELEASE_LICENSE_2022 = (
    "The 2022 release text grants a limited personal, non-commercial license "
    "to display the content on an individual device, and it forbids copying, "
    "archiving, or creating tables, charts, or time-series derivatives without "
    "written permission."
)
BRANDING_ACCESS_2025 = (
    "The 2025 branding note says public access to releases, tables, and "
    "historical data continues via ismworld.org/ism-pmi."
)
TERMS_OF_USE = (
    "The general terms PDF says ISM products and data may be used for "
    "personal, non-commercial use only, and reproduction needs express "
    "written permission."
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
REDISTRIBUTABLE_1948_LABELS = frozenset({
    "1948",
    "1948 history",
    "redistributable history",
    "1948 redistributable",
    "1948 redistributable history",
})


def _rejects_1948_history(label) -> bool:
    text = str(label).strip().lower()
    if text in REDISTRIBUTABLE_1948_LABELS:
        return True
    return "1948" in text and "redistribut" in text


def record_series_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and (
        str(label).strip().lower() in FORBIDDEN_LABELS or _rejects_1948_history(label)
    ):
        raise ValueError(
            "a Manufacturing PMI figure is not a settlement, a yield, a trade, "
            "a forecast, an observation, a completed harvest, or a benchmark, "
            "and 1948 is not a redistributable history"
        )
    citation = str(citation_url).strip()
    if citation != ISM_MANUFACTURING_PMI_URL:
        raise ValueError("citation_url is not the opened terms PDF")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "unit": UNIT,
        "administrative_area": ADMINISTRATIVE_AREA,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
        "release_license_2022": RELEASE_LICENSE_2022,
        "branding_access_2025": BRANDING_ACCESS_2025,
        "terms_of_use": TERMS_OF_USE,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "ism-manufacturing-pmi.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
