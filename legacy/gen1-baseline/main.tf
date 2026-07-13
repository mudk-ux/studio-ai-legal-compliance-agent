terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.38.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
  default     = "your-gcp-project-id"
}

variable "region" {
  description = "Target Vertex AI / Agent Runtime region"
  type        = string
  default     = "us-central1"
}

# Declarative Cloud Storage Staging Bucket for Multimodal Asset Intake
resource "google_storage_bucket" "intake_staging_bucket" {
  name                        = "${var.project_id}-ai-staging"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
}

# Declarative IAM Binding for Vertex AI Agent Runtime Execution Service Account
resource "google_project_iam_member" "agent_runtime_storage_access" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.agent_runtime_sa.email}"
}

resource "google_service_account" "agent_runtime_sa" {
  account_id   = "me-compliance-agent-runtime"
  display_name = "Studio Legal & VFX Compliance Agent Runtime Service Account"
}
