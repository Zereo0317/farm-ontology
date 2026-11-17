"""Printed update intervals. This module does not fetch and stores no price.

BPA balancing file prints "at 5-minute intervals":
https://transmission.bpa.gov/Business/Operations/Wind/baltwg.txt

USGS instantaneous values print "Readings are usually made every 15
minutes and transmitted hourly":
https://waterservices.usgs.gov/docs/instantaneous-values/

JMA national daily table prints "更新時刻は、毎時40分頃です。":
https://www.data.jma.go.jp/stats/data/mdrr/synopday/

SMAP L3 prints Temporal Resolution "1 day":
https://nsidc.org/data/spl3smp/versions/9

USDA NASS prints "Crop progress surveys are conducted weekly":
https://www.nass.usda.gov/surveys/guide-to-nass-surveys/crop-progress-and-condition

Sentinel-2 prints "a high revisit frequency of 5 days at the Equator":
https://sentiwiki.copernicus.eu/web/s2-mission

World Bank Pink Sheet data prints "Monthly prices":
https://www.worldbank.org/en/research/commodity-markets

Conab soy columns are crop years. The 2026/27 column is labelled
"2026/27 Previsão (¹)", a forecast, not completed output:
https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/safras/series-historicas/graos/soja/sojaseriehist.xls

EIA prints "Weekly Petroleum Status Report":
https://www.eia.gov/petroleum/supply/weekly/

The Pink Sheet, Conab, NASS, and the EIA weekly report are not a
5-minute or hourly feed. permits_financial_use stays false. Class C
stays closed. An interval is not a trade. A missing citation writes
nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

BPA_URL = "https://transmission.bpa.gov/Business/Operations/Wind/baltwg.txt"
USGS_URL = "https://waterservices.usgs.gov/docs/instantaneous-values/"
JMA_URL = "https://www.data.jma.go.jp/stats/data/mdrr/synopday/"
SMAP_URL = "https://nsidc.org/data/spl3smp/versions/9"
NASS_URL = (
    "https://www.nass.usda.gov/surveys/guide-to-nass-surveys/"
    "crop-progress-and-condition"
)
SENTINEL_URL = "https://sentiwiki.copernicus.eu/web/s2-mission"
PINK_SHEET_URL = "https://www.worldbank.org/en/research/commodity-markets"
CONAB_URL = (
    "https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/"
    "safras/series-historicas/graos/soja/sojaseriehist.xls"
)
EIA_URL = "https://www.eia.gov/petroleum/supply/weekly/"

INTERVALS = (
    {
        "source": "BPA balancing file",
        "interval": "5-minute readings",
        "printed": "at 5-minute intervals",
        "citation_url": BPA_URL,
    },
    {
        "source": "USGS instantaneous streamflow",
        "interval": "15-minute record, hourly transmission",
        "printed": "Readings are usually made every 15 minutes and transmitted hourly.",
        "citation_url": USGS_URL,
    },
    {
        "source": "JMA national daily table",
        "interval": "updated about 40 minutes past each hour",
        "printed": "更新時刻は、毎時40分頃です。",
        "citation_url": JMA_URL,
    },
    {
        "source": "SMAP temporal resolution",
        "interval": "1 day",
        "printed": "Temporal Resolution: 1 day",
        "citation_url": SMAP_URL,
    },
    {
        "source": "USDA NASS Crop Progress",
        "interval": "weekly",
        "printed": "Crop progress surveys are conducted weekly",
        "citation_url": NASS_URL,
    },
    {
        "source": "Sentinel-2 revisit",
        "interval": "5 days at the Equator",
        "printed": "a high revisit frequency of 5 days at the Equator",
        "citation_url": SENTINEL_URL,
    },
    {
        "source": "World Bank Pink Sheet",
        "interval": "monthly",
        "printed": "Monthly prices",
        "citation_url": PINK_SHEET_URL,
    },
    {
        "source": "Conab soy series",
        "interval": "crop year",
        "printed": "2026/27 Previsão (¹)",
        "note": "The 2026/27 column is a forecast, not completed output.",
        "citation_url": CONAB_URL,
    },
    {
        "source": "EIA Weekly Petroleum Status Report",
        "interval": "weekly",
        "printed": "Weekly Petroleum Status Report",
        "citation_url": EIA_URL,
    },
)

NOT_A_FAST_FEED = frozenset(
    {
        "World Bank Pink Sheet",
        "Conab soy series",
        "USDA NASS Crop Progress",
        "EIA Weekly Petroleum Status Report",
    }
)
FAST_FEEDS = frozenset(
    {
        "5-minute",
        "5-minute readings",
        "5-minute feed",
        "hourly",
        "hourly feed",
    }
)


def record_printed_intervals(
    path: Path,
    citations: dict | None,
    *,
    source: str | None = None,
    feed: str | None = None,
    label: str | None = None,
    price: object = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed intervals, or write nothing."""

    if not isinstance(citations, dict) or not citations:
        raise ValueError("an interval is not stored without a citation_url")
    expected = {row["source"]: row["citation_url"] for row in INTERVALS}
    if citations != expected:
        raise ValueError("an interval is not stored for a different citation")
    if permits_financial_use not in (None, False):
        raise ValueError("permits_financial_use stays false")
    if class_c_policy not in (None, CLASS_C_POLICY):
        raise ValueError("Class C stays closed")
    if price is not None:
        raise ValueError("a printed interval does not store a price")
    if label is not None and label.strip().lower() in {"trade", "settlement"}:
        raise ValueError("an interval is not a trade while permits_financial_use is false")
    if source in NOT_A_FAST_FEED and feed is not None and feed.strip().lower() in FAST_FEEDS:
        raise ValueError("that series is not a 5-minute or hourly feed")
    statement = {
        "intervals": [dict(row) for row in INTERVALS],
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(statement, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
