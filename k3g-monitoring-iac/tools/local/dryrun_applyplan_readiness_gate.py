#!/usr/bin/env python3
"""FASE 2.41.1 — Dry-Run ApplyPlan Gate Hardening."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


def check_approved_record(record: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate approved ApprovalRecord for dry-run ApplyPlan."""
    status = record.get("status", "").lower()
    if status != "approved":
        return False, f"Status {status} (need approved)"

    if not record.get("approved_by"):
        return False, "No approved_by"
    if not record.get("approved_at"):
        return False, "No approved_at"
    if not record.get("approval_reason"):
        return False, "No approval_reason"

    if not record.get("evidence_hash"):
        return False, "No evidence_hash"
    if not record.get("proposed_payload"):
        return False, "No proposed_payload"

    if not record.get("object_type"):
        return False, "No object_type"
    if not record.get("object_key"):
        return False, "No object_key"

    flags = record.get("safety", {}) or record.get("safety_flags", {})
    required_flags = {"no_netbox_write", "no_apply_plan_created", "manual_review_required", "human_decision_required", "proposed_only"}
    missing = required_flags - set(flags.keys())
    if missing:
        return False, f"Missing flags: {', '.join(sorted(missing))}"

    for flag in required_flags:
        if not flags.get(flag):
            return False, f"Flag {flag} not true"

    payload_str = json.dumps(record.get("proposed_payload", {})).lower()
    secrets = ["token", "password", "secret", "api_key", "private key", "bearer", "authorization"]
    if any(s in payload_str for s in secrets):
        return False, "Secrets in payload"

    state_history = record.get("state_history", [])
    if not isinstance(state_history, list):
        return False, "Invalid state_history"

    states = [s.get("to", "").lower() for s in state_history if isinstance(s, dict)]
    if "manual_approval_reviewed" not in states:
        return False, "Missing manual_approval_reviewed"
    if "approved_for_dry_run_applyplan" not in states:
        return False, "Missing approved_for_dry_run_applyplan (BLOCKER)"

    return True, "Valid"


def validate_policy_baseline(baseline_file: Path) -> Tuple[str, str]:
    """Validate policy baseline decision."""
    if not baseline_file.exists():
        return "BASELINE_BLOCKED", f"Missing: {baseline_file}"

    try:
        content = baseline_file.read_text(encoding="utf-8")
    except Exception as e:
        return "BASELINE_BLOCKED", f"Cannot read: {e}"

    if "POLICY_BASELINE_OK" in content:
        return "BASELINE_OK", "Validation passed"
    elif "POLICY_BASELINE_WITH_WARNINGS" in content:
        return "BASELINE_WITH_WARNINGS", "Has warnings"
    elif "POLICY_BASELINE_BLOCKED" in content:
        return "BASELINE_BLOCKED", "Validation failed"
    else:
        return "BASELINE_UNKNOWN", "No decision found"


def main() -> int:
    """Run dry-run ApplyPlan readiness gate."""
    parser = argparse.ArgumentParser(description="FASE 2.41.1 — Dry-Run ApplyPlan Readiness Gate")
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True, type=int)
    parser.add_argument("--approved-dir", type=Path, required=True)
    parser.add_argument("--policy-baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()

    eligible = []
    not_eligible = []

    if args.approved_dir.exists():
        for record_file in args.approved_dir.glob("approval-record-*.json"):
            try:
                with open(record_file, encoding="utf-8") as f:
                    record = json.load(f)
            except Exception:
                continue

            valid, reason = check_approved_record(record)
            if valid:
                eligible.append({
                    "file": record_file.name,
                    "approval_id": record.get("approval_record_id", "?"),
                    "object_type": record.get("object_type", "?"),
                    "object_key": record.get("object_key", "?"),
                    "approved_by": record.get("approved_by", "?"),
                })
            else:
                not_eligible.append({"file": record_file.name, "reason": reason})

    baseline_status, baseline_reason = validate_policy_baseline(args.policy_baseline)

    timestamp = datetime.utcnow().isoformat() + "+00:00"

    if len(eligible) == 0:
        decision = "NOT_READY_FOR_DRYRUN_APPLYPLAN"
        reason = "No eligible approved records"
    elif baseline_status == "BASELINE_BLOCKED":
        decision = "NOT_READY_FOR_DRYRUN_APPLYPLAN"
        reason = f"Baseline blocked: {baseline_reason}"
    elif baseline_status == "BASELINE_WITH_WARNINGS":
        decision = "READY_WITH_RESTRICTIONS"
        reason = f"Ready with restrictions: {baseline_reason}"
    else:
        decision = "READY_FOR_DRYRUN_APPLYPLAN"
        reason = f"{len(eligible)} approved records validated"

    lines = [
        "# Dry-Run ApplyPlan Readiness Gate",
        "",
        f"**Device:** {args.device} (ID: {args.device_id})",
        f"**Generated:** {timestamp}",
        "",
        "## Decision",
        "",
        f"### {decision}",
        reason,
        "",
        "## Summary",
        "",
        f"- Total approved: {len(eligible) + len(not_eligible)}",
        f"- Eligible: {len(eligible)}",
        f"- Not eligible: {len(not_eligible)}",
        f"- Baseline: {baseline_status}",
        "",
    ]

    if eligible:
        lines.extend([
            "## Eligible Records",
            "",
            "| Approval ID | Object Type | Object Key | Approved By |",
            "|---|---|---|---|",
        ])
        for item in eligible:
            lines.append(f"| {item['approval_id']} | {item['object_type']} | {item['object_key']} | {item['approved_by']} |")
        lines.append("")

    if not_eligible:
        lines.extend([
            "## Not Eligible",
            "",
            "| File | Reason |",
            "|---|---|",
        ])
        for item in not_eligible:
            lines.append(f"| {item['file']} | {item['reason']} |")
        lines.append("")

    lines.extend([
        "## Security",
        "",
        "✓ No NetBox writes",
        "✓ No ApplyPlan created",
        "✓ All local validation",
        "",
    ])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"✓ Report: {args.output}")
    print(f"✓ Decision: {decision}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
