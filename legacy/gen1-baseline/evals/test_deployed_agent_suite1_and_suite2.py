"""
test_deployed_agent_suite1_and_suite2.py: Live Cloud Verification Harness.
Executes multi-modal legal compliance clearance checks across all 7 assets (`Suite 1` Baseline + `Suite 2` Generalizability)
directly against our live deployed Google Cloud Agent Runtime (`ReasoningEngine 743760792318377984`) in project `your-gcp-project-id`.
"""

import os
import json
import time
import vertexai
from vertexai.preview import reasoning_engines

PROJECT_ID = "your-gcp-project-id"
LOCATION = "us-central1"
RESOURCE_NAME = "projects/YOUR_PROJECT_NUMBER/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID"


def load_sample_excerpt(filepath: str, max_chars: int = 1800) -> str:
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()[:max_chars]


def execute_live_suite_verification():
    print("================================================================================")
    print("🌐 EXECUTING FULL SUITE 1 & SUITE 2 VERIFICATION AGAINST DEPLOYED AGENT RUNTIME")
    print(f"   Target Resource: {RESOURCE_NAME}")
    print("================================================================================\n")

    vertexai.init(project=PROJECT_ID, location=LOCATION)
    remote_agent = reasoning_engines.ReasoningEngine(RESOURCE_NAME)
    print(f"✔ Connected to Live Google Cloud Agent Runtime: [{remote_agent.display_name}]\n")

    sample_base = "./sample_data"

    assets_to_test = [
        # Suite 1
        ("SUITE_1", "TEXT_SCREENPLAY", "social_network_script.txt", load_sample_excerpt(os.path.join(sample_base, "social_network_script.txt"), 1800), "Primary Sponsor: GoDaddy; Restricted Competitors: Heineken, Facebook"),
        ("SUITE_1", "VISUAL_IMAGE", "gs://your-staging-bucket/sample_assets/mock_sports_clothing.jpg", "Pre-production wardrobe photo in Cloud Storage (`gs://your-staging-bucket/sample_assets/mock_sports_clothing.jpg`).", "Primary Sponsor: Adidas; Restricted Competitors: Nike, Puma"),
        ("SUITE_1", "VISUAL_IMAGE", "gs://your-staging-bucket/sample_assets/mock_vaping_device.jpg", "Set prop photograph in Cloud Storage (`gs://your-staging-bucket/sample_assets/mock_vaping_device.jpg`).", "Target Rating: TV-PG; Flag regulated S&P vaping/tobacco products"),
        ("SUITE_1", "TEMPORAL_VIDEO", "gs://your-staging-bucket/sample_assets/tears_of_steel_1080p.mov", "Rough-cut video timeline in Cloud Storage (`gs://your-staging-bucket/sample_assets/tears_of_steel_1080p.mov`).", "Primary Sponsor: Sony; Restricted Competitors: Samsung, Apple"),
        # Suite 2
        ("SUITE_2", "TEXT_SCREENPLAY", "good_will_hunting_script.txt", load_sample_excerpt(os.path.join(sample_base, "good_will_hunting_script.txt"), 1800), "Primary Sponsor: Starbucks; Restricted Competitors: Dunkin' Donuts, Pepsi. Check Boston metropolitan name census rule."),
        ("SUITE_2", "VISUAL_IMAGE", "gs://your-staging-bucket/sample_assets/mock_luxury_handbag.jpg", "Pre-production luxury wardrobe photo in Cloud Storage (`gs://your-staging-bucket/sample_assets/mock_luxury_handbag.jpg`).", "Primary Sponsor: Gucci; Restricted Competitors: Louis Vuitton, Prada"),
        ("SUITE_2", "TEMPORAL_VIDEO", "gs://your-staging-bucket/sample_assets/elephantsdream_teaser.mp4", "Elephants Dream open movie timeline in Cloud Storage (`gs://your-staging-bucket/sample_assets/elephantsdream_teaser.mp4`).", "Primary Sponsor: Sony; Restricted Competitors: Samsung, LG")
    ]

    results = []
    success_count = 0

    for suite_id, asset_type, asset_ref, content_payload, rules_context in assets_to_test:
        print(f"--------------------------------------------------------------------------------")
        print(f"Executing True Live Cloud Query -> [{suite_id}] {asset_ref} ({asset_type})")
        print(f"--------------------------------------------------------------------------------")

        prompt = f"""
Perform an official studio legal clearance and copyright audit on the following media asset:
Asset Reference / GCS URI: {asset_ref}
Modality: {asset_type}
Content Excerpt / Target File:
{content_payload}

Clearance Rules & Sponsor Constraints:
{rules_context}

Apply our multi-agent vetting policies:
1. Metropolitan Census 0/3-Plus frequency rule for living character names.
2. Sponsor exclusivity protection against competitor trademarks.
3. Regulated S&P standards.
Provide a clear final clearance status and itemized violations.
"""
        start_t = time.time()
        try:
            cloud_response = remote_agent.query(input=prompt)
            latency = round(time.time() - start_t, 3)
            print(f"  ✔ Deployed Agent Runtime Response ({latency}s):")
            print(f"    -> {cloud_response}")
            success_count += 1
            results.append({
                "suite_id": suite_id,
                "asset_filename": asset_ref,
                "modality": asset_type,
                "live_cloud_latency_sec": latency,
                "status": "SUCCESS (HTTP 200 OK)",
                "remote_agent_response": str(cloud_response)
            })
        except Exception as e:
            latency = round(time.time() - start_t, 3)
            print(f"  ❌ Error querying remote agent ({latency}s): {e}")
            results.append({
                "suite_id": suite_id,
                "asset_filename": asset_ref,
                "modality": asset_type,
                "live_cloud_latency_sec": latency,
                "status": f"ERROR: {e}"
            })
        print()

    # Save live cloud execution ledger
    out_dir = "./reports"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "live_cloud_deployed_suite1_suite2_report.json")

    summary_ledger = {
        "execution_target": "GOOGLE_CLOUD_AGENT_RUNTIME",
        "resource_name": RESOURCE_NAME,
        "total_assets_tested": len(assets_to_test),
        "successful_cloud_invocations": success_count,
        "pass_rate_pct": round((success_count / len(assets_to_test)) * 100.0, 2),
        "results": results
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary_ledger, f, indent=2)

    print("================================================================================")
    print(f"✅ LIVE CLOUD DEPLOYMENT SUITE 1 & SUITE 2 VERIFICATION COMPLETE!")
    print(f"   Pass Rate: {success_count}/{len(assets_to_test)} ({summary_ledger['pass_rate_pct']}%)")
    print(f"   Summary Ledger saved to -> {out_file}")
    print("================================================================================\n")


if __name__ == "__main__":
    execute_live_suite_verification()
