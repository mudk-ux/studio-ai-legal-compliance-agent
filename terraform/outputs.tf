output "staging_bucket" {
  value       = "gs://${google_storage_bucket.staging.name}"
  description = "Set STUDIO_STAGING_BUCKET to this value"
}

output "runtime_service_account" {
  value       = google_service_account.agent_runtime.email
  description = "Service account for the Agent Engine runtime"
}
