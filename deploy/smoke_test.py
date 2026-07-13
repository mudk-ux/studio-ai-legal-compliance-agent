"""Post-deploy smoke test: verifies the engine is live, calls real tools, and
returns a structured report with provenance — before you spend money on the
full eval suite.

    python deploy/smoke_test.py --engine-id projects/.../reasoningEngines/...
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile

from _common import init_vertex

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "evals"))
from engine_client import collect_response_text, extract_report  # noqa: E402
from studio_compliance.config import load_config  # noqa: E402
from studio_compliance.storage import read_text, upload_file  # noqa: E402

SMOKE_SCRIPT = """SMOKE TEST SCRIPT

INT. OFFICE - DAY
A producer sips a Starbucks latte beside a Sony monitor.
MARK ZUCKERBERG (from archive footage) appears on screen.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine-id", required=True)
    args = parser.parse_args()

    config = load_config()
    init_vertex(config)

    from vertexai import agent_engines

    engine = agent_engines.get(args.engine_id)

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
        fh.write(SMOKE_SCRIPT)
        local = fh.name
    asset_uri = upload_file(local, f"{config.require_staging_bucket().rstrip('/')}/smoke/")
    print(f"Uploaded smoke asset: {asset_uri}")

    constraints = {
        "show_context": "Smoke test",
        "target_rating": "TV-PG",
        "exclusivity_deals": {"primary_sponsor": "Starbucks", "restricted_competitors": ["Sony"]},
    }
    prompt = (
        "Run a compliance audit now.\n"
        f"Asset URI: {asset_uri}\nModality: TEXT_SCREENPLAY\n"
        f"Constraints JSON: {json.dumps(constraints)}\n"
        "Call run_compliance_audit and reproduce its JSON result verbatim in a "
        "fenced json code block."
    )

    print("Querying engine...")
    text = collect_response_text(engine, user_id="smoke-test", prompt=prompt)

    report = None
    parse_error = None
    try:
        report = extract_report(text, download=read_text)
    except Exception as exc:
        parse_error = str(exc)

    findings = (report or {}).get("findings", [])
    checks = {
        "response non-empty": bool(text.strip()),
        "report retrievable (compact block + report_uri, or inline)": report is not None,
        "verdict present": bool((report or {}).get("verdict")),
        "verdict is not FAILED": (report or {}).get("verdict") not in (None, "FAILED"),
        "provenance on findings": bool(findings) and all("source_api" in f for f in findings),
        "restricted competitor flagged (Sony breach)": any(
            f.get("category") == "SPONSOR_EXCLUSIVITY_BREACH" and "sony" in f.get("entity", "").lower()
            for f in findings
        ),
    }
    print("\n=== SMOKE CHECKS ===")
    passed = True
    for name, ok in checks.items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        passed = passed and ok
    if not passed:
        if parse_error:
            print(f"\nparse error: {parse_error}")
        if report and report.get("failures"):
            print(f"stage failures: {report['failures']}")
        print("\n--- first 2000 chars of response ---")
        print(text[:2000])
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
