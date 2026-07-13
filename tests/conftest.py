"""Test fixtures. Mock perception lives HERE and only here — production code
has no fallback path to these."""

from __future__ import annotations

import pytest

from studio_compliance.config import AppConfig
from studio_compliance.hitl import HITLStore
from studio_compliance.perception.base import PerceptionError
from studio_compliance.perception.vision import VisionResult
from studio_compliance.schemas import (
    DetectedEntity,
    EntityType,
    PersonAssessment,
    ScriptAnalysis,
    Severity,
    SourceApi,
    TimecodeRange,
)


class FakeLanguageClient:
    def __init__(self, entities=None, error: str | None = None):
        self.entities = entities or []
        self.error = error
        self.calls: list[str] = []

    def analyze_entities(self, text: str):
        self.calls.append(text)
        if self.error:
            raise PerceptionError("natural_language", self.error)
        return list(self.entities)


class FakeVisionClient:
    def __init__(self, logos=None, ocr_text: str = "", error: str | None = None):
        self.result = VisionResult(logos=logos or [], ocr_text=ocr_text)
        self.error = error

    def scan_image(self, image_uri: str):
        if self.error:
            raise PerceptionError("vision", self.error)
        return self.result


class FakeVideoClient:
    def __init__(self, entities=None, error: str | None = None):
        self.entities = entities or []
        self.error = error

    def scan_video(self, video_uri: str):
        if self.error:
            raise PerceptionError("video_intelligence", self.error)
        return list(self.entities)


class FakeScriptAnalyzer:
    def __init__(self, analysis: ScriptAnalysis | None = None, error: str | None = None):
        self.analysis = analysis or ScriptAnalysis()
        self.error = error

    def assess(self, script_text, person_entities, show_context="(n/a)"):
        if self.error:
            raise PerceptionError("script_llm", self.error)
        return self.analysis


@pytest.fixture
def config(tmp_path):
    return AppConfig(project_id="test-project", hitl_store=str(tmp_path / "hitl"), _env_file=None)


@pytest.fixture
def hitl_store(tmp_path):
    return HITLStore(str(tmp_path / "hitl"))


# ---------------------------------------------------------------------------
# Entity factories
# ---------------------------------------------------------------------------
def org(name, **kw):
    return DetectedEntity(
        name=name, entity_type=EntityType.ORGANIZATION,
        source_api=SourceApi.GCP_NATURAL_LANGUAGE, **kw,
    )


def person(name, **kw):
    return DetectedEntity(
        name=name, entity_type=EntityType.PERSON,
        source_api=SourceApi.GCP_NATURAL_LANGUAGE, **kw,
    )


def logo(name, confidence=0.9, **kw):
    return DetectedEntity(
        name=name, entity_type=EntityType.BRAND,
        source_api=SourceApi.GCP_VISION_LOGO, confidence=confidence, **kw,
    )


def video_brand(name, start="00:02:28.000", end="00:02:35.500", confidence=0.8):
    return DetectedEntity(
        name=name, entity_type=EntityType.BRAND,
        source_api=SourceApi.GCP_VIDEO_INTELLIGENCE, confidence=confidence,
        timecodes=[TimecodeRange(start=start, end=end)],
    )


def living_person_assessment(name, risk=Severity.HIGH, public=True):
    return PersonAssessment(
        name=name, is_real_living_person=True, is_public_figure=public,
        portrayal_risk=risk, rationale="Real living public figure portrayed in script.",
    )


def fictional_assessment(name):
    return PersonAssessment(
        name=name, is_real_living_person=False, is_public_figure=False,
        portrayal_risk=Severity.LOW, rationale="Fictional character.",
    )
