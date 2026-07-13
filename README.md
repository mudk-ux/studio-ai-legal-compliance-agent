# Studio Compliance — M&E Legal Clearance on Google Cloud

Production implementation (v1.0) of a media & entertainment legal-compliance
platform: **E&O clearance, sponsor exclusivity, and Standards & Practices
vetting** for screenplays, set/wardrobe images, and rough-cut video —
deployable by anyone to their own GCP project on **Vertex AI Agent Engine**.

Verified live in an enterprise GCP environment: both agent tracks deployed,
6/6 smoke gates each, 85.7% local / 84.6% deployed verdict accuracy against a
labeled ground-truth benchmark, zero precision-trap violations, zero silent
failures. Full validation history in [`docs/VERIFICATION.md`](docs/VERIFICATION.md).

Two deployable tracks share one audited core:

| Track | What it is | Deploy with |
| --- | --- | --- |
| **Baseline** | One ADK agent (Gemini Flash) driving the full audited pipeline via a single tool | `python deploy/deploy_baseline.py` |
| **Multi-agent** | Coordinator (Flash) routing to Script / Brand specialists (Gemini Pro) + a remediation-slate compiler | `python deploy/deploy_multiagent.py` |

## Repository layout

| Path | Contents |
| --- | --- |
| `src/studio_compliance/` | The production platform: perception, policy engine, pipeline, agents, HITL |
| `tests/` | 73 unit tests (no GCP credentials required; all mocks live here) |
| `deploy/` · `terraform/` · `evals/` | Deployment scripts, infrastructure as code, scored evaluation harness |
| `docs/` | [Three-implementation review](docs/EVOLUTION.md) · [verification history](docs/VERIFICATION.md) · [rendered architecture review](docs/architecture-review.html) |
| `legacy/` | The two archived predecessor implementations, preserved for provenance ([why they were replaced](legacy/README.md)) |

## Project history

This platform is the third generation of the codebase. Generation 1 (a
single-agent prototype) proved the domain decomposition and the deployment
path; Generation 2 (a multi-agent orchestrator) sketched the
coordinator–specialist architecture without an LLM in the loop; both relied on
perception fallbacks that could fabricate detections. Generation 3 — this
implementation — kept their contributions and rebuilt the execution around
fail-loud, provenance-carrying evidence. The candid comparison of all three,
including limitations and drawbacks of each, is in
[`docs/EVOLUTION.md`](docs/EVOLUTION.md).

## Design principles

1. **Evidence over vibes.** Every finding carries provenance: which API
   produced it (`GCP_VISION_LOGO`, `GCP_VIDEO_INTELLIGENCE`, `GEMINI_SCRIPT_ANALYSIS`, …),
   the API's real confidence score, and real timecodes. Agents are instructed —
   and structurally limited — to report tool results, never invent detections.
2. **Fail loud.** If a perception API or the LLM fails, the report verdict is
   `FAILED` ("this asset was NOT fully vetted"). There is no silent fallback
   path anywhere in production code; mocks exist only inside `tests/`.
3. **Deterministic policy.** Exclusivity matching, S&P substance gating and the
   verdict ladder are plain auditable Python (`src/studio_compliance/policy.py`),
   type-aware (a PERSON named "Worthing" never trips a brand rule) and
   alias-normalized ("DUNKIN' DOUGHNUTS" matches a "Dunkin' Donuts" restriction).
4. **Real HITL.** CRITICAL/HIGH findings persist pending-review records. The
   verdict recomputes only after a named reviewer approves (waives) or enforces
   each one via `python -m studio_compliance.hitl`.
5. **No hardcoded environment.** Project, region, bucket and models all come
   from `STUDIO_*` env vars (`config.env.example`).

## Architecture

```
                          ┌────────────────────────────────────────────┐
 request ──▶ ADK agent(s) │  agents/: routing, legal reasoning, output │
                          └───────────────┬────────────────────────────┘
                                          │ tools (JSON in/out)
                          ┌───────────────▼────────────────────────────┐
                          │ pipeline.py: perception → policy → report  │
                          │  • language.py  (NL API, chunked NER)      │
                          │  • vision.py    (logo + OCR)               │
                          │  • video.py     (logo tracks, HH:MM:SS.mmm)│
                          │  • script_llm.py(Gemini structured output) │
                          │  • policy.py    (deterministic rules)      │
                          │  • hitl.py      (persisted review queue)   │
                          └────────────────────────────────────────────┘
```

## Quickstart (any GCP project)

### 0. Prerequisites
- Python 3.10+, `gcloud` authenticated (`gcloud auth application-default login`)
- A GCP project with billing enabled

### 1. Provision infrastructure (once)
```bash
cd terraform
terraform init
terraform apply -var project_id=YOUR_PROJECT -var staging_bucket_name=YOUR_UNIQUE_BUCKET
cd ..
```
(Or enable the APIs and create the bucket by hand; `terraform/main.tf` lists them.)

