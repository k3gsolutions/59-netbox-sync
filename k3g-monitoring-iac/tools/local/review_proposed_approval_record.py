#!/usr/bin/env python3
"""FASE 2.40.1 — Manual Approval Review Hardening.

Review proposed ApprovalRecords with hardened validations.

Hardened requirements:
- All required safety_flags must be true
- Secret scanning on payload
- Evidence integrity validated
- state_history tracks manual_approval_reviewed + approved_for_dry_run_applyplan
- Metadata (object_type, object_key) required

No NetBox writes. No tokens. No apply.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple

REQUIRED_SAFETY_FLAGS = {
    "no_netbox_write",
    "no_apply_plan_created",
    "manual_review_required",
    "human_decision_required",
    "proposed_only",
}

SECRET_KEYWORDS = [
    "token", "password", "secret", "api_key",
    "private key", "bearer", "authorization"
]


def load_record(record_file: Path) -> Dict[str, Any]:
    """Load approval record."""
    with open(record_file, encoding="utf-8") as f:
        return json.load(f)


def validate_record(record: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate record structure and safety (hardened)."""
    # Status must be proposed/pending
    status = record.get("status", "").lower()
    if status not in ("proposed", "pending"):
        return False, f"Status {status}: must be proposed/pending"

    # Required fields
    if not record.get("reviewer"):
        return False, "Missing reviewer"
    if not record.get("object_type"):
        return False, "Missing object_type"
    if not record.get("object_key"):
        return False, "Missing object_key"
    if not record.get("evidence_hash"):
        return False, "Missing evidence_hash"

    # Safety flags (hardened: ALL required)
    flags = record.get("safety", {}) or record.get("safety_flags", {})
    missing = REQUIRED_SAFETY_FLAGS - set(flags.keys())
    if missing:
        return False, f"Missing safety flags: {', '.join(sorted(missing))}"

    # Each flag must be true
    for flag in REQUIRED_SAFETY_FLAGS:
        if not flags.get(flag):
            return False, f"Flag {flag} not true"

    # Secret scanning
    payload = record.get("proposed_payload", {})
    payload_str = json.dumps(payload).lower()
    for secret_kw in SECRET_KEYWORDS:
        if secret_kw in payload_str:
            return False, f"Secret keyword in payload: {secret_kw}"

    return True, ""


def approve_record(
    record: Dict[str, Any],
    reviewer: str,
    reason: str,
) -> Dict[str, Any]:
    """Approve record. Add manual_approval_reviewed + approved_for_dry_run_applyplan."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"
    approved = record.copy()

    approved["status"] = "approved"
    approved["state"] = "approved"
    approved["approved_by"] = reviewer
    approved["approved_at"] = timestamp
    approved["approval_reason"] = reason

    # Add state transitions
    state_history = approved.get("state_history", [])
    if not isinstance(state_history, list):
        state_history = []

    state_history.append({
        "from": "proposed",
        "to": "manual_approval_reviewed",
        "by": reviewer,
        "at": timestamp,
        "reason": reason,
    })

    state_history.append({
        "from": "manual_approval_reviewed",
        "to": "approved_for_dry_run_applyplan",
        "by": reviewer,
        "at": timestamp,
        "reason": reason,
    })

    approved["state_history"] = state_history
    return approved


def reject_record(
    record: Dict[str, Any],
    reviewer: str,
    reason: str,
) -> Dict[str, Any]:
    """Reject record."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"
    rejected = record.copy()

    rejected["status"] = "rejected"
    rejected["state"] = "rejected"
    rejected["rejected_by"] = reviewer
    rejected["rejected_at"] = timestamp
    rejected["rejection_reason"] = reason

    state_history = rejected.get("state_history", [])
    if not isinstance(state_history, list):
        state_history = []

    state_history.append({
        "from": "proposed",
        "to": "rejected_by_manual_review",
        "by": reviewer,
        "at": timestamp,
        "reason": reason,
    })

    rejected["state_history"] = state_history
    return rejected


