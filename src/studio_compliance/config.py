"""Environment-driven configuration.

Every deployment-specific value (project, region, bucket, models) comes from
environment variables prefixed with ``STUDIO_`` (see config.env.example).
Nothing in the codebase hardcodes a project or bucket, so any operator can
deploy to their own GCP environment.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigError(RuntimeError):
    """Raised when required configuration is missing for the requested operation."""


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="STUDIO_", env_file=".env", extra="ignore")

    project_id: str | None = None
    location: str = "us-central1"
    staging_bucket: str | None = None

    coordinator_model: str = "gemini-2.5-flash"
    specialist_model: str = "gemini-2.5-pro"

    hitl_store: str = "./hitl_store"
    llm_required: bool = True

    # Cloud Natural Language caps requests at ~1MB of text; we chunk below that.
    nl_chunk_bytes: int = 900_000
    # LOGO_RECOGNITION on a 12-minute 1080p file exceeds 600s; 1800s covers
    # feature-trailer-length assets. Override via STUDIO_VIDEO_OPERATION_TIMEOUT_S.
    video_operation_timeout_s: int = 1800

    def require_project(self) -> str:
        if not self.project_id:
            raise ConfigError(
                "STUDIO_PROJECT_ID is not set. Copy config.env.example to .env and "
                "fill in your GCP project, or export the variable."
            )
        return self.project_id

    def require_staging_bucket(self) -> str:
        if not self.staging_bucket:
            raise ConfigError(
                "STUDIO_STAGING_BUCKET is not set (needed for deployment and remote "
                "evals). Set it to a gs:// bucket in your project."
            )
        if not self.staging_bucket.startswith("gs://"):
            raise ConfigError(
                f"STUDIO_STAGING_BUCKET must be a gs:// URI, got {self.staging_bucket!r}"
            )
        return self.staging_bucket


def load_config() -> AppConfig:
    """Load configuration from the environment / .env file."""
    return AppConfig()
