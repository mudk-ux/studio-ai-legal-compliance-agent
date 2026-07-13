variable "project_id" {
  description = "GCP project to deploy into"
  type        = string
}

variable "location" {
  description = "Region for Vertex AI and the staging bucket"
  type        = string
  default     = "us-central1"
}

variable "staging_bucket_name" {
  description = "Globally-unique name for the staging bucket (without gs://)"
  type        = string
}

variable "eval_asset_ttl_days" {
  description = "Days before uploaded eval/smoke assets are auto-deleted"
  type        = number
  default     = 14
}

variable "report_ttl_days" {
  description = "Days to retain generated compliance report JSONs under reports/ (audit artifacts)"
  type        = number
  default     = 90
}

variable "grant_reasoning_engine_agent" {
  description = "Grant the Google-managed Reasoning Engine service agent write access to the staging bucket (required for deployed engines; the agent must already exist — see main.tf note)"
  type        = bool
  default     = true
}
