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
  description = "Private remote state bucket in the isolated archive project with an explicit Terraform operator grant."
}

output "web_runtime_service_account" {
  value       = google_service_account.web_runtime.email
  description = "Dedicated web service identity; attach only after OIDC and membership-store configuration is ready."
}

output "web_access_bucket_name" {
  value       = google_storage_bucket.web_access.name
  description = "Private farm-only bucket containing web OIDC membership documents."
}

output "web_record_managed_folder" {
  value       = google_storage_managed_folder.web_tenant_records.name
  description = "Tenant record prefix for which the web runtime receives read and create-only permissions."
}

output "web_deployer_service_account" {
  value       = google_service_account.web_deployer.email
  description = "Dedicated main-branch deploy identity with service-scoped Cloud Run update permission."
}

output "web_membership_administrator_member" {
  value       = var.web_membership_administrator_member
  description = "Mirror this owner-authorized principal to GitHub FARM_WEB_MEMBERSHIP_ADMINISTRATOR for exact IAM policy checks."
}
