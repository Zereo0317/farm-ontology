"""CONAB soybean series cells for Brazil, copied from the live workbook.

The file opened on 17 Nov 2026 is the Companhia Nacional de Abastecimento
historical soybean workbook. The citation is that file:

https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/safras/series-historicas/graos/soja/sojaseriehist.xls

The Produção sheet prints row BRASIL, column 2025/26, as 180406.6. The unit
line on that sheet is "Em mil toneladas". The 2025/26 header has no previsão
mark. This cell is the Brazil national total, not a farm yield.

The same row's 2026/27 column is labelled "2026/27 Previsão (¹)". The legend
line prints "Legenda: (¹) Estimativa em novembro/2026." That cell is a
forecast, not a completed harvest. Its number format prints one decimal, and
the printed figure is 181616.6.

Área BRASIL 2025/26 prints 48608.6 with the unit line "Em mil hectares".
Produtividade BRASIL 2025/26 prints 3711.4147229091154 with the unit line
"Em kg/ha". The productivity cell is stored unrounded. Yield is not derived
from production and area.

The workbook prints "Fonte: Conab". permits_financial_use stays false. Class C
stays closed. A missing citation writes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

CONAB_SOJA_URL = (
    "https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/"
    "safras/series-historicas/graos/soja/sojaseriehist.xls"
)

SOURCE = "Conab"
PRODUCT = "SOJA - BRASIL"
ROW = "BRASIL"
PRODUCTION_2025_26 = 180406.6
PRODUCTION_UNIT = "Em mil toneladas"
PRODUCTION_COLUMN = "2025/26"
FORECAST_PRODUCTION = 181616.6
FORECAST_COLUMN = "2026/27 Previsão (¹)"
FORECAST_LEGEND = "Legenda: (¹) Estimativa em novembro/2026."
FORECAST_LABEL = "forecast"
AREA_2025_26 = 48608.6
AREA_UNIT = "Em mil hectares"
AREA_SERIES = "Série Histórica de Área Plantada"
PRODUCTIVITY_2025_26 = 3711.4147229091154
PRODUCTIVITY_UNIT = "Em kg/ha"
PRODUCTIVITY_SERIES = "Série Histórica de Produtividade"
PRODUCTION_SERIES = "Série Histórica de Produção"

FORBIDDEN_LABELS = frozenset(
    {
        "yield",
        "farm yield",
        "price",
        "trade",
        "harvest",
        "completed harvest",
    }
)

CELLS = (
    {
        "sheet": "Produção",
        "series": PRODUCTION_SERIES,
        "row": ROW,
        "column": PRODUCTION_COLUMN,
        "value": PRODUCTION_2025_26,
        "unit": PRODUCTION_UNIT,
    },
    {
        "sheet": "Produção",
        "series": PRODUCTION_SERIES,
        "row": ROW,
        "column": FORECAST_COLUMN,
        "value": FORECAST_PRODUCTION,
        "unit": PRODUCTION_UNIT,
        "label": FORECAST_LABEL,
        "legend": FORECAST_LEGEND,
    },
    {
        "sheet": "Área",
        "series": AREA_SERIES,
        "row": ROW,
        "column": PRODUCTION_COLUMN,
        "value": AREA_2025_26,
        "unit": AREA_UNIT,
    },
    {
        "sheet": "Produtividade",
        "series": PRODUCTIVITY_SERIES,
        "row": ROW,
        "column": PRODUCTION_COLUMN,
        "value": PRODUCTIVITY_2025_26,
        "unit": PRODUCTIVITY_UNIT,
    },
)


def record_conab_soja(
    path: Path,
    citation_url: str | None,
    *,
    source: str | None = None,
    product: str | None = None,
    row: str | None = None,
    cells: object = None,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed CONAB cells, or write nothing."""

    if citation_url is None or citation_url.strip() == "":
        raise ValueError("a CONAB soybean cell is not stored without a citation_url")
    if citation_url != CONAB_SOJA_URL:
        raise ValueError("a CONAB soybean cell is not stored for a different citation")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("a CONAB soybean cell is not a yield, price, trade, or harvest")
    if any(
        value is not None
        for value in (
            source,
            product,
            row,
            cells,
            permits_financial_use,
            class_c_policy,
        )
    ):
        raise ValueError("a CONAB soybean cell is not stored with a different value")
    header = {
        "source": SOURCE,
        "product": PRODUCT,
        "row": ROW,
        "cells": [dict(cell) for cell in CELLS],
        "citation_url": CONAB_SOJA_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
