"""One decision about records the suite already stores.

The statement is the six sentences below and nothing beyond them. It
does not invent a price, a yield, or a trade. A request to record a
trade, a settlement, or financial use raises before a file is written.
permits_financial_use stays false. Class C stays closed.
"""

from __future__ import annotations

from pathlib import Path

from farm_ontology.policy import CLASS_C_POLICY

STATEMENT = (
    "A stored national crop total is not a farm yield and not a completed harvest "
    "when the source marks the column as a forecast.\n"
    "A stored reanalysis temperature, wind component, or dewpoint is not relative "
    "humidity and not a harvest.\n"
    "A stored topsoil class share is not volumetric soil moisture.\n"
    "A stored water withdrawal and a stored flight count are not prices.\n"
    "An index is not a quantity of goods.\n"
    "A request to record a trade, a settlement, or financial use raises and writes "
    "nothing while permits_financial_use is false.\n"
)

REFUSED_REQUESTS = frozenset({"trade", "settlement", "financial use"})


def decision_statement() -> str:
    """Return the decision statement."""

    if CLASS_C_POLICY != "closed":
        raise ValueError("class C stays closed")
    return STATEMENT


def record_decision_statement(
    path: Path,
    *,
    ask: str | None = None,
    permits_financial_use: bool | None = None,
) -> str:
    """Write the decision statement, or write nothing."""

    if ask is not None and ask.strip().lower() in REFUSED_REQUESTS:
        raise ValueError(
            "a request to record a trade, a settlement, or financial use "
            "raises and writes nothing while permits_financial_use is false"
        )
    if permits_financial_use is not None:
        raise ValueError(
            "a request to record a trade, a settlement, or financial use "
            "raises and writes nothing while permits_financial_use is false"
        )
    text = decision_statement()
    path.write_text(text, encoding="utf-8")
    return text
