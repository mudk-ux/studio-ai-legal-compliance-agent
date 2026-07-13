"""Scoring for eval runs: entity recall, precision traps, verdict accuracy.

All numbers are computed from actual run results. Nothing here hardcodes a
conclusion — if every run errors, the report says so.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_SEVERITY_RANK = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}


def _normalize(name: str) -> str:
    import re
    import unicodedata

    s = unicodedata.normalize("NFKD", name).casefold().replace("’", "'")
    s = re.sub(r"'s\b", "", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _matches(finding_entity: str, expected_name: str, aliases: list[str]) -> bool:
    import re

    candidates = [expected_name, *aliases]
    entity_norm = _normalize(finding_entity)
    for candidate in candidates:
        c = _normalize(candidate)
        if entity_norm == c or re.search(rf"\b{re.escape(c)}\b", entity_norm):
            return True
    return False


@dataclass
class ProfileResult:
    asset_id: str
    profile: str
    expected_verdict: str | None
    actual_verdict: str | None
    error: str | None = None
    entity_hits: list[str] = field(default_factory=list)
    entity_misses: list[str] = field(default_factory=list)
    forbidden_violations: list[str] = field(default_factory=list)
    uncertain: bool = False
    findings: list[dict] = field(default_factory=list)

    @property
    def pipeline_failed(self) -> bool:
        """The pipeline itself could not vet the asset (API/credentials/quota).
        Reported separately — an infra failure is not a wrong verdict."""
        return self.actual_verdict == "FAILED" and self.expected_verdict != "FAILED"

    @property
    def verdict_correct(self) -> bool | None:
        if self.uncertain or self.expected_verdict is None or self.error or self.pipeline_failed:
            return None
        return self.actual_verdict == self.expected_verdict


def score_profile(
    asset: dict[str, Any],
    profile_name: str,
    profile: dict[str, Any],
    report: dict[str, Any] | None,
    error: str | None,
) -> ProfileResult:
    result = ProfileResult(
        asset_id=asset["id"],
        profile=profile_name,
        expected_verdict=profile.get("expected_verdict"),
        actual_verdict=(report or {}).get("verdict"),
        error=error,
        uncertain=bool(asset.get("uncertain")),
        findings=(report or {}).get("findings", []),
    )
    if error or report is None:
        return result

    findings = report.get("findings", [])

    for expected in asset.get("expected_entities", []):
        # An expectation may apply only to specific constraint profiles
        # (e.g. 'Apple' is only findable when Apple is a restricted term).
        if expected.get("profiles") and profile_name not in expected["profiles"]:
            continue
        min_rank = _SEVERITY_RANK[expected.get("min_severity", "LOW")]
        hit = any(
            _matches(f["entity"], expected["name"], expected.get("aliases", []))
            and _SEVERITY_RANK.get(f["severity"], -1) >= min_rank
            for f in findings
        )
        (result.entity_hits if hit else result.entity_misses).append(expected["name"])

    for forbidden in asset.get("forbidden_entities", []):
        violated = any(
            _matches(f["entity"], forbidden["name"], [])
            and _SEVERITY_RANK.get(f["severity"], -1) >= _SEVERITY_RANK["MEDIUM"]
            for f in findings
        )
        if violated:
            result.forbidden_violations.append(forbidden["name"])

    return result


def summarize(results: list[ProfileResult]) -> dict[str, Any]:
    scored = [r for r in results if not r.uncertain]
    errored = [r for r in results if r.error]
    pipeline_failed = [r for r in results if r.pipeline_failed]
    verdict_evaluated = [r for r in scored if r.verdict_correct is not None]

    total_expected = sum(len(r.entity_hits) + len(r.entity_misses) for r in scored)
    total_hits = sum(len(r.entity_hits) for r in scored)
    total_forbidden = sum(len(r.forbidden_violations) for r in scored)

    return {
        "runs_total": len(results),
        "runs_errored": len(errored),
        "runs_pipeline_failed": len(pipeline_failed),
        "runs_uncertain_unscored": len([r for r in results if r.uncertain]),
        "verdicts_evaluated": len(verdict_evaluated),
        "verdicts_correct": sum(1 for r in verdict_evaluated if r.verdict_correct),
        "verdict_accuracy": (
            round(sum(1 for r in verdict_evaluated if r.verdict_correct) / len(verdict_evaluated), 4)
            if verdict_evaluated
            else None
        ),
        "expected_entities_total": total_expected,
        "expected_entities_detected": total_hits,
        "entity_recall": round(total_hits / total_expected, 4) if total_expected else None,
        "forbidden_entity_violations": total_forbidden,
    }


def render_markdown(results: list[ProfileResult], summary: dict[str, Any], target: str) -> str:
    lines = [
        "# Eval report",
        "",
        f"Target: `{target}`",
        "",
        "## Summary (computed from this run — no hardcoded claims)",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- **{key}**: {value}")

    lines += ["", "## Per-run results", "",
              "| Asset | Profile | Expected | Actual | Verdict OK | Entity hits | Misses | Forbidden hits | Error |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in results:
        ok = {True: "yes", False: "**NO**", None: "n/a"}[r.verdict_correct]
        lines.append(
            f"| {r.asset_id} | {r.profile} | {r.expected_verdict or '—'} | {r.actual_verdict or '—'} "
            f"| {ok} | {', '.join(r.entity_hits) or '—'} | {', '.join(r.entity_misses) or '—'} "
            f"| {', '.join(r.forbidden_violations) or '—'} | {r.error or '—'} |"
        )

    uncertain = [r for r in results if r.uncertain]
    if uncertain:
        lines += ["", "## Unlabeled assets — review these detections and add ground truth to the manifest", ""]
        for r in uncertain:
            lines.append(f"### {r.asset_id} ({r.profile})")
            lines.append(f"Verdict returned: `{r.actual_verdict or r.error}`")
            if r.findings:
                for f in r.findings:
                    tc = "; ".join(f"{t['start']}–{t['end']}" for t in f.get("timecodes", []))
                    lines.append(
                        f"- {f['severity']} {f['category']} `{f['entity']}` "
                        f"(source {f['source_api']}, conf {f.get('confidence')}) {tc}"
                    )
            else:
                lines.append("- No findings returned.")
            lines.append("")
    return "\n".join(lines)
