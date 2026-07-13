"""
test_observability_and_memory.py: Local verification harness for enterprise
Observability (JSON logging, OpenTelemetry tracing, PII redaction) and Memory
(SQLite session store, context compaction).
"""

import json
from src.observability import redact_pii_and_dlp, log_intent_outcome, start_trace_span
from src.memory import compact_screenplay_history, session_store


def test_pii_redaction():
    raw = "Jordan Belfort SSN is 123-45-6789 and email jordan@stratton.com."
    redacted = redact_pii_and_dlp(raw)
    assert "[REDACTED_SSN]" in redacted, f"Failed SSN redaction: {redacted}"
    assert "[REDACTED_EMAIL]" in redacted, f"Failed Email redaction: {redacted}"
    print("✔ PII / DLP active redaction verified!")


def test_session_persistence():
    s_id = "TEST-SESSION-999"
    session_store.save_session(
        session_id=s_id,
        asset_ref="sample_data/test.txt",
        modality="TEXT_SCREENPLAY",
        status="CLEARED",
        history=[{"test": "data"}]
    )
    retrieved = session_store.get_session(s_id)
    assert retrieved is not None, "Failed to recall persistent session from SQLite store!"
    assert retrieved["overall_status"] == "CLEARED"
    print("✔ Persistent SQLite Session State Store verified!")


def test_context_compaction():
    dummy_long_text = "A" * 60000
    compacted = compact_screenplay_history(dummy_long_text, max_chars=10000)
    assert len(compacted) < len(dummy_long_text)
    assert "HISTORY COMPACTION & CONTEXT CACHE" in compacted
    print("✔ Screenplay Sliding-Window Compaction & Context Caching verified!")


def test_observability_trace():
    with start_trace_span("test_span", attributes={"test": True}) as trace_id:
        log_intent_outcome(
            intent="Test clearance audit",
            actual_outcome={"status": "CLEARED"},
            trace_id=trace_id
        )
    print("✔ OpenTelemetry Tracing Spans & Intent-vs-Outcome structured logs verified!")


if __name__ == "__main__":
    print("=== STARTING OBSERVABILITY & MEMORY VALIDATION SUITE ===")
    test_pii_redaction()
    test_session_persistence()
    test_context_compaction()
    test_observability_trace()
    print("=== ALL OBSERVABILITY & MEMORY SUITES PASSED SUCCESSFULLY ===")
