"""BMKG weekly rain-outlook header.

One page from the address that was fetched. The stored record is the
printed h1. The publisher is BMKG / Badan Meteorologi, Klimatologi, dan
Geofisika. The product is Potensi Hujan Sepekan ke Depan. The citation
stays on
https://www.bmkg.go.id/cuaca/potensi-hujan-sepekan.
https://www.bmkg.go.id/ is not the citation.
https://www.bmkg.go.id/cuaca/prakiraan-cuaca is not the citation.
https://www.bmkg.go.id/cuaca/ikhtisar-cuaca-harian is not the citation.
https://data.bmkg.go.id/prakiraan-cuaca/ is not the citation.
The document title is Potensi Hujan Sepekan ke Depan - Cuaca - BMKG.
Potensi Hujan Sepekan ke Depan is the h1. It is the product and the kind.
BMKG is a printed short name inside the one publisher.
The word hujan in the title is not a rainfall amount.
Cuaca is not a second kind.
Prakiraan is not a second kind.
Child article links were not opened.
Ikhtisar Cuaca Harian was not opened.
Ketentuan Penggunaan was not opened.
The stored period includes untuk sepekan ke depan and the printed Periode spans.
Unit is omitted.
Administrative area is omitted.
The description sentence was not used to fill an administrative area.
Province names printed beside rainfall figures were not stored.
Do not store a rainfall amount.
Do not store a temperature.
A forecast is not a completed harvest.
An index is not a quantity of goods.
The header is not marked public domain.
permits_financial_use stays false.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

BMKG_POTENSI_URL = "https://www.bmkg.go.id/cuaca/potensi-hujan-sepekan"

PUBLISHER = "BMKG / Badan Meteorologi, Klimatologi, dan Geofisika"
PRODUCT = "Potensi Hujan Sepekan ke Depan"
PERIOD = (
    "untuk sepekan ke depan; "
    "16 Nov 2026; Periode 17 \u2013 23 November 2026; "
    "12 Nov 2026; Periode 13 \u2013 19 November 2026; "
    "10 Nov 2026; Periode 10 \u2013 16 November 2026; "
    "6 Nov 2026; Periode 6 \u2013 12 November 2026; "
    "5 Nov 2026; Periode 3 \u2013 10 November 2026; "
    "29 Oct 2026; Periode 30 Oktober \u2013 5 November 2026; "
    "26 Oct 2026; Periode 27 Oktober\u20132 November 2026; "
    "22 Oct 2026; Periode 23\u201329 Oktober 2026; "
    "20 Oct 2026; Periode 20\u201326 Oktober 2026; "
    "15 Oct 2026; Periode 16\u201322 Oktober 2026; "
    "12 Oct 2026; Periode 13\u201319 Oktober 2026; "
    "8 Oct 2026; Periode 9\u201315 Oktober 2026"
)
KIND = "Potensi Hujan Sepekan ke Depan"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "price",
    "trade",
    "observation",
    "completed harvest",
    "public domain",
    "benchmark",
    "index",
    "rainfall amount",
    "temperature",
    "figure",
    "ringkasan",
    "cuaca",
    "prakiraan",
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
    value=None,
) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and (
        str(label).strip().lower() in FORBIDDEN_LABELS or _stores_figure(label)
    ):
        raise ValueError(
            "a forecast header is not a settlement, a yield, a price, a "
            "trade, an observation, a completed harvest, a benchmark, or "
            "an index, and a rainfall amount, a temperature, or a figure "
            "is not stored"
        )
    if period is not None:
        raise ValueError("period is not replaced")
    if unit is not None or administrative_area is not None:
        raise ValueError("unit and administrative_area are omitted")
    if value is not None:
        raise ValueError("a figure is not stored")
    citation = str(citation_url).strip()
    if citation != BMKG_POTENSI_URL:
        raise ValueError("citation_url is not the opened weekly outlook")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "bmkg-potensi.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
