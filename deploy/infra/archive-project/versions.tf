terraform {
  required_version = ">= 1.8.0"

  backend "gcs" {}

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 7.0, < 9.0"
    }
  }
}

provider "google" {
  project               = var.source_project_id
  region                = var.region
  user_project_override = true
  billing_project       = var.source_project_id
}

provider "google" {
  alias                 = "archive"
  project               = var.archive_project_id
  region                = var.region
  user_project_override = true
  billing_project       = var.source_project_id
}
