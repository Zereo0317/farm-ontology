"""BMKG forecast-page header.

One forecast-page title from the page that was already opened. The
stored record is that title. The publisher is Badan Meteorologi,
Klimatologi, dan Geofisika. The product is Prakiraan Cuaca. The
citation stays on
https://www.bmkg.go.id/cuaca/prakiraan-cuaca.
https://www.bmkg.go.id/ is not the citation.
https://data.bmkg.go.id/prakiraan-cuaca/ is not the citation.
The homepage title is BMKG - Badan Meteorologi, Klimatologi, dan Geofisika.
That title is the publisher. It is not a forecast product title.
BMKG is a printed short name, not a second publisher.
The forecast page title is Prakiraan Cuaca | BMKG - Badan Meteorologi, Klimatologi, dan Geofisika.
Prakiraan Cuaca Kelurahan/Desa is menu text, not the product.
Ikhtisar Cuaca Harian was not opened.
Potensi Hujan Sepekan ke Depan was not opened.
Period was not opened and is omitted.
Unit was not opened and is omitted.
The stored administrative area is di seluruh wilayah Indonesia.
Peringatan dini di wilayah Indonesia. is not the administrative area.
Provinsi Lainnya is not the administrative area.
Aceh, DKI Jakarta, and Papua Pegunungan are province names. They are not the administrative area.
Jl. Angkasa I No.2 Kemayoran, Jakarta Pusat 10610, PO Box 3540 Jkt. is not the administrative area.
© 2026 is a copyright line, not a period.
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

BMKG_PRAKIRAAN_URL = "https://www.bmkg.go.id/cuaca/prakiraan-cuaca"

PUBLISHER = "Badan Meteorologi, Klimatologi, dan Geofisika"
PRODUCT = "Prakiraan Cuaca"
ADMINISTRATIVE_AREA = "di seluruh wilayah Indonesia"
KIND = "Prakiraan Cuaca"
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
        raise ValueError("period and unit were not opened")
    if administrative_area is not None:
        raise ValueError("administrative_area is not replaced")
    if value is not None:
        raise ValueError("a figure is not stored")
    citation = str(citation_url).strip()
    if citation != BMKG_PRAKIRAAN_URL:
        raise ValueError("citation_url is not the opened forecast page")
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
    path = folder / "bmkg-prakiraan.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
