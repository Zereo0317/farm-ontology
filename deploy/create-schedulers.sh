#!/usr/bin/env bash
# WS2 scheduled ingestion: one Cloud Run JOB per worker + one Cloud
# Scheduler binding per job, all time-zone Asia/Tokyo.
#
# Pattern proven by infra (deploy/create-observation-job.sh): deploy the
# job (idempotent re-deploy), then bind a schedule. Jobs run
# `python pipelines/run_worker.py <job>` (worker image) against the
# DURABLE record bucket with the compute service account, which already
# holds storage.objectUser on farm-seges-ai-records and the run.invoker
# surface for Cloud Run jobs.
#
# Idempotence: `jobs deploy` updates in place; schedules are created
# only when missing (a replace deletes history, so we leave standing
# schedules alone unless UPDATE_SCHEDULES=1).
#
# Usage:
#   ./create-schedulers.sh                          # all four jobs
#   WORKER_IMAGE=<uri> ./create-schedulers.sh       # custom worker image
#   UPDATE_SCHEDULES=1 ./create-schedulers.sh       # replace schedules too
#
# Deletion/removal is NOT scripted here on purpose: schedules are the
# only thing that spends money idly; removing one is a deliberate
# `gcloud run jobs schedules delete` (see scheduler-setup.md).
set -euo pipefail

PROJECT=${GCP_PROJECT:-seges-ai}
REGION=${FARM_REGION:-asia-east1}
SA=${WORKER_SA:-451400509859-compute@developer.gserviceaccount.com}
IMAGE=${WORKER_IMAGE:?set WORKER_IMAGE=<worker-image-uri>; see deploy/scheduler-setup.md}
TIMEZONE=${WORKER_TIMEZONE:-Asia/Tokyo}

ENV_VARS="FARM_RECORD_BACKEND=gcs,FARM_RECORD_BUCKET=farm-seges-ai-records,GCP_PROJECT=$PROJECT"

schedule_for() {
    case "$1" in
        weather-hourly) echo "20 * * * *" ;;
        planet-nightly) echo "0 22 * * *" ;;
        hazard-daily)   echo "30 7 * * *" ;;
        ndvi-weekly)    echo "0 6 * * MON" ;;
        *) echo "" ;;
    esac
}

create_one() {
    local job="$1"
    local cron
    cron="$(schedule_for "$job")"

    gcloud run jobs deploy "farm-worker-$job" \
        --project="$PROJECT" --region="$REGION" \
        --image="$IMAGE" \
        --service-account="$SA" \
        --max-retries=1 \
        --task-timeout=10m \
        --args="$job" \
        --set-env-vars="$ENV_VARS"

    local schedule_name="sched-$job"
    if gcloud run jobs schedules describe "$schedule_name" \
        --project="$PROJECT" --location="$REGION" >/dev/null 2>&1; then
        if [[ "${UPDATE_SCHEDULES:-0}" == "1" ]]; then
            gcloud run jobs schedules delete "$schedule_name" \
                --project="$PROJECT" --location="$REGION" --quiet
            gcloud run jobs create-schedule "$schedule_name" \
                --project="$PROJECT" --location="$REGION" \
                --job="farm-worker-$job" \
                --schedule="$cron" \
                --time-zone="$TIMEZONE"
        else
            echo "schedule $schedule_name already exists; leaving it (UPDATE_SCHEDULES=1 to replace)"
        fi
    else
        gcloud run jobs create-schedule "$schedule_name" \
            --project="$PROJECT" --location="$REGION" \
            --job="farm-worker-$job" \
            --schedule="$cron" \
            --time-zone="$TIMEZONE"
    fi
    echo "bound: $schedule_name -> farm-worker-$job ($cron $TIMEZONE)"
}

for job in weather-hourly planet-nightly hazard-daily ndvi-weekly; do
    create_one "$job"
done

echo
echo "All four workers deployed and scheduled. First manual checks:"
echo "  gcloud run jobs execute farm-worker-weather-hourly --project=$PROJECT --region=$REGION --wait"
echo "  gsutil ls gs://farm-seges-ai-records/pipelines/run-log/"
