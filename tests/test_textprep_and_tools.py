"""Round-5 regressions: Gutenberg boilerplate stripping and entity state-passing."""

import json

from conftest import FakeLanguageClient, FakeScriptAnalyzer, FakeVideoClient, FakeVisionClient
from studio_compliance.agents.tools import MAX_INLINE_ENTITIES, compact_entities, evaluate_policy
from studio_compliance.pipeline import CompliancePipeline
from studio_compliance.schemas import Modality, Verdict
from studio_compliance.textprep import strip_gutenberg_boilerplate

PG_TEXT = (
    "The Project Gutenberg eBook of The Importance of Being Earnest\n"
    "*** START OF THE PROJECT GUTENBERG EBOOK THE IMPORTANCE OF BEING EARNEST ***\n"
    "ALGERNON. Did you hear what I was playing, Lane?\n"
    "*** END OF THE PROJECT GUTENBERG EBOOK THE IMPORTANCE OF BEING EARNEST ***\n"
    "Donations to the Project Gutenberg Literary Archive Foundation are welcome."
)


def test_strip_gutenberg_keeps_only_the_work():
    stripped = strip_gutenberg_boilerplate(PG_TEXT)
    assert "ALGERNON" in stripped
    assert "Literary Archive Foundation" not in stripped
    assert "eBook of The Importance" not in stripped


def test_strip_gutenberg_no_markers_is_identity():
    text = "INT. OFFICE - DAY\nA producer waits."
    assert strip_gutenberg_boilerplate(text) == text


def test_pipeline_strips_boilerplate_before_ner(config, hitl_store, tmp_path):
    # Live regression: PG footer orgs ('Project Gutenberg Literary Archive
    # Foundation') were flagged as uncleared references on the earnest script.
    script = tmp_path / "earnest.txt"
    script.write_text(PG_TEXT, encoding="utf-8")
    language = FakeLanguageClient()
    pipeline = CompliancePipeline(
        config=config, language=language, vision=FakeVisionClient(),
        video=FakeVideoClient(), script_analyzer=FakeScriptAnalyzer(), hitl_store=hitl_store,
    )
    pipeline.run(str(script), Modality.TEXT_SCREENPLAY, {})
    analyzed_text = language.calls[0]
    assert "ALGERNON" in analyzed_text
    assert "Literary Archive Foundation" not in analyzed_text


def _entity(name, etype="ORGANIZATION", salience=0.5):
    return {
        "name": name, "entity_type": etype, "source_api": "GCP_NATURAL_LANGUAGE",
        "confidence": None, "salience": salience, "mention_count": 1,
        "timecodes": [], "knowledge_linked": False, "detail": None,
    }


def test_compact_entities_is_token_safe():
    # Live regression: 301 entities (~40KB) serialized into a tool argument
    # got truncated by the LLM, crashing evaluate_policy with JSONDecodeError.
    entities = [_entity(f"Org {i}", salience=i / 400) for i in range(301)]
    compact = compact_entities(entities, "gs://b/entities/x.json")
    assert compact["entities_total"] == 301
    assert compact["entities_uri"] == "gs://b/entities/x.json"
    assert len(compact["entities_preview"]) == MAX_INLINE_ENTITIES
    assert compact["entities_preview"][0]["name"] == "Org 300"  # most salient first
    assert len(json.dumps(compact)) < 8_000


def test_evaluate_policy_accepts_detections_uri(tmp_path):
    stored = tmp_path / "entities.json"
    stored.write_text(json.dumps([_entity("Facebook")]), encoding="utf-8")
    result = evaluate_policy(
        detections_uri=str(stored),
        constraints_json=json.dumps(
            {"exclusivity_deals": {"primary_sponsor": "Starbucks", "restricted_competitors": ["Facebook"]}}
        ),
    )
    assert result["verdict"] == Verdict.BLOCKED.value
    assert result["findings"][0]["entity"] == "Facebook"


def test_evaluate_policy_surfaces_errors_not_exceptions():
    assert "error" in evaluate_policy()  # neither source provided
    truncated = '[{"name": "Fac'  # the exact live failure shape
    result = evaluate_policy(detections_json=truncated)
    assert "error" in result and result["findings"] == []
