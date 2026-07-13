"""Tool functions exposed to the ADK agents.

Each tool is a thin, JSON-in/JSON-out wrapper over the audited pipeline and
perception layer. Agents never fabricate findings: everything they report
traces back to a tool result, and every tool result carries provenance.
"""

from __future__ import annotations

import json
from functools import lru_cache

from ..hitl import HITLStore
from ..pipeline import CompliancePipeline
from ..policy import compute_verdict, evaluate_entities
from ..schemas import DetectedEntity, HITLStatus, IntakeConstraints


@lru_cache(maxsize=1)
def _pipeline() -> CompliancePipeline:
    return CompliancePipeline()


def run_compliance_audit(asset_uri: str, modality: str, constraints_json: str) -> dict:
    """Run the full audited compliance pipeline on one asset.

    Args:
        asset_uri: gs:// URI (or container-local path) of the asset to vet.
        modality: One of TEXT_SCREENPLAY, VISUAL_IMAGE, TEMPORAL_VIDEO.
        constraints_json: JSON object with show_context, target_rating and
            exclusivity_deals {primary_sponsor, restricted_competitors}.

    Returns:
        A compact result: verdict, severity counts, a preview of the top
        findings, stage failures, pending human-review tokens, and
        'report_uri' — the GCS location of the full report JSON. (Full
        feature-script reports exceed LLM output limits, so they are stored,
        not echoed. If no staging bucket is configured, the full report dict
        is returned directly.)
    """
    from ..observability import log_event
    from ..reporting import compact_report
    from ..storage import upload_text

    constraints = json.loads(constraints_json) if constraints_json else {}
    pipe = _pipeline()
    report = pipe.run(asset_uri, modality, constraints)
    full = report.model_dump(mode="json")

    staging = pipe.config.staging_bucket
    if not staging:
        return full
    try:
        report_uri = upload_text(
            f"{staging.rstrip('/')}/reports/{report.run_id}.json",
            json.dumps(full, indent=2),
        )
    except Exception as exc:
        # Never lose the report over a storage hiccup: fall back to inline.
        log_event("REPORT_UPLOAD_FAILED", severity="WARNING", run_id=report.run_id, error=str(exc))
        return full
    return compact_report(report, report_uri)


MAX_INLINE_ENTITIES = 30


def compact_entities(entities: list[dict], entities_uri: str) -> dict:
    """Token-safe summary of an entity list stored at entities_uri.

    Feature scripts yield 300+ entities (~40KB+ serialized); passing that
    inline through the LLM as a tool argument gets truncated mid-JSON
    (observed live). The full list is stored; agents pass the reference.
    """
    type_counts: dict[str, int] = {}
    for entity in entities:
        type_counts[entity["entity_type"]] = type_counts.get(entity["entity_type"], 0) + 1
    ranked = sorted(entities, key=lambda e: -(e.get("salience") or 0.0))
    return {
        "entities_uri": entities_uri,
        "entities_total": len(entities),
        "type_counts": type_counts,
        "entities_preview": [
            {
                "name": e["name"],
                "entity_type": e["entity_type"],
                "salience": e.get("salience"),
                "mention_count": e.get("mention_count"),
            }
            for e in ranked[:MAX_INLINE_ENTITIES]
        ],
        "note": (
            "Full entity list stored at entities_uri. Pass entities_uri as the "
            "detections_uri argument of evaluate_policy — do NOT re-serialize "
            "the entity list inline."
        ),
    }


