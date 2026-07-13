"""The shared compliance pipeline: perception -> policy -> report.

Both deployable agents (baseline single-agent and the multi-agent workflow)
execute this same audited core; the agents differ in how work is routed and
explained, never in what counts as evidence.
"""

from __future__ import annotations

import time

from .config import AppConfig, load_config
from .hitl import HITLStore
from .observability import log_event, redact_pii, trace_span
from .perception import LanguageClient, PerceptionError, VideoClient, VisionClient
from .policy import (
    SUBSTANCE_CATEGORIES,
    compute_verdict,
    evaluate_entities,
    scan_script_for_rule_entities,
    scan_text_for_terms,
)
from .schemas import (
    ComplianceReport,
    DetectedEntity,
    EntityType,
    HITLStatus,
    IntakeConstraints,
    Modality,
    ScriptAnalysis,
    SourceApi,
    StageFailure,
    Verdict,
)
from .script_llm import ScriptAnalyzer, make_noop_analysis
from .storage import asset_basename, read_text
from .textprep import strip_gutenberg_boilerplate


class CompliancePipeline:
    def __init__(
        self,
        config: AppConfig | None = None,
        language: LanguageClient | None = None,
        vision: VisionClient | None = None,
        video: VideoClient | None = None,
        script_analyzer: ScriptAnalyzer | None = None,
        hitl_store: HITLStore | None = None,
    ):
        self.config = config or load_config()
        self.language = language or LanguageClient(chunk_bytes=self.config.nl_chunk_bytes)
        self.vision = vision or VisionClient()
        self.video = video or VideoClient(operation_timeout_s=self.config.video_operation_timeout_s)
        self.script_analyzer = script_analyzer or ScriptAnalyzer(self.config)
        self.hitl_store = hitl_store or HITLStore(self.config.hitl_store)

    # ------------------------------------------------------------------
    def run(self, asset_uri: str, modality: Modality | str, constraints: IntakeConstraints | dict) -> ComplianceReport:
        modality = Modality(modality)
        if isinstance(constraints, dict):
            constraints = IntakeConstraints.model_validate(constraints)

        started = time.perf_counter()
        entities: list[DetectedEntity] = []
        failures: list[StageFailure] = []
        script_analysis: ScriptAnalysis | None = None

        with trace_span("compliance_pipeline_run", asset=asset_uri, modality=modality.value) as trace_id:
            if modality == Modality.TEXT_SCREENPLAY:
                entities, script_analysis, failures = self._run_text(asset_uri, constraints)
            elif modality == Modality.VISUAL_IMAGE:
                entities, failures = self._run_image(asset_uri)
            elif modality == Modality.TEMPORAL_VIDEO:
                entities, failures = self._run_video(asset_uri)

            findings = evaluate_entities(entities, constraints, script_analysis)
            verdict = compute_verdict(findings, failures)

            report = ComplianceReport(
                asset_uri=asset_uri,
                asset_name=asset_basename(asset_uri),
                modality=modality,
                constraints=constraints,
                verdict=verdict,
                findings=findings,
                failures=failures,
                detected_entities=entities,
                script_analysis=script_analysis,
                models_used={
                    "script_analysis": (script_analysis.model_id or "none") if script_analysis else "n/a",
                },
                trace_id=trace_id,
            )

            # Persist pending human reviews for findings that demand sign-off.
            for finding in report.findings:
                if finding.requires_human_review and verdict != Verdict.FAILED:
                    record = self.hitl_store.create(report.run_id, asset_uri, finding)
                    report.pending_hitl_tokens.append(record.token)

            report.duration_ms = round((time.perf_counter() - started) * 1000, 2)
            log_event(
                "PIPELINE_COMPLETE",
                trace_id=trace_id,
                run_id=report.run_id,
                verdict=report.verdict.value,
                findings=len(report.findings),
                failures=len(report.failures),
                pending_reviews=len(report.pending_hitl_tokens),
            )
        return report

    # ------------------------------------------------------------------
    def _run_text(self, asset_uri: str, constraints: IntakeConstraints):
        entities: list[DetectedEntity] = []
        failures: list[StageFailure] = []
        script_analysis: ScriptAnalysis | None = None

        try:
            raw_text = read_text(asset_uri)
        except Exception as exc:
            return entities, script_analysis, [StageFailure(stage="storage", error=str(exc))]

        sanitized = redact_pii(strip_gutenberg_boilerplate(raw_text))
        try:
            entities = self.language.analyze_entities(sanitized)
        except PerceptionError as exc:
            failures.append(StageFailure(stage=exc.stage, error=exc.detail))
            return entities, script_analysis, failures

        # NER-independent scan for the deal's own terms (restricted competitors,
        # sponsor, substance brands) — catches all-caps action lines and
        # lowercase prop notes the NL API misses.
        entities = entities + scan_script_for_rule_entities(sanitized, constraints, entities)

        persons = [e for e in entities if e.entity_type == EntityType.PERSON]
        try:
            script_analysis = self.script_analyzer.assess(
                sanitized, persons, show_context=constraints.show_context
            )
        except PerceptionError as exc:
            if self.config.llm_required:
                failures.append(StageFailure(stage=exc.stage, error=exc.detail))
            else:
                script_analysis = make_noop_analysis(exc.detail)
                log_event("SCRIPT_LLM_SKIPPED", severity="WARNING", reason=exc.detail)
        return entities, script_analysis, failures

    def _run_image(self, asset_uri: str):
        entities: list[DetectedEntity] = []
        failures: list[StageFailure] = []
        try:
            result = self.vision.scan_image(asset_uri)
        except PerceptionError as exc:
            return entities, [StageFailure(stage=exc.stage, error=exc.detail)]

        entities.extend(result.logos)
        # Scan OCR evidence for substance brands and printed brand terms that
        # the logo model missed; provenance stays OCR.
        if result.ocr_text:
            detected_names = {e.name.casefold() for e in entities}
            ocr_terms = scan_text_for_terms(result.ocr_text, list(SUBSTANCE_CATEGORIES.keys()))
            for term in ocr_terms:
                if term.casefold() not in detected_names:
                    entities.append(
                        DetectedEntity(
                            name=term.title(),
                            entity_type=EntityType.BRAND,
                            source_api=SourceApi.GCP_VISION_OCR,
                            detail="Printed brand text recognized via OCR",
                        )
                    )
        return entities, failures

    def _run_video(self, asset_uri: str):
        try:
            return self.video.scan_video(asset_uri), []
        except PerceptionError as exc:
            return [], [StageFailure(stage=exc.stage, error=exc.detail)]

    # ------------------------------------------------------------------
    def finalize(self, report: ComplianceReport) -> ComplianceReport:
        """Recompute the verdict after human reviews have been resolved."""
        from .policy import recompute_verdict_with_resolutions

        resolutions = self.hitl_store.resolutions_for_run(report.run_id)
        report.verdict = recompute_verdict_with_resolutions(report.findings, report.failures, resolutions)
        report.pending_hitl_tokens = [
            f.hitl_token
            for f in report.findings
            if f.hitl_token and resolutions.get(f.hitl_token, HITLStatus.PENDING) == HITLStatus.PENDING
        ]
        return report


# Convenience for scripts / notebooks
def run_compliance_audit(asset_uri: str, modality: str, constraints: dict) -> dict:
    """One-call helper: runs the pipeline with environment config and returns a JSON-safe dict."""
    pipeline = CompliancePipeline()
    return pipeline.run(asset_uri, modality, constraints).model_dump(mode="json")
