"""
schemas.py: Formal input/output and data models for M&E Compliance Vetting Platform.
Supports Pydantic (when installed) with seamless standard-library Dataclass fallback for standalone execution.
"""

from typing import List, Optional, Dict, Any

try:
    from pydantic import BaseModel, Field

    class ExclusivityConstraints(BaseModel):
        primary_sponsor: Optional[str] = None
        restricted_competitors: List[str] = Field(default_factory=list)

    class TemporalVettingTarget(BaseModel):
        timestamp: str
        target_element: str
        action: str

    class IntakeConstraints(BaseModel):
        show_context: str = "General Media Production"
        target_rating: str = "TV-14"
        exclusivity_deals: ExclusivityConstraints = Field(default_factory=ExclusivityConstraints)
        temporal_clearance_targets: List[TemporalVettingTarget] = Field(default_factory=list)
        custom_rules: List[str] = Field(default_factory=list)

    class VFXPaintOutSlate(BaseModel):
        start_timecode: str
        end_timecode: str
        target_description: str
        remediation_action: str = "DIGITAL_PAINT_OUT_OR_BLUR"

    class FlaggedViolation(BaseModel):
        flag_id: str
        phase: str
        location_or_timecode: str
        detected_entity: str
        violation_category: str
        severity: str
        policy_triggered: str
        actionable_remediation: str
        hitl_status: str = "PENDING_LEGAL_REVIEW"
        vfx_slate: Optional[VFXPaintOutSlate] = None

    class ComplianceReport(BaseModel):
        run_id: str
        asset_name: str
        overall_status: str
        summary_metrics: Dict[str, int] = Field(default_factory=dict)
        violations: List[FlaggedViolation] = Field(default_factory=list)
        audit_trail_meta: Dict[str, Any] = Field(default_factory=dict)

except ImportError:
    from dataclasses import dataclass, field

    @dataclass
    class ExclusivityConstraints:
        primary_sponsor: Optional[str] = None
        restricted_competitors: List[str] = field(default_factory=list)

    @dataclass
    class TemporalVettingTarget:
        timestamp: str = "00:00:00"
        target_element: str = ""
        action: str = ""

    @dataclass
    class IntakeConstraints:
        show_context: str = "General Media Production"
        target_rating: str = "TV-14"
        exclusivity_deals: ExclusivityConstraints = field(default_factory=ExclusivityConstraints)
        temporal_clearance_targets: List[TemporalVettingTarget] = field(default_factory=list)
        custom_rules: List[str] = field(default_factory=list)

        @classmethod
        def model_validate(cls, data: dict):
            excl_data = data.get("exclusivity_deals", {})
            excl = ExclusivityConstraints(
                primary_sponsor=excl_data.get("primary_sponsor"),
                restricted_competitors=excl_data.get("restricted_competitors", [])
            )
            targets = [
                TemporalVettingTarget(
                    timestamp=t.get("timestamp", ""),
                    target_element=t.get("target_element", ""),
                    action=t.get("action", "")
                )
                for t in data.get("temporal_clearance_targets", [])
            ]
            return cls(
                show_context=data.get("show_context", "General Media Production"),
                target_rating=data.get("target_rating", "TV-14"),
                exclusivity_deals=excl,
                temporal_clearance_targets=targets,
                custom_rules=data.get("custom_rules", [])
            )

    @dataclass
    class VFXPaintOutSlate:
        start_timecode: str
        end_timecode: str
        target_description: str
        remediation_action: str = "DIGITAL_PAINT_OUT_OR_BLUR"

    @dataclass
    class FlaggedViolation:
        flag_id: str
        phase: str
        location_or_timecode: str
        detected_entity: str
        violation_category: str
        severity: str
        policy_triggered: str
        actionable_remediation: str
        hitl_status: str = "PENDING_LEGAL_REVIEW"
        vfx_slate: Optional[VFXPaintOutSlate] = None

    @dataclass
    class ComplianceReport:
        run_id: str
        asset_name: str
        overall_status: str
        summary_metrics: Dict[str, int] = field(default_factory=dict)
        violations: List[FlaggedViolation] = field(default_factory=list)
        audit_trail_meta: Dict[str, Any] = field(default_factory=dict)
