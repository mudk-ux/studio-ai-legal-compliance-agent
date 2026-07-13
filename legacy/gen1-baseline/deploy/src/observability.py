"""
observability.py: Enterprise Structured JSON Logging, OpenTelemetry Tracing Spans,
Intent-vs-Outcome Operational Audit Records, and Active PII/DLP Redaction.
Designed for structured Google Cloud Logging compatibility.
"""

import json
import logging
import re
import sys
import time
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# 1. ACTIVE PII / DLP REDACTION MECHANISM
# ---------------------------------------------------------------------------
def redact_pii_and_dlp(text: str) -> str:
    """Active PII/DLP redaction mechanism to sanitize input/output before logging or persistence."""
    if not text or not isinstance(text, str):
        return str(text)

    # SSN pattern
    sanitized = re.sub(
        r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]", text
    )
    # Email pattern
    sanitized = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b",
        "[REDACTED_EMAIL]",
        sanitized,
    )
    # Credit Card pattern
    sanitized = re.sub(
        r"\b(?:\d{4}[-\s]?){3}\d{4}\b", "[REDACTED_CARD]", sanitized
    )
    # Phone pattern
    sanitized = re.sub(
        r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "[REDACTED_PHONE]",
        sanitized,
    )
    return sanitized


# ---------------------------------------------------------------------------
# 2. STRUCTURED JSON LOGGER (GOOGLE CLOUD LOGGING COMPLIANT)
# ---------------------------------------------------------------------------
class JSONStructuredLogger:
    """Emits pure structured JSON log lines for Google Cloud Logging and OpenTelemetry aggregators."""

    def __init__(self, service_name: str = "MECopyrightComplianceService"):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.INFO)
            self.logger.addHandler(handler)

    def log_structured(
        self,
        event_type: str,
        severity: str = "INFO",
        trace_id: Optional[str] = None,
        intent: Optional[str] = None,
        actual_outcome: Optional[Any] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "service": self.service_name,
            "event": event_type,
            "severity": severity.upper(),
            "trace_id": trace_id or str(uuid.uuid4()),
        }
        if intent:
            record["intent"] = redact_pii_and_dlp(str(intent))
        if actual_outcome is not None:
            if isinstance(actual_outcome, (dict, list)):
                record["actual_outcome"] = actual_outcome
            else:
                record["actual_outcome"] = redact_pii_and_dlp(str(actual_outcome))
        if payload:
            record["payload"] = {
                k: redact_pii_and_dlp(str(v)) if isinstance(v, str) else v
                for k, v in payload.items()
            }

        log_line = json.dumps(record)
        if severity.upper() in ["ERROR", "CRITICAL"]:
            self.logger.error(log_line)
        else:
            self.logger.info(log_line)
        return record


# Global singleton structured logger
structured_logger = JSONStructuredLogger()


def log_intent_outcome(
    intent: str,
    actual_outcome: Any,
    trace_id: Optional[str] = None,
    status: str = "COMPLETED",
) -> Dict[str, Any]:
    """Operational log recording the agent's initial intent versus actual clearance outcome."""
    return structured_logger.log_structured(
        event_type="AGENT_INTENT_OUTCOME_AUDIT",
        severity="INFO" if status in ["COMPLETED", "CLEARED"] else "WARNING",
        trace_id=trace_id,
        intent=intent,
        actual_outcome=actual_outcome,
        payload={"execution_status": status},
    )


# ---------------------------------------------------------------------------
# 3. OPENTELEMETRY-COMPATIBLE DISTRIBUTED TRACING SPAN WRAPPER
# ---------------------------------------------------------------------------
@contextmanager
def start_trace_span(
    span_name: str,
    trace_id: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
):
    """Context manager simulating OpenTelemetry distributed tracing spans with structured telemetry."""
    t_id = trace_id or str(uuid.uuid4())
    start_time = time.time()
    structured_logger.log_structured(
        event_type="SPAN_START",
        trace_id=t_id,
        payload={"span_name": span_name, "attributes": attributes or {}},
    )
    try:
        yield t_id
    except Exception as exc:
        structured_logger.log_structured(
            event_type="SPAN_EXCEPTION",
            severity="ERROR",
            trace_id=t_id,
            payload={"span_name": span_name, "exception": str(exc)},
        )
        raise
    finally:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        structured_logger.log_structured(
            event_type="SPAN_END",
            trace_id=t_id,
            payload={"span_name": span_name, "duration_ms": duration_ms},
        )
