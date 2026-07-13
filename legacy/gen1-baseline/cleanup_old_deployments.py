"""
cleanup_old_deployments.py: Safely deletes old/superseded Reasoning Engine deployments
in project your-gcp-project-id while strictly preserving the upgraded production deployment
(`projects/YOUR_PROJECT_NUMBER/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID`).
"""

import vertexai
from vertexai.preview import reasoning_engines

PROJECT_ID = "your-gcp-project-id"
LOCATION = "us-central1"

# Production deployment to strictly preserve
ACTIVE_PRODUCTION_ENGINE = "projects/YOUR_PROJECT_NUMBER/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID"

# Old superseded deployments to delete as explicitly requested by user
OLD_ENGINES_TO_DELETE = [
    "projects/YOUR_PROJECT_NUMBER/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID",
]


def cleanup():
    print("================================================================================")
    print("CLEANING UP SUPERSEDED REASONING ENGINE DEPLOYMENTS (`your-gcp-project-id`)")
    print("================================================================================")
    print(f"🔒 PRESERVING ACTIVE PRODUCTION DEPLOYMENT:\n   -> {ACTIVE_PRODUCTION_ENGINE}\n")

    vertexai.init(project=PROJECT_ID, location=LOCATION)

    for resource_id in OLD_ENGINES_TO_DELETE:
        print(f"🗑️ Deleting old Reasoning Engine:\n   -> {resource_id}...")
        try:
            engine = reasoning_engines.ReasoningEngine(resource_id)
            engine.delete()
            print(f"   ✔ Successfully deleted {resource_id}\n")
        except Exception as e:
            print(f"   ⚠️ Could not delete {resource_id}: {e}\n")

    print("================================================================================")
    print("✅ DEPLOYMENT CLEANUP COMPLETE!")
    print("================================================================================")


if __name__ == "__main__":
    cleanup()
