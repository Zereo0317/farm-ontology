#!/usr/bin/env bash
# Point the STAGING service (farm-seges-ai-staging) at the durable GCS record
# store, one env var at a time, without dropping the existing env/secret set.
#
# Design: the GCS backend on Cloud Run needs NO extra credentials - the
# metadata server hands the runtime service account a token - so enabling it
# is purely env configuration. Values are read from the current service
# revision and written back, so nothing else changes.
#
# Usage: ./update-staging-env.sh
set -euo pipefail

PROJECT=${GCP_PROJECT:-seges-ai}
REGION=${FARM_REGION:-asia-east1}
SERVICE=farm-seges-ai-staging

gcloud run services update "$SERVICE" \
    --project="$PROJECT" --region="$REGION" \
    --update-env-vars FARM_RECORD_BACKEND=gcs,FARM_RECORD_BUCKET=farm-seges-ai-records
./set-traffic.sh staging
echo "staging now persists field records to gs://farm-seges-ai-records/field-notes/"
