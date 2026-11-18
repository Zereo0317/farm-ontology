"""Lead capture (Sprint-K): the landing's two funnels land here.

POST /leads (through http_service.handle_lead_post) — one JSON body:
  { kind: pro-waitlist|governance-briefing|access-code-request,
    name, email, locale, consent:true, statement, org?, role?, needs?,
    source_landing_version? }
422 on consent/shape problems; the row lands at
leads/YYYYMMDD/<kind>-<stamp>-<hex>.json in the shared record store
(local dir or GCS), sha256-hashed, consent-stamped, replayable.
GET /leads (admin, ?token= or X-Access-Token) lists the newest 50.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets as _secrets
from datetime import datetime, timezone

from farm_ontology.record import _now, _stamp
from farm_ontology.record_store import open_backend

ALLOWED_KINDS = ("pro-waitlist", "governance-briefing", "access-code-request")
LOCALES = {"zh-TW", "zh-CN", "en", "ja", "th"}

_LANDING_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "LEADS_ALLOWED_ORIGINS",
        "https://farm-seges-ai-landing-451400509859.asia-east1.run.app",
    ).split(",")
    if origin.strip()
]


def _cors_headers(origin: str | None) -> dict:
    if origin and (origin in _LANDING_ORIGINS or "*" in _LANDING_ORIGINS):
        return {"Access-Control-Allow-Origin": origin, "Vary": "Origin"}
    return {}


def lead_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _store():
    from farm_ontology.record import record_dir

    return open_backend(record_dir())


def submit_lead(payload: dict, *, origin: str | None = None, at: datetime | None = None) -> dict:
    moment = at or _now()
    kind = payload.get("kind")
    if kind not in ALLOWED_KINDS:
        raise ValueError(f"lead kind must be one of {', '.join(ALLOWED_KINDS)} (got {kind!r})")
    if payload.get("consent") is not True:
        raise ValueError("consent must be explicitly true — the funnel records the sentence it showed")
    name = str(payload.get("name") or "").strip()
    email = str(payload.get("email") or "").strip()
    locale = payload.get("locale")
    if not name:
        raise ValueError("name is empty")
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("email does not look like an address")
    if locale not in LOCALES:
        raise ValueError(f"locale must be one of {', '.join(sorted(LOCALES))}")
    row = {
        "kind": kind,
        "name": name,
        "email": email,
        "org": str(payload.get("org") or "").strip() or None,
        "role": str(payload.get("role") or "").strip() or None,
        "needs": [str(n) for n in (payload.get("needs") or [])][:8],
        "locale": locale,
        "statement": str(payload.get("statement") or "")[:300],
        "source_landing_version": str(payload.get("source_landing_version") or "unknown"),
        "received_at": moment.astimezone(timezone.utc).isoformat(),
        "consent": True,
    }
    row["hash"] = lead_hash({k: v for k, v in row.items() if k != "hash"})
    store = _store()
    object_name = f"leads/{moment.astimezone(timezone.utc):%Y%m%d}/{kind}-{_stamp(moment)}-{_secrets.token_hex(3)}.json"
    store.write(object_name, (json.dumps(row, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    return {
        "ok": True,
        "file": object_name,
        "hash": row["hash"],
        "received_at": row["received_at"],
    }


def list_leads(limit: int = 50) -> dict:
    store = _store()
    names = store.list_paths("leads/", "**/*.json") or store.list_paths("leads/", "*.json")
    names.sort()
    leads = []
    for name in names[-limit:]:
        try:
            body = json.loads(store.read_text(name))
        except (OSError, ValueError):
            continue
        leads.append(
            {
                "file": name,
                "kind": body.get("kind"),
                "locale": body.get("locale"),
                "received_at": body.get("received_at"),
                "hash": body.get("hash"),
                "name": body.get("name"),
                "org": body.get("org"),
            }
        )
    return {"count": len(leads), "leads": leads}


def cors_preflight(origin: str | None) -> dict:
    headers = _cors_headers(origin)
    headers.update(
        {
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "86400",
        }
    )
    return headers
