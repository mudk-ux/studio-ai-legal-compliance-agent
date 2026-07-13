"""Parsing of deployed-agent responses into full compliance reports.

The agent's conversational reply carries a compact JSON block containing
`report_uri` (GCS location of the full report). This module extracts that
reference and downloads the report. It also tolerates two live-observed
variants: ADK nesting tool output under '<tool_name>_response', and older
replies that embedded the full report inline.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable

_GS_JSON_URI = re.compile(r"gs://[^\s'\"`)\]}]+\.json")


def _unwrap_tool_response(obj: dict) -> dict:
    """ADK wraps a tool's dict return under '<tool_name>_response'."""
    for key, value in obj.items():
        if key.endswith("_response") and isinstance(value, dict):
            return value
    return obj


def _json_candidates(text: str) -> list[dict]:
    candidates = []
    for chunk in text.split("```"):
        chunk = chunk.strip()
        if chunk.startswith("json"):
            chunk = chunk[4:]
        try:
            obj = json.loads(chunk)
        except (ValueError, TypeError):
            continue
        if isinstance(obj, dict):
            candidates.append(_unwrap_tool_response(obj))
    return candidates


def extract_report(text: str, download: Callable[[str], str]) -> dict:
    """Return the FULL report dict referenced by (or embedded in) an agent reply.

    Resolution order:
    1. compact JSON block with 'report_uri'  -> download full report from GCS
    2. bare gs://...json URI in the text     -> download
    3. inline dict with 'verdict'            -> use directly (legacy/no-bucket)
    Raises RuntimeError when nothing usable is found.
    """
    candidates = _json_candidates(text)

    for obj in candidates:
        uri = obj.get("report_uri")
        if isinstance(uri, str) and uri.startswith("gs://"):
            return json.loads(download(uri))

    uri_match = _GS_JSON_URI.search(text)
    if uri_match:
        try:
            return json.loads(download(uri_match.group(0)))
        except Exception:
            pass  # fall through to inline candidates

    inline = [c for c in candidates if "verdict" in c]
    if inline:
        return max(inline, key=lambda c: len(json.dumps(c)))

    raise RuntimeError(
        f"No report reference or report JSON found in agent response ({len(text)} chars)"
    )


def collect_response_text(engine, user_id: str, prompt: str) -> str:
    """Drain an Agent Engine stream_query into plain text."""
    parts: list[str] = []
    for event in engine.stream_query(user_id=user_id, message=prompt):
        content = event.get("content", {}) if isinstance(event, dict) else {}
        for part in content.get("parts", []):
            if "text" in part:
                parts.append(part["text"])
    return "\n".join(parts)
