"""
deploy_adk2_engine.py: Deploys isolated ADK 2.0 Multi-Agent Orchestrator
to Gemini Enterprise Agent Platform (formerly Vertex AI) under display name
`ADK2EnterpriseComplianceOrchestrator` without touching existing deployments.
"""

import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

import vertexai
from vertexai.preview import reasoning_engines
from adk2_multiagent_studio.src.orchestration import ADK2MultiAgentGraphOrchestrator

PROJECT_ID = "your-gcp-project-id"
LOCATION = "us-central1"
STAGING_BUCKET = "gs://your-staging-bucket"


class ADK2EnterpriseComplianceOrchestratorApp:
    """Serverless application wrapper for true ADK 2.0 multi-agent orchestration."""

    def __init__(self):
        self.orchestrator = ADK2MultiAgentGraphOrchestrator()

    def query(self, asset_path: str, asset_type: str, constraints_data: dict) -> dict:
        return self.orchestrator.execute_adk_workflow(
            asset_path, asset_type, constraints_data
        )


def deploy_adk2_orchestrator():
    print("================================================================================")
    print("🚀 DEPLOYING ADK 2.0 MULTI-AGENT STUDIO TO GEMINI ENTERPRISE AGENT PLATFORM")
    print(f"   Project: {PROJECT_ID} | Region: {LOCATION}")
    print("================================================================================\n")

    vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)

    remote_engine = reasoning_engines.ReasoningEngine.create(
        ADK2EnterpriseComplianceOrchestratorApp(),
        requirements=[
            "google-adk>=1.0.0",
            "google-genai>=1.9.0",
            "google-cloud-aiplatform>=1.45.0",
            "google-cloud-language>=2.10.0",
            "google-cloud-vision>=3.4.0",
            "google-cloud-videointelligence>=2.11.0",
            "google-cloud-storage>=2.10.0",
            "google-cloud-logging>=3.8.0",
            "pydantic>=2.0.0",
        ],
        extra_packages=["src", "adk2_multiagent_studio"],
        display_name="ADK2EnterpriseComplianceOrchestrator",
        description="True Google ADK 2.0 Multi-Agent Orchestrator with explicit HITL execution pause hooks",
    )

    print("\n================================================================================")
    print("✅ DEPLOYMENT TO GEMINI ENTERPRISE AGENT PLATFORM COMPLETE!")
    print(f"  ✔ Deployed Resource Name : {remote_engine.resource_name}")
    print(f"  ✔ Display Name           : {remote_engine.display_name}")
    print("================================================================================\n")

    # Automatically update app_adk2_studio.py with the new Reasoning Engine ID
    try:
        app_file = os.path.join(os.path.dirname(__file__), "frontend", "app_adk2_studio.py")
        with open(app_file, "r", encoding="utf-8") as f:
            code = f.read()
        import re
        new_code = re.sub(
            r'RESOURCE_NAME\s*=\s*"projects/[^"]+"',
            f'RESOURCE_NAME = "{remote_engine.resource_name}"',
            code
        )
        with open(app_file, "w", encoding="utf-8") as f:
            f.write(new_code)
        print(f"  ✔ Successfully updated app_adk2_studio.py RESOURCE_NAME target to: {remote_engine.resource_name}\n")
    except Exception as e:
        print(f"  ⚠ Note on updating UI target ID: {e}\n")



if __name__ == "__main__":
    deploy_adk2_orchestrator()
