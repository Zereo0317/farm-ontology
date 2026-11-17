"""INDEC September 2026 index level.

The stored citation is the September 2026 informe

https://www.indec.gob.ar/uploads/informesdeprensa/ipi_manufacturero_11_2630BE216D2B.pdf.

Cuadro 1 prints the serie original nivel general for Septiembre de 2026
as 122,4, base 2004=100. The informe's first sentence names that index.
The desestacionalizada level, the tendencia-ciclo level, and the
variación porcentual columns are not stored. The attribution sentence
stays with the figure. The workbook was not opened. An index is not a
quantity of goods and not a trade. Reproduction with attribution is not
a right to trade. permits_financial_use stays false. Class C stays
closed. This module does not change the header function that rejects a
number. This module is not called from a field save.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from farm_ontology.indec_ipi import (
    ADMINISTRATIVE_AREA,
    COPYRIGHT_NOTICE,
    INDEC_IPI_URL,
    PERIOD,
    PRODUCT,
)
from farm_ontology.policy import CLASS_C_POLICY

SERIES = "serie original"
UNIT = "base 2004=100"
_ROW = re.compile(
    r"2026\*\s+Enero\b.*?Septiembre\s+"
    r"(-?\d+,\d+)\s+(-?\d+,\d+)\s+(-?\d+,\d+)\s+"
    r"(-?\d+,\d+)\s+(-?\d+,\d+)\s+(-?\d+,\d+)\s+(-?\d+,\d+)",
    re.DOTALL,
)
FORBIDDEN_LABELS = frozenset(
    {
        "trade",
        "completed harvest",
        "harvest",
        "quantity of goods",
        "trading right",
        "percent",
        "porcentual",
        "variación porcentual",
    }
)


def _plain(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


def _original_level(text: str) -> str:
    plain = _plain(text)
    if (
        PRODUCT not in plain
        or PERIOD not in plain
        or "total del país" not in plain
        or "base 2004=100" not in plain
        or COPYRIGHT_NOTICE not in plain
    ):
        raise ValueError("the informe prints no September 2026 index level")
    match = _ROW.search(plain)
    if match is None:
        raise ValueError("the informe prints no September 2026 index level")
    return match.group(1)


def record_index_level(
    path: Path,
    citation_url: str | None,
    body: str | None = None,
    *,
    source_url: str | None = None,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write the printed serie original level, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("an index level is not stored without the informe")
    if citation_url != INDEC_IPI_URL:
        raise ValueError("an index level is not stored for a different citation")
    if source_url not in (None, INDEC_IPI_URL):
        raise ValueError("the workbook is not opened")
    if body is None or body.strip() == "":
        raise ValueError("the informe prints no September 2026 index level")
    if label is not None and (
        label.strip().lower() in FORBIDDEN_LABELS
        or "%" in label
        or "％" in label
    ):
        raise ValueError("an index is not a quantity of goods and not a trade")
    if permits_financial_use not in (None, False) or class_c_policy not in (
        None,
        CLASS_C_POLICY,
    ):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    level = _original_level(body)
    stored = {
        "copyright_notice": COPYRIGHT_NOTICE,
        "product": PRODUCT,
        "period": PERIOD,
        "administrative_area": ADMINISTRATIVE_AREA,
        "unit": UNIT,
        "series": SERIES,
        "value": level,
        "kind": "index",
        "citation_url": INDEC_IPI_URL,
        "permits_financial_use": False,
        "class_c_policy": CLASS_C_POLICY,
    }
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
