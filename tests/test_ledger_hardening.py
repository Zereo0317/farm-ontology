# -*- coding: utf-8 -*-
"""Producer tests for the ledger-hardening closures (fail on pre-fix code).

D1: concurrent appends on ONE shared JsonFileLedgerStore — every returned
    receipt must exist durably in the chain (old code silently dropped
    racing appends on Windows).
D2: gate refusals name their violated tokens via FinanceGateRejection
    (covered via the model suite; here the exception contract is pinned).
"""

import json
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from farm_ontology.markets import finance_controls as fc
from farm_ontology.markets.ledger_store import JsonFileLedgerStore

NOW = datetime(2026, 11, 27, tzinfo=timezone.utc)


def _intent(iid: str) -> "fc.HedgeOrderIntent":
    import decimal

    return fc.HedgeOrderIntent(
        intent_id=iid,
        artifact_sha256="b" * 64,
        instrument_family="short-cbot-soybean-futures",
        side="sell",
        quantity=decimal.Decimal("5000"),
        quantity_unit="bu",
        cap_sheet_sha256="c" * 64,
        rights_bundle_sha256="d" * 64,
        scope="own-account",
        feeds=("open-meteo.jma-msm", "usda.wasde"),
        territory="JP",
        uses_farmer_data=False,
        farmer_consent_grant_fingerprints=(),
        created_at=NOW,
        expires_at=NOW + timedelta(days=30),
    )


class ConcurrencyReceiptDurability(unittest.TestCase):
    def test_shared_instance_two_threads_all_receipts_durable(self):
        """Two threads × 50 appends on separate kinds through ONE shared
        store: 100/100 entries durable, sequences contiguous. (Old code
        raced at the file layer on Windows.)"""
        with tempfile.TemporaryDirectory() as tmp:
            store = JsonFileLedgerStore(Path(tmp))
            KIND = "hedge-intent-audit"
            errors = []

            def worker(base: int) -> None:
                previous = "0" * 64
                for n in range(50):
                    intent = _intent(f"i-{base}-{n}")
                    event = fc.IntentEvent(
                        sequence=n + 1,
                        intent_id=intent.intent_id,
                        intent_sha256=intent.fingerprint,
                        event_type=fc.EventType.PROPOSED,
                        at=NOW,
                        actor="tester",
                        evidence_sha256=intent.artifact_sha256,
                        previous_sha256=previous,
                        event_sha256="0" * 64,
                    )
                    try:
                        _, entry_hash = store.append(
                            f"{KIND}-{base}",
                            event,
                            intent_payload=intent.payload(),
                        )
                        previous = entry_hash
                    except Exception as error:  # loud failures acceptable
                        errors.append(f"{base}:{n}: {error}")

            threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=30)
            self.assertFalse(any(thread.is_alive() for thread in threads))
            self.assertEqual(errors, [], f"append failures: {errors}")
            for base in range(2):
                path = Path(tmp) / "ledgers" / f"{KIND}-{base}.jsonl"
                lines = path.read_text(encoding="utf-8").splitlines()
                self.assertEqual(
                    len(lines), 50, f"stream {base}: expected 50 durable entries"
                )
                # chain verifies contiguity
                for i, line in enumerate(lines, 1):
                    doc = json.loads(line)
                    self.assertEqual(doc["sequence"], i)


class RejectionDetail(unittest.TestCase):
    def test_finance_gate_rejection_is_a_value_error_with_tokens(self):
        self.assertTrue(issubclass(fc.FinanceGateRejection, ValueError))
        error = fc.FinanceGateRejection("finance approval gates did not pass: x; y", violations=("x", "y"))
        self.assertEqual(error.violations, ("x", "y"))


if __name__ == "__main__":
    unittest.main()
