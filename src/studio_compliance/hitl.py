"""Human-in-the-Loop review store.

CRITICAL and HIGH findings create persisted PENDING records. A report that
generated pending records stays BLOCKED (or CONDITIONAL) until a named
reviewer resolves each record via the CLI:

    python -m studio_compliance.hitl list
    python -m studio_compliance.hitl show   HITL-XXXX
    python -m studio_compliance.hitl approve HITL-XXXX --reviewer "J. Doe" --note "waiver on file"
    python -m studio_compliance.hitl enforce HITL-XXXX --reviewer "J. Doe" --note "paint-out mandatory"

Records live either in a local directory or a gs://bucket/prefix so multiple
reviewers / serverless replicas share the same queue.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from .observability import log_event
from .schemas import Finding, HITLRecord, HITLStatus
from .storage import is_gcs_uri, split_gcs_uri


class HITLStore:
    """File-per-record store over a local directory or GCS prefix."""

    def __init__(self, root: str):
        self.root = root.rstrip("/")

    # -- backend helpers -----------------------------------------------------
    def _gcs(self):
        # Shared cached client: constructing storage.Client() per call costs
        # ~50s behind enterprise certificate proxies (observed live).
        from .storage import _client

        return _client()

    def _write(self, name: str, payload: str) -> None:
        if is_gcs_uri(self.root):
            bucket, prefix = split_gcs_uri(self.root + "/")
            self._gcs().bucket(bucket).blob(f"{prefix}{name}").upload_from_string(
                payload, content_type="application/json"
            )
        else:
            os.makedirs(self.root, exist_ok=True)
            with open(os.path.join(self.root, name), "w", encoding="utf-8") as fh:
                fh.write(payload)

    def _read(self, name: str) -> str | None:
        if is_gcs_uri(self.root):
            bucket, prefix = split_gcs_uri(self.root + "/")
            blob = self._gcs().bucket(bucket).blob(f"{prefix}{name}")
            return blob.download_as_text() if blob.exists() else None
        path = os.path.join(self.root, name)
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as fh:
            return fh.read()

    def _list_names(self) -> list[str]:
        if is_gcs_uri(self.root):
            bucket, prefix = split_gcs_uri(self.root + "/")
            return [
                b.name[len(prefix):]
                for b in self._gcs().bucket(bucket).list_blobs(prefix=prefix)
                if b.name.endswith(".json")
            ]
        if not os.path.isdir(self.root):
            return []
        return [n for n in os.listdir(self.root) if n.endswith(".json")]

    # -- public API ----------------------------------------------------------
    def create(self, run_id: str, asset_uri: str, finding: Finding) -> HITLRecord:
        record = HITLRecord(run_id=run_id, asset_uri=asset_uri, finding=finding)
        finding.hitl_token = record.token
        finding.requires_human_review = True
        self._write(f"{record.token}.json", record.model_dump_json(indent=2))
        log_event("HITL_PENDING_CREATED", token=record.token, run_id=run_id, entity=finding.entity)
        return record

    def get(self, token: str) -> HITLRecord | None:
        raw = self._read(f"{token}.json")
        return HITLRecord.model_validate_json(raw) if raw else None

    def list(self, status: HITLStatus | None = None) -> list[HITLRecord]:
        records = []
        for name in self._list_names():
            raw = self._read(name)
            if raw:
                record = HITLRecord.model_validate_json(raw)
                if status is None or record.status == status:
                    records.append(record)
        return sorted(records, key=lambda r: r.created_at)

    def resolve(self, token: str, decision: HITLStatus, reviewer: str, note: str | None = None) -> HITLRecord:
        record = self.get(token)
        if record is None:
            raise KeyError(f"No HITL record {token}")
        if record.status != HITLStatus.PENDING:
            raise ValueError(f"{token} already resolved as {record.status.value}")
        if decision not in (HITLStatus.APPROVED, HITLStatus.ENFORCED):
            raise ValueError("Decision must be APPROVED or ENFORCED")
        record.status = decision
        record.reviewer = reviewer
        record.note = note
        record.resolved_at = datetime.now(timezone.utc).isoformat()
        self._write(f"{record.token}.json", record.model_dump_json(indent=2))
        log_event("HITL_RESOLVED", token=token, decision=decision.value, reviewer=reviewer)
        return record

    def resolutions_for_run(self, run_id: str) -> dict[str, HITLStatus]:
        return {r.token: r.status for r in self.list() if r.run_id == run_id}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    from .config import load_config

    parser = argparse.ArgumentParser(prog="studio_compliance.hitl", description="HITL review queue")
    parser.add_argument("--store", default=None, help="Override STUDIO_HITL_STORE")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list").add_argument("--all", action="store_true", help="include resolved records")
    sub.add_parser("show").add_argument("token")
    for cmd in ("approve", "enforce"):
        p = sub.add_parser(cmd)
        p.add_argument("token")
        p.add_argument("--reviewer", required=True)
        p.add_argument("--note", default=None)

    args = parser.parse_args(argv)
    store = HITLStore(args.store or load_config().hitl_store)

    if args.cmd == "list":
        records = store.list(None if args.all else HITLStatus.PENDING)
        if not records:
            print("No records.")
        for r in records:
            print(f"{r.token}  {r.status.value:9s}  {r.finding.severity.value:8s} "
                  f"{r.finding.entity:30s}  {r.asset_uri}")
        return 0
    if args.cmd == "show":
        record = store.get(args.token)
        if record is None:
            print(f"Not found: {args.token}", file=sys.stderr)
            return 1
        print(json.dumps(json.loads(record.model_dump_json()), indent=2))
        return 0
    decision = HITLStatus.APPROVED if args.cmd == "approve" else HITLStatus.ENFORCED
    record = store.resolve(args.token, decision, reviewer=args.reviewer, note=args.note)
    print(f"{record.token} -> {record.status.value} by {record.reviewer}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
