# Record retention policy — field archive (APPROVAL-GATED; nothing is enforced yet)

Status 2026-11-18: **POLICY DOCUMENT ONLY.** No Object Lifecycle rule
exists on `farm-seges-ai-records`, no delete job exists, and
`pipelines/record_export.py` is deliberately incapable of deleting
anything. Activating ANY rule below requires the product owner's
approval (cost/data-loss tradeoffs belong to a human).

## Current unconditional floor (active, needs no approval)

- Bucket `farm-seges-ai-records` has **object versioning ON**: every
  overwrite keeps the prior generation until it is explicitly deleted.
- Default **soft-delete retention 7 days** (GCS default at creation,
  2026-11-17): accidentally deleted objects are restorable
  (`gcloud storage restore soft-deleted ...`) for a week.
- Snapshots are ADDITIVE (`record-snapshot-<utcstamp>.tar.gz` never
  collides), so versioning churn on archive objects should not occur
  at all; manifests rewrite their OWN day-file (small, versioned).

## Proposed policy (FOR APPROVAL — 90-day rolling export window)

| Aspect | Proposal | Rationale |
| --- | --- | --- |
| Snapshot retention | 90 days rolling, exact-day `deltas` kept forever? NO — keep ALL daily full snapshots' manifest ROWS forever (tiny NDJSON), delete snapshot OBJECTS older than 90 days | manifest is the permanent index; 90 d of blobs is the pragmatic floor stated by roadmap WS1.2 |
| Mechanism | Object Lifecycle rule on `field-archive/` prefix only: `Delete` when `Age >= 90d`, `IsLive` versions only | native, free, no job to babysit |
| Original record objects (`field-notes/**`) | NEVER lifecycle-managed; correctness demands versioning forever (record = the honesty product) | the record itself must never lose generations |
| `pipelines/**` run-log/alert rows | keep ≥ 1 year (audit trail), revisit when size warrants | cheap, high forensic value |
| Early intervention | NONE — belt (lifecycle, 90 d) lives fine with suspenders (manual quarterly cleanup review) | solo-founder simplicity |

Activation command (WHEN APPROVED):

```bash
cat <<'EOF' > /tmp/lifecycle.json
{
  "rule": [
    {
      "action": {"type": "Delete"},
      "condition": {"age": 90, "matchesPrefix": ["field-archive/"]}
    }
  ]
}
EOF
gcloud storage buckets update gs://farm-seges-ai-records \
  --lifecycle-file=/tmp/lifecycle.json
gcloud storage buckets describe gs://farm-seges-ai-records \
  --format=json(configuration.lifecycle)   # VERIFY before considering it done
```

Guardrail: `matchesPrefix` is mandatory — a bare age rule would silently
eat the RECORD (the opposite of this whole workstream).
