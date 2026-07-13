"""Schemas round-trip, timecode math, storage URI parsing, PII redaction,
report rendering, chunking."""

import pytest

from conftest import logo, video_brand
from studio_compliance.observability import redact_pii
from studio_compliance.perception.language import _chunk_text
from studio_compliance.perception.video import format_timecode
from studio_compliance.reporting import save_report, to_markdown
from studio_compliance.schemas import (
    ComplianceReport,
    ExclusivityDeal,
    IntakeConstraints,
    Modality,
    Verdict,
)
from studio_compliance.storage import StorageError, asset_basename, split_gcs_uri


def test_format_timecode_handles_minutes_and_hours():
    # The legacy code rendered 148s as 00:00:148 — this is the regression test.
    assert format_timecode(148.0) == "00:02:28.000"
    assert format_timecode(3735.5) == "01:02:15.500"
    assert format_timecode(0) == "00:00:00.000"
    assert format_timecode(-5) == "00:00:00.000"


def test_split_gcs_uri():
    assert split_gcs_uri("gs://bucket/a/b.mp4") == ("bucket", "a/b.mp4")
    with pytest.raises(StorageError):
        split_gcs_uri("gs://bucketonly")
    with pytest.raises(StorageError):
        split_gcs_uri("/local/path.mp4")


def test_asset_basename_local_and_gcs():
    assert asset_basename("gs://b/x/y/script.txt") == "script.txt"
    assert asset_basename(r"C:\media\clip.mp4".replace("\\", "/")) == "clip.mp4"


def test_read_text_normalizes_crlf(tmp_path):
    # CRLF payloads crash the live NL API's response deserialization.
    p = tmp_path / "crlf.txt"
    p.write_bytes(b"INT. OFFICE - DAY\r\nA producer waits.\rEnd.")
    from studio_compliance.storage import read_text

    assert read_text(str(p)) == "INT. OFFICE - DAY\nA producer waits.\nEnd."


def test_keep_entity_filters_common_noun_consumer_goods():
    # Live NL returns 'bread'/'sofa'/'piano' as CONSUMER_GOOD with zero
    # proper-noun mentions; they must not become 'uncleared brands'.
    from studio_compliance.perception.language import keep_entity
    from studio_compliance.schemas import EntityType

    assert not keep_entity(EntityType.BRAND, proper_mentions=0)
    assert not keep_entity(EntityType.ORGANIZATION, proper_mentions=0)
    assert keep_entity(EntityType.BRAND, proper_mentions=1)
    assert keep_entity(EntityType.PERSON, proper_mentions=0)


def test_redact_pii():
    text = "Call 555-867-5309, SSN 123-45-6789, mail agent@studio.com"
    redacted = redact_pii(text)
    assert "[REDACTED_PHONE]" in redacted
    assert "[REDACTED_SSN]" in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "867" not in redacted


def test_chunk_text_respects_limit_and_preserves_content():
    text = "\n\n".join(f"Paragraph {i} " + "x" * 100 for i in range(200))
    chunks = _chunk_text(text, max_bytes=2000)
    assert all(len(c.encode("utf-8")) <= 2000 for c in chunks)
    assert "".join(chunks).replace("\n\n", "").count("Paragraph") == 200


def make_report(**kw):
    defaults = dict(
        asset_uri="gs://b/a.jpg",
        asset_name="a.jpg",
        modality=Modality.VISUAL_IMAGE,
        constraints=IntakeConstraints(
            exclusivity_deals=ExclusivityDeal(primary_sponsor="Nike", restricted_competitors=["Adidas"])
        ),
        verdict=Verdict.CLEARED,
    )
    defaults.update(kw)
    return ComplianceReport(**defaults)


def test_report_json_roundtrip():
    report = make_report(detected_entities=[logo("Nike", 0.98), video_brand("Sony")])
    restored = ComplianceReport.model_validate_json(report.model_dump_json())
    assert restored.detected_entities[1].timecodes[0].start == "00:02:28.000"


def test_markdown_render_failed_report_screams(tmp_path):
    from studio_compliance.schemas import StageFailure

    report = make_report(
        verdict=Verdict.FAILED,
        failures=[StageFailure(stage="vision", error="quota exceeded")],
    )
    md = to_markdown(report)
    assert "NOT fully vetted" in md
    assert "quota exceeded" in md
    json_path, md_path = save_report(report, str(tmp_path))
    assert json_path.endswith(".json") and md_path.endswith(".md")
