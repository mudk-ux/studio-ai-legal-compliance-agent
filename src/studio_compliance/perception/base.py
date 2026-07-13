"""Perception layer contract.

Every client raises PerceptionError on failure. There are NO silent fallbacks:
a failed API call becomes a StageFailure on the report and the verdict becomes
FAILED. Mock perception exists only in the test suite, injected explicitly.
"""

from __future__ import annotations


class PerceptionError(RuntimeError):
    def __init__(self, stage: str, detail: str, cause: Exception | None = None):
        super().__init__(f"[{stage}] {detail}")
        self.stage = stage
        self.detail = detail
        self.cause = cause
