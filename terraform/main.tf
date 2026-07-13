terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.30"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.location
}

data "google_project" "project" {
  project_id = var.project_id
}

# ---------------------------------------------------------------------------
# APIs required by the platform
# ---------------------------------------------------------------------------
resource "google_project_service" "required" {
  for_each = toset([
    "aiplatform.googleapis.com",
    "language.googleapis.com",
    "vision.googleapis.com",
    "videointelligence.googleapis.com",
    "storage.googleapis.com",
    "logging.googleapis.com",
  ])
  service            = each.key
  disable_on_destroy = false
}

# ---------------------------------------------------------------------------
# Staging bucket (Agent Engine staging, eval asset uploads, HITL store)
# ---------------------------------------------------------------------------
resource "google_storage_bucket" "staging" {
  name                        = var.staging_bucket_name
  location                    = var.location
  uniform_bucket_level_access = true
  force_destroy               = false

  lifecycle_rule {
    condition {
      age            = var.eval_asset_ttl_days
      matches_prefix = ["eval_assets/", "smoke/", "entities/"]
    }
    action {
      type = "Delete"
    }
  }

  # Reports are audit artifacts; kept much longer than working files but
  # still capped so the bucket cannot grow unbounded.
  lifecycle_rule {
    condition {
      age            = var.report_ttl_days
      matches_prefix = ["reports/"]
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.required]
}

# ---------------------------------------------------------------------------
# Runtime service account for the deployed engines
# ---------------------------------------------------------------------------
resource "google_service_account" "agent_runtime" {
  account_id   = "studio-compliance-agent"
  display_name = "Studio Compliance Agent Engine runtime"
}

resource "google_project_iam_member" "vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.agent_runtime.email}"
}

resource "google_storage_bucket_iam_member" "staging_rw" {
  bucket = google_storage_bucket.staging.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.agent_runtime.email}"
}

resource "google_project_iam_member" "log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.agent_runtime.email}"
}

# ---------------------------------------------------------------------------
# Google-managed Reasoning Engine service agent needs bucket access: deployed
# engines write HITL records and report JSONs to the staging bucket (verified
# live: runs crash on pending-review writes without this).
# NOTE: this service agent is created by Google on the FIRST Agent Engine
# deployment in the project. If `terraform apply` fails with "service account
# does not exist", deploy an engine once and re-apply, or set
# grant_reasoning_engine_agent=false to skip until it exists.
# ---------------------------------------------------------------------------
resource "google_storage_bucket_iam_member" "reasoning_engine_agent_rw" {
  count  = var.grant_reasoning_engine_agent ? 1 : 0
  bucket = google_storage_bucket.staging.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
}
