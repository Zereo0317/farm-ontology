#!/usr/bin/env bash
# Post-deploy traffic pin for the farm-seges-ai services.
#
# WHY THIS EXISTS (the traffic-shift gotcha): on this service a --source
# deploy creates and readies a new revision but does NOT always move the
# 100% traffic tag to it (2026-11-17 ship day, backend-live.md note 2).
# Rollouts must end with an explicit update-traffic --to-latest, checked
# against latestCreatedRevisionName.
#
# Usage:
#   ./set-traffic.sh                # staging, then prod (asks gcloud for state)
#   ./set-traffic.sh staging        # staging only
#   ./set-traffic.sh prod           # prod only
# Requires: gcloud authenticated on project seges-ai.
set -euo pipefail

PROJECT=${GCP_PROJECT:-seges-ai}
REGION=${FARM_REGION:-asia-east1}

pick() {
    case "$1" in
        staging) printf '%s\n' farm-seges-ai-staging ;;
        prod) printf '%s\n' farm-seges-ai ;;
        *) printf '%s\n' farm-seges-ai-staging farm-seges-ai ;;
    esac
}

for service in $(pick "${1:-all}"); do
    before=$(gcloud run services describe "$service" \
        --project="$PROJECT" --region="$REGION" \
        --format='value(status.traffic[0].percent,status.traffic[0].revisionName)')
    echo "== $service before: percent/revision = ${before:-<none>}"
    gcloud run services update-traffic "$service" \
        --project="$PROJECT" --region="$REGION" --to-latest
    after=$(gcloud run services describe "$service" \
        --project="$PROJECT" --region="$REGION" \
        --format='value(status.traffic[0].percent,status.traffic[0].revisionName) created=status.latestCreatedRevisionName' 2>/dev/null || true)
    after=$(gcloud run services describe "$service" \
        --project="$PROJECT" --region="$REGION" \
        --format='value(status.traffic[0].percent,status.traffic[0].revisionName)')
    latest=$(gcloud run services describe "$service" \
        --project="$PROJECT" --region="$REGION" \
        --format='value(status.latestCreatedRevisionName)')
    echo "== $service after: percent/revision = ${after}"
    pinned=$(gcloud run services describe "$service" \
        --project="$PROJECT" --region="$REGION" \
        --format='flattened(status.traffic[0].revisionName)' 2>/dev/null | tail -n 1 || true)
    if [[ "${after#* }" == "$latest" ]]; then
        echo "== $service: traffic pinned to latest revision ${latest} OK"
    else
        echo "== $service: WARNING traffic (${after#* }) != latest ($latest); re-check manually" >&2
        exit 1
    fi
done
