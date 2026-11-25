variable "source_project_id" {
  description = "Existing project that owns the farm record API and Cloud Run export job."
  type        = string
  default     = "seges-ai"

  validation {
    condition     = var.source_project_id == "seges-ai"
    error_message = "This stack is scoped to the shared seges-ai project; do not point it at a sibling project."
  }
}

variable "archive_project_id" {
  description = "New, isolated GCP project for farm archive records. Must be globally unique and farm-prefixed."
  type        = string
  default     = "farm-seges-ai-records-archive"

  validation {
    condition     = startswith(var.archive_project_id, "farm-seges-ai-records-archive") && var.archive_project_id != "seges-ai"
    error_message = "The archive project must be separate from seges-ai and use the farm-seges-ai prefix."
  }
}

variable "archive_bucket_name" {
  description = "Globally unique name for the archive bucket."
  type        = string
  default     = "farm-seges-ai-records-archive"

  validation {
    condition     = startswith(var.archive_bucket_name, "farm-seges-ai-records-archive") && var.archive_bucket_name != "farm-seges-ai-records"
    error_message = "Archive bucket names must use the dedicated records-archive prefix and differ from the fixed source bucket."
  }
}

variable "restore_bucket_name" {
  description = "Globally unique, private bucket used only for seven-day restore drills."
  type        = string
  default     = "farm-seges-ai-archive-restore"

  validation {
    condition     = startswith(var.restore_bucket_name, "farm-seges-ai-archive-restore")
    error_message = "The restore drill bucket must use the dedicated farm-prefixed name."
  }
}

variable "billing_account_id" {
  description = "Billing account used by the archive project, in the form 000000-000000-000000."
  type        = string
  sensitive   = true

  validation {
    condition     = can(regex("^[0-9A-Z]{6}-[0-9A-Z]{6}-[0-9A-Z]{6}$", var.billing_account_id))
    error_message = "Provide a valid Cloud Billing account ID."
  }
}

variable "archive_monthly_budget_twd" {
  description = "Owner-approved monthly alert budget for the archive project (TWD); choose within the existing farm-wide cost target."
  type        = number

  validation {
    condition     = var.archive_monthly_budget_twd > 0 && floor(var.archive_monthly_budget_twd) == var.archive_monthly_budget_twd
    error_message = "The archive budget must be a positive whole-number TWD amount."
  }
}

variable "budget_alert_email" {
  description = "Email recipient for archive-project budget thresholds."
  type        = string

  validation {
    condition     = can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.budget_alert_email))
    error_message = "Provide a valid budget notification email address."
  }
}

variable "exporter_deployer_service_account" {
  description = "Existing GitHub Actions/deployer service account that updates the farm archive job."
  type        = string

  validation {
    condition     = can(regex("^[^@]+@seges-ai\\.iam\\.gserviceaccount\\.com$", var.exporter_deployer_service_account))
    error_message = "The deployer identity must belong to the seges-ai project."
  }
}

variable "source_record_bucket_name" {
  description = "Existing source record bucket in the shared project."
  type        = string
  default     = "farm-seges-ai-records"

  validation {
    condition     = var.source_record_bucket_name == "farm-seges-ai-records"
    error_message = "The source bucket is fixed to farm-seges-ai-records."
  }
}

variable "web_access_bucket_name" {
  description = "Private farm-only bucket for OIDC membership documents in the service project."
  type        = string
  default     = "farm-seges-ai-access-v2"

  validation {
    condition     = startswith(var.web_access_bucket_name, "farm-seges-ai-access")
    error_message = "The membership bucket must use the dedicated farm-prefixed name."
  }
}

variable "web_runtime_service_account_id" {
  description = "Dedicated runtime identity for the farm field web service."
  type        = string
  default     = "farm-web-runtime"

  validation {
    condition     = var.web_runtime_service_account_id == "farm-web-runtime"
    error_message = "The web promotion workflow is pinned to the farm-web-runtime service account ID."
  }
}

variable "web_deployer_service_account_id" {
  description = "Dedicated GitHub Actions identity for the farm web deployment lane."
  type        = string
  default     = "farm-web-deployer"

  validation {
    condition     = var.web_deployer_service_account_id == "farm-web-deployer"
    error_message = "The GitHub OIDC binding and workflow are pinned to the farm-web-deployer service account ID."
  }
}

variable "web_membership_administrator_member" {
  description = "Owner-approved human or group principal that creates and revokes farm membership records."
  type        = string

  validation {
    condition     = can(regex("^(user|group):[^\\s]+$", var.web_membership_administrator_member))
    error_message = "Provide an explicitly authorized user: or group: membership-administrator principal."
  }
}

variable "region" {
  description = "Farm stack region."
  type        = string
  default     = "asia-east1"

  validation {
    condition     = var.region == "asia-east1"
    error_message = "The farm stack region is fixed to asia-east1."
  }
}

variable "retention_days" {
  description = "Initially-unlocked archive retention period. The owner must approve before changing it."
  type        = number
  default     = 90

  validation {
    condition     = var.retention_days == 90
    error_message = "This rollout uses the approved initial 90-day retention period."
  }
}

variable "enable_archive_schedule" {
  description = "Opt in only after the archive smoke execution and isolated restore drill are accepted."
  type        = bool
  default     = false
}

variable "terraform_state_operator_member" {
  description = "IAM principal that runs Terraform and needs object-level access to the remote state bucket."
  type        = string

  validation {
    condition     = can(regex("^(user|serviceAccount|group):[^\\s]+$", var.terraform_state_operator_member))
    error_message = "Provide one explicit user:, serviceAccount:, or group: principal for Terraform state access."
  }
}
