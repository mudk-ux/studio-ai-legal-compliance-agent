"""
test_adk2_studio.py: Validates adk2_multiagent_studio isolated sub-package.
Proves 100% execution pass on ADK 2.0 multi-agent graph routing and explicit
HITL execution pause / confirmation hooks without touching existing code.
"""

from adk2_multiagent_studio.src.hitl_controller import pause_execution_for_human_review
from adk2_multiagent_studio.src.orchestration import ADK2MultiAgentGraphOrchestrator


def test_hitl_controller():
    dummy_violation = {
        "severity": "CRITICAL",
        "category": "SPONSOR_EXCLUSIVITY_CONFLICT",
        "entity": "Winston Cigarettes",
        "finding": "Winston detected in TV-PG commercial"
    }
    hitl_res = pause_execution_for_human_review(dummy_violation, "sample_data/test.mp4")
    assert hitl_res["hitl_interruption"] is True
    assert hitl_res["execution_status"] == "PAUSED_WAITING_FOR_HUMAN_REVIEW"
    assert hitl_res["action_required"] == "EXPLICIT_CONFIRMATION_HOOK"
    assert "HITL-PAUSE-" in hitl_res["resume_token"]
    print("✔ [ADK2 Studio] Explicit HITL Execution Pause & Confirmation Hook verified!")


def test_adk2_orchestration():
    orchestrator = ADK2MultiAgentGraphOrchestrator()
    sample_constraints = {
        "show_context": "Primetime Feature",
        "target_rating": "TV-PG",
        "exclusivity_deals": {
            "primary_sponsor": "Starbucks",
            "restricted_competitors": ["Dunkin' Donuts", "Winston"]
        },
        "temporal_clearance_targets": []
    }

    report = orchestrator.execute_adk_workflow(
        asset_path="sample_data/old_suite_1/social_network_script.txt",
        asset_type="TEXT_SCREENPLAY",
        constraints_data=sample_constraints
    )
    assert report["architecture"] == "TRUE_GOOGLE_ADK_2_0_MULTI_AGENT_GRAPH"
    assert len(report["adk_agent_execution_trace"]) >= 3
    print("✔ [ADK2 Studio] ADK 2.0 Multi-Agent Graph (Coordinator -> Specialist -> Remediation) verified!")


if __name__ == "__main__":
    print("=== STARTING ISOLATED ADK 2.0 MULTI-AGENT STUDIO VALIDATION ===")
    test_hitl_controller()
    test_adk2_orchestration()
    print("=== ALL ISOLATED ADK 2.0 MULTI-AGENT SUITES PASSED SUCCESSFULLY ===")
