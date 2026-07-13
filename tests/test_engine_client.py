"""Agent-response parsing: report_uri download, ADK response nesting, fallbacks."""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "evals"))

from engine_client import extract_report  # noqa: E402

FULL_REPORT = {"verdict": "BLOCKED", "findings": [{"entity": "Sony"}], "run_id": "RUN-1"}


def fake_download(uri):
    assert uri == "gs://bucket/reports/RUN-1.json"
    return json.dumps(FULL_REPORT)


def test_compact_block_with_report_uri_downloads_full_report():
    text = (
        "Here is the audit outcome.\n```json\n"
        + json.dumps({"report_uri": "gs://bucket/reports/RUN-1.json", "verdict": "BLOCKED"})
        + "\n```"
    )
    assert extract_report(text, download=fake_download) == FULL_REPORT


def test_adk_nested_tool_response_is_unwrapped():
    # Live-observed: ADK wraps tool output under '<tool_name>_response'.
    nested = {"run_compliance_audit_response": {"report_uri": "gs://bucket/reports/RUN-1.json"}}
    text = "```json\n" + json.dumps(nested) + "\n```"
    assert extract_report(text, download=fake_download) == FULL_REPORT


def test_bare_uri_in_prose_is_found():
    text = "The full report was saved to gs://bucket/reports/RUN-1.json for review."
    assert extract_report(text, download=fake_download) == FULL_REPORT


def test_inline_report_fallback_without_bucket():
    text = "```json\n" + json.dumps(FULL_REPORT) + "\n```"
    assert extract_report(text, download=fake_download) == FULL_REPORT


def test_truncated_json_without_uri_raises():
    # An LLM cut off mid-report must be an error, not a silent partial parse.
    truncated = '```json\n{"verdict": "BLOCKED", "findings": [{"entity": "So'
    with pytest.raises(RuntimeError, match="No report"):
        extract_report(truncated, download=fake_download)


def test_compact_report_is_token_safe():
    from studio_compliance.reporting import MAX_INLINE_FINDINGS, compact_report
    from studio_compliance.schemas import (
        ComplianceReport,
        EntityType,
        Finding,
        FindingCategory,
        IntakeConstraints,
        Modality,
        Severity,
        SourceApi,
        Verdict,
    )

    findings = [
        Finding(
            category=FindingCategory.UNCLEARED_ORGANIZATION_REFERENCE,
            severity=Severity.CRITICAL if i == 0 else Severity.MEDIUM,
            entity=f"Entity {i}",
            entity_type=EntityType.ORGANIZATION,
            description="d" * 500,
            remediation="r" * 500,
            source_api=SourceApi.GCP_NATURAL_LANGUAGE,
        )
        for i in range(300)
    ]
    report = ComplianceReport(
        asset_uri="gs://b/big_script.txt",
        asset_name="big_script.txt",
        modality=Modality.TEXT_SCREENPLAY,
        constraints=IntakeConstraints(),
        verdict=Verdict.BLOCKED,
        findings=findings,
    )
    compact = compact_report(report, "gs://b/reports/X.json")
    assert compact["report_uri"] == "gs://b/reports/X.json"
    assert compact["findings_total"] == 300
    assert len(compact["findings_preview"]) == MAX_INLINE_FINDINGS
    assert compact["findings_preview"][0]["severity"] == "CRITICAL"  # ranked first
    # The whole compact payload must stay far below LLM output ceilings.
    assert len(json.dumps(compact)) < 8_000
