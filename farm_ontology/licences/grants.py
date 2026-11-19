"""Grant certificates v2. Expired, unknown, and specimen unlock nothing.

A grant is a machine-readable certificate that a feed's licence permits a
named use inside a territory until a timezone-aware expiry. Evaluation is
deterministic and fails closed: an expired grant, an unregistered feed, or a
`specimen` example never unlocks anything. The existing frozen `LicenceGrant`
record in `farm_ontology.model` is untouched; this module composes with it.

WS6 (docs/decision-infra-roadmap.md §2, deliverables 6.1-6.4).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

from farm_ontology.policy import CLASS_C_USES
from farm_ontology.timeutil import parse_time

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GRANTS_DIR = REPO_ROOT / "grants"
STATE_FILENAME = "state.json"

#: Feeds this engine knows how to issue certificates for. Anything else is
#: unknown and evaluates to a refusal, never to silence.
KNOWN_FEEDS: tuple[str, ...] = (
    "planet.psscene",
    "planet.planetary-variable.soil-water-content",
    "earth-engine.export",
    "open-meteo.jma-msm",
    "jma.hazard",
    "usdm.hazard",
    # WS7 market-lane feeds (registered 2026-11-18 after the arbitration
    # rehearsal D-finding: the financial unlock design needs these named,
    # not discovered as unknown_feed at rail time).
    "usda.wasde",
    "ams.soybean-bid",
    "fao.food-price-index",
    "imf.pcps",
    "worldbank.pink-sheet",
)

#: Use vocabulary a grant may name. Case is normalised to lowercase.
USES: frozenset[str] = frozenset(
    {
        "screening",
        "research",
        "operational",
        "commercial",
        "settlement",
        "hedge",
        "trigger",
        "nature-unit",
        "redistribution",
    }
)

#: The class C family (derived lowercase from policy.CLASS_C_USES: the
#: Settlement/hedge/trigger/nature-unit set that stays shut behind gates).
FINANCIAL_USES: frozenset[str] = frozenset(use.lower() for use in CLASS_C_USES)

_REQUIRED_FIELDS = (
    "grant_id",
    "issuer",
    "grantee_seat",
    "feeds",
    "uses",
    "territory",
    "purpose",
    "expiry_utc",
    "evidence_url",
)
_OPTIONAL_FIELDS = ("issued_at_utc", "permits_redistribution", "specimen", "specimen_note")


def _norm_tuple(raw, name: str) -> tuple[str, ...]:
    if isinstance(raw, str) or not isinstance(raw, (list, tuple)):
        raise ValueError(f"{name} must be a JSON array of strings")
    items = tuple(str(item).strip() for item in raw)
    if not items or any(not item for item in items):
        raise ValueError(f"{name} must be non-empty strings")
    if len(set(items)) != len(items):
        raise ValueError(f"{name} contains duplicates")
    return items


@dataclass(frozen=True)
class Grant:
    """Certificate v2. Immutable; `fingerprint` is derived, never stored."""

    grant_id: str
    issuer: str
    grantee_seat: str
    feeds: tuple[str, ...]
    uses: tuple[str, ...]
    territory: str
    purpose: str
    expiry_utc: str
    evidence_url: str
    issued_at_utc: str | None = None
    permits_redistribution: bool = False
    specimen: bool = False
    specimen_note: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "grant_id",
            "issuer",
            "grantee_seat",
            "territory",
            "purpose",
            "expiry_utc",
            "evidence_url",
        ):
            if not str(getattr(self, name) or "").strip():
                raise ValueError(f"Grant.{name} must be non-empty")
        object.__setattr__(self, "feeds", _norm_tuple(self.feeds, "feeds"))
        object.__setattr__(self, "uses", _norm_tuple(self.uses, "uses"))
        unknown = sorted(set(self.uses) - USES)
        if unknown:
            raise ValueError(f"Grant.uses names an unknown use: {unknown}")
        if not str(self.evidence_url).startswith(("http://", "https://")):
            raise ValueError("Grant.evidence_url must be a URL")
        for feed in self.feeds:
            if feed not in KNOWN_FEEDS:
                raise ValueError(f"Grant {self.grant_id} names unknown feed {feed!r}")
        if not isinstance(self.specimen, bool):
            raise ValueError("Grant.specimen must be a boolean")
        if not isinstance(self.permits_redistribution, bool):
            raise ValueError("Grant.permits_redistribution must be a boolean")
        parse_time(self.expiry_utc)  # naive or malformed expiry dies loudly here
        if self.issued_at_utc is not None:
            parse_time(self.issued_at_utc)

    @property
    def expiry_dt(self) -> datetime:
        """Timezone-aware expiry in UTC. The instant itself is still valid."""
        return parse_time(self.expiry_utc)

    @property
    def is_expired(self) -> bool:
        return self.expiry_dt < datetime.now(timezone.utc)

    @property
    def financial_uses(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.uses) & FINANCIAL_USES))

    def to_payload(self) -> dict:
        """JSON-round-trippable mapping of every stored field."""
        payload = {}
        for item in fields(self):
            value = getattr(self, item.name)
            payload[item.name] = list(value) if isinstance(value, tuple) else value
        return payload

    @property
    def fingerprint(self) -> str:
        """sha256 over the canonical JSON of the payload (sorted, compact)."""
        canonical = json.dumps(
            self.to_payload(),
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    @property
    def issued_dt(self) -> datetime | None:
        raw = self.issued_at_utc
        if not isinstance(raw, str) or not raw.strip():
            return None
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))

    def is_live_at(self, at: datetime) -> bool:
        """A specimen is never live; validity is inclusive of the expiry instant.

        An issuance instant, when declared, must have passed too — a
        certificate does not reach backwards before it existed."""
        if self.specimen:
            return False
        if self.expiry_dt.astimezone(timezone.utc) < at:
            return False
        issued = self.issued_dt
        return issued is None or issued.astimezone(timezone.utc) <= at

    def permits_use(self, use: str) -> bool:
        return normalize_use(use) in self.uses

    @classmethod
    def from_payload(cls, payload: Mapping, *, source: str = "") -> "Grant":
        """Strict loader: unknown keys die loudly, because a typo is a grant bug."""
        where = f" ({source})" if source else ""
        missing = [name for name in _REQUIRED_FIELDS if payload.get(name) in (None, "")]
        if missing:
            raise ValueError(f"grant missing fields{where}: {missing}")
        extra = sorted(set(payload) - set(_OPTIONAL_FIELDS) - set(_REQUIRED_FIELDS))
        if extra:
            raise ValueError(f"grant carries unknown fields{where}: {extra}")
        return cls(
            grant_id=str(payload["grant_id"]).strip(),
            issuer=str(payload["issuer"]).strip(),
            grantee_seat=str(payload["grantee_seat"]).strip(),
            feeds=_norm_tuple(payload["feeds"], "feeds"),
            uses=tuple(str(use).strip().lower() for use in _norm_tuple(payload["uses"], "uses")),
            territory=str(payload["territory"]).strip(),
            purpose=str(payload["purpose"]).strip(),
            expiry_utc=str(payload["expiry_utc"]).strip(),
            evidence_url=str(payload["evidence_url"]).strip(),
            issued_at_utc=payload.get("issued_at_utc") or None,
            permits_redistribution=bool(payload.get("permits_redistribution", False)),
            specimen=bool(payload.get("specimen", False)),
            specimen_note=payload.get("specimen_note") or None,
        )


def normalize_use(use: object) -> str:
    return str(use or "").strip().lower()


def _check_at(at: datetime) -> datetime:
    if not isinstance(at, datetime) or at.tzinfo is None:
        raise ValueError("`at` must be a timezone-aware datetime")
    return at.astimezone(timezone.utc)


def load_grants(directory: str | Path = DEFAULT_GRANTS_DIR) -> tuple[Grant, ...]:
    """Load every `*.json` grant in `directory`, skipping the `state.json` export.

    A missing directory or a malformed grant raises: loading is the repo's
    own housekeeping, and only the *evaluation* below fails closed.
    """
    directory = Path(directory)
    grants: list[Grant] = []
    seen: set[str] = set()
    for path in sorted(directory.glob("*.json")):
        if path.name == STATE_FILENAME:
            continue  # generated export, not a grant
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload = [payload]
        if not isinstance(payload, list):
            raise ValueError(f"{path.name} is neither a grant object nor a list")
        for item in payload:
            grant = Grant.from_payload(item, source=path.name)
            if grant.grant_id in seen:
                raise ValueError(f"duplicate grant_id {grant.grant_id!r} in {path.name}")
            seen.add(grant.grant_id)
            grants.append(grant)
    return tuple(sorted(grants, key=lambda grant: grant.grant_id))


def evaluate_grants(
    grants: Iterable[Grant], feed_id: str, use: object, at: datetime
) -> tuple[bool, Grant | None, str]:
    """Deterministic fail-closed evaluation: (allowed, grant|None, reason).

    Reason precedence among covering candidates:
    `use_not_granted` < `expired` < `specimen`; a live, non-specimen candidate
    wins outright, picking the earliest-expiring one (the binding constraint).
    """
    at = _check_at(at)
    if feed_id not in KNOWN_FEEDS:
        return False, None, "unknown_feed"
    normalized = normalize_use(use)
    if normalized not in USES:
        return False, None, "unknown_use"
    candidates = sorted(
        (
        grant
        for grant in grants
            if feed_id in grant.feeds
            and (grant.issued_dt is None or grant.issued_dt.astimezone(timezone.utc) <= at)
        ),
    key=lambda grant: grant.grant_id,
)
    if not candidates:
        return False, None, "no_grant"
    covering = [grant for grant in candidates if normalized in grant.uses]
    if not covering:
        # Nothing grants this use. When the feed's shelf holds only
        # specimens the operational truth is 'specimen': the next action is
        # replacing the specimen, not amending a use list.
        if candidates and all(grant.specimen for grant in candidates):
            return False, candidates[0], "specimen"
        return False, None, "use_not_granted"
    live = [grant for grant in covering if grant.is_live_at(at)]
    if live:
        winner = min(live, key=lambda grant: (grant.expiry_dt, grant.grant_id))
        return True, winner, "ok"
    real = [grant for grant in covering if not grant.specimen]
    if real:
        loser = max(real, key=lambda grant: grant.expiry_dt)
        return False, loser, "expired"
    return False, covering[0], "specimen"


def evaluate(
    feed_id: str, use: object, at: datetime, grants_dir: str | Path | None = None
) -> tuple[bool, Grant | None, str]:
    """Module-level convenience: load the repo grants, then evaluate."""
    grants = load_grants(DEFAULT_GRANTS_DIR if grants_dir is None else grants_dir)
    return evaluate_grants(grants, feed_id, use, at)


_STATE_SCHEMA = "farm-ontology.grants.state/1"


def _feed_reason(grants: tuple[Grant, ...], feed_id: str, at: datetime) -> tuple[bool, str]:
    """Fail-closed verdict for the financial family on one feed."""
    last_reason = "no_grant"
    for use in sorted(FINANCIAL_USES):
        allowed, _, reason = evaluate_grants(grants, feed_id, use, at)
        if allowed:
            return True, "ok"
        last_reason = reason
    return False, last_reason


_REASON_RANK = {"specimen": 0, "expired": 1, "use_not_granted": 2, "no_grant": 3}


def build_state(grants: Iterable[Grant], at: datetime) -> dict:
    """Machine-readable unlock-ledger snapshot. Specimens never flip a feed."""
    grants = tuple(grants)
    at = _check_at(at)
    feeds: dict[str, dict] = {}
    every_feed = list(KNOWN_FEEDS)
    every_feed.extend(feed for grant in grants for feed in grant.feeds if feed not in KNOWN_FEEDS)
    for feed_id in sorted(every_feed):
        allowed, reason = _feed_reason(tuple(grants), feed_id, at)
        feeds[feed_id] = {
            "use_class": "Screening",
            "permits_financial_use": allowed,
            "reason": reason,
        }
    return {
        "schema": _STATE_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluated_at": at.isoformat(),
        "fail_closed": True,
        "policy": "class C stays closed; a grant unlocks financial_use only for a valid non-specimen certificate",
        "feeds": feeds,
        "grants": [
            {**grant.to_payload(), "fingerprint": grant.fingerprint} for grant in grants
        ],
    }


def write_state(
    grants: Iterable[Grant],
    out_path: str | Path,
    at: datetime | None = None,
) -> Path:
    """Persist the ledger snapshot. Deterministic given the same `at`+grants."""
    at = at or datetime.now(timezone.utc)
    path = Path(out_path)
    path.write_text(
        json.dumps(build_state(grants, at), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path
