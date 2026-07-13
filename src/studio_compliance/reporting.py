"""Human-readable rendering of compliance reports."""

from __future__ import annotations

import json
import os

from .schemas import ComplianceReport, Verdict

_VERDICT_LABELS = {
    Verdict.CLEARED: "CLEARED — no unresolved compliance findings",
    Verdict.CONDITIONAL_CLEARANCE: "CONDITIONAL CLEARANCE — resolve itemized findings before distribution",
    Verdict.BLOCKED: "BLOCKED — do not distribute until findings are remediated and signed off",
    Verdict.FAILED: "FAILED — one or more analysis stages failed; this asset was NOT fully vetted",
}


def to_markdown(report: ComplianceReport) -> str:
    lines = [
        f"# Compliance Report `{report.run_id}`",
        "",
        f"- **Asset:** `{report.asset_name}` (`{report.asset_uri}`)",
        f"- **Modality:** {report.modality.value}",
        f"- **Engine:** {report.engine}",
        f"- **Verdict:** **{report.verdict.value}** — {_VERDICT_LABELS[report.verdict]}",
        f"- **Generated:** {report.created_at}  |  duration: {report.duration_ms} ms",
        f"- **Primary sponsor:** {report.constraints.exclusivity_deals.primary_sponsor or 'n/a'}"
        f"  |  restricted: {', '.join(report.constraints.exclusivity_deals.restricted_competitors) or 'none'}",
        f"- **Target rating:** {report.constraints.target_rating}",
    ]
    if report.failures:
        lines += ["", "## Stage failures (asset NOT fully vetted)", ""]
        lines += [f"- `{f.stage}`: {f.error}" for f in report.failures]

    if report.pending_hitl_tokens:
        lines += [
            "",
            "## Pending human reviews",
            "",
            "The following findings require reviewer sign-off "
            "(`python -m studio_compliance.hitl list`):",
            "",
        ]
        lines += [f"- `{t}`" for t in report.pending_hitl_tokens]

    lines += ["", "## Findings", ""]
    if not report.findings:
        lines.append("_None._")
    else:
        lines.append("| Severity | Category | Entity | Source | Confidence | Timecodes | Remediation |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for f in sorted(report.findings, key=lambda x: -x.severity.rank):
            tcs = "; ".join(f"{t.start}–{t.end}" for t in f.timecodes) or "—"
            conf = f"{f.confidence:.3f}" if f.confidence is not None else "—"
            lines.append(
                f"| {f.severity.value} | {f.category.value} | {f.entity} | "
                f"{f.source_api.value} | {conf} | {tcs} | {f.remediation} |"
            )

    slates = [(f, s) for f in report.findings for s in f.vfx_slates]
    if slates:
        lines += ["", "## VFX remediation slate", ""]
        lines.append("| Start | End | Target | Action |")
        lines.append("| --- | --- | --- | --- |")
        for _, s in slates:
            lines.append(f"| {s.start_timecode} | {s.end_timecode} | {s.target_description} | {s.action} |")

    lines += [
        "",
        "## Evidence provenance",
        "",
        f"Detected entities: {len(report.detected_entities)} "
        f"(sources: {', '.join(sorted({e.source_api.value for e in report.detected_entities})) or 'none'})",
    ]
    return "\n".join(lines)


MAX_INLINE_FINDINGS = 20


def compact_report(report: ComplianceReport, report_uri: str) -> dict:
    """Small, token-safe summary of a report for agent conversational output.

    Full reports on feature screenplays run 50–200 KB — past any LLM output
    ceiling, so an agent instructed to echo them gets truncated mid-JSON
    (observed live). The agent returns this compact form instead; the full
    report lives at report_uri and callers download it from GCS.
    """
    ranked = sorted(report.findings, key=lambda f: -f.severity.rank)
    return {
        "report_uri": report_uri,
        "run_id": report.run_id,
        "verdict": report.verdict.value,
        "asset_uri": report.asset_uri,
        "modality": report.modality.value,
        "severity_counts": report.summary_counts(),
        "findings_total": len(report.findings),
        "findings_preview": [
            {
                "severity": f.severity.value,
                "category": f.category.value,
                "entity": f.entity,
                "source_api": f.source_api.value,
                "confidence": f.confidence,
                "timecodes": [f"{t.start}-{t.end}" for t in f.timecodes],
            }
            for f in ranked[:MAX_INLINE_FINDINGS]
        ],
        "failures": [f.model_dump(mode="json") for f in report.failures],
        "pending_hitl_tokens": report.pending_hitl_tokens,
        "note": f"Full report JSON (all {len(report.findings)} findings) at report_uri.",
    }


def save_report(report: ComplianceReport, out_dir: str) -> tuple[str, str]:
    """Write <run_id>.json and <run_id>.md; returns both paths."""
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, f"{report.run_id}.json")
    md_path = os.path.join(out_dir, f"{report.run_id}.md")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(report.model_dump(mode="json"), fh, indent=2)
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(to_markdown(report))
    return json_path, md_path
