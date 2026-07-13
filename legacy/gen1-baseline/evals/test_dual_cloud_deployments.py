"""
test_dual_cloud_deployments.py: Comprehensive Dual-Container Cloud Verification Suite.
Sends real multimodal payloads (.txt, .jpg, .mp4) to BOTH live remote containers on
Gemini Enterprise Agent Platform (formerly Vertex AI):
1. Baseline Production Container: `ReasoningEngine 9047272605282729984`
2. ADK 2.0 Multi-Agent Container: `ReasoningEngine 148441216575340544`
"""

import json
import os
import sys
import time
from typing import Any, Dict

import vertexai
from vertexai.preview import reasoning_engines

PROJECT_ID = "your-gcp-project-id"
LOCATION = "us-central1"
STAGING_BUCKET = "gs://your-staging-bucket"

BASELINE_ID = "projects/YOUR_PROJECT_NUMBER/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID"
ADK2_ID = "projects/YOUR_PROJECT_NUMBER/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID"


def run_dual_container_evaluation():
    print("================================================================================")
    print("🧪 STARTING DUAL-CONTAINER CLOUD EVALUATION SUITE ON GEMINI ENTERPRISE AGENT PLATFORM")
    print(f"   Project: {PROJECT_ID} | Region: {LOCATION}")
    print(f"   Baseline Container : {BASELINE_ID}")
    print(f"   ADK 2.0 Container  : {ADK2_ID}")
    print("================================================================================\n")

    vertexai.init(project=PROJECT_ID, location=LOCATION)

    baseline_engine = reasoning_engines.ReasoningEngine(BASELINE_ID)
    adk2_engine = reasoning_engines.ReasoningEngine(ADK2_ID)

    results_matrix = []

    # ---------------------------------------------------------------------------
    # SUITE A: BASELINE PRODUCTION CONTAINER (9047272605282729984)
    # ---------------------------------------------------------------------------
    print("--------------------------------------------------------------------------------")
    print("1️⃣ TESTING BASELINE PRODUCTION CONTAINER (9047272605282729984)")
    print("--------------------------------------------------------------------------------")

    # A1. Text Screenplay (Good Will Hunting)
    print("  [A1] Sending full 110-page text screenplay (`good_will_hunting_script.txt`)...")
    start_t = time.time()
    payload_a1 = json.dumps({
        "asset_path": "sample_data/new_suite_2/good_will_hunting_script.txt",
        "asset_type": "TEXT_SCREENPLAY",
        "constraints": {
            "show_context": "Boston Drama",
            "target_rating": "TV-PG",
            "exclusivity_deals": {
                "primary_sponsor": "Starbucks",
                "restricted_competitors": ["Dunkin' Donuts", "Winston"]
            }
        }
    })
    res_a1 = baseline_engine.query(input=payload_a1)
    lat_a1 = round(time.time() - start_t, 2)
    verdict_a1 = "BLOCKED" if "BLOCKED" in str(res_a1).upper() or "CRITICAL" in str(res_a1).upper() else "CLEARED"
    results_matrix.append(("Baseline (9047...)", "TEXT_SCREENPLAY", "good_will_hunting.txt", lat_a1, verdict_a1, "N/A"))
    print(f"       ✔ Result: {verdict_a1} ({lat_a1}s)\n")

    # A2. Multimodal Image (Luxury Handbag)
    print("  [A2] Sending visual wardrobe prop (`mock_luxury_handbag.jpg`)...")
    start_t = time.time()
    payload_a2 = json.dumps({
        "asset_path": "sample_data/new_suite_2/mock_luxury_handbag.jpg",
        "asset_type": "VISUAL_IMAGE",
        "constraints": {
            "show_context": "Wardrobe Spot",
            "target_rating": "TV-PG",
            "exclusivity_deals": {
                "primary_sponsor": "Gucci",
                "restricted_competitors": ["Louis Vuitton"]
            }
        }
    })
    res_a2 = baseline_engine.query(input=payload_a2)
    lat_a2 = round(time.time() - start_t, 2)
    verdict_a2 = "BLOCKED" if "BLOCKED" in str(res_a2).upper() or "CRITICAL" in str(res_a2).upper() else "CLEARED"
    results_matrix.append(("Baseline (9047...)", "VISUAL_IMAGE", "mock_luxury_handbag.jpg", lat_a2, verdict_a2, "N/A"))
    print(f"       ✔ Result: {verdict_a2} ({lat_a2}s)\n")

    # A3. Temporal Video (Elephants Dream Teaser)
    print("  [A3] Sending temporal video cut (`elephantsdream_teaser.mp4`)...")
    start_t = time.time()
    payload_a3 = json.dumps({
        "asset_path": "sample_data/new_suite_2/elephantsdream_teaser.mp4",
        "asset_type": "TEMPORAL_VIDEO",
        "constraints": {
            "show_context": "Video Commercial",
            "target_rating": "TV-PG",
            "exclusivity_deals": {
                "primary_sponsor": "General Mills",
                "restricted_competitors": ["Winston"]
            }
        }
    })
    res_a3 = baseline_engine.query(input=payload_a3)
    lat_a3 = round(time.time() - start_t, 2)
    verdict_a3 = "BLOCKED" if "BLOCKED" in str(res_a3).upper() or "CRITICAL" in str(res_a3).upper() else "CLEARED"
    results_matrix.append(("Baseline (9047...)", "TEMPORAL_VIDEO", "elephantsdream_teaser.mp4", lat_a3, verdict_a3, "N/A"))
    print(f"       ✔ Result: {verdict_a3} ({lat_a3}s)\n")

    # ---------------------------------------------------------------------------
    # SUITE B: ADK 2.0 MULTI-AGENT & HITL CONTAINER (148441216575340544)
    # ---------------------------------------------------------------------------
    print("--------------------------------------------------------------------------------")
    print("2️⃣ TESTING ADK 2.0 MULTI-AGENT & HITL CONTAINER (148441216575340544)")
    print("--------------------------------------------------------------------------------")

    # B1. Text Screenplay (Good Will Hunting via gs:// URI)
    print("  [B1] Sending GCS object (`gs://.../good_will_hunting_script.txt`)...")
    start_t = time.time()
    res_b1 = adk2_engine.query(
        asset_path="gs://your-staging-bucket/sample_assets/good_will_hunting_script.txt",
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
    lat_b1 = round(time.time() - start_t, 2)
    verdict_b1 = res_b1.get("overall_status", "UNKNOWN")
    hitl_b1 = str(res_b1.get("hitl_interruption_triggered", False))
    results_matrix.append(("ADK 2.0 (1484...)", "TEXT_SCREENPLAY", "good_will_hunting.txt (GCS)", lat_b1, verdict_b1, hitl_b1))
    print(f"       ✔ Result: {verdict_b1} (HITL Hold: {hitl_b1} | {lat_b1}s)\n")

    # B2. Multimodal Image (Luxury Handbag via gs:// URI)
    print("  [B2] Sending GCS object (`gs://.../mock_luxury_handbag.jpg`)...")
    start_t = time.time()
    res_b2 = adk2_engine.query(
        asset_path="gs://your-staging-bucket/sample_assets/mock_luxury_handbag.jpg",
        asset_type="VISUAL_IMAGE",
        constraints_data={
            "show_context": "Luxury Spot",
            "target_rating": "TV-PG",
            "exclusivity_deals": {
                "primary_sponsor": "Gucci",
                "restricted_competitors": ["Louis Vuitton"]
            }
        }
    )
    lat_b2 = round(time.time() - start_t, 2)
    verdict_b2 = res_b2.get("overall_status", "UNKNOWN")
    hitl_b2 = str(res_b2.get("hitl_interruption_triggered", False))
    results_matrix.append(("ADK 2.0 (1484...)", "VISUAL_IMAGE", "mock_luxury_handbag.jpg (GCS)", lat_b2, verdict_b2, hitl_b2))
    print(f"       ✔ Result: {verdict_b2} (HITL Hold: {hitl_b2} | {lat_b2}s)\n")

    # B3. Temporal Video (Elephants Dream Teaser via gs:// URI)
    print("  [B3] Sending GCS temporal video (`gs://.../elephantsdream_teaser.mp4`)...")
    start_t = time.time()
    res_b3 = adk2_engine.query(
        asset_path="gs://your-staging-bucket/sample_assets/elephantsdream_teaser.mp4",
        asset_type="TEMPORAL_VIDEO",
        constraints_data={
            "show_context": "Video Commercial",
            "target_rating": "TV-PG",
            "exclusivity_deals": {
                "primary_sponsor": "General Mills",
                "restricted_competitors": ["Winston"]
            }
        }
    )
    lat_b3 = round(time.time() - start_t, 2)
    verdict_b3 = res_b3.get("overall_status", "UNKNOWN")
    hitl_b3 = str(res_b3.get("hitl_interruption_triggered", False))
    results_matrix.append(("ADK 2.0 (1484...)", "TEMPORAL_VIDEO", "elephantsdream_teaser.mp4 (GCS)", lat_b3, verdict_b3, hitl_b3))
    print(f"       ✔ Result: {verdict_b3} (HITL Hold: {hitl_b3} | {lat_b3}s)\n")

    # ---------------------------------------------------------------------------
    # FINAL REPORT MATRIX
    # ---------------------------------------------------------------------------
    print("================================================================================")
    print("🏆 DUAL-CONTAINER EVALUATION SUMMARY MATRIX")
    print("================================================================================")
    print(f"{'Container Deployment':<20} | {'Modality':<16} | {'Asset Target':<28} | {'Latency':<8} | {'Verdict':<10} | {'HITL Hold':<10}")
    print("-" * 105)
    for row in results_matrix:
        print(f"{row[0]:<20} | {row[1]:<16} | {row[2]:<28} | {row[3]:<7}s | {row[4]:<10} | {row[5]:<10}")
    print("================================================================================\n")


if __name__ == "__main__":
    run_dual_container_evaluation()
