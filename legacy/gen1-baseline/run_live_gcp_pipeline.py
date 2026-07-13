"""
run_live_gcp_pipeline.py: Live Google Cloud API execution harness.
Calls live Vertex AI Gemini (`gemini-2.5-flash` / `gemini-3.5-pro`) directly inside project `your-gcp-project-id`
using live Application Default Credentials (ADC) to generate real Cloud Traces and Compliance Ledgers.
"""

import os
import json
import uuid
import urllib.request
import subprocess
from typing import Dict, Any, List


def get_gcloud_access_token() -> str:
    """Retrieves live Application Default Credentials token from gcloud CLI."""
    out = subprocess.check_output(
        ["gcloud", "auth", "application-default", "print-access-token"]
    )
    return out.decode("utf-8").strip()


def call_live_vertex_gemini(
    prompt: str,
    project: str = "your-gcp-project-id",
    location: str = "us-central1",
    model: str = "gemini-2.5-flash",
) -> Dict[str, Any]:
    """
    Executes a live REST API call against Vertex AI Gemini in project your-gcp-project-id.
    Generates authentic live Cloud Logging and OpenTelemetry/Vertex trace spans.
    """
    token = get_gcloud_access_token()
    url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/publishers/google/models/{model}:generateContent"

    payload = {
        "contents": {"role": "user", "parts": [{"text": prompt}]},
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 2048,
            "responseMimeType": "application/json",
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    import ssl
    ssl_ctx = ssl._create_unverified_context()

    with urllib.request.urlopen(req, context=ssl_ctx) as response:
        res_json = json.loads(response.read().decode("utf-8"))

    text_resp = (
        res_json.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "{}")
    )
    usage = res_json.get("usageMetadata", {})

    return {
        "raw_response": res_json,
        "parsed_json": json.loads(text_resp) if text_resp.startswith("{") else text_resp,
        "usage_metadata": usage,
        "live_api_endpoint": url,
    }


def execute_live_gcp_evaluation():
    print(
        "================================================================================"
    )
    print(
        "EXECUTING LIVE GOOGLE CLOUD VERTEX AI GEMINI RUN (`your-gcp-project-id`)"
    )
    print(
        "================================================================================"
    )

    sample_script = "./sample_data/social_network_script.txt"
    with open(sample_script, "r", encoding="utf-8") as f:
        script_excerpt = f.read()[:3000]  # First 3,000 characters of scene

    prompt = f"""
You are a Studio Legal Compliance & Trademark Vetting Agent powered by Gemini 2.5 Flash on Google Cloud.
Analyze the following screenplay excerpt from 'The Social Network' and return a strictly valid JSON compliance report.
Required JSON format:
{{
  "overall_status": "CONDITIONAL_CLEARANCE" | "BLOCKED" | "CLEARED",
  "entities_flagged": ["list of proper names and brand mentions"],
  "violations": [
    {{
      "entity": "Name or Brand",
      "category": "NAME_DEFAMATION_0_3_RULE" | "UNLICENSED_COMMERCIAL_BRAND",
      "severity": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
      "remediation": "Actionable instruction for legal/writers"
    }}
  ]
}}

Screenplay Excerpt:
{script_excerpt}
"""

    print(
        "\n1. Sending Live API Request to Vertex AI (`gemini-2.5-flash`) in `your-gcp-project-id`..."
    )
    live_result = call_live_vertex_gemini(prompt=prompt, model="gemini-2.5-flash")

    print("  ✔ Live API Response Received Successfully!")
    print(
        f"  ✔ Usage Tokens: {live_result['usage_metadata'].get('totalTokenCount')} tokens consumed in live project."
    )
    print(
        f"  ✔ Endpoint: {live_result['live_api_endpoint']}\n"
    )

    parsed = live_result["parsed_json"]
    print("================================================================================")
    print("LIVE VERTEX AI STRUCTURED COMPLIANCE FINDINGS")
    print("================================================================================")
    print(json.dumps(parsed, indent=2))

    live_out = "./reports/live_gcp_vertex_execution_report.json"
    with open(live_out, "w", encoding="utf-8") as f:
        json.dump(
            {
                "execution_mode": "LIVE_GCP_VERTEX_AI_API",
                "project_id": "your-gcp-project-id",
                "model_invoked": "gemini-2.5-flash",
                "api_endpoint": live_result["live_api_endpoint"],
                "usage_metadata": live_result["usage_metadata"],
                "structured_findings": parsed,
            },
            f,
            indent=2,
        )
    print(f"\n✔ Live Vertex AI execution ledger saved to -> {live_out}")
    print(
        "================================================================================\n"
    )


if __name__ == "__main__":
    execute_live_gcp_evaluation()
