"""
hitl_controller.py: Explicit Human-in-the-Loop (HITL) Execution Pause Hook.
Halts automated workflow execution when critical/high severity infractions are encountered,
emitting a structured interactive confirmation hook payload requiring human reviewer sign-off.
"""

import time
import uuid
from typing import Any, Dict


def pause_execution_for_human_review(
    violation: Dict[str, Any],
    asset_reference: str,
    reviewer_role: str = "Senior E&O Legal Reviewer / Standards & Practices VP",
) -> Dict[str, Any]:
    """
    Explicit Human-in-the-Loop (HITL) execution pause hook.
    Halts workflow progression when a CRITICAL or HIGH severity finding is flagged,
    returning an explicit confirmation hook payload requiring interactive sign-off.
    """
    resume_token = f"HITL-PAUSE-{uuid.uuid4().hex[:8].upper()}"
    hitl_payload = {
        "hitl_interruption": True,
        "execution_status": "PAUSED_WAITING_FOR_HUMAN_REVIEW",
        "action_required": "EXPLICIT_CONFIRMATION_HOOK",
        "required_role": reviewer_role,
        "asset_reference": asset_reference,
        "resume_token": resume_token,
        "flagged_violation": violation,
        "timestamp_paused": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "interactive_prompt": (
            "AUTOMATED WORKFLOW PAUSED: Critical/High severity compliance risk detected. "
            "Please review the itemized finding below and explicitly confirm approval, "
            "override, or enforce VFX paint-out slate prior to releasing hold."
        ),
    }
    return hitl_payload
