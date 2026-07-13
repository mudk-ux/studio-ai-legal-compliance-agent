"""Eval harness: run the benchmark manifest against the local pipeline or a
deployed Agent Engine, score against ground truth, and write an honest report.

Local pipeline (needs GCP credentials for the perception APIs, no deployment):
    python evals/run_evals.py --target local --assets-dir /path/to/benchmark_assets

Deployed engine (assets are uploaded to your staging bucket automatically):
    python evals/run_evals.py --target engine --engine-id <RESOURCE_NAME> \
        --assets-dir /path/to/benchmark_assets

Notes:
- TEMPORAL_VIDEO assets always require GCS, so both modes upload them.
- Results land in eval_results/ as JSON + Markdown, computed from actual runs.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

from engine_client import collect_response_text, extract_report  # noqa: E402
from scoring import ProfileResult, render_markdown, score_profile, summarize  # noqa: E402
from studio_compliance.config import load_config  # noqa: E402
from studio_compliance.schemas import Modality  # noqa: E402


def _resolve_asset_uri(local_path: str, modality: str, config, upload_all: bool) -> str:
    """Upload to the staging bucket when required (videos always; everything in engine mode)."""
    from studio_compliance.storage import upload_file

    needs_gcs = upload_all or modality == Modality.TEMPORAL_VIDEO.value
    if not needs_gcs:
        return local_path
    bucket = config.require_staging_bucket()
    dest = f"{bucket.rstrip('/')}/eval_assets/"
    print(f"    uploading {os.path.basename(local_path)} -> {dest}")
    return upload_file(local_path, dest)


def _run_local(asset_uri: str, modality: str, constraints: dict) -> dict:
    from studio_compliance.pipeline import CompliancePipeline

    pipeline = CompliancePipeline()
    return pipeline.run(asset_uri, modality, constraints).model_dump(mode="json")


def _run_engine(engine, asset_uri: str, modality: str, constraints: dict) -> dict:
    """Query a deployed agent, then download the full report it references.

    The agent returns a compact JSON block with 'report_uri'; the full report
    (which exceeds LLM output limits for feature scripts) is fetched from GCS.
    """
    from studio_compliance.storage import read_text

    prompt = (
        "Run a compliance audit now.\n"
        f"Asset URI: {asset_uri}\nModality: {modality}\n"
        f"Constraints JSON: {json.dumps(constraints)}\n"
        "Call run_compliance_audit and reproduce its JSON result verbatim in a "
        "fenced json code block."
    )
    # One retry on transient stream errors (503 gateway resets behind
    # corporate cert proxies were observed on ~20% of long runs).
    transient_markers = ("503", "ServiceUnavailable", "Stream removed", "DeadlineExceeded")
    for attempt in (1, 2):
        try:
            text = collect_response_text(engine, user_id="eval-harness", prompt=prompt)
            return extract_report(text, download=read_text)
        except Exception as exc:
            if attempt == 1 and any(marker in str(exc) for marker in transient_markers):
                print(f"       transient error, retrying in 15s: {exc}")
                time.sleep(15)
                continue
            raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the benchmark eval suite")
    parser.add_argument("--target", choices=["local", "engine"], required=True)
    parser.add_argument("--engine-id", help="Agent Engine resource name (projects/.../reasoningEngines/...)")
    parser.add_argument("--assets-dir", required=True, help="Directory containing the benchmark asset files")
    parser.add_argument("--manifest", default=os.path.join(os.path.dirname(__file__), "manifest.yaml"))
    parser.add_argument("--out-dir", default="eval_results")
    parser.add_argument("--only", default=None, help="Comma-separated asset ids to run")
    args = parser.parse_args()

    config = load_config()
    with open(args.manifest, encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh)
    defaults = manifest.get("defaults", {})

    engine = None
    if args.target == "engine":
        if not args.engine_id:
            parser.error("--engine-id is required with --target engine")
        import vertexai
        from vertexai import agent_engines

        vertexai.init(
            project=config.require_project(),
            location=config.location,
            staging_bucket=config.require_staging_bucket(),
        )
        engine = agent_engines.get(args.engine_id)

    only = set(args.only.split(",")) if args.only else None
    results: list[ProfileResult] = []
    uri_cache: dict[str, str] = {}

    for asset in manifest["assets"]:
        if only and asset["id"] not in only:
            continue
        local_path = os.path.join(args.assets_dir, asset["file"])
        if not os.path.exists(local_path):
            print(f"[skip] {asset['id']}: file not found at {local_path}")
            for profile_name, profile in asset["profiles"].items():
                results.append(score_profile(asset, profile_name, profile, None, "asset file missing"))
            continue

        for profile_name, profile in asset["profiles"].items():
            constraints = {
                "show_context": defaults.get("show_context", "Benchmark audit"),
                "target_rating": defaults.get("target_rating", "TV-PG"),
                "exclusivity_deals": profile["exclusivity_deals"],
            }
            print(f"[run ] {asset['id']} / {profile_name}")
            started = time.time()
            report, error = None, None
            try:
                if local_path not in uri_cache:
                    uri_cache[local_path] = _resolve_asset_uri(
                        local_path, asset["modality"], config, upload_all=(args.target == "engine")
                    )
                asset_uri = uri_cache[local_path]
                if args.target == "local":
                    report = _run_local(asset_uri, asset["modality"], constraints)
                else:
                    report = _run_engine(engine, asset_uri, asset["modality"], constraints)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                print(f"       ERROR: {error}")
            else:
                print(f"       verdict={report['verdict']} findings={len(report['findings'])} "
                      f"({round(time.time() - started, 1)}s)")
            results.append(score_profile(asset, profile_name, profile, report, error))

    summary = summarize(results)
    os.makedirs(args.out_dir, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    json_path = os.path.join(args.out_dir, f"eval-{stamp}.json")
    md_path = os.path.join(args.out_dir, f"eval-{stamp}.md")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump({"summary": summary, "results": [r.__dict__ for r in results]}, fh, indent=2, default=str)
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(render_markdown(results, summary, args.engine_id or "local pipeline"))

    print("\n=== SUMMARY ===")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    print(f"\nReports: {json_path}\n         {md_path}")
    return 1 if (summary["runs_errored"] or summary["runs_pipeline_failed"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
