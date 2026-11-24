data "google_project" "source" {
  project_id = var.source_project_id
}

resource "google_service_account" "web_runtime" {
  project      = var.source_project_id
  account_id   = var.web_runtime_service_account_id
  display_name = "Farm field web runtime"
  description  = "Reads only farm OIDC membership documents; no keys are created."

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_service_account" "web_deployer" {
  project      = var.source_project_id
  account_id   = var.web_deployer_service_account_id
  display_name = "Farm web GitHub deployer"
  description  = "GitHub main-branch deployment identity for only farm-seges-ai-web."

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_iam_custom_role" "web_policy_reader" {
  project     = var.source_project_id
  role_id     = "farmWebPolicyReader"
  title       = "Farm web policy metadata reader"
  description = "Reads IAM policy metadata from the farm web access and records buckets."
  permissions = [
    "storage.buckets.getIamPolicy",
    "storage.managedFolders.getIamPolicy",
  ]
  stage = "GA"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_iam_custom_role" "web_project_policy_reader" {
  project     = var.source_project_id
  role_id     = "farmWebProjectPolicyReader"
  title       = "Farm web project policy metadata reader"
  description = "Reads only project IAM policy metadata required for fail-closed deployment checks."
  permissions = ["resourcemanager.projects.getIamPolicy"]
  stage       = "GA"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_service_account_iam_member" "github_main_can_use_web_deployer" {
  service_account_id = google_service_account.web_deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principal://iam.googleapis.com/projects/${data.google_project.source.number}/locations/global/workloadIdentityPools/github/subject/repo:Zereo0317/farm-ontology:ref:refs/heads/main"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_iam_member" "web_deployer_reads_project_policy" {
  project = var.source_project_id
  role    = google_project_iam_custom_role.web_project_policy_reader.name
  member  = "serviceAccount:${google_service_account.web_deployer.email}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_artifact_registry_repository_iam_member" "web_deployer_reads_images" {
  project    = var.source_project_id
  location   = var.region
  repository = "cloud-run-source-deploy"
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.web_deployer.email}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_cloud_run_v2_service_iam_member" "web_deployer_updates_web" {
  project  = var.source_project_id
  location = var.region
  name     = "farm-seges-ai-web"
  role     = "roles/run.developer"
  member   = "serviceAccount:${google_service_account.web_deployer.email}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_storage_bucket" "web_access" {
  project                     = var.source_project_id
  name                        = var.web_access_bucket_name
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  lifecycle {
    prevent_destroy = true

    precondition {
      condition = alltrue([
        var.web_access_bucket_name != var.source_record_bucket_name,
        var.web_access_bucket_name != var.archive_bucket_name,
        var.web_access_bucket_name != var.restore_bucket_name,
      ])
      error_message = "The membership bucket must be distinct from source, archive, and restore buckets."
    }
  }
}

resource "google_storage_bucket_iam_member" "web_runtime_reads_memberships" {
  bucket = google_storage_bucket.web_access.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.web_runtime.email}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_storage_bucket_iam_member" "web_membership_administrator" {
  bucket = google_storage_bucket.web_access.name
  role   = "roles/storage.objectUser"
  member = var.web_membership_administrator_member

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_storage_managed_folder" "web_tenant_records" {
  bucket        = var.source_record_bucket_name
  name          = "field-notes/farms/"
  force_destroy = false

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_storage_managed_folder_iam_member" "web_runtime_reads_tenant_records" {
  bucket         = google_storage_managed_folder.web_tenant_records.bucket
  managed_folder = google_storage_managed_folder.web_tenant_records.name
  role           = "roles/storage.objectViewer"
  member         = "serviceAccount:${google_service_account.web_runtime.email}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_storage_managed_folder_iam_member" "web_runtime_creates_tenant_records" {
  bucket         = google_storage_managed_folder.web_tenant_records.bucket
  managed_folder = google_storage_managed_folder.web_tenant_records.name
  role           = "roles/storage.objectCreator"
  member         = "serviceAccount:${google_service_account.web_runtime.email}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_secret_manager_secret_iam_member" "web_runtime_reads_planet_thumbnail" {
  project   = var.source_project_id
  secret_id = "Planet-labs"
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.web_runtime.email}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_storage_bucket_iam_member" "web_deployer_reads_access_policy" {
  bucket = google_storage_bucket.web_access.name
  role   = google_project_iam_custom_role.web_policy_reader.name
  member = "serviceAccount:${google_service_account.web_deployer.email}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_storage_bucket_iam_member" "web_deployer_reads_records_policy" {
  bucket = var.source_record_bucket_name
  role   = google_project_iam_custom_role.web_policy_reader.name
  member = "serviceAccount:${google_service_account.web_deployer.email}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_storage_managed_folder_iam_member" "web_deployer_reads_records_folder_policy" {
  bucket         = google_storage_managed_folder.web_tenant_records.bucket
  managed_folder = google_storage_managed_folder.web_tenant_records.name
  role           = google_project_iam_custom_role.web_policy_reader.name
  member         = "serviceAccount:${google_service_account.web_deployer.email}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_secret_manager_secret" "web_oidc_client" {
  project   = var.source_project_id
  secret_id = "farm-web-oidc-client-secret"

  replication {
    auto {}
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_secret_manager_secret" "web_session" {
  project   = var.source_project_id
  secret_id = "farm-web-session-secret"

  replication {
    auto {}
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_secret_manager_secret_iam_member" "web_runtime_reads_oidc_client" {
  project   = var.source_project_id
  secret_id = google_secret_manager_secret.web_oidc_client.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.web_runtime.email}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_secret_manager_secret_iam_member" "web_runtime_reads_session_secret" {
  project   = var.source_project_id
  secret_id = google_secret_manager_secret.web_session.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.web_runtime.email}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_secret_manager_secret_iam_member" "web_deployer_lists_oidc_client_versions" {
  project   = var.source_project_id
  secret_id = google_secret_manager_secret.web_oidc_client.secret_id
  role      = "roles/secretmanager.viewer"
  member    = "serviceAccount:${google_service_account.web_deployer.email}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_secret_manager_secret_iam_member" "web_deployer_lists_session_versions" {
  project   = var.source_project_id
  secret_id = google_secret_manager_secret.web_session.secret_id
  role      = "roles/secretmanager.viewer"
  member    = "serviceAccount:${google_service_account.web_deployer.email}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_service_account_iam_member" "web_deployer_can_attach_runtime" {
  service_account_id = google_service_account.web_runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.web_deployer.email}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_secret_manager_secret_iam_member" "web_secret_operator_adds_oidc_versions" {
  project   = var.source_project_id
  secret_id = google_secret_manager_secret.web_oidc_client.secret_id
  role      = "roles/secretmanager.secretVersionAdder"
  member    = var.terraform_state_operator_member

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_secret_manager_secret_iam_member" "web_secret_operator_adds_session_versions" {
  project   = var.source_project_id
  secret_id = google_secret_manager_secret.web_session.secret_id
  role      = "roles/secretmanager.secretVersionAdder"
  member    = var.terraform_state_operator_member

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_storage_bucket" "terraform_state" {
  provider                    = google.archive
  name                        = "farm-seges-ai-iac-state"
  project                     = google_project.archive.project_id
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

  depends_on = [google_project_service.archive_services]
}

resource "google_storage_bucket_iam_member" "terraform_state_operator" {
  bucket = google_storage_bucket.terraform_state.name
  role   = "roles/storage.objectAdmin"
  member = var.terraform_state_operator_member

  lifecycle {
    create_before_destroy = true
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
      with_state     = "LIVE"
    }
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      matches_prefix             = ["field-archive/"]
      matches_suffix             = [".tar.gz"]
      days_since_noncurrent_time = var.retention_days
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
      with_state     = "LIVE"
    }
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      matches_prefix             = ["restore-drills/"]
      days_since_noncurrent_time = 7
    }
  }

  lifecycle {
    prevent_destroy = true

    precondition {
      condition = alltrue([
        var.restore_bucket_name != var.archive_bucket_name,
        var.restore_bucket_name != var.source_record_bucket_name,
      ])
      error_message = "The restore bucket must be distinct from source and archive buckets."
    }
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
  account_id   = "farm-seges-ai-arch-sched"
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
  count = var.enable_archive_schedule ? 1 : 0

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
