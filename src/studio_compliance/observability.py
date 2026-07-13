"""Structured JSON logging, tracing spans, and PII redaction.

Log lines are single-line JSON on stdout, which Cloud Logging ingests as
structured payloads from Agent Engine / Cloud Run containers.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import time
import uuid
from contextlib import contextmanager
from typing import Any

_LOGGER = logging.getLogger("studio_compliance")
_LOGGER.setLevel(logging.INFO)
if not _LOGGER.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _LOGGER.addHandler(_handler)
    _LOGGER.propagate = False

_PII_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}\b"), "[REDACTED_EMAIL]"),
    (re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"), "[REDACTED_CARD]"),
    (re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[REDACTED_PHONE]"),
]


def redact_pii(text: str) -> str:
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def log_event(event: str, severity: str = "INFO", trace_id: str | None = None, **payload: Any) -> None:
    record = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "service": "studio-compliance",
        "event": event,
        "severity": severity.upper(),
        "trace_id": trace_id,
        **{k: (redact_pii(v) if isinstance(v, str) else v) for k, v in payload.items()},
    }
    line = json.dumps(record, default=str)
    if severity.upper() in ("ERROR", "CRITICAL"):
        _LOGGER.error(line)
    elif severity.upper() == "WARNING":
        _LOGGER.warning(line)
    else:
        _LOGGER.info(line)


@contextmanager
def trace_span(name: str, trace_id: str | None = None, **attributes: Any):
    t_id = trace_id or uuid.uuid4().hex
    start = time.perf_counter()
    log_event("SPAN_START", trace_id=t_id, span=name, **attributes)
    try:
        yield t_id
    except Exception as exc:
        log_event("SPAN_ERROR", severity="ERROR", trace_id=t_id, span=name, error=str(exc))
        raise
    finally:
        log_event(
            "SPAN_END",
            trace_id=t_id,
            span=name,
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )
