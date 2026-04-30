#!/usr/bin/env python3
"""FASE 4.48 - Cycle-002 Manual Approval Decision.

Manual, local decision for one proposed ApprovalRecord.
No NetBox write. No token. No ApplyPlan.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ALLOWED_DECISIONS = {"approve", "reject", "request_changes", "defer", "block"}
DECISION_DIRS = {
    "approve": "approved",
    "reject": "rejected",
    "request_changes": "changes-requested",
    "defer": "deferred",
    "block": "blocked",
}


def safe_text(value: Any) -> str:
    return str(value or "").strip()


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def has_secret(text: str) -> bool:
    lowered = safe_text(text).lower()
    blocked = ["netbox_write_token", "authorization: token", "token=", "password=", "secret=", "api_key", "private key", "bearer"]
    return any(term in lowered for term in blocked)


def validate_record(record: Dict[str, Any]) -> List[str]:
    issues: List[str] = []
    if safe_text(record.get("cycle_id")) != "cycle-002":
        issues.append("cycle_id must be cycle-002")
    if safe_text(record.get("status")) not in {"proposed", "pending"}:
        issues.append("status must be proposed or pending")
    if safe_text(record.get("state")) not in {"proposed", "pending"}:
        issues.append("state must be proposed or pending")
    if not safe_text(record.get("approval_id")):
        issues.append("approval_id required")
    if not safe_text(record.get("object_type")):
        issues.append("object_type required")
    if not safe_text(record.get("object_key")):
        issues.append("object_key required")
    if not record.get("proposed_payload"):
        issues.append("proposed_payload required")
    if not safe_text(record.get("evidence_hash")):
        issues.append("evidence_hash required")
    safety = record.get("safety_confirmations") or {}
    for flag in ["no_netbox_write", "no_apply_plan_created", "manual_review_required", "human_decision_required", "proposed_only"]:
        if not safety.get(flag):
            issues.append(f"safety flag missing: {flag}")
    text = json.dumps(record, sort_keys=True).lower()
    for term in ["netbox_write_token", "authorization: token", "token=", "password=", "secret=", "api_key", "private key", "bearer"]:
        if term in text:
            issues.append(f"blocked keyword: {term}")
    return issues


def mutate_record(record: Dict[str, Any], decision: str, reviewer: str, reason: str) -> Dict[str, Any]:
    timestamp = datetime.now(timezone.utc).isoformat()
    updated = json.loads(json.dumps(record))
    updated["status"] = "approved" if decision == "approve" else decision.replace("_", "-")
    updated["state"] = "approved" if decision == "approve" else decision.replace("_", "-")
    if decision == "reject":
        updated["status"] = "rejected"
        updated["state"] = "rejected"
    elif decision == "request_changes":
        updated["status"] = "changes-requested"
        updated["state"] = "changes-requested"
    elif decision == "defer":
        updated["status"] = "deferred"
        updated["state"] = "deferred"
    elif decision == "block":
        updated["status"] = "blocked"
        updated["state"] = "blocked"
    updated["manual_review_decision"] = decision
    updated["manual_review_reason"] = reason
    updated["manual_reviewed_by"] = reviewer
    updated["manual_reviewed_at"] = timestamp
    history = list(updated.get("state_history") or [])
    history.append({
        "status": updated["status"],
        "timestamp": timestamp,
        "event": "cycle_manual_approval_reviewed",
        "by": reviewer,
        "decision": decision,
        "reason": reason,
    })
    if decision == "approve":
        history.append({
            "status": "approved",
            "timestamp": timestamp,
            "event": "approved_for_cycle_dryrun_applyplan",
            "by": reviewer,
        })
        updated["approved_by"] = reviewer
        updated["approved_at"] = timestamp
        updated["approval_reason"] = reason
    elif decision == "reject":
        history.append({"status": "rejected", "timestamp": timestamp, "event": "rejected_by_manual_review", "by": reviewer, "reason": reason})
    elif decision == "request_changes":
        history.append({"status": "changes-requested", "timestamp": timestamp, "event": "changes_requested_by_manual_review", "by": reviewer, "reason": reason})
    elif decision == "defer":
        history.append({"status": "deferred", "timestamp": timestamp, "event": "deferred_by_manual_review", "by": reviewer, "reason": reason})
    elif decision == "block":
        history.append({"status": "blocked", "timestamp": timestamp, "event": "blocked_by_manual_review", "by": reviewer, "reason": reason})
    updated["state_history"] = history
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="FASE 4.48 - Cycle-002 Manual Approval Decision")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--approval-record", type=Path, required=True)
    parser.add_argument("--decision", required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    if args.cycle_id != "cycle-002":
        print("✗ cycle_id must be cycle-002")
        return 1
    if args.decision not in ALLOWED_DECISIONS:
        print("✗ invalid decision")
        return 1
    if not args.reviewer:
        print("✗ reviewer required")
        return 1
    if not args.reason:
        print("✗ reason required")
        return 1
    if has_secret(args.reviewer) or has_secret(args.reason):
        print("✗ blocked keyword in reviewer/reason")
        return 1
    if not args.approval_record.exists():
        print("✗ approval record missing")
        return 1

    record = load_json(args.approval_record)
    issues = validate_record(record)
    if issues and args.decision == "approve":
        print("✗ approval record invalid")
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    target_dir = args.output_dir / DECISION_DIRS[args.decision]
    target_dir.mkdir(parents=True, exist_ok=True)

    updated = mutate_record(record, args.decision, args.reviewer, args.reason)
    target_file = target_dir / args.approval_record.name
    target_file.write_text(json.dumps(updated, indent=2), encoding="utf-8")

    timestamp = datetime.now(timezone.utc).isoformat()
    if args.decision == "approve":
        decision = "CYCLE_APPROVAL_REVIEW_APPROVED"
    elif args.decision in {"reject", "block"}:
        decision = "CYCLE_APPROVAL_REVIEW_BLOCKED"
    else:
        decision = "CYCLE_APPROVAL_REVIEW_WITH_RESTRICTIONS"

    report_lines = [
        f"# {args.cycle_id.upper()} Manual Approval Review",
        "",
        f"## Decision: {decision}",
        "",
        f"- record: {args.approval_record.name}",
        f"- human decision: {args.decision}",
        f"- reviewer: {args.reviewer}",
        f"- reason: {args.reason}",
        f"- output: {target_file.relative_to(args.output_dir)}",
        "",
        "## Safety",
        "- No NetBox write",
        "- No ApplyPlan",
        "- No automatic approval",
        "- Human decision required",
    ]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(report_lines), encoding="utf-8")

    payload = {
        "cycle_id": args.cycle_id,
        "decision": decision,
        "manual_decision": args.decision,
        "reviewer": args.reviewer,
        "reason": args.reason,
        "record_file": args.approval_record.name,
        "output_file": str(target_file.relative_to(args.output_dir)),
        "reviewed_at": timestamp,
        "issues": issues,
        "no_netbox_write": True,
        "no_apply_plan_created": True,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    cycle_status = args.approval_record.parents[2] / "CYCLE-002-STATUS.md"
    cycle_status.write_text(f"# CYCLE-002\n\nStatus: {decision}\n", encoding="utf-8")

    print(f"✓ Manual approval review decision: {decision}")
    print(f"✓ Output: {target_file}")
    print(f"✓ Report: {args.report}")
    print(f"✓ JSON: {args.output_json}")
    return 0 if decision in {"CYCLE_APPROVAL_REVIEW_APPROVED", "CYCLE_APPROVAL_REVIEW_WITH_RESTRICTIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
