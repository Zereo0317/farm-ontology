output "archive_project_id" {
  value       = google_project.archive.project_id
  description = "Isolated farm archive project."
}

output "archive_bucket_name" {
  value       = google_storage_bucket.archive.name
  description = "Bucket configured for create/read archive access, unlocked 90-day retention, and snapshot-only expiration."
}

output "restore_bucket_name" {
  value       = google_storage_bucket.restore_drill.name
  description = "Private, seven-day scratch bucket used only by isolated restore drills."
}

output "exporter_service_account" {
  value       = google_service_account.exporter.email
  description = "Attach this account to farm-nightly-export after applying the reviewed plan."
}

output "scheduler_service_account" {
  value       = google_service_account.scheduler.email
  description = "Cloud Scheduler identity with invoke-only access to farm-nightly-export."
}

output "state_bucket_name" {
  value       = google_storage_bucket.terraform_state.name
  description = "Restricted remote state bucket; no runtime service account receives access."
}
