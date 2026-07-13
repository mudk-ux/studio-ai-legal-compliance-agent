"""Track 2 — multi-agent workflow.

A coordinator (Gemini Flash) routes to modality specialists (Gemini Pro) that
call perception tools directly, and a remediation specialist (Flash) compiles
the final deliverable. All evidence still comes from the same audited tool
layer — the agents add routing, legal reasoning and explanation, not facts.
"""

from __future__ import annotations

from ..config import load_config
from .tools import (
    analyze_script_entities,
    evaluate_policy,
    list_pending_reviews,
    run_compliance_audit,
    scan_image_asset,
    scan_video_asset,
)

_SCRIPT_INSTRUCTION = """You are the Script Clearance specialist for studio legal E&O.

Given a screenplay asset URI and intake constraints:
1. Call `analyze_script_entities` to extract persons/organizations/brands.
   If the tool returns an error, report the failure — do not proceed or guess.
2. Call `evaluate_policy` passing the tool's `entities_uri` value as the
   `detections_uri` argument, plus the constraints. NEVER copy the entity
   list into `detections_json` — feature scripts have 300+ entities and the
   serialized list exceeds tool-argument limits and gets truncated.
3. Add your legal reasoning on top: docudrama / First Amendment context for
   real living persons, right-of-publicity exposure, negative-check guidance
   for fictional names. Clearly separate tool-verified findings from your
   qualitative counsel notes.
Never invent entities that the tools did not detect."""

_BRAND_INSTRUCTION = """You are the Brand & Exclusivity specialist for images and video.

Given an asset URI and intake constraints:
1. For images call `scan_image_asset`; for videos call `scan_video_asset`
   (videos must be gs:// URIs). If the tool reports an error, surface it as a
   failed vet — never guess what might be in the asset.
2. Call `evaluate_policy` with the detected entities and constraints.
3. Report findings with their real confidence scores and timecodes, and for
   video breaches list the VFX paint-out ranges.
Never invent detections, confidences or timecodes."""

_REMEDIATION_INSTRUCTION = """You are the Remediation Slate specialist.

Given findings from the other specialists, compile the production deliverable:
1. Group findings by department (Editorial/VFX, Wardrobe/Props, Legal/Clearance, S&P).
2. For timecoded breaches, emit an EDL-style slate table: start, end, target, action.
3. List every pending human-review token with the CLI command to resolve it.
4. End with the verdict verbatim from the policy engine — you do not override verdicts."""

_COORDINATOR_INSTRUCTION = """You are the M&E compliance workflow coordinator.

Route incoming clearance requests:
- Screenplay/text assets -> transfer to script_clearance_agent.
- Image or video assets  -> transfer to brand_exclusivity_agent.
- "Compile/summarize remediation" requests over prior findings -> remediation_slate_agent.
- Status questions about pending sign-offs: call `list_pending_reviews` yourself.
- For a one-shot full audit where the user wants everything in one step, you
  may call `run_compliance_audit` directly.

Always collect: asset URI, modality, target rating, primary sponsor and
restricted competitors. Ask for whatever is missing; never guess constraints.
Never fabricate findings — every fact must come from a tool result or a
specialist's tool-backed report.

When you call `run_compliance_audit` yourself, end your reply with the tool's
JSON result reproduced VERBATIM in a fenced ```json code block; it contains
`report_uri` (the full report's GCS location). Never try to expand the full
report inline."""


def build_agent():
    from google.adk.agents import LlmAgent

    config = load_config()

    script_agent = LlmAgent(
        name="script_clearance_agent",
        model=config.specialist_model,
        description="Screenplay E&O / right-of-publicity clearance specialist",
        instruction=_SCRIPT_INSTRUCTION,
        tools=[analyze_script_entities, evaluate_policy],
    )
    brand_agent = LlmAgent(
        name="brand_exclusivity_agent",
        model=config.specialist_model,
        description="Image/video logo and sponsor-exclusivity specialist",
        instruction=_BRAND_INSTRUCTION,
        tools=[scan_image_asset, scan_video_asset, evaluate_policy],
    )
    remediation_agent = LlmAgent(
        name="remediation_slate_agent",
        model=config.coordinator_model,
        description="Compiles department-facing remediation slates from findings",
        instruction=_REMEDIATION_INSTRUCTION,
        tools=[],
    )

    return LlmAgent(
        name="compliance_workflow_coordinator",
        model=config.coordinator_model,
        description="Coordinator for the multi-agent compliance workflow",
        instruction=_COORDINATOR_INSTRUCTION,
        tools=[run_compliance_audit, list_pending_reviews],
        sub_agents=[script_agent, brand_agent, remediation_agent],
    )


def create_app():
    from vertexai.preview.reasoning_engines import AdkApp

    return AdkApp(agent=build_agent(), enable_tracing=True)