def request_changes(
    record: Dict[str, Any],
    reviewer: str,
    reason: str,
) -> Dict[str, Any]:
    """Request changes."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"
    modified = record.copy()

    modified["status"] = "request_changes"
    modified["state"] = "changes_requested"
    modified["reviewed_by"] = reviewer
    modified["reviewed_at"] = timestamp
    modified["review_reason"] = reason

    state_history = modified.get("state_history", [])
    if not isinstance(state_history, list):
        state_history = []

    state_history.append({
        "from": "proposed",
        "to": "changes_requested_by_manual_review",
        "by": reviewer,
        "at": timestamp,
        "reason": reason,
    })

    modified["state_history"] = state_history
    return modified


def defer_record(
    record: Dict[str, Any],
    reviewer: str,
    reason: str,
) -> Dict[str, Any]:
    """Defer record."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"
    deferred = record.copy()

    deferred["status"] = "deferred"
    deferred["state"] = "deferred"
    deferred["deferred_by"] = reviewer
    deferred["deferred_at"] = timestamp
    deferred["deferral_reason"] = reason

    state_history = deferred.get("state_history", [])
    if not isinstance(state_history, list):
        state_history = []

    state_history.append({
        "from": "proposed",
        "to": "deferred_by_manual_review",
        "by": reviewer,
        "at": timestamp,
        "reason": reason,
    })

    deferred["state_history"] = state_history
    return deferred


def block_record(
    record: Dict[str, Any],
    reviewer: str,
    reason: str,
) -> Dict[str, Any]:
    """Block record."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"
    blocked = record.copy()

    blocked["status"] = "blocked"
    blocked["state"] = "blocked"
    blocked["blocked_by"] = reviewer
    blocked["blocked_at"] = timestamp
    blocked["block_reason"] = reason

    state_history = blocked.get("state_history", [])
    if not isinstance(state_history, list):
        state_history = []

    state_history.append({
        "from": "proposed",
        "to": "blocked_by_manual_review",
        "by": reviewer,
        "at": timestamp,
        "reason": reason,
    })

    blocked["state_history"] = state_history
    return blocked


def save_record(record: Dict[str, Any], output_dir: Path, decision: str) -> Path:
    """Save reviewed record."""
    output_dir.mkdir(parents=True, exist_ok=True)
    approval_id = record.get("approval_record_id", record.get("approval_id", "unknown"))
    output_file = output_dir / f"approval-record-{approval_id}-{decision}.json"
    output_file.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return output_file


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="FASE 2.40.1 — Manual Approval Review")
    parser.add_argument("--approval-record", type=Path, required=True, help="Record JSON file")
    parser.add_argument(
        "--decision",
        required=True,
        choices=["approve", "reject", "request_changes", "defer", "block"],
    )
    parser.add_argument("--reviewer", required=True, help="Reviewer name")
    parser.add_argument("--reason", required=True, help="Decision reason")
    parser.add_argument("--output-dir", type=Path, required=True, help="Output directory")

    args = parser.parse_args()

    if not args.approval_record.exists():
        print(f"✗ Record not found: {args.approval_record}")
        return 1

    record = load_record(args.approval_record)

    valid, msg = validate_record(record)
    if not valid:
        print(f"✗ Invalid: {msg}")
        return 1

    # Process decision
    if args.decision == "approve":
        result = approve_record(record, args.reviewer, args.reason)
    elif args.decision == "reject":
        result = reject_record(record, args.reviewer, args.reason)
    elif args.decision == "request_changes":
        result = request_changes(record, args.reviewer, args.reason)
    elif args.decision == "defer":
        result = defer_record(record, args.reviewer, args.reason)
    else:
        result = block_record(record, args.reviewer, args.reason)

    output_file = save_record(result, args.output_dir, args.decision)
    print(f"✓ {args.decision}: {output_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
