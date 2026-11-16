"""INDEC manufacturing production index header.

One report from the September 2026 informe that was already opened. The
stored record is the printed header plus the informe's Creative Commons
sentence. Reproduction with attribution is not a financial-use grant.
The current release is this informe, not Estimador mensual industrial.
The EMI archive page was not opened. The masthead prints Informes
técnicos. Vol. 10, nº 274, ISSN 2545-6636, Industria manufacturera.
Vol. 10, nº 37, ISSN 2545-6733, and Buenos Aires, noviembre de 2026.
The coverage sentence prints la cobertura geográfica es para el total
del país. The publication address names Ciudad Autónoma de Buenos
Aires, Argentina. That address does not replace total del país. The
cuadro title prints Serie original, desestacionalizada y
tendencia-ciclo, base 2004=100, en números índice y variación
porcentual. No percent and no index level is stored. The indicator page
footer says the site material has a Creative Commons licence unless a
content note says otherwise, and the words link to
https://creativecommons.org/licenses/by-sa/4.0/deed.es.
That deed page was not opened. The Política de difusión del INDEC PDF
was not opened. The footer prints © 2026. The workbook
https://www.indec.gob.ar/ftp/cuadros/economia/sh_ipi_manufacturero_2026.xls
was not opened. The informe says those digital cuadros run desde enero
de 2016 hasta el período de referencia del presente informe. That span
was not checked inside the file. 2016 is not a verified start. The
report is not a quantity of goods and is not a trading right. This
module is not called from a field save.
"""

from __future__ import annotations

import json
from pathlib import Path

INDEC_IPI_URL = (
    "https://www.indec.gob.ar/uploads/informesdeprensa/"
    "ipi_manufacturero_11_2630BE216D2B.pdf"
)

PUBLISHER = "Instituto Nacional de Estadística y Censos"
PRODUCT = "Índice de producción industrial manufacturero"
PERIOD = "Septiembre de 2026"
UNIT = "base 2004=100, en números índice"
ADMINISTRATIVE_AREA = "total del país"
KIND = "report"
COPYRIGHT_NOTICE = (
    "Esta publicación utiliza una licencia Creative Commons. "
    "Se permite su reproducción con atribución de la fuente."
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
    "quantity of goods",
    "trading right",
    "verified start",
    "index level",
    "percent",
    "porcentual",
    "variación porcentual",
})


def _stores_number(label) -> bool:
    text = str(label)
    if any(character.isdigit() for character in text):
        return True
    return any(mark in text for mark in ("=", "＝", "%", "％"))


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
        str(label).strip().lower() in FORBIDDEN_LABELS or _stores_number(label)
    ):
        raise ValueError(
            "an INDEC industrial-production figure is not a settlement, a "
            "yield, a trade, a forecast, an observation, a completed harvest, "
            "or a benchmark, and a number is not stored"
        )
    if (
        period is not None
        or unit is not None
        or administrative_area is not None
        or value is not None
    ):
        raise ValueError("a number is not stored")
    citation = str(citation_url).strip()
    if citation != INDEC_IPI_URL:
        raise ValueError("citation_url is not the opened September 2026 informe")
    header = {
        "publisher": PUBLISHER,
        "product": PRODUCT,
        "period": PERIOD,
        "unit": UNIT,
        "administrative_area": ADMINISTRATIVE_AREA,
        "citation_url": citation,
        "kind": KIND,
        "permits_financial_use": False,
        "copyright_notice": COPYRIGHT_NOTICE,
    }
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "indec-ipi.json"
    path.write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"file": path.name, "header": header}
