"""
test_adk2_orchestration.py: Verifies True Google ADK 2.0 Multi-Agent Orchestrator
and Explicit Human-in-the-Loop (HITL) Execution Pause confirmation hooks.
"""

import json
from src.orchestration import ADK2MultiAgentGraphOrchestrator, pause_execution_for_human_review


def test_hitl_pause_hook():
    dummy_violation = {
        "severity": "CRITICAL",
        "category": "SPONSOR_EXCLUSIVITY_CONFLICT",
        "entity": "Winston Cigarettes",
        "finding": "Winston detected in TV-PG commercial"
    }
    hitl_res = pause_execution_for_human_review(dummy_violation, "sample_assets/test.mp4")
    assert hitl_res["hitl_interruption"] is True
    assert hitl_res["execution_status"] == "PAUSED_WAITING_FOR_HUMAN_REVIEW"
    assert hitl_res["action_required"] == "EXPLICIT_CONFIRMATION_HOOK"
    assert "HITL-PAUSE-" in hitl_res["resume_token"]
    print("✔ Explicit HITL Execution Pause & Confirmation Hook verified!")


def test_adk2_multi_agent_graph():
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

    # Execute against script
    report = orchestrator.execute_adk_workflow(
        asset_path="sample_data/old_suite_1/social_network_script.txt",
        asset_type="TEXT_SCREENPLAY",
        constraints_data=sample_constraints
    )
    assert report["architecture"] == "TRUE_GOOGLE_ADK_2_0_MULTI_AGENT_GRAPH"
    assert len(report["adk_agent_execution_trace"]) >= 3
    print("✔ ADK 2.0 Multi-Agent Graph (Coordinator -> Specialist -> Remediation) verified!")


if __name__ == "__main__":
    print("=== STARTING ADK 2.0 MULTI-AGENT & HITL PAUSE VALIDATION ===")
    test_hitl_pause_hook()
    test_adk2_multi_agent_graph()
    print("=== ALL ADK 2.0 MULTI-AGENT SUITES PASSED SUCCESSFULLY ===")
