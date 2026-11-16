"""CONAB Safra de grãos header.

One in-season estimate from the series page that was already opened.
The stored record is the printed header. It is not an observation, not
a completed harvest, and not a farm yield. It does not store an area,
a production total, or a yield figure. This module is not called from
a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

PUBLISHER = "Companhia Nacional de Abastecimento"
PRODUCT = "Safra de grãos"
PERIOD = "monthly during the crop year; bulletins numbered from October 2013"
UNIT = "not printed on the opened series page"
ADMINISTRATIVE_AREA = "Brazil, national and state"
CITATION_URL = (
    "https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/"
    "safras/safra-de-graos/safra-de-graos"
)
KIND = "estimate"
FORBIDDEN_LABELS = frozenset({
    "settlement",
    "yield",
    "trade",
    "observation",
    "completed harvest",
})


def record_crop_table_header(directory, *, citation_url=None, label=None) -> dict:
    if citation_url is None or str(citation_url).strip() == "":
        raise ValueError("citation_url is required")
    if label is not None and str(label).strip().lower() in FORBIDDEN_LABELS:
        raise ValueError(
            "a Safra de grãos figure is not a settlement, a yield, a trade, "
            "an observation, or a completed harvest"
        )
    citation = str(citation_url).strip()
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "unit": UNIT,
        "administrative_area": ADMINISTRATIVE_AREA,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "safra-de-graos.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
