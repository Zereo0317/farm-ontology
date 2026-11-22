"""Unlock ledger. Financial use requires independently verified provider rights.

This composes with, and never mutates, the frozen `LicenceGrant` stored on
observations in `farm_ontology.model`: the ledger reads a feed's *state* plus
certificates and returns the effective answer for one instant. A grant that
expires mid-timeline automatically demotes the feed's effective flag to false
(fail closed) at the tick after expiry — no writer, patch, or review is
involved, so nothing can forget.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime

from farm_ontology.licences.grants import (
    FINANCIAL_USES,
    KNOWN_FEEDS,
    Grant,
    _check_at,
    evaluate_grants,
)

_ALIAS_TO_TASKS = {
    "no_feed_state": "give the ledger a feed_id-bearing state mapping",
    "recorded_false": "the feed records demotion; only its writer can record promotion",
    "unknown_feed": "register the feed id in licences.KNOWN_FEEDS",
    "no_grant": "attach a signed grant whose uses[] name a financial use",
    "specimen": "replace the SPECIMEN with an executed grant",
    "expired": "attach a renewed grant before using the feed financially",
    "provider_rights_unverified": "verify provider rights independently of farmer or operator authorization",
}

REMEDIY_HINTS = _ALIAS_TO_TASKS


def _covering_financial(grants: Iterable[Grant], feed_id: str) -> list[Grant]:
    return [
        grant
        for grant in grants
        if feed_id in grant.feeds and (set(grant.uses) & FINANCIAL_USES)
    ]


def effective_permits_financial_use(
    feed_state: Mapping, grants: Iterable[Grant], at: datetime
) -> bool:
    """Pure predicate: is financial use of this feed effectively permitted at `at`?

    Rules, all fail closed:
    1. a mapping without a string `feed_id`, or whose recorded
       `permits_financial_use` is not exactly True, stays demoted — the
       ledger never promotes a feed beyond its own recorded state;
    2. the licence evaluator must allow at least one financial use at `at`;
    3. while provider rights remain unverified, every such use is refused.

    Raises on a naive `at`; never mutates any argument.
    """
    at = _check_at(at)
    if not isinstance(feed_state, Mapping):
        return False
    feed_id = feed_state.get("feed_id")
    if not isinstance(feed_id, str) or not feed_id.strip():
        return False
    if feed_state.get("permits_financial_use") is not True:
        return False
    if feed_id.strip() not in KNOWN_FEEDS:
        return False
    grants = tuple(grants)
    return any(evaluate_grants(grants, feed_id.strip(), use, at)[0]
               for use in FINANCIAL_USES)


def demoted_reason(
    feed_state: Mapping, grants: Iterable[Grant], at: datetime
) -> str | None:
    """Why is financial use demoted (alarm/ledger narrative)? None means live.

    Speaks for the WHOLE financial family (any of settlement/hedge/trigger/
    nature-unit), unlike `evaluate_grants`, which answers per use.
    """
    at = _check_at(at)
    if not isinstance(feed_state, Mapping):
        return "no_feed_state"
    feed_id = feed_state.get("feed_id")
    if not isinstance(feed_id, str) or not feed_id.strip():
        return "no_feed_state"
    feed_id = feed_id.strip()
    if feed_id not in KNOWN_FEEDS:
        return "unknown_feed"
    if feed_state.get("permits_financial_use") is not True:
        return "recorded_false"
    covering = _covering_financial(tuple(grants), feed_id)
    if not covering:
        return "no_grant"
    if any(grant.is_live_at(at) for grant in covering):
        return "provider_rights_unverified"
    real = [grant for grant in covering if not grant.specimen]
    return "expired" if real else "specimen"


def expiry_alarm_rows(grants: Iterable[Grant], at: datetime) -> list[dict]:
    """Rows for the expiry alarm: live non-specimen grants ordered by expiry."""
    at = _check_at(at)
    rows = []
    for grant in tuple(grants):
        if grant.specimen:
            continue
        rows.append(
            {
                "grant_id": grant.grant_id,
                "feeds": list(grant.feeds),
                "expiry_utc": grant.expiry_utc,
                "expired": not grant.is_live_at(at),
            }
        )
    return sorted(rows, key=lambda row: row["expiry_utc"])