### 2. Configure
```bash
cp config.env.example .env    # then edit: project, bucket
pip install -e ".[agents,dev]"
```

### 3. Unit tests (no GCP needed)
```bash
pytest          # mocked perception; verifies policy, pipeline, HITL, scoring
ruff check .
```

### 4. Local end-to-end run (uses your GCP APIs, no deployment)
```bash
python -c "
from studio_compliance.pipeline import run_compliance_audit
import json
print(json.dumps(run_compliance_audit(
    'path/to/script.txt', 'TEXT_SCREENPLAY',
    {'target_rating': 'TV-PG',
     'exclusivity_deals': {'primary_sponsor': 'Starbucks',
                           'restricted_competitors': [\"Dunkin' Donuts\"]}}), indent=2))
"
```

### 5. Deploy
```bash
python deploy/deploy_baseline.py      # and/or
python deploy/deploy_multiagent.py
```
Each prints its Agent Engine resource name.

### 6. Smoke test, then evaluate against your benchmark assets
```bash
python deploy/smoke_test.py --engine-id <RESOURCE_NAME>

python evals/run_evals.py --target engine --engine-id <RESOURCE_NAME> \
    --assets-dir /path/to/benchmark_assets
# or, without deploying:
python evals/run_evals.py --target local --assets-dir /path/to/benchmark_assets
```
Eval output (`eval_results/eval-*.md|json`) reports **computed** entity recall,
precision-trap violations and verdict accuracy. Assets marked `uncertain: true`
in `evals/manifest.yaml` aren't scored; the report prints their detections so
you can label them once and promote them to scored ground truth.

### 7. Human review workflow
```bash
python -m studio_compliance.hitl list
python -m studio_compliance.hitl approve HITL-XXXX --reviewer "J. Doe" --note "waiver on file"
python -m studio_compliance.hitl enforce HITL-XXXX --reviewer "J. Doe" --note "paint-out mandatory"
```

## Benchmark asset notes (ground truth provenance)

`evals/manifest.yaml` was labeled by direct inspection of the benchmark suite.
Two data defects exist in the original zip and are documented there:
`elephantsdream_teaser.mp4` is byte-identical to `big_buck_bunny_clip.mp4`,
and `cc0_open_prop_beverage_can.jpg` is byte-identical to
`mock_luxury_handbag.jpg`. Known traps the suite tests: the Good Will Hunting
"DO YOU LIKE APPLES?" line (fruit, not Apple Inc.), the Damier-lookalike
handbag (no explicit logo), and the salted Sintel script (Sony/Apple ×120).

## Extending

- **New rule categories:** add to `SUBSTANCE_CATEGORIES` / `_RATING_BLOCKLIST`
  or extend `evaluate_entities` in `policy.py` — one table-driven module, fully
  unit-tested.
- **New modality:** add a perception client raising `PerceptionError`, a
  `_run_<modality>` branch in `pipeline.py`, and a tool wrapper in
  `agents/tools.py`.
- **New assets in the eval:** append to `evals/manifest.yaml`; mark
  `uncertain: true` until you've reviewed the first run's detections.

## Known limitations & post-MVP roadmap

The MVP is scoped to what has been verified live. Deliberately deferred
(identified during live deployment validation; none block production use):

- **Long-video resilience/cost**: remote runs on 10+ minute assets can hit
  transient 503 stream resets behind corporate cert proxies (one retry is
  built in). Roadmap: segment-scoped analysis (`video_context.segments`),
  low-res proxy transcodes, hash-based upload dedup.
- **Video logo false positives**: Video Intelligence emits sub-second flicker
  detections on CG content (honest MEDIUMs today). Roadmap: track-duration /
  confidence floor as an auditable policy rule.
- **Pattern-similarity infringement** (e.g. Damier-style lookalikes with no
  explicit logo): needs a contextual multimodal pass, not logo detection.
- **HITL concurrency**: the file-per-record GCS store is safe for a small
  reviewer team; a Firestore backend would add transactional guarantees for
  simultaneous reviewers.
- **Coordinator structured output**: `evals/engine_client.py` makes response
  parsing robust; a `response_schema` on the coordinator would harden it
  further.
- **429 quota retries** under heavy concurrent audit load (tenacity/backoff
  in the perception layer).
- **Script–video timestamp alignment** for contextual scene-level vetting
  (transcription + forced alignment; targets portrayal-based violations that
  logo detection cannot see).

## Cost & scale notes

- Vision/NL calls are per-asset and cheap; Video Intelligence LOGO_RECOGNITION
  is the dominant cost (per-minute of footage) — the eval uploads videos once
  and reuses the GCS URI across constraint profiles.
- Agent Engine scales to zero; the deterministic pipeline is stateless, so
  horizontal scale is limited only by API quotas (`aiplatform.googleapis.com`,
  `videointelligence.googleapis.com`).
