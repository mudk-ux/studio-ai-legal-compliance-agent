"""
export_live_cloud_reports.py: Parses live cloud execution ledgers from deployed Google Cloud Agent Runtime
(`ReasoningEngine 743760792318377984`) and exports individual physical JSON + Markdown output reports for each asset.
"""

import os
import json


def export_individual_live_reports():
    in_file = "./reports/live_cloud_deployed_suite1_suite2_report.json"
    out_dir = "./reports/live_cloud"
    os.makedirs(out_dir, exist_ok=True)

    if not os.path.exists(in_file):
        print(f"Error: Master summary report not found at {in_file}")
        return

    with open(in_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = data.get("results", [])
    print("================================================================================")
    print("EXPORTING INDIVIDUAL LIVE CLOUD OUTPUT REPORTS (`/CIBuild/reports/live_cloud/`)")
    print("================================================================================")

    for idx, item in enumerate(results, 1):
        suite = item.get("suite_id", "UNKNOWN")
        asset_ref = item.get("asset_filename", f"asset_{idx}")
        modality = item.get("modality", "UNKNOWN")
        latency = item.get("live_cloud_latency_sec", 0)
        resp = item.get("remote_agent_response", "")

        clean_name = os.path.basename(asset_ref).replace(".txt", "").replace(".jpg", "").replace(".mp4", "").replace(".mov", "")
        json_out = os.path.join(out_dir, f"{suite.lower()}_{clean_name}_live_report.json")
        md_out = os.path.join(out_dir, f"{suite.lower()}_{clean_name}_live_report.md")

        report_payload = {
            "execution_target": "GOOGLE_CLOUD_AGENT_RUNTIME",
            "resource_id": "projects/YOUR_PROJECT_NUMBER/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID",
            "suite_id": suite,
            "asset_reference": asset_ref,
            "modality": modality,
            "live_latency_seconds": latency,
            "agent_output_report": resp
        }

        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(report_payload, f, indent=2)

        md_content = f"""# Live Cloud Compliance Audit Report

* **Target Cloud Endpoint:** `projects/YOUR_PROJECT_NUMBER/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID`
* **Suite:** `{suite}`
* **Asset Reference:** `{asset_ref}`
* **Modality:** `{modality}`
* **Serverless Execution Latency:** `{latency}s`

---

## Deployed Agent Runtime Output Report

```text
{resp}
```
"""
        with open(md_out, "w", encoding="utf-8") as f:
            f.write(md_content)

        print(f"  ✔ Exported [{suite}]: {clean_name:<28} -> {os.path.basename(json_out)}")

    print("================================================================================\n")


if __name__ == "__main__":
    export_individual_live_reports()
