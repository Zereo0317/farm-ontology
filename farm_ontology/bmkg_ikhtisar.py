"""BMKG daily-summary header.

One page from the address that was fetched. The stored record is the
printed h1. The publisher is BMKG / Badan Meteorologi, Klimatologi, dan
Geofisika. The product is Ikhtisar Cuaca Harian. The citation stays on
https://www.bmkg.go.id/cuaca/ikhtisar-cuaca-harian.
https://www.bmkg.go.id/ is not the citation.
https://www.bmkg.go.id/cuaca/prakiraan-cuaca is not the citation.
https://data.bmkg.go.id/prakiraan-cuaca/ is not the citation.
https://dataweb.bmkg.go.id/cuaca/dokumen/ikhtisar-cuaca-harian.pdf was not opened.
https://docs.google.com/viewer was not opened.
https://www.bmkg.go.id/cuaca/potensi-hujan-sepekan was not opened.
The document title is Ikhtisar Cuaca Harian - Cuaca - BMKG.
Ikhtisar Cuaca Harian is the h1. It is the product and the kind.
BMKG is a printed short name inside the one publisher.
Ringkasan is not a second kind.
Cuaca is a title segment, not a second kind.
Prakiraan Cuaca is a menu heading, not the product.
Period is omitted.
Unit is omitted.
The word harian stays inside the product. It is not a period.
dddd, D MMMM YYYY is an empty-element attribute, not a printed date.
The stored administrative area is di wilayah Indonesia.
Jakarta Pusat is the office address, not the administrative area.
Ketentuan Penggunaan was not opened.
Do not store a rainfall amount.
Do not store a temperature.
A forecast is not a completed harvest.
The header is not marked public domain.
permits_financial_use stays false.
This module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

BMKG_IKHTISAR_URL = "https://www.bmkg.go.id/cuaca/ikhtisar-cuaca-harian"

PUBLISHER = "BMKG / Badan Meteorologi, Klimatologi, dan Geofisika"
PRODUCT = "Ikhtisar Cuaca Harian"
ADMINISTRATIVE_AREA = "di wilayah Indonesia"
KIND = "Ikhtisar Cuaca Harian"
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
    if period is not None or unit is not None:
        raise ValueError("period and unit are omitted")
    if administrative_area is not None:
        raise ValueError("administrative_area is not replaced")
    if value is not None:
        raise ValueError("a figure is not stored")
    citation = str(citation_url).strip()
    if citation != BMKG_IKHTISAR_URL:
        raise ValueError("citation_url is not the opened daily summary")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "administrative_area": ADMINISTRATIVE_AREA,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "bmkg-ikhtisar.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
