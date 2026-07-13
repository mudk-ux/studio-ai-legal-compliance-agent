"""
agent.py: Google Cloud Agent Runtime (Reasoning Engine) deployment package
for the M&E Copyright Infringement & Legal Compliance Platform.
Uses Google ADK 2.0 and LifecycleOptimizedAgent wrapper.
"""

from google.adk import Agent
from google.adk.models.google_llm import Gemini
from src.tools.gcp_ml_tools import extract_proper_nouns, scan_image_logos, detect_video_brand_timestamps
from src.tools.ffmpeg_slicer import extract_keyframe_at_timecode

# Configure Vertex AI client credentials for Agent Runtime deployment
model_config = {
    "vertexai": True,
    "project": "your-gcp-project-id",
    "location": "us-central1"
}

# Coordinator & High-Volume Triage Model (Gemini 2.5 Flash)
flash_model = Gemini(
    model="gemini-2.5-flash",
    client_kwargs=model_config
)

# Frontier Legal & Exclusivity Specialist Model (Gemini 3.5 Pro)
pro_model = Gemini(
    model="gemini-3.5-pro",
    client_kwargs=model_config
)


class LifecycleOptimizedAgent(Agent):
    """Subclass to safely unbind cached asyncio event loop clients inside Agent Runtime."""
    async def run_async(self, *args, **kwargs):
        for key in ["api_client", "_api_backend"]:
            if hasattr(self.model, "__dict__") and key in self.model.__dict__:
                del self.model.__dict__[key]
        async for event in super().run_async(*args, **kwargs):
            yield event


# Root Agent Runtime Compliance Coordinator
compliance_coordinator_agent = LifecycleOptimizedAgent(
    name="me_copyright_compliance_coordinator",
    model=flash_model,
    tools=[
        extract_proper_nouns,
        scan_image_logos,
        detect_video_brand_timestamps,
        extract_keyframe_at_timecode
    ],
    instruction="""You are the Master M&E Copyright Infringement & Legal Compliance Agent running on Google Cloud Agent Runtime.
Your task is to orchestrate multi-modal script, visual, and temporal video clearances against studio static legal policies and dynamic operator constraints (`constraints.json`).

Guidelines:
1. When vetting screenplays (`TEXT_SCREENPLAY`), invoke `extract_proper_nouns` to extract living public figures and commercial brands. Evaluate living names against the 0/3-Plus Metropolitan Census frequency rule.
2. When vetting pre-production set or wardrobe images (`VISUAL_IMAGE`), invoke `scan_image_logos` to identify third-party emblems (`Nike`, `Louis Vuitton`) and cross-reference them against active sponsor exclusivity deals (`restricted_competitors`).
3. When vetting rough-cut videos (`TEMPORAL_VIDEO`), invoke `detect_video_brand_timestamps` to track temporal brand occurrences (`Samsung`, `Apple`) across frame timecodes, and output actionable VFX Paint-Out Slates (`EDL/XML`).
4. Compile all itemized flags into a structured, auditable `ComplianceReport` JSON ledger with exact severities (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) and remediation slates for production departments.
"""
)


class MECopyrightComplianceApp:
    """Master Reasoning Engine runtime wrapper exposing `.query()` endpoint for Google Cloud Agent Runtime."""
    def __init__(self):
        self.agent = compliance_coordinator_agent

    def query(self, input: str) -> str:
        import asyncio
        import concurrent.futures
        from google.adk.runners import InMemoryRunner

        def _run_in_new_loop():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            runner = InMemoryRunner(node=self.agent)
            events = new_loop.run_until_complete(runner.run_debug(input))
            new_loop.close()
            return events

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run_in_new_loop)
            events = future.result()

        collected_chunks = []
        for event in events:
            # Check all possible text/payload holding attributes on ADK events
            for attr in ["output", "content", "text", "message"]:
                val = getattr(event, attr, None)
                if val:
                    val_str = str(val).strip()
                    if val_str and val_str not in collected_chunks:
                        collected_chunks.append(val_str)

        # Prefer returning the largest structured block (the compiled compliance report JSON/Markdown)
        structured_reports = [c for c in collected_chunks if ("ComplianceReport" in c or "clearance_status" in c or "Itemized Findings" in c or "VIOLATION" in c.upper())]
        if structured_reports:
            return max(structured_reports, key=len)

        if collected_chunks:
            return "\n\n".join(collected_chunks)

        return "Compliance review completed."
