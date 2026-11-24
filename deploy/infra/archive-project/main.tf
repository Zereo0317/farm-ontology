data "google_project" "source" {
  project_id = var.source_project_id
}

resource "google_storage_bucket" "terraform_state" {
  name                        = "farm-seges-ai-iac-state"
  project                     = var.source_project_id
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  versioning {
    enabled = true
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project" "archive" {
  project_id          = var.archive_project_id
  name                = "Seges farm records archive"
  billing_account     = var.billing_account_id
  auto_create_network = false

  labels = {
    product     = "farm-seges-ai"
    environment = "production"
    purpose     = "records-archive"
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_service" "archive_services" {
  provider = google.archive
  for_each = toset([
    "storage.googleapis.com",
    "monitoring.googleapis.com",
    "billingbudgets.googleapis.com",
  ])

  project            = google_project.archive.project_id
  service            = each.value
  disable_on_destroy = false

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_storage_bucket" "archive" {
  provider                    = google.archive
  name                        = var.archive_bucket_name
  project                     = google_project.archive.project_id
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  versioning {
    enabled = true
  }

  retention_policy {
    retention_period = var.retention_days * 86400
    is_locked        = false
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age            = var.retention_days
      matches_prefix = ["field-archive/"]
      matches_suffix = [".tar.gz"]
      is_live        = true
    }
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age            = var.retention_days
      matches_prefix = ["field-archive/"]
      matches_suffix = [".tar.gz"]
      is_live        = false
    }
  }

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_project_service.archive_services]
}

resource "google_storage_bucket" "restore_drill" {
  provider                    = google.archive
  name                        = var.restore_bucket_name
  project                     = google_project.archive.project_id
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age            = 7
      matches_prefix = ["restore-drills/"]
      is_live        = true
    }
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age            = 7
      matches_prefix = ["restore-drills/"]
      is_live        = false
    }
  }

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_project_service.archive_services]
}

resource "google_service_account" "exporter" {
  project      = var.source_project_id
  account_id   = "farm-seges-ai-archive-exporter"
  display_name = "Farm archive exporter"
  description  = "Reads farm records, writes archive snapshots, and records export run evidence. No secrets or unrelated service access."

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_service_account_iam_member" "deployer_can_attach_exporter" {
  service_account_id = google_service_account.exporter.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${var.exporter_deployer_service_account}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_iam_member" "exporter_logs" {
  project = var.source_project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.exporter.email}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_storage_bucket_iam_member" "exporter_reads_source" {
  bucket = var.source_record_bucket_name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.exporter.email}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_storage_bucket_iam_member" "exporter_writes_only_pipeline_evidence" {
  bucket = var.source_record_bucket_name
  role   = "roles/storage.objectUser"
  member = "serviceAccount:${google_service_account.exporter.email}"

  condition {
    title       = "farm_archive_export_pipeline_evidence_only"
    description = "The archive job may update only its run-log and alert artifacts in the source bucket."
    expression = format(
      "resource.name.startsWith('projects/_/buckets/%s/objects/pipelines/run-log/') || resource.name.startsWith('projects/_/buckets/%s/objects/pipelines/alerts/')",
      var.source_record_bucket_name,
      var.source_record_bucket_name,
    )
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_storage_bucket_iam_member" "exporter_creates_archive" {
  provider = google.archive
  bucket   = google_storage_bucket.archive.name
  role     = "roles/storage.objectCreator"
  member   = "serviceAccount:${google_service_account.exporter.email}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_storage_bucket_iam_member" "exporter_verifies_archive" {
  provider = google.archive
  bucket   = google_storage_bucket.archive.name
  role     = "roles/storage.objectViewer"
  member   = "serviceAccount:${google_service_account.exporter.email}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_service_account" "scheduler" {
  project      = var.source_project_id
  account_id   = "farm-seges-ai-archive-scheduler"
  display_name = "Farm archive scheduler invoker"
  description  = "Can invoke only the farm nightly-export Cloud Run job."

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_cloud_run_v2_job_iam_member" "scheduler_can_run_export" {
  project  = var.source_project_id
  location = var.region
  name     = "farm-nightly-export"
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler.email}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_cloud_scheduler_job" "archive_export" {
  project          = var.source_project_id
  region           = var.region
  name             = "farm-sched-record-export"
  description      = "Exports a farm record snapshot twice per hour to the isolated archive project."
  schedule         = "*/30 * * * *"
  time_zone        = "Asia/Tokyo"
  attempt_deadline = "320s"

  retry_config {
    retry_count          = 1
    max_retry_duration   = "300s"
    min_backoff_duration = "5s"
    max_backoff_duration = "60s"
    max_doublings        = 1
  }

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${data.google_project.source.number}/jobs/farm-nightly-export:run"

    oauth_token {
      service_account_email = google_service_account.scheduler.email
      scope                 = "https://www.googleapis.com/auth/cloud-platform"
    }
  }

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_cloud_run_v2_job_iam_member.scheduler_can_run_export]
}

resource "google_monitoring_notification_channel" "archive_budget" {
  provider     = google.archive
  project      = google_project.archive.project_id
  display_name = "Farm archive budget email"
  type         = "email"

  labels = {
    email_address = var.budget_alert_email
  }

  depends_on = [google_project_service.archive_services]

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_billing_budget" "archive" {
  billing_account = var.billing_account_id
  display_name    = "Farm archive monthly cost guard"

  budget_filter {
    projects = ["projects/${google_project.archive.number}"]
  }

  amount {
    specified_amount {
      currency_code = "TWD"
      units         = tostring(var.archive_monthly_budget_twd)
    }
  }

  threshold_rules {
    threshold_percent = 0.5
    spend_basis       = "CURRENT_SPEND"
  }
  threshold_rules {
    threshold_percent = 0.9
    spend_basis       = "CURRENT_SPEND"
  }
  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "CURRENT_SPEND"
  }

  all_updates_rule {
    monitoring_notification_channels = [google_monitoring_notification_channel.archive_budget.id]
    disable_default_iam_recipients   = true
    schema_version                   = "1.0"
  }

  lifecycle {
    prevent_destroy = true
  }
}
