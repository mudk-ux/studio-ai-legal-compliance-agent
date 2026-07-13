"""Pipeline behavior: fail-loud semantics, provenance, HITL creation."""

from conftest import (
    FakeLanguageClient,
    FakeScriptAnalyzer,
    FakeVideoClient,
    FakeVisionClient,
    living_person_assessment,
    logo,
    org,
    person,
    video_brand,
)
from studio_compliance.pipeline import CompliancePipeline
from studio_compliance.schemas import (
    FindingCategory,
    HITLStatus,
    Modality,
    ScriptAnalysis,
    Verdict,
)


def make_pipeline(config, hitl_store, **clients):
    return CompliancePipeline(
        config=config,
        language=clients.get("language", FakeLanguageClient()),
        vision=clients.get("vision", FakeVisionClient()),
        video=clients.get("video", FakeVideoClient()),
        script_analyzer=clients.get("script_analyzer", FakeScriptAnalyzer()),
        hitl_store=hitl_store,
    )


def constraints_dict(sponsor="Starbucks", restricted=("Facebook",)):
    return {
        "show_context": "Test",
        "target_rating": "TV-PG",
        "exclusivity_deals": {
            "primary_sponsor": sponsor,
            "restricted_competitors": list(restricted),
        },
    }


# ---------------------------------------------------------------------------
# Fail-loud: perception failures can NEVER produce a clearance
# ---------------------------------------------------------------------------
def test_vision_failure_yields_failed_verdict_not_cleared(config, hitl_store):
    pipeline = make_pipeline(config, hitl_store, vision=FakeVisionClient(error="auth denied"))
    report = pipeline.run("gs://b/image.jpg", Modality.VISUAL_IMAGE, constraints_dict())
    assert report.verdict == Verdict.FAILED
    assert report.failures[0].stage == "vision"
    assert report.findings == []  # nothing fabricated
    assert report.pending_hitl_tokens == []  # no reviews created for unvetted assets


def test_video_failure_yields_failed(config, hitl_store):
    pipeline = make_pipeline(config, hitl_store, video=FakeVideoClient(error="timeout"))
    report = pipeline.run("gs://b/cut.mp4", Modality.TEMPORAL_VIDEO, constraints_dict())
    assert report.verdict == Verdict.FAILED


def test_missing_text_asset_yields_failed(config, hitl_store):
    pipeline = make_pipeline(config, hitl_store)
    report = pipeline.run("Z:/does/not/exist.txt", Modality.TEXT_SCREENPLAY, constraints_dict())
    assert report.verdict == Verdict.FAILED
    assert report.failures[0].stage == "storage"


def test_llm_failure_fails_report_when_required(config, hitl_store, tmp_path):
    script = tmp_path / "s.txt"
    script.write_text("MARK ZUCKERBERG enters.", encoding="utf-8")
    pipeline = make_pipeline(
        config, hitl_store,
        language=FakeLanguageClient(entities=[person("Mark Zuckerberg")]),
        script_analyzer=FakeScriptAnalyzer(error="model unavailable"),
    )
    report = pipeline.run(str(script), Modality.TEXT_SCREENPLAY, constraints_dict())
    assert report.verdict == Verdict.FAILED


def test_llm_failure_degrades_visibly_when_not_required(config, hitl_store, tmp_path):
    config.llm_required = False
    script = tmp_path / "s.txt"
    script.write_text("MARK ZUCKERBERG enters.", encoding="utf-8")
    pipeline = make_pipeline(
        config, hitl_store,
        language=FakeLanguageClient(entities=[person("Mark Zuckerberg")]),
        script_analyzer=FakeScriptAnalyzer(error="model unavailable"),
    )
    report = pipeline.run(str(script), Modality.TEXT_SCREENPLAY, constraints_dict())
    assert report.verdict != Verdict.FAILED
    assert "skipped" in (report.script_analysis.docudrama_context or "")
    # Person surfaces as LOW candidate, not silently dropped
    assert report.findings[0].category == FindingCategory.PERSON_CLEARANCE_CANDIDATE


