"""One printed Argentina agricultural estimate from the cited catalog.

The citation already stored in the tests is

https://www.datos.gob.ar/dataset/estimaciones-agricolas

The refetch of that URL returned HTTP 200 and stayed on that URL.
The catalog prints no production or area figure for a campaign and a
province or department. It links one CSV titled Estimaciones agrícolas.
Only that linked file was opened. Its latest campaign's last printed
row is trigo total, 2024/2025, Buenos Aires, General Arenales,
production 117600 tm. The yield column is not stored. A province or
department is not a farm. An estimate is not a completed harvest and
not a trade. A missing citation, a failed request, or a page with no
printed figure writes nothing. A figure is not invented and a URL is
not guessed.
permits_financial_use stays false. Class C stays closed.
"""

from __future__ import annotations

import csv
import html
import io
import json
import re
from pathlib import Path

from farm_ontology.argentina_estimates import CITATION_URL
from farm_ontology.policy import CLASS_C_POLICY

FORBIDDEN_LABELS = frozenset(
    {
        "trade",
        "farm",
        "yield",
        "settlement",
        "completed harvest",
        "observation",
    }
)
_CAMPAIGN = re.compile(r"\d{4}/\d{4}")


def _linked_file(catalog: str) -> str:
    found: list[str] = []
    for block in re.split(r'<li class="resource-item"', catalog)[1:]:
        if 'title="Estimaciones agrícolas"' not in block or "CSV" not in block:
            continue
        match = re.search(r'href="(https://[^"]+\.csv)"', block)
        if match:
            found.append(html.unescape(match.group(1)))
    if len(found) != 1:
        raise ValueError("the catalog does not link one data file")
    return found[0]


def _number(token: str):
    if not re.fullmatch(r"\d+", token):
        raise ValueError("the printed figure is not a whole number")
    number = int(token)
    if json.dumps(number) != token:
        return token
    return number


def _figure(file_body: str) -> dict:
    reader = csv.DictReader(io.StringIO(file_body))
    required = {
        "cultivo",
        "campania",
        "provincia",
        "departamento",
        "produccion_tm",
        "superficie_sembrada_ha",
        "superficie_cosechada_ha",
    }
    if reader.fieldnames is None or not required.issubset(reader.fieldnames):
        raise ValueError("the file has no production or area figure")
    chosen: dict | None = None
    campaign: str | None = None
    for row in reader:
        period = (row.get("campania") or "").strip()
        province = (row.get("provincia") or "").strip()
        department = (row.get("departamento") or "").strip()
        if _CAMPAIGN.fullmatch(period) is None or (province == "" and department == ""):
            continue
        production = (row.get("produccion_tm") or "").strip()
        sown = (row.get("superficie_sembrada_ha") or "").strip()
        harvested = (row.get("superficie_cosechada_ha") or "").strip()
        if production:
            figure, token, unit = "produccion_tm", production, "tm"
        elif sown:
            figure, token, unit = "superficie_sembrada_ha", sown, "ha"
        elif harvested:
            figure, token, unit = "superficie_cosechada_ha", harvested, "ha"
        else:
            continue
        if campaign is None or period > campaign:
            campaign = period
            chosen = None
        if period != campaign:
            continue
        chosen = {
            "series": (row.get("cultivo") or "").strip(),
            "period": period,
            "province": province,
            "department": department,
            "figure": figure,
            "value": _number(token),
            "unit": unit,
        }
    if chosen is None or chosen["series"] == "":
        raise ValueError("the file has no production or area figure")
    chosen["kind"] = "estimate"
    return chosen


def record_argentina_estimate_current(
    path: Path,
    citation_url: str | None,
    catalog_body: str | None = None,
    file_body: str | None = None,
    *,
    request_failed: bool = False,
    label: str | None = None,
    permits_financial_use: bool | None = None,
    class_c_policy: str | None = None,
) -> None:
    """Write one printed estimate, or write nothing."""

    if request_failed or citation_url is None or citation_url.strip() == "":
        raise ValueError("a figure is not stored without the cited catalog")
    if citation_url != CITATION_URL:
        raise ValueError("a figure is not stored for a different citation")
    if catalog_body is None or catalog_body.strip() == "":
        raise ValueError("the catalog has no figure")
    if label is not None and label.strip().lower() in FORBIDDEN_LABELS:
        raise ValueError("an estimate is not a farm, a completed harvest, or a trade")
    if permits_financial_use not in (None, False) or class_c_policy not in (None, CLASS_C_POLICY):
        raise ValueError("permits_financial_use stays false and Class C stays closed")
    file_url = _linked_file(catalog_body)
    if file_body is None or file_body.strip() == "":
        raise ValueError("the linked file has no figure")
    stored = _figure(file_body)
    stored["citation_url"] = CITATION_URL
    stored["file_url"] = file_url
    stored["permits_financial_use"] = False
    stored["class_c_policy"] = CLASS_C_POLICY
    path.write_text(
        json.dumps(stored, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
