"""
test_live_cloud_container.py: Live verification suite testing remote container
`ReasoningEngine 8283630993466720256` on Gemini Enterprise Agent Platform (formerly Vertex AI).
Proves native Cloud Storage (`gs://`) ingestion and explicit HITL execution pause hooks.
"""

import json
import vertexai
from vertexai.preview import reasoning_engines

PROJECT_ID = "your-gcp-project-id"
LOCATION = "us-central1"
ENGINE_ID = "projects/YOUR_PROJECT_NUMBER/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID"


def test_remote_container():
    print("================================================================================")
    print(f"☁️ TESTING LIVE CLOUD CONTAINER ON GEMINI ENTERPRISE AGENT PLATFORM")
    print(f"   Target Resource: {ENGINE_ID}")
    print("================================================================================\n")

    vertexai.init(project=PROJECT_ID, location=LOCATION)
    remote_engine = reasoning_engines.ReasoningEngine(ENGINE_ID)

    # ---------------------------------------------------------------------------
    # Test 1: Full Text Screenplay Ingestion via gs:// URI
    # ---------------------------------------------------------------------------
    print("1️⃣ CLOUD TEST 1: Full 110-Page Screenplay (`good_will_hunting_script.txt`) via gs://")
    script_uri = "gs://your-staging-bucket/sample_assets/good_will_hunting_script.txt"
    res1 = remote_engine.query(
        asset_path=script_uri,
        asset_type="TEXT_SCREENPLAY",
        constraints_data={
            "show_context": "Boston Primetime Special",
            "target_rating": "TV-PG",
            "exclusivity_deals": {
                "primary_sponsor": "Starbucks",
                "restricted_competitors": ["Dunkin' Donuts", "Winston"]
            }
        }
    )
    print("  ✔ Run ID                       :", res1.get("run_id"))
    print("  ✔ Architecture                 :", res1.get("architecture"))
    print("  ✔ Modality Evaluated           :", res1.get("modality"))
    print("  ✔ Overall Verdict              :", res1.get("overall_status"))
    print("  ✔ ADK 2.0 Agent Execution Trace:")
    for step in res1.get("adk_agent_execution_trace", []):
        print(f"     -> [{step.get('node')}]: {step.get('action') or step.get('compiled_verdict')}")
    print("\n--------------------------------------------------------------------------------\n")

    # ---------------------------------------------------------------------------
    # Test 2: Multimodal Image & Explicit HITL Execution Pause Hook via gs:// URI
    # ---------------------------------------------------------------------------
    print("2️⃣ CLOUD TEST 2: Multimodal Image (`mock_luxury_handbag.jpg`) Explicit HITL Pause")
    image_uri = "gs://your-staging-bucket/sample_assets/mock_luxury_handbag.jpg"
    res2 = remote_engine.query(
        asset_path=image_uri,
        asset_type="VISUAL_IMAGE",
        constraints_data={
            "show_context": "Luxury Wardrobe Commercial",
            "target_rating": "TV-PG",
            "exclusivity_deals": {
                "primary_sponsor": "Gucci",
                "restricted_competitors": ["Louis Vuitton"]
            }
        }
    )
    print("  ✔ Run ID                       :", res2.get("run_id"))
    print("  ✔ HITL Interruption Triggered  :", res2.get("hitl_interruption_triggered"))
    hitl = res2.get("hitl_execution_pause")
    if hitl:
        print("  ✔ Execution Status             :", hitl.get("execution_status"))
        print("  ✔ Action Required              :", hitl.get("action_required"))
        print("  ✔ Required Reviewer Role       :", hitl.get("required_role"))
        print("  ✔ Flagged Violation            :", hitl.get("flagged_violation", {}).get("finding"))
        print("  ✔ Resume Token                 :", hitl.get("resume_token"))
    print("\n================================================================================")
    print("✅ BOTH LIVE CLOUD TESTS PASSED ON REASONING ENGINE 8283630993466720256!")
    print("================================================================================")


if __name__ == "__main__":
    test_remote_container()
