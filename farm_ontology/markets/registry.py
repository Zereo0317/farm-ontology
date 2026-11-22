"""Provenance registry + grant bridge for the markets rails (fix sprint D1/D2).

Two registries and one bridge, all fail-closed and offline:

- :class:`RegisteredGrants` — the CURRENT grant attestation: the set of
  grant fingerprints rails will trust RIGHT NOW. Loaded from the WS6
  unlock ledger's generated ``grants/state.json`` when reachable, else
  from an explicit JSON file named by the ``FARM_GRANT_REGISTRY`` env
  var (``{"fingerprints": [...]}``), else EMPTY — and an empty registry
  unlocks nothing. Fingerprints are sha256 over the canonical JSON
  payload, the same scheme ``licences.Grant.fingerprint`` uses.
- :class:`RegisteredCapSheets` — the quarterly premium-cap attestation
  (D6): quarter -> sha256 of the signed cap-sheet JSON, plus whether the
  attested sheet is still a SPECIMEN. The shipped default is the
  specimen sheet only: real caps do not exist yet, so every premium
  budget dies with the rail named until the risk owner signs a real
  sheet and its hash is registered.
- :func:`bridge_licences_to_grantref` — the licences→rails adapter the
  rehearsal wished for. It ports the ORIGINAL licences verdict reason
  (``specimen`` / ``no_grant`` / ``use_not_granted`` / ``expired`` /
  ``ok``) into ``GrantRef.state_detail`` verbatim (D2: no more
  flattening to "closed") and carries the licences ``Grant.fingerprint``
  so the rails registry check has a real join key (D1).

This module never mutates the licences package and never calls the
network. Feed-id mapping between the markets slugs and the licences
registry is explicit below.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from farm_ontology.licences.grants import evaluate as licences_evaluate
from farm_ontology.markets.rails import GrantRef

#: Markets feed slugs -> licences KNOWN_FEEDS ids (fixed by the lead on
#: main, commit cc23281, answering the rehearsal finding).
PIT_TO_LICENCES_FEED = {
    "usda_wasde": "usda.wasde",
    "ams_soybean_bid": "ams.soybean-bid",
    "fao_food_price_index": "fao.food-price-index",
    "imf_pcps": "imf.pcps",
    "pink_sheet": "worldbank.pink-sheet",
}

#: Generated unlock-ledger snapshot (WS6), relative to this package.
_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GRANT_STATE_PATH = _REPO_ROOT / "grants" / "state.json"

#: Env fallback: path to a JSON file shaped ``{"fingerprints": [...]}``.
ENV_GRANT_REGISTRY = "FARM_GRANT_REGISTRY"

#: The shipped SPECIMEN premium-cap sheet (D6): proves the registry
#: mechanics while never unlocking real caps.
CAP_SHEET_SPECIMEN_PATH = (
    _REPO_ROOT / "farm_ontology" / "markets" / "fixtures" / "cap-sheet-2026Q4-SPECIMEN.json"
)

REGISTRY_ENV_NOTE = (
    "set FARM_GRANT_REGISTRY to a JSON file {\"fingerprints\": [...]} when "
    "the WS6 state.json is not reachable"
)


def compute_fingerprint(payload) -> str:
    """sha256 over canonical JSON (sorted keys, compact) — the same
    scheme as ``licences.Grant.fingerprint``."""
    canonical = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _is_fingerprint(value: str) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


class RegisteredGrants:
    """The current grant attestation. Membership by fingerprint only."""

    def __init__(self, fingerprints=(), source: str = "explicit") -> None:
        self.source = source
        self._fingerprints: dict[str, None] = {}
        for item in fingerprints:
            if not _is_fingerprint(item):
                raise ValueError(
                    f"registry entries must be 64-hex fingerprints, got {item!r}"
                )
            self._fingerprints.setdefault(item)

    @classmethod
    def from_fingerprints(cls, *fingerprints) -> "RegisteredGrants":
        return cls(fingerprints, source="explicit")

    @classmethod
    def from_state_json(cls, path=None) -> "RegisteredGrants":
        target = Path(path) if path is not None else DEFAULT_GRANT_STATE_PATH
        payload = json.loads(Path(target).read_text(encoding="utf-8"))
        fingerprints = [
            grant["fingerprint"]
            for grant in payload.get("grants", [])
            if isinstance(grant, dict) and grant.get("fingerprint")
        ]
        return cls(fingerprints, source=str(target))

    @classmethod
    def from_env(cls, env_var: str = ENV_GRANT_REGISTRY) -> "RegisteredGrants | None":
        raw = os.environ.get(env_var, "").strip()
        if not raw:
            return None
        payload = json.loads(Path(raw).read_text(encoding="utf-8"))
        return cls(payload.get("fingerprints", []), source=raw)

    @classmethod
    def default(cls) -> "RegisteredGrants":
        """Repo state.json if present, else the env file, else EMPTY.

        An EMPTY registry is a valid attestation: it attests nothing, so
        nothing unlocks (fail closed).
        """
        if DEFAULT_GRANT_STATE_PATH.exists():
            return cls.from_state_json()
        from_env = cls.from_env()
        if from_env is not None:
            return from_env
        return cls(source="empty-fail-closed")

    def with_fingerprint(self, fingerprint: str) -> "RegisteredGrants":
        return RegisteredGrants(
            (*self.fingerprints(), fingerprint), source=self.source
        )

    def contains(self, fingerprint: str) -> bool:
        return fingerprint in self._fingerprints

    def fingerprints(self) -> tuple[str, ...]:
        return tuple(self._fingerprints)

    def __len__(self) -> int:
        return len(self._fingerprints)


class RegisteredCapSheets:
    """Quarter -> (sha256, specimen?) attestation for premium caps."""

    def __init__(self, entries=None, source: str = "explicit") -> None:
        self.source = source
        self._entries: dict[str, tuple[str, bool]] = {}
        for quarter, fingerprint, specimen in entries or ():
            if not quarter:
                raise ValueError("cap-sheet quarter must be non-empty")
            if not _is_fingerprint(fingerprint):
                raise ValueError(
                    f"cap-sheet hash for {quarter!r} must be a 64-hex sha256"
                )
            self._entries[quarter] = (fingerprint, bool(specimen))

    @classmethod
    def from_sheet_paths(cls, *paths) -> "RegisteredCapSheets":
        entries = []
        for path in paths:
            sheet = load_cap_sheet(path)
            entries.append(
                (sheet["quarter"], cap_sheet_hash(sheet), bool(sheet.get("specimen")))
            )
        return cls(entries, source="; ".join(str(path) for path in paths))

    @classmethod
    def default(cls) -> "RegisteredCapSheets":
        """The shipped SPECIMEN sheet only — real caps do not exist yet."""
        return cls.from_sheet_paths(CAP_SHEET_SPECIMEN_PATH)

    def entry(self, quarter: str) -> tuple[str, bool] | None:
        return self._entries.get(quarter)

    def quarters(self) -> tuple[str, ...]:
        return tuple(sorted(self._entries))


def load_cap_sheet(path) -> dict:
    """Load and sanity-check a quarterly cap-sheet JSON (D6 fixture shape)."""
    sheet = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("quarter", "specimen", "caps"):
        if key not in sheet:
            raise ValueError(f"cap sheet missing {key!r}: {path}")
    if not isinstance(sheet["caps"], dict):
        raise ValueError("cap sheet 'caps' must be an object")
    return sheet


def cap_sheet_hash(sheet: dict) -> str:
    """The hash a PremiumBudget must quote: sha256 of the sheet JSON."""
    return compute_fingerprint(sheet)


def bridge_licences_to_grantref(
    feed_id: str, at: datetime, grants_dir=None
) -> tuple[GrantRef, str]:
    """Adapt the licences engine's verdict into a rails ``GrantRef``.

    Returns ``(ref, reason)`` where reason is the licences verdict
    VERBATIM (D2): ``ok`` / ``specimen`` / ``no_grant`` /
    ``use_not_granted`` / ``expired`` / ``unknown_feed``. The ref carries
    that reason in ``state_detail`` and the licences fingerprint when a
    certificate exists on the shelf, so a registry attestation can admit
    it later without re-deriving anything.
    """
    licences_feed = PIT_TO_LICENCES_FEED.get(feed_id, feed_id)
    _allowed_commercial, grant_commercial, reason_commercial = licences_evaluate(
        licences_feed, "commercial", at, grants_dir=grants_dir
    )
    _allowed_financial, grant_financial, reason_financial = licences_evaluate(
        licences_feed, "hedge", at, grants_dir=grants_dir
    )
    shelf_grant = grant_commercial or grant_financial
    state_detail = (
        reason_commercial if reason_commercial != "ok" else reason_financial
    )
    fingerprint = shelf_grant.fingerprint if shelf_grant is not None else ""
    specimen = state_detail == "specimen"
    expiry = (
        shelf_grant.expiry_utc
        if shelf_grant is not None
        else "2026-01-01T00:00:00+00:00"
    )
    evidence = (
        shelf_grant.evidence_url
        if shelf_grant is not None
        else "https://invalid.example/no-certificate"
    )
    # Use the actual licence verdict, not the certificate's claims.
    # The rails preserve expired and missing-grant reasons separately.
    cert_permits_market = _allowed_commercial
    cert_permits_financial = _allowed_financial
    ref = GrantRef(
        name=f"bridged:{licences_feed}",
        issuer=shelf_grant.issuer if shelf_grant is not None else "licences engine",
        seat=shelf_grant.grantee_seat if shelf_grant is not None else "bridged-seat",
        scope=licences_feed,
        territory=shelf_grant.territory if shelf_grant is not None else "*",
        purpose=(
            "bridge probe (markets rehearsal)"
            if state_detail == "ok"
            else f"licences verdict recorded verbatim: {state_detail}"
        ),
        expiry=expiry,
        evidence_url=evidence,
        permits_financial_use=cert_permits_financial,
        permits_market_data_use=cert_permits_market,
        specimen=specimen,
        state_detail=state_detail,
        fingerprint=fingerprint,
    )
    return ref, state_detail


__all__ = [
    "PIT_TO_LICENCES_FEED",
    "DEFAULT_GRANT_STATE_PATH",
    "ENV_GRANT_REGISTRY",
    "CAP_SHEET_SPECIMEN_PATH",
    "REGISTRY_ENV_NOTE",
    "RegisteredGrants",
    "RegisteredCapSheets",
    "bridge_licences_to_grantref",
    "cap_sheet_hash",
    "compute_fingerprint",
    "load_cap_sheet",
]
