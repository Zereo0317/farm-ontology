"""CLI for the grant certificate engine.

    python -m farm_ontology.licences.cli list
    python -m farm_ontology.licences.cli evaluate --feed planet.psscene --use settlement
    python -m farm_ontology.licences.cli state [--out PATH]

Stdlib only. `evaluate` exits 1 (denied) or 0 (allowed) and prints one JSON
line, so shell pipelines can gate on it.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from farm_ontology.licences.grants import (
    DEFAULT_GRANTS_DIR,
    STATE_FILENAME,
    build_state,
    evaluate_grants,
    load_grants,
)
from farm_ontology.licences.ledger import expiry_alarm_rows
from farm_ontology.timeutil import parse_time

_UNKNOWN = "__unknown__"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m farm_ontology.licences.cli",
        description="grant certificate engine (WS6): list | evaluate | state",
    )
    parser.add_argument("--dir", default=str(DEFAULT_GRANTS_DIR), help="grants directory")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="list grants and expiry alarm rows")
    p_list.add_argument("--at", default=None, help="ISO-8601 aware instant (default now)")

    p_eval = sub.add_parser("evaluate", help="evaluate (allowed, grant, reason)")
    p_eval.add_argument("--feed", required=True)
    p_eval.add_argument("--use", required=True)
    p_eval.add_argument("--at", default=None, help="ISO-8601 aware instant (default now)")

    p_state = sub.add_parser("state", help="write grants/state.json")
    p_state.add_argument("--out", default=None, help=f"default <dir>/{STATE_FILENAME}")
    p_state.add_argument("--at", default=None, help="ISO-8601 aware instant (default now)")
    return parser


def main(argv: list[str] | None = None) -> int:
    ns = _parser().parse_args(argv)
    at = parse_time(ns.at) if ns.at else datetime.now(timezone.utc)
    if ns.command == "list":
        grants = load_grants(ns.dir)
        for grant in grants:
            flag = "SPECIMEN" if grant.specimen else "executed"
            print(
                json.dumps(
                    {
                        "grant_id": grant.grant_id,
                        "issuer": grant.issuer,
                        "seat": grant.grantee_seat,
                        "feeds": list(grant.feeds),
                        "uses": list(grant.uses),
                        "territory": grant.territory,
                        "expiry_utc": grant.expiry_utc,
                        "status": flag,
                        "fingerprint": grant.fingerprint,
                    },
                    ensure_ascii=False,
                )
            )
        for row in expiry_alarm_rows(grants, at):
            state = "EXPIRED" if row["expired"] else "live"
            print(f"alarm {state} {row['grant_id']} expiry {row['expiry_utc']}", file=sys.stderr)
        return 0
    if ns.command == "evaluate":
        grants = load_grants(ns.dir)
        allowed, grant, reason = evaluate_grants(grants, ns.feed, ns.use, at)
        print(
            json.dumps(
                {
                    "feed": ns.feed,
                    "use": ns.use,
                    "at": at.isoformat(),
                    "allowed": allowed,
                    "grant": grant.grant_id if grant is not None else None,
                    "reason": reason,
                },
                ensure_ascii=False,
            )
        )
        return 0 if allowed else 1
    if ns.command == "state":
        grants = load_grants(ns.dir)
        out = ns.out or (str(ns.dir).rstrip("/\\") + "/" + STATE_FILENAME)
        from farm_ontology.licences.grants import write_state

        path = write_state(grants, out, at)
        print(path)
        return 0
    return 2  # argparse guarantees a known subcommand; defensive only


if __name__ == "__main__":
    raise SystemExit(main())