# ---------------------------------------------------------------------------
# End-to-end (mocked perception) happy paths
# ---------------------------------------------------------------------------
def test_script_flow_with_llm_assessment(config, hitl_store, tmp_path):
    script = tmp_path / "sn.txt"
    script.write_text("ZUCKERBERG talks about Facebook at Harvard.", encoding="utf-8")
    pipeline = make_pipeline(
        config, hitl_store,
        language=FakeLanguageClient(
            entities=[org("Facebook"), org("Harvard"), person("Mark Zuckerberg")]
        ),
        script_analyzer=FakeScriptAnalyzer(
            analysis=ScriptAnalysis(persons=[living_person_assessment("Mark Zuckerberg")])
        ),
    )
    report = pipeline.run(str(script), Modality.TEXT_SCREENPLAY, constraints_dict())
    assert report.verdict == Verdict.BLOCKED  # Facebook restricted
    categories = {f.category for f in report.findings}
    assert FindingCategory.SPONSOR_EXCLUSIVITY_BREACH in categories
    assert FindingCategory.RIGHT_OF_PUBLICITY in categories
    assert FindingCategory.UNCLEARED_ORGANIZATION_REFERENCE in categories  # Harvard


def test_script_flow_term_scan_catches_what_ner_missed(config, hitl_store, tmp_path):
    # Live-run regression: NL returned nothing for "DUNKIN' DOUGHNUTS" in an
    # all-caps action line; the constraint-term scan must still find it.
    script = tmp_path / "gwh.txt"
    script.write_text(
        "He waits in the Cadillac with two cups of DUNKIN' DOUGHNUTS coffee.\n"
        "DO YOU LIKE APPLES?",
        encoding="utf-8",
    )
    pipeline = make_pipeline(
        config, hitl_store,
        language=FakeLanguageClient(entities=[]),  # NER found nothing
    )
    report = pipeline.run(
        str(script), Modality.TEXT_SCREENPLAY,
        constraints_dict(sponsor="Starbucks", restricted=("Dunkin' Donuts",)),
    )
    assert report.verdict == Verdict.BLOCKED
    breach = report.findings[0]
    assert breach.entity == "Dunkin' Donuts"
    assert breach.source_api.value == "DETERMINISTIC_TEXT_SCAN"
    # And the fruit line produced nothing (Apple is not a constraint term here).
    assert all("apple" not in f.entity.lower() for f in report.findings)


def test_image_flow_ocr_supplements_logo_detection(config, hitl_store):
    pipeline = make_pipeline(
        config, hitl_store,
        vision=FakeVisionClient(logos=[], ocr_text="VUSE device barrel text"),
    )
    report = pipeline.run("gs://b/vape.jpg", Modality.VISUAL_IMAGE, constraints_dict())
    assert report.verdict == Verdict.BLOCKED
    finding = report.findings[0]
    assert finding.category == FindingCategory.SP_SUBSTANCE_VIOLATION
    assert finding.source_api.value == "GCP_VISION_OCR"  # provenance is honest


def test_video_flow_attaches_slates_and_creates_hitl(config, hitl_store):
    pipeline = make_pipeline(
        config, hitl_store,
        video=FakeVideoClient(entities=[video_brand("Sony")]),
    )
    report = pipeline.run(
        "gs://b/cut.mp4", Modality.TEMPORAL_VIDEO,
        constraints_dict(sponsor="Apple", restricted=("Sony",)),
    )
    assert report.verdict == Verdict.BLOCKED
    assert report.findings[0].vfx_slates
    assert len(report.pending_hitl_tokens) == 1
    # The record is really persisted
    record = hitl_store.get(report.pending_hitl_tokens[0])
    assert record is not None
    assert record.finding.entity == "Sony"


def test_hitl_resolution_flips_verdict_on_finalize(config, hitl_store):
    pipeline = make_pipeline(
        config, hitl_store,
        video=FakeVideoClient(entities=[video_brand("Sony")]),
    )
    report = pipeline.run(
        "gs://b/cut.mp4", Modality.TEMPORAL_VIDEO,
        constraints_dict(sponsor="Apple", restricted=("Sony",)),
    )
    token = report.pending_hitl_tokens[0]
    hitl_store.resolve(token, decision=HITLStatus.APPROVED, reviewer="QA")
    finalized = pipeline.finalize(report)
    assert finalized.verdict == Verdict.CLEARED
    assert finalized.pending_hitl_tokens == []


def test_report_carries_provenance_and_trace(config, hitl_store):
    pipeline = make_pipeline(
        config, hitl_store, vision=FakeVisionClient(logos=[logo("Nike", confidence=0.987)])
    )
    report = pipeline.run("gs://b/jacket.jpg", Modality.VISUAL_IMAGE, constraints_dict())
    assert report.trace_id
    assert report.detected_entities[0].confidence == 0.987
    assert report.duration_ms is not None
