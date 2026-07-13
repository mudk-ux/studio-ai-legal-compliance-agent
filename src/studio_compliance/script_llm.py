"""Gemini-based script analysis (structured output).

The deterministic NER layer finds *names*; this pass answers the legal
question a name alone cannot: is this a real, living person portrayed in the
script (right-of-publicity / defamation exposure) or a fictional character?

Uses google-genai against Vertex AI with a strict response schema, so the
output is machine-checkable — no free-text parsing.
"""

from __future__ import annotations

from .config import AppConfig
from .observability import trace_span
from .perception.base import PerceptionError
from .schemas import DetectedEntity, PersonAssessment, ScriptAnalysis

_PROMPT = """You are a studio legal E&O analyst. The screenplay excerpt below was \
processed by an entity-extraction pass which found these PERSON names:

{names}

Show context: {show_context}

For EACH name, assess:
- is_real_living_person: true only if the name refers to an identifiable real
  person who is (or may plausibly be) alive today, as portrayed in this script.
  Fictional characters are false. Historical figures dead well over 70 years are false.
- is_public_figure: whether that real person is a public figure (affects the
  First Amendment / docudrama analysis).
- portrayal_risk: CRITICAL, HIGH, MEDIUM or LOW — how legally exposed the
  portrayal is (negative/defamatory portrayal of a living person is HIGH+;
  incidental neutral mention of a public figure is MEDIUM; ambiguous is MEDIUM).
- rationale: one sentence.

Also summarize in docudrama_context whether this script as a whole portrays
real events/people (docudrama) or is purely fictional.

Base your assessment ONLY on the script content provided and well-known public
facts about the named individuals.

SCRIPT EXCERPT (may be truncated):
{script}
"""


class ScriptAnalyzer:
    def __init__(self, config: AppConfig, model_id: str | None = None):
        self.config = config
        self.model_id = model_id or config.specialist_model

    def assess(
        self,
        script_text: str,
        person_entities: list[DetectedEntity],
        show_context: str = "(not provided)",
    ) -> ScriptAnalysis:
        if not person_entities:
            return ScriptAnalysis(persons=[], docudrama_context="No person entities detected.", model_id=None)
        try:
            from google import genai
        except ImportError as exc:
            raise PerceptionError("script_llm", "google-genai is not installed", exc) from exc

        names = "\n".join(f"- {e.name}" for e in person_entities[:60])
        # Feature scripts fit comfortably in the 1M context window; cap defensively.
        excerpt = script_text[:800_000]
        prompt = _PROMPT.format(names=names, show_context=show_context, script=excerpt)

        with trace_span("script_llm_assess", model=self.model_id, persons=len(person_entities)):
            try:
                client = genai.Client(
                    vertexai=True,
                    project=self.config.require_project(),
                    location=self.config.location,
                )
                response = client.models.generate_content(
                    model=self.model_id,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": ScriptAnalysis,
                        "temperature": 0.0,
                    },
                )
                analysis: ScriptAnalysis = response.parsed  # pydantic instance
                if analysis is None:
                    raise PerceptionError("script_llm", "model returned unparseable output")
            except PerceptionError:
                raise
            except Exception as exc:
                raise PerceptionError("script_llm", f"generate_content failed: {exc}", exc) from exc

        analysis.model_id = self.model_id
        # Guard against the model inventing names not in the input list.
        # Normalized comparison, not raw casefold: the model may echo
        # 'MISS PRISM' as 'Miss Prism' — a dropped assessment leaves the name
        # as an unassessed candidate instead of a vetted one.
        from .policy import normalize_name

        allowed = {normalize_name(e.name) for e in person_entities}
        analysis.persons = [p for p in analysis.persons if normalize_name(p.name) in allowed]
        return analysis


def make_noop_analysis(reason: str) -> ScriptAnalysis:
    """Used when STUDIO_LLM_REQUIRED=false and the operator opted out of LLM analysis."""
    return ScriptAnalysis(persons=[], docudrama_context=f"LLM analysis skipped: {reason}", model_id=None)


__all__ = ["ScriptAnalyzer", "make_noop_analysis", "PersonAssessment"]
