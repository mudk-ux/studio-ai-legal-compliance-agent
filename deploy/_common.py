"""Shared deployment plumbing for Vertex AI Agent Engine."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from studio_compliance.config import AppConfig, load_config  # noqa: E402

# Pinned runtime requirements installed inside the Agent Engine container.
# Keep in sync with pyproject.toml.
RUNTIME_REQUIREMENTS = [
    "google-adk>=1.5",
    "google-cloud-aiplatform[adk,agent_engines]>=1.95",
    "pydantic>=2.7",
    "pydantic-settings>=2.2",
    "google-cloud-language>=2.13",
    "google-cloud-vision>=3.7",
    "google-cloud-videointelligence>=2.13",
    "google-cloud-storage>=2.14",
    "google-genai>=1.9",
]

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_PACKAGE = os.path.join(REPO_ROOT, "src", "studio_compliance")


def _stage_package() -> str:
    """Copy the package into a flat build dir and return that dir.

    The Agent Engine build tars extra_packages member paths verbatim and
    unpacks them under /code, so the archive must contain a TOP-LEVEL
    'studio_compliance/' member: a '..' component fails the build ("Member
    name contains '..'"), and an absolute path embeds the entire host
    directory tree, leaving the package un-importable inside the container
    (both failure modes observed live). Deploy therefore chdirs into this
    build dir and passes the bare relative name.
    """
    import shutil

    build_dir = os.path.join(REPO_ROOT, ".deploy_build")
    shutil.rmtree(build_dir, ignore_errors=True)
    shutil.copytree(
        SRC_PACKAGE,
        os.path.join(build_dir, "studio_compliance"),
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    return build_dir


def init_vertex(config: AppConfig) -> None:
    import vertexai

    vertexai.init(
        project=config.require_project(),
        location=config.location,
        staging_bucket=config.require_staging_bucket(),
    )


def env_vars_for_engine(config: AppConfig) -> dict[str, str]:
    """Propagate configuration into the deployed container. The HITL store must
    be a GCS prefix in a deployed environment (containers are ephemeral)."""
    hitl_store = config.hitl_store
    if not hitl_store.startswith("gs://"):
        hitl_store = f"{config.require_staging_bucket().rstrip('/')}/hitl_store"
        print(f"NOTE: STUDIO_HITL_STORE is local ({config.hitl_store}); the deployed "
              f"engine will use {hitl_store} instead.")
    return {
        "STUDIO_PROJECT_ID": config.require_project(),
        "STUDIO_LOCATION": config.location,
        "STUDIO_STAGING_BUCKET": config.require_staging_bucket(),
        "STUDIO_COORDINATOR_MODEL": config.coordinator_model,
        "STUDIO_SPECIALIST_MODEL": config.specialist_model,
        "STUDIO_HITL_STORE": hitl_store,
        "STUDIO_LLM_REQUIRED": "true" if config.llm_required else "false",
    }


def deploy(app, display_name: str, description: str):
    from vertexai import agent_engines

    config = load_config()
    init_vertex(config)
    build_dir = _stage_package()
    print(f"Deploying '{display_name}' to project "
          f"{config.project_id} ({config.location})...")
    original_cwd = os.getcwd()
    os.chdir(build_dir)
    try:
        remote = agent_engines.create(
            agent_engine=app,
            display_name=display_name,
            description=description,
            requirements=RUNTIME_REQUIREMENTS,
            extra_packages=["studio_compliance"],
            env_vars=env_vars_for_engine(config),
        )
    finally:
        os.chdir(original_cwd)
    print("\nDeployment complete.")
    print(f"  Resource name : {remote.resource_name}")
    print(f"  Display name  : {display_name}")
    print("\nNext steps:")
    print(f"  python deploy/smoke_test.py --engine-id {remote.resource_name}")
    print(f"  python evals/run_evals.py --target engine --engine-id {remote.resource_name} "
          "--assets-dir <your benchmark_assets dir>")
    return remote
