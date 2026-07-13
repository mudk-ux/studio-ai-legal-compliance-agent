"""
deploy_to_agent_runtime.py: Automates deployment of the M&E Copyright Infringement & Legal Compliance Agent
to Google Cloud Agent Runtime (Vertex AI Reasoning Engine) in project `your-gcp-project-id`.
"""

import os
import sys

# Ensure deploy/ folder is on path
deploy_dir = os.path.join(os.path.dirname(__file__), "deploy")
sys.path.append(deploy_dir)

import vertexai
from vertexai.preview import reasoning_engines
from agent import MECopyrightComplianceApp

PROJECT_ID = "your-gcp-project-id"
LOCATION = "us-central1"
STAGING_BUCKET = "gs://your-staging-bucket"


def deploy_agent_runtime():
    print("================================================================================")
    print(f"🚀 DEPLOYING M&E COMPLIANCE AGENT TO GOOGLE CLOUD AGENT RUNTIME")
    print(f"   Project: {PROJECT_ID} | Region: {LOCATION}")
    print("================================================================================\n")

    vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)

    print("1. Packaging ADK 2.0 multi-agent graph & deterministic tool wrappers...")
    print("2. Initiating Vertex AI Reasoning Engine (Agent Runtime) remote build...\n")

    # Ensure we run from inside CIBuild/deploy so local packages bundle properly
    os.chdir(deploy_dir)

    remote_agent = reasoning_engines.ReasoningEngine.create(
        MECopyrightComplianceApp(),
        requirements=[
            "google-adk>=1.0.0",
            "google-genai>=1.9.0",
            "google-cloud-aiplatform>=1.45.0",
            "google-cloud-language>=2.10.0",
            "google-cloud-vision>=3.4.0",
            "google-cloud-videointelligence>=2.11.0",
            "google-cloud-storage>=2.10.0",
            "google-cloud-logging>=3.8.0",
            "pydantic>=2.0.0"
        ],
        extra_packages=["agent.py", "src"],
        display_name="MECopyrightComplianceAgent",
        description="Master M&E Copyright Infringement & Legal Compliance Vetting Agent (Generalized Architecture)"
    )

    print("\n================================================================================")
    print("✅ DEPLOYMENT TO GOOGLE CLOUD AGENT RUNTIME COMPLETE!")
    print("================================================================================")
    print(f"  ✔ Deployed Resource Name : {remote_agent.resource_name}")
    print(f"  ✔ Display Name           : {remote_agent.display_name}")
    print("================================================================================\n")

    # Auto-update frontend/app.py with the newly deployed Reasoning Engine ID
    try:
        app_file = os.path.join(os.path.dirname(__file__), "..", "frontend", "app.py")
        with open(app_file, "r", encoding="utf-8") as f:
            app_code = f.read()
        import re
        new_app_code = re.sub(
            r'RESOURCE_NAME\s*=\s*"projects/[^"]+"',
            f'RESOURCE_NAME = "{remote_agent.resource_name}"',
            app_code
        )
        with open(app_file, "w", encoding="utf-8") as f:
            f.write(new_app_code)
        print(f"  ✔ Updated frontend/app.py target to: {remote_agent.resource_name}\n")
    except Exception as e:
        print(f"  ⚠ Note on updating frontend target ID: {e}\n")

    # Automated Live Cloud Test Query
    print("================================================================================")
    print("🧪 EXECUTING LIVE CLOUD TEST QUERY AGAINST DEPLOYED AGENT RUNTIME")
    print("================================================================================")
    test_prompt = "Perform a text script clearance audit on this character mention: 'Larry Summers walks into the Boston coffee shop.' Check metropolitan census name rules."
    print(f"Test Query Prompt: \"{test_prompt}\"\n")
    try:
        remote_response = remote_agent.query(input=test_prompt)
        print("  ✔ Live Deployed Agent Response:")
        print("--------------------------------------------------------------------------------")
        print(remote_response)
        print("--------------------------------------------------------------------------------")
    except Exception as e:
        print(f"  ⚠ Note on live remote query output: {e}")
    print("================================================================================\n")

    return remote_agent


if __name__ == "__main__":
    deploy_agent_runtime()
