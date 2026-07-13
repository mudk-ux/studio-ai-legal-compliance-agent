# Verification History — MVP 1.0

The production implementation was validated through five independent QA and
deployment-validation rounds plus a final acceptance run, executed in an
enterprise GCP environment against live Google Cloud APIs and Vertex AI Agent
Engine. Environment identifiers (project numbers, engine resource IDs) are
redacted throughout this repository.

## Round-by-round

| Round | Gate | Outcome |
| --- | --- | --- |
| R1 | First deployment attempt | Build failed (packaging paths) · Natural Language API crash on CRLF text → fixed with build staging, CRLF normalization, `protobuf<7` pin |
| R2 | Deploy retry + eval integrity | Container import failure exposed and fixed · policy recalibrated from live NL API behavior (advisory LOW/INFO severities, honorific pass) |
| R3 | Engines must start | **Deployment succeeded** · smoke tests passed · multi-agent routing and remote HITL verified · report-retrieval defects identified |
| R4 | Remote eval must complete | **10/11 verdicts correct** via the `report_uri` retrieval architecture · multi-agent tool-argument serialization ceiling found |
| R5 | Script specialist on a feature screenplay | **Passed** — 301 entities passed by GCS reference (`entities_uri`), no truncation · license-boilerplate stripping and transient-503 retry added |
| Final | MVP acceptance | Both engines 6/6 smoke gates · local eval 12/14 · deployed eval 11/13 · HITL approve/enforce/double-reject verified end to end → declared **MVP 1.0** |

## Final acceptance metrics (2026-07)

| Metric | Local pipeline (C.1) | Deployed engine (C.4) |
| --- | --- | --- |
| Runs total | 15 | 15 |
| Runs errored | 0 | 1 (transient 503 on a 10-minute video, environment) |
| Pipeline failures (`FAILED` verdicts) | 0 | 0 |
| Verdicts evaluated / correct | 14 / 12 | 13 / 11 |
| Verdict accuracy | 0.8571 | 0.8462 |
| Entity recall | 0.7917 | 0.7826 |
| Forbidden-entity (precision-trap) violations | 0 | 0 |

Additional verified behavior:

- **Deployment**: both tracks build and start on Vertex AI Agent Engine in ~90 seconds each.
- **Multi-agent state passing**: the script specialist processed a feature screenplay by writing 404 extracted entities to GCS and passing the reference between tools — no large payloads transit the model context.
- **HITL lifecycle**: pending records created by remote runs were listed, approved, and enforced via the CLI by a named reviewer; double resolution is rejected with a validation error; verdicts recompute only on resolution.
- **Smoke gates** (per engine): response non-empty · report retrievable via `report_uri` · verdict present · verdict not `FAILED` · provenance on findings · restricted competitor correctly flagged.

## Scoring method

All numbers are computed by `evals/run_evals.py` against the labeled
ground-truth manifest (`evals/manifest.yaml`):

- **Verdict accuracy** — exact match against per-profile expected verdicts.
- **Entity recall** — expected entities detected at or above their labeled minimum severity (alias-aware matching).
- **Forbidden-entity violations** — precision traps that must *not* be flagged (e.g. the fruit line "DO YOU LIKE APPLES?" must not match Apple Inc.).
- Infrastructure failures are bucketed separately (`runs_errored`, `runs_pipeline_failed`) and never counted toward accuracy.
- Assets whose detections proved run-variable are marked `uncertain` and excluded from scoring; their detections are recorded verbatim for labeling.

The two remaining verdict deltas (an 1895 stage play scoring
`CONDITIONAL_CLEARANCE` instead of `CLEARED`) are conservative behavior on
real historical institutions named in dialogue, not detection errors; see the
period-context item in the [future-work roadmap](EVOLUTION.md#future-work).
