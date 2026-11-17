#!/usr/bin/env bash
# One-shot Cloud Run JOB that writes ONE real observation round-trip through
# the configured record backend, under the runtime service account. Used to
# prove durability (record survives because it lands in GCS, not the
# ephemeral container FS) and doubles as the post-recycle acceptance drill.
#
# Usage:
#   ./create-observation-job.sh                       # creates + runs the job
#   gcloud run jobs execute farm-observation-drill --region=asia-east1 --wait
#
# The job runs farm_ontology/record_store.py's drill entry point, which writes
# a dry-run observation (synthetic 0N,0E point, labelled as such) and prints a
# JSON summary. Exit 0 == round trip through the record store succeeded.
set -euo pipefail

PROJECT=${GCP_PROJECT:-seges-ai}
REGION=${FARM_REGION:-asia-east1}
IMAGE=${DRILL_IMAGE:-asia-east1-docker.pkg.dev/seges-ai/farm/drill:obsdrill-20261117d}
JOB=farm-observation-drill

gcloud run jobs deploy "$JOB" \
    --project="$PROJECT" --region="$REGION" \
    --image="$IMAGE" \
    --service-account=451400509859-compute@developer.gserviceaccount.com \
    --region="$REGION" \
    --max-retries=1 \
    --task-timeout=10m \
    --args=python,-m,farm_ontology.record_store \
    --set-env-vars FARM_RECORD_BACKEND=gcs,FARM_RECORD_BUCKET=farm-seges-ai-records,GCP_PROJECT="$PROJECT"

gcloud run jobs execute "$JOB" --project="$PROJECT" --region="$REGION" --wait