def analyze_script_entities(asset_uri: str) -> dict:
    """Extract person/organization/brand entities from a screenplay text asset.

    Args:
        asset_uri: gs:// URI or local path of the script text file.

    Returns:
        A compact summary: entity counts by type, a preview of the most
        salient entities, and 'entities_uri' — the GCS location of the full
        entity list. Pass entities_uri to evaluate_policy as detections_uri.
        Returns 'error' if the perception stage failed. (If no staging bucket
        is configured, the full 'entities' list is returned inline.)
    """
    import uuid

    from ..observability import log_event, redact_pii
    from ..storage import read_text, upload_text
    from ..textprep import strip_gutenberg_boilerplate

    pipe = _pipeline()
    try:
        text = redact_pii(strip_gutenberg_boilerplate(read_text(asset_uri)))
        entities = pipe.language.analyze_entities(text)
    except Exception as exc:  # surfaced in the tool result, never swallowed
        return {"error": str(exc), "entities": []}

    dumped = [e.model_dump(mode="json") for e in entities]
    staging = pipe.config.staging_bucket
    if not staging:
        return {"entities": dumped}
    try:
        entities_uri = upload_text(
            f"{staging.rstrip('/')}/entities/{uuid.uuid4().hex[:12]}.json",
            json.dumps(dumped),
        )
    except Exception as exc:
        log_event("ENTITIES_UPLOAD_FAILED", severity="WARNING", error=str(exc))
        return {"entities": dumped}
    return compact_entities(dumped, entities_uri)


def scan_image_asset(asset_uri: str) -> dict:
    """Detect logos and printed brand text in an image asset (Vision API).

    Args:
        asset_uri: gs:// URI or local path of the image.

    Returns:
        Dict with 'entities' carrying real API confidence scores, or 'error'.
    """
    pipe = _pipeline()
    entities, failures = pipe._run_image(asset_uri)
    return {
        "entities": [e.model_dump(mode="json") for e in entities],
        "error": failures[0].error if failures else None,
    }


def scan_video_asset(asset_uri: str) -> dict:
    """Detect brand logos with timecodes in a video asset (Video Intelligence API).

    Args:
        asset_uri: gs:// URI of the video (Video Intelligence requires GCS).

    Returns:
        Dict with 'entities' including HH:MM:SS.mmm timecode ranges, or 'error'.
    """
    pipe = _pipeline()
    entities, failures = pipe._run_video(asset_uri)
    return {
        "entities": [e.model_dump(mode="json") for e in entities],
        "error": failures[0].error if failures else None,
    }


def evaluate_policy(detections_json: str = "", constraints_json: str = "", detections_uri: str = "") -> dict:
    """Apply the deterministic policy engine to previously detected entities.

    Args:
        detections_json: JSON list of detected entities — ONLY for small lists
            (image/video scans). For screenplay entity lists, use
            detections_uri instead; large inline JSON gets truncated.
        constraints_json: JSON intake constraints (sponsor, restricted list, rating).
        detections_uri: gs:// URI of a stored entity list (the 'entities_uri'
            returned by analyze_script_entities). Preferred for large lists.

    Returns:
        Dict with 'findings' and the computed 'verdict', or 'error'.
    """
    from ..storage import read_text

    try:
        if detections_uri:
            raw = json.loads(read_text(detections_uri))
        elif detections_json:
            raw = json.loads(detections_json)
        else:
            return {"error": "Provide detections_uri (preferred) or detections_json.", "findings": []}
        entities = [DetectedEntity.model_validate(e) for e in raw]
    except Exception as exc:
        return {"error": f"Could not load detections: {exc}", "findings": []}

    constraints = IntakeConstraints.model_validate(json.loads(constraints_json) if constraints_json else {})
    findings = evaluate_entities(entities, constraints)
    verdict = compute_verdict(findings, failures=[])
    return {
        "verdict": verdict.value,
        "findings": [f.model_dump(mode="json") for f in findings],
    }


def list_pending_reviews() -> dict:
    """List Human-in-the-Loop reviews still awaiting a named reviewer's sign-off.

    Returns:
        Dict with 'pending' records (token, severity, entity, asset).
    """
    store: HITLStore = _pipeline().hitl_store
    return {
        "pending": [
            {
                "token": r.token,
                "severity": r.finding.severity.value,
                "entity": r.finding.entity,
                "asset_uri": r.asset_uri,
                "created_at": r.created_at,
            }
            for r in store.list(HITLStatus.PENDING)
        ]
    }


__all__ = [
    "run_compliance_audit",
    "analyze_script_entities",
    "scan_image_asset",
    "scan_video_asset",
    "evaluate_policy",
    "list_pending_reviews",
]
