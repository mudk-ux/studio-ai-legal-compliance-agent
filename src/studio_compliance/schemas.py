"""Typed domain models.

Every finding carries explicit provenance (which API produced the evidence,
at what confidence). A report can never silently degrade: if a perception
stage fails, the failure is recorded and the verdict becomes FAILED.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class Modality(str, Enum):
    TEXT_SCREENPLAY = "TEXT_SCREENPLAY"
    VISUAL_IMAGE = "VISUAL_IMAGE"
    TEMPORAL_VIDEO = "TEMPORAL_VIDEO"


class EntityType(str, Enum):
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    BRAND = "BRAND"  # logo / consumer-good detections
    LOCATION = "LOCATION"
    OTHER = "OTHER"


class SourceApi(str, Enum):
    GCP_NATURAL_LANGUAGE = "GCP_NATURAL_LANGUAGE"
    GCP_VISION_LOGO = "GCP_VISION_LOGO"
    GCP_VISION_OCR = "GCP_VISION_OCR"
    GCP_VIDEO_INTELLIGENCE = "GCP_VIDEO_INTELLIGENCE"
    GEMINI_SCRIPT_ANALYSIS = "GEMINI_SCRIPT_ANALYSIS"
    DETERMINISTIC_TEXT_SCAN = "DETERMINISTIC_TEXT_SCAN"  # constraint-term scan of script text
    POLICY_ENGINE = "POLICY_ENGINE"


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

    @property
    def rank(self) -> int:
        return {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}[self.value]


class FindingCategory(str, Enum):
    SPONSOR_EXCLUSIVITY_BREACH = "SPONSOR_EXCLUSIVITY_BREACH"
    SP_SUBSTANCE_VIOLATION = "SP_SUBSTANCE_VIOLATION"
    UNCLEARED_BRAND_REFERENCE = "UNCLEARED_BRAND_REFERENCE"
    UNCLEARED_ORGANIZATION_REFERENCE = "UNCLEARED_ORGANIZATION_REFERENCE"
    RIGHT_OF_PUBLICITY = "RIGHT_OF_PUBLICITY"
    PERSON_CLEARANCE_CANDIDATE = "PERSON_CLEARANCE_CANDIDATE"
    SPONSOR_VERIFIED = "SPONSOR_VERIFIED"


class Verdict(str, Enum):
    CLEARED = "CLEARED"
    CONDITIONAL_CLEARANCE = "CONDITIONAL_CLEARANCE"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"  # a perception/LLM stage failed; the asset was NOT fully vetted


class HITLStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"  # reviewer waived / cleared the finding
    ENFORCED = "ENFORCED"  # reviewer upheld the finding (remediation mandatory)


# ---------------------------------------------------------------------------
# Intake
# ---------------------------------------------------------------------------
class ExclusivityDeal(BaseModel):
    primary_sponsor: str | None = None
    restricted_competitors: list[str] = Field(default_factory=list)


class IntakeConstraints(BaseModel):
    show_context: str = "Production clearance audit"
    target_rating: str = "TV-PG"
    exclusivity_deals: ExclusivityDeal = Field(default_factory=ExclusivityDeal)
    custom_rules: str | None = None
    # Severity applied to commercial brands/organizations that are neither the
    # primary sponsor nor restricted competitors.
    uncleared_reference_severity: Severity = Severity.MEDIUM


# ---------------------------------------------------------------------------
# Perception output
# ---------------------------------------------------------------------------
class TimecodeRange(BaseModel):
    start: str  # "HH:MM:SS.mmm"
    end: str


class DetectedEntity(BaseModel):
    name: str
    entity_type: EntityType
    source_api: SourceApi
    confidence: float | None = None  # only when the API reports one
    salience: float | None = None
    mention_count: int = 1
    timecodes: list[TimecodeRange] = Field(default_factory=list)
    knowledge_linked: bool = False  # NL API linked it to a KG/Wikipedia entry
    detail: str | None = None


# ---------------------------------------------------------------------------
# LLM script analysis (structured output from Gemini)
# ---------------------------------------------------------------------------
class PersonAssessment(BaseModel):
    name: str
    is_real_living_person: bool
    is_public_figure: bool = False
    portrayal_risk: Severity = Severity.LOW
    rationale: str


class ScriptAnalysis(BaseModel):
    persons: list[PersonAssessment] = Field(default_factory=list)
    docudrama_context: str | None = None
    model_id: str | None = None


# ---------------------------------------------------------------------------
# Findings & report
# ---------------------------------------------------------------------------
class VFXSlate(BaseModel):
    start_timecode: str
    end_timecode: str
    target_description: str
    action: str = "DIGITAL_PAINT_OUT_OR_BLUR"


class Finding(BaseModel):
    finding_id: str = Field(default_factory=lambda: f"F-{uuid.uuid4().hex[:8].upper()}")
    category: FindingCategory
    severity: Severity
    entity: str
    entity_type: EntityType
    description: str
    remediation: str
    source_api: SourceApi
    confidence: float | None = None
    timecodes: list[TimecodeRange] = Field(default_factory=list)
    vfx_slates: list[VFXSlate] = Field(default_factory=list)
    requires_human_review: bool = False
    hitl_token: str | None = None


class StageFailure(BaseModel):
    stage: str
    error: str


class HITLRecord(BaseModel):
    token: str = Field(default_factory=lambda: f"HITL-{uuid.uuid4().hex[:10].upper()}")
    run_id: str
    asset_uri: str
    finding: Finding
    status: HITLStatus = HITLStatus.PENDING
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: str | None = None
    reviewer: str | None = None
    note: str | None = None


class ComplianceReport(BaseModel):
    run_id: str = Field(default_factory=lambda: f"RUN-{uuid.uuid4().hex[:8].upper()}")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    asset_uri: str
    asset_name: str
    modality: Modality
    constraints: IntakeConstraints
    verdict: Verdict
    findings: list[Finding] = Field(default_factory=list)
    failures: list[StageFailure] = Field(default_factory=list)
    pending_hitl_tokens: list[str] = Field(default_factory=list)
    detected_entities: list[DetectedEntity] = Field(default_factory=list)
    script_analysis: ScriptAnalysis | None = None
    engine: str = "pipeline"  # pipeline | baseline-agent | multiagent
    models_used: dict[str, str] = Field(default_factory=dict)
    duration_ms: float | None = None
    trace_id: str | None = None

    def summary_counts(self) -> dict[str, int]:
        counts = {s.value: 0 for s in Severity}
        for f in self.findings:
            counts[f.severity.value] += 1
        return counts
