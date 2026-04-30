#!/usr/bin/env python3
"""FASE 4.7 — Controlled Operation Cycle Week 2 Preparation.

Prepare Week 2 review based on Week 1 validation results.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def load_json_safe(file_path: Path) -> Dict[str, Any]:
    """Load JSON file safely."""
    if not file_path.exists():
        return {}

    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def evaluate_preparation(validation_data: Dict[str, Any]) -> str:
    """Evaluate Week 2 preparation readiness."""
    summary = validation_data.get("summary", {})

    if summary.get("blocked", 0) > 0:
        return "WEEK2_PREPARATION_BLOCKED"

    if summary.get("valid", 0) > 0:
        if summary.get("valid", 0) == summary.get("total_responses", 0):
            return "WEEK2_PREPARATION_READY"
        else:
            return "WEEK2_PREPARATION_READY_WITH_RESTRICTIONS"

    return "WEEK2_PREPARATION_BLOCKED"


def generate_week2_plan(cycle_id: str, device: str) -> str:
    """Generate Week 2 plan markdown."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    plan = f"""# {cycle_id} — Week 2 Review Plan

## 1. Objective

Review and approve validated responses from Week 1.

## 2. Timeline

**Start:** {timestamp}
**Target:** 5 business days
**Gate:** All responses approved or escalated

## 3. Process

1. Reviewers access Web UI or download decisions.csv
2. Review each validated response
3. Make decision: approve / request_changes / reject
4. Document evidence (reference, approval_id)
5. Submit decision

## 4. Decisions Available

- **Approve:** Response is ready for ApprovalRecord
- **Request Changes:** More information needed before approval
- **Reject:** Response does not meet criteria

## 5. Review Board

Reviewers assigned per response type:
- Interface: Network Ops lead
- IP Address: Network Ops + Service team
- BGP: BGP team lead
- VRF: Network Ops

## 6. Output

- week2-review-decisions.csv with all approvals/rejections
- ApprovalRecords generated after reviews complete

---

**Cycle ID:** {cycle_id}
**Device:** {device}
**Created:** {timestamp}
"""
    return plan


def generate_review_board(valid_count: int) -> str:
    """Generate review board markdown."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    board = f"""# Week 2 Review Board

## Status

- Items to review: {valid_count}
- Reviewers: 3+
- Timeline: 5 business days
- Gate: All decisions recorded

## Assignments

### Network Ops Review
- Interface configurations
- VRF assignments
- IP address allocation
- Equipment access

### Service Team Review
- Tenant mapping
- Service type alignment
- Business owner validation
- Documentation completeness

### BGP Team Review
- Peer ASN correctness
- Policy intent
- Criticality validation
- Regional alignment

## Review Process

1. Open decisions.csv
2. Filter by assigned_reviewer = your name
3. Open response_file link
4. Review data against policies
5. Enter decision (approve/request_changes/reject)
6. Save row locally (will sync on next validation)
7. Re-run validation to lock

## Gate Conditions

- ✓ All reviews completed
- ✓ No blocking issues
- ✓ All decisions documented
- ✓ Evidence references added
- ✓ Ready for ApprovalRecord creation

---

**Generated:** {timestamp}
"""
    return board


def generate_decisions_csv(cycle_id: str, valid_count: int) -> str:
    """Generate decisions CSV template."""
    csv_header = "item_id,object_type,team,decision,reviewed_by,evidence_reference,notes,approval_record_allowed"
    csv_lines = [csv_header]

    for i in range(valid_count):
        csv_lines.append(f"item-{i+1},unknown,unknown,pending,,,,false")

    return "\n".join(csv_lines)


def generate_approval_draft(cycle_id: str, item_index: int) -> Dict[str, Any]:
    """Generate approval draft (local only, not official ApprovalRecord)."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    return {
        "cycle_id": cycle_id,
        "approval_id": f"draft-{cycle_id}-{item_index:03d}",
        "status": "draft",
        "created_at": timestamp,
        "object_type": "unknown",
        "object_id": f"item-{item_index+1}",
        "evidence": {
            "device_compliance_check": False,
            "naming_convention_check": False,
            "policy_compliance_check": False,
        },
        "safety_confirmations": {
            "no_token_exposure": True,
            "no_secrets_in_draft": True,
            "manual_review_required": True,
        },
        "notes": "Draft created during Week 2 preparation. Not official ApprovalRecord.",
    }


def main() -> int:
    """Run FASE 4.7."""
    parser = argparse.ArgumentParser(description="FASE 4.7 — Controlled Operation Cycle Week 2 Prepare")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--cycle-dir", type=Path, required=True)
    parser.add_argument("--week1-validation", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)

    args = parser.parse_args()

    # Load Week 1 validation
    validation_data = load_json_safe(args.week1_validation)
    summary = validation_data.get("summary", {})
    valid_count = summary.get("valid", 0)

    # Create week2 directory structure
    week2_dir = args.output_dir
    week2_dir.mkdir(parents=True, exist_ok=True)
    (week2_dir / "approval-drafts").mkdir(exist_ok=True)

    timestamp = datetime.utcnow().isoformat() + "+00:00"

    # Generate Week 2 Plan
    plan = generate_week2_plan(args.cycle_id, args.device)
    plan_file = week2_dir / f"{args.cycle_id.upper()}-WEEK2-PLAN.md"
    plan_file.write_text(plan, encoding="utf-8")

    # Generate Review Board
    board = generate_review_board(valid_count)
    board_file = week2_dir / f"{args.cycle_id.upper()}-WEEK2-REVIEW-BOARD.md"
    board_file.write_text(board, encoding="utf-8")

    # Generate Decisions CSV
    decisions_csv = generate_decisions_csv(args.cycle_id, valid_count)
    decisions_file = week2_dir / f"{args.cycle_id.upper()}-WEEK2-DECISIONS.csv"
    decisions_file.write_text(decisions_csv, encoding="utf-8")

    # Generate Status
    status = {
        "cycle_id": args.cycle_id,
        "device": args.device,
        "device_id": args.device_id,
        "week": 2,
        "status": evaluate_preparation(validation_data),
        "created_at": timestamp,
        "decisions": {
            "total_to_review": valid_count,
            "approved": 0,
            "rejected": 0,
            "request_changes": 0,
        },
        "events": [
            {
                "timestamp": timestamp,
                "event": "WEEK2_PREPARED",
                "status": evaluate_preparation(validation_data),
            }
        ],
    }
    status_file = week2_dir / f"{args.cycle_id.upper()}-WEEK2-STATUS.json"
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2)

    # Generate approval drafts (local only, not official)
    for i in range(valid_count):
        draft = generate_approval_draft(args.cycle_id, i)
        draft_file = week2_dir / "approval-drafts" / f"draft-{i+1:03d}.json"
        with open(draft_file, "w", encoding="utf-8") as f:
            json.dump(draft, f, indent=2)

    print(f"✓ Week 2 prepared for {args.cycle_id}")
    print(f"✓ Status: {status['status']}")
    print(f"✓ Items to review: {valid_count}")
    print(f"✓ Plan: {plan_file}")
    print(f"✓ Review Board: {board_file}")
    print(f"✓ Decisions: {decisions_file}")
    print(f"✓ Status: {status_file}")
    print(f"✓ Approval drafts: {valid_count} files in approval-drafts/")

    return 0 if "READY" in status["status"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
