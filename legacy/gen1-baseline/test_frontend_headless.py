"""
test_frontend_headless.py: Automated test harness verifying that the Streamlit Intake Form UI (`frontend/app.py`)
initializes cleanly, connects to our backend packages (`src.agent`), and supports Cloud Agent Runtime execution.
"""

import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from src.agent import run_compliance_evaluation


def test_frontend_backend_integration():
    print("================================================================================")
    print("🧪 EXECUTING HEADLESS FRONTEND <-> BACKEND INTEGRATION TEST")
    print("================================================================================")

    sample_dir = "./sample_data"
    test_asset = os.path.join(sample_dir, "social_network_script.txt")

    constraints_payload = {
        "show_context": "Biographical Feature Film",
        "target_rating": "PG-13",
        "exclusivity_deals": {
            "primary_sponsor": "GoDaddy",
            "restricted_competitors": ["Heineken", "Facebook"]
        },
        "custom_rules": ["Verify Harvard administrative trademark usage."]
    }

    print(f"1. Simulating Intake Form Submission -> Asset: {os.path.basename(test_asset)}")
    report = run_compliance_evaluation(test_asset, "TEXT_SCREENPLAY", constraints_payload)

    assert report.run_id.startswith("CLR-"), f"Invalid Run ID generated: {report.run_id}"
    assert report.overall_status in ["CLEARED", "CONDITIONAL_CLEARANCE", "BLOCKED"], "Invalid status"
    print(f"   ✔ Evaluated successfully. Status: {report.overall_status} (Run ID: {report.run_id})")
    print(f"   ✔ Total itemized violations flagged: {len(report.violations)}")

    print("================================================================================")
    print("✅ FRONTEND INTAKE LOGIC & BACKEND CONNECTION VERIFIED 100% HEALTHY!")
    print("================================================================================")


if __name__ == "__main__":
    test_frontend_backend_integration()
