"""The eval scorer must be as honest as the pipeline: errors count as errors,
uncertain assets are excluded, and summaries are computed, never asserted."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "evals"))

from scoring import score_profile, summarize  # noqa: E402


def asset_fixture():
    return {
        "id": "test_asset",
        "expected_entities": [
            {"name": "Dunkin' Doughnuts", "min_severity": "MEDIUM", "aliases": ["Dunkin' Donuts"]},
        ],
        "forbidden_entities": [{"name": "Apple", "reason": "fruit"}],
    }


def profile_fixture(expected="BLOCKED"):
    return {"exclusivity_deals": {}, "expected_verdict": expected}


def report_fixture(findings, verdict="BLOCKED"):
    return {"verdict": verdict, "findings": findings}


def finding(entity, severity="CRITICAL"):
    return {"entity": entity, "severity": severity, "category": "X", "source_api": "Y", "timecodes": []}


def test_alias_hit_and_verdict_match():
    result = score_profile(
        asset_fixture(), "p", profile_fixture(),
        report_fixture([finding("Dunkin' Donuts")]), None,
    )
    assert result.entity_hits == ["Dunkin' Doughnuts"]
    assert result.verdict_correct is True


def test_miss_when_severity_below_minimum():
    result = score_profile(
        asset_fixture(), "p", profile_fixture(),
        report_fixture([finding("Dunkin' Donuts", severity="LOW")]), None,
    )
    assert result.entity_misses == ["Dunkin' Doughnuts"]


def test_forbidden_violation_detected():
    result = score_profile(
        asset_fixture(), "p", profile_fixture(),
        report_fixture([finding("Apple", severity="MEDIUM"), finding("Dunkin' Donuts")]), None,
    )
    assert result.forbidden_violations == ["Apple"]


def test_error_run_is_not_scored_as_success():
    result = score_profile(asset_fixture(), "p", profile_fixture(), None, "boom")
    assert result.verdict_correct is None
    summary = summarize([result])
    assert summary["runs_errored"] == 1
    assert summary["verdict_accuracy"] is None  # no fake 100%


def test_profile_scoped_expectations_only_apply_to_named_profiles():
    asset = {
        "id": "t",
        "expected_entities": [
            {"name": "Apple", "min_severity": "MEDIUM", "profiles": ["sony_primary"]},
        ],
        "forbidden_entities": [],
    }
    scoped_out = score_profile(asset, "no_deal", profile_fixture("CONDITIONAL_CLEARANCE"),
                               report_fixture([], verdict="CONDITIONAL_CLEARANCE"), None)
    assert scoped_out.entity_misses == []  # expectation doesn't apply here
    scoped_in = score_profile(asset, "sony_primary", profile_fixture(),
                              report_fixture([], verdict="BLOCKED"), None)
    assert scoped_in.entity_misses == ["Apple"]


def test_pipeline_failed_run_tracked_separately_not_as_wrong_verdict():
    result = score_profile(
        asset_fixture(), "p", profile_fixture(expected="CLEARED"),
        report_fixture([], verdict="FAILED"), None,
    )
    assert result.pipeline_failed
    assert result.verdict_correct is None
    summary = summarize([result])
    assert summary["runs_pipeline_failed"] == 1
    assert summary["verdicts_evaluated"] == 0


def test_uncertain_assets_excluded_from_scores():
    asset = {**asset_fixture(), "uncertain": True}
    result = score_profile(asset, "p", {"exclusivity_deals": {}, "expected_verdict": None},
                           report_fixture([finding("Whatever")]), None)
    summary = summarize([result])
    assert summary["runs_uncertain_unscored"] == 1
    assert summary["verdicts_evaluated"] == 0
