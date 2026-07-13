# Legacy Implementations

This directory preserves the two earlier generations of the platform, exactly as
they were built (with deployment identifiers replaced by placeholders). They are
**archived for provenance and are not maintained**: they are excluded from CI,
from linting, and from the test suite, and they should not be deployed.

| Folder | Generation | Summary |
| --- | --- | --- |
| `gen1-baseline/` | Generation 1 | Single-agent coordinator on Vertex AI Reasoning Engine with dual-mode perception tools and a Streamlit dashboard. Proved the domain decomposition and the deployment path. |
| `gen2-adk2-studio/` | Generation 2 | Coordinator–specialist "multi-agent" orchestrator with a human-in-the-loop payload design. Introduced the architecture that the current platform implements with real LLM agents. |

## Why they were replaced

Both generations shared a perception layer with silent fallbacks: when a live
API call failed, detection quietly degraded to filename-based heuristics with
fabricated confidence scores — a disqualifying failure mode for a legal
clearance tool. Generation 2 additionally carried model names as labels without
invoking any model, and its human-in-the-loop pause returned a payload without
pausing execution.

The current platform (repository root) is a ground-up rewrite around fail-loud
semantics: perception failures produce a `FAILED` verdict, never a fabricated
clearance, and every finding carries API provenance, real confidence scores,
and real timecodes.

The full comparison — architecture and flow diagrams, accomplishments,
limitations, and drawbacks for all three generations — is in
[`docs/EVOLUTION.md`](../docs/EVOLUTION.md) and the rendered
[`docs/architecture-review.html`](../docs/architecture-review.html).
