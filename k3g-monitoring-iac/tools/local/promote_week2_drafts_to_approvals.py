#!/usr/bin/env python3
"""
Promote Week 2 Drafts to Official ApprovalRecords (FASE 2.14).

Reads week2-review-decisions.csv and promotes ONLY drafts with explicit approval.

Promotion Requirements (ALL must be satisfied):
- decision = "approve_for_approval_record"
- approval_record_allowed = true/True
- reviewer field filled
- reviewed_at field filled with valid datetime
- Draft file exists and is valid JSON

No NetBox writes. No tokens. Manual review only.

Drafts that don't meet criteria are NOT promoted and documented in report.

Usage:
    python3 promote_week2_drafts_to_approvals.py \\
        --device <device_name> \\
        --device-id <id> \\
        --decisions <path/to/week2-review-decisions.csv> \\
        --drafts-dir <path/to/week2-approval-drafts> \\
        --output-dir <path/to/week2-review>
"""

import argparse
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import uuid


def calculate_hash(content: str) -> str:
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Promote Week 2 drafts to official ApprovalRecords"
    )
    parser.add_argument("--device", required=True, help="Device name")
    parser.add_argument("--device-id", required=True, type=int, help="Device ID")
    parser.add_argument("--decisions", required=True, help="Decisions CSV file")
    parser.add_argument("--drafts-dir", required=True, help="Drafts directory")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--report", help="Optional promotion report path")
    return parser.parse_args()


def read_decisions(decisions_file: str) -> List[Dict]:
    """Read decisions from CSV."""
    decisions = []
    with open(decisions_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row and row.get("object_key") and row.get("decision"):
                decisions.append(row)
    return decisions


def validate_decision_row(row: Dict) -> Tuple[bool, str]:
    """
    Validate if a decision row qualifies for promotion.

    Returns: (is_valid, reason)
    """
    object_key = row.get("object_key", "").strip()
    decision = row.get("decision", "").strip().lower()
    approval_allowed = row.get("approval_record_allowed", "").strip().lower()
    reviewer = row.get("reviewer", "").strip()
    reviewed_at = row.get("reviewed_at", "").strip()
    reason = row.get("reason", "").strip()
    notes = row.get("notes", "").strip()

    # Check decision
    if decision != "approve_for_approval_record":
        return False, f"decision={decision}, expected 'approve_for_approval_record'"

    # Check approval_record_allowed
    if approval_allowed not in ("true", "1", "yes"):
        return False, f"approval_record_allowed={approval_allowed}, expected 'true'"

    # Check reviewer
    if not reviewer:
        return False, "reviewer field is empty"

    # Check reviewed_at
    if not reviewed_at:
        return False, "reviewed_at field is empty"

    # Try to parse reviewed_at
    try:
        datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return False, f"reviewed_at='{reviewed_at}', not valid ISO datetime"

    if not (reason or notes):
        return False, "reason or notes field is empty"

    return True, "All criteria met"


def load_draft(draft_file: Path) -> Tuple[bool, Dict]:
    """Load and validate draft JSON file."""
    try:
        with open(draft_file, "r", encoding="utf-8") as f:
            draft = json.load(f)

        # Validate draft structure
        required_keys = ["draft_id", "status", "device", "device_id", "object_key"]
        if not all(k in draft for k in required_keys):
            return False, {}

        if draft.get("status") != "draft_review":
            return False, {}

        return True, draft
    except (json.JSONDecodeError, IOError):
        return False, {}


def create_approval_record(draft: Dict, reviewer: str, reviewed_at: str) -> Dict:
    """
    Create official ApprovalRecord from draft.

    Transforms draft_review → proposed status.
    Creates unique approval_record_id.
    """
    approval_record_id = str(uuid.uuid4())

    record = {
        "approval_id": approval_record_id,
        "approval_record_id": approval_record_id,
        "status": "proposed",
        "device": draft["device"],
        "device_id": draft["device_id"],
        "object_type": draft["object_type"],
        "object_key": draft["object_key"],
        "action": draft["action"],
        "category": draft["category"],
        "source_draft": draft["draft_id"],
        "source_decision_csv": "",
        "evidence_hash": calculate_hash(json.dumps(draft, sort_keys=True)),
        "reviewer": reviewer,
        "reviewed_at": reviewed_at,
        "created_at": datetime.utcnow().isoformat() + "+00:00",
        "source_draft_id": draft["draft_id"],
        "promotion_timestamp": datetime.utcnow().isoformat() + "+00:00",
        "state_history": [
            {
                "from": "draft_review",
                "to": "draft_review_created",
                "by": "week2-review",
                "at": draft.get("created_at", datetime.utcnow().isoformat() + "+00:00"),
            },
            {
                "from": "draft_review",
                "to": "human_review_approved_for_approval_record",
                "by": reviewer,
                "at": reviewed_at,
            },
            {
                "from": "draft_review",
                "to": "promoted_to_proposed",
                "by": reviewer,
                "at": datetime.utcnow().isoformat() + "+00:00",
            },
        ],
        "review": {
            "status": "proposed",
            "reviewed_by": reviewer,
            "reviewed_at": reviewed_at,
            "decision": "approve_for_approval_record",
            "comment": "",
            "changes_requested": [],
        },
        "audit": {
            "created_at": datetime.utcnow().isoformat() + "+00:00",
            "updated_at": datetime.utcnow().isoformat() + "+00:00",
            "created_by": reviewer,
            "report_path": "",
            "report_timestamp": "",
            "evidence_hash": calculate_hash(json.dumps(draft, sort_keys=True)),
            "source_draft": draft["draft_id"],
            "source_decision_csv": "",
        },
        "safety": {
            "no_netbox_write": True,
            "no_apply_plan_created": True,
            "manual_review_required": True,
        },
        "notes": [
            "Promoted from draft_review status by week2-review decision process",
            "Status: proposed (awaiting approval/rejection)",
            "Reviewer: " + reviewer,
            "Reviewed at: " + reviewed_at,
        ],
    }

    return record


def main():
    args = parse_args()

    # Load decisions
    decisions = read_decisions(args.decisions)
    print(f"✓ Loaded {len(decisions)} decision rows")

    # Validate output directory
    output_dir = Path(args.output_dir)
    promoted_dir = output_dir / "promoted"
    promoted_dir.mkdir(parents=True, exist_ok=True)

    # Track results
    promoted = []
    not_promoted = []
    missing_drafts = []

    # Process each decision
    for row in decisions:
        object_key = row.get("object_key", "").strip()
        is_valid, reason = validate_decision_row(row)

        if not is_valid:
            not_promoted.append({
                "object_key": object_key,
                "reason": reason,
                "decision": row.get("decision", ""),
                "reviewer": row.get("reviewer", ""),
            })
            continue

        # Find draft file
        draft_filename = f"approval-draft-{object_key.replace('.', '-').replace('/', '-')}.json"
        drafts_dir = Path(args.drafts_dir)
        draft_file = drafts_dir / draft_filename

        if not draft_file.exists():
            missing_drafts.append({
                "object_key": object_key,
                "expected_file": draft_filename,
            })
            continue

        # Load draft
        is_valid_draft, draft = load_draft(draft_file)
        if not is_valid_draft:
            not_promoted.append({
                "object_key": object_key,
                "reason": f"Draft file invalid or corrupted: {draft_filename}",
                "decision": row.get("decision", ""),
                "reviewer": row.get("reviewer", ""),
            })
            continue

        # Create approval record
        reviewer = row.get("reviewer", "").strip()
        reviewed_at = row.get("reviewed_at", "").strip()

        approval_record = create_approval_record(draft, reviewer, reviewed_at)
        decision_csv = str(Path(args.decisions).resolve())
        approval_record["source_decision_csv"] = decision_csv
        approval_record["audit"]["report_path"] = str(draft_file)
        approval_record["audit"]["report_timestamp"] = reviewed_at
        approval_record["audit"]["source_decision_csv"] = decision_csv
        approval_record["review"]["comment"] = row.get("reason", "").strip() or row.get("notes", "").strip()
        if row.get("reason", "").strip():
            approval_record["review"]["changes_requested"] = [row.get("reason", "").strip()]

        # Save approval record
        record_file = promoted_dir / f"approval-record-{approval_record['approval_record_id']}.json"
        with open(record_file, "w", encoding="utf-8") as f:
            json.dump(approval_record, f, indent=2)

        promoted.append({
            "object_key": object_key,
            "approval_record_id": approval_record["approval_record_id"],
            "status": "proposed",
            "file": record_file.name,
        })

    # Generate promotion report
    timestamp = datetime.utcnow().isoformat() + "+00:00"
    report = f"""# Week 2 Draft Promotion Report — {args.device}

**Generated:** {timestamp}
**Device ID:** {args.device_id}

---

## Summary

| Status | Count |
|--------|-------|
| Promoted to ApprovalRecord | {len(promoted)} |
| Not promoted | {len(not_promoted)} |
| Missing draft files | {len(missing_drafts)} |
| **Total decisions processed** | **{len(decisions)}** |

---

## Promoted to ApprovalRecord (status: proposed)

Drafts promoted with explicit human approval:

"""

    if promoted:
        report += "| Object Key | Approval Record ID | File |\n"
        report += "|------------|-------------------|------|\n"
        for item in promoted:
            report += f"| {item['object_key']} | {item['approval_record_id']} | {item['file']} |\n"
    else:
        report += "No drafts promoted.\n"

    report += f"""
---

## Not Promoted (Failed Validation)

Decisions that did NOT meet promotion criteria:

"""

    if not_promoted:
        report += "| Object Key | Decision | Reviewer | Reason |\n"
        report += "|------------|----------|----------|--------|\n"
        for item in not_promoted:
            report += f"| {item['object_key']} | {item['decision']} | {item['reviewer']} | {item['reason']} |\n"
    else:
        report += "All decisions met promotion criteria.\n"

    if missing_drafts:
        report += f"""
---

## Missing Draft Files

Expected draft files that were not found:

"""
        report += "| Object Key | Expected File |\n"
        report += "|------------|---------------|\n"
        for item in missing_drafts:
            report += f"| {item['object_key']} | {item['expected_file']} |\n"

    report += f"""
---

## Promotion Criteria (ALL required)

✅ decision = "approve_for_approval_record"
✅ approval_record_allowed = true
✅ reviewer field filled
✅ reviewed_at field filled with valid ISO datetime
✅ Draft file exists and valid JSON

---

## Promoted ApprovalRecords

Location: {promoted_dir}

Created ApprovalRecords have status = "proposed" (not auto-approved).

Approval workflow:
1. ApprovalRecord created with status: proposed
2. Manual approval/rejection required (separate step)
3. No automatic transitions
4. Audit trail maintained

---

## Safety Confirmations

✅ No NetBox API calls
✅ No NetBox writes
✅ No ApplyPlan created
✅ No automatic approvals
✅ Manual review required
✅ Audit trail complete

---

**Status:** Promotion complete
**Next:** Review promoted ApprovalRecords in {promoted_dir}
**Then:** Proceed to approval/rejection workflow
"""

    # Save report
    report_file = Path(args.report) if args.report else output_dir / "week2-promotion-report.md"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"✓ Promoted: {len(promoted)} draft(s) to ApprovalRecord")
    print(f"✓ Not promoted: {len(not_promoted)} decision(s) failed validation")
    if missing_drafts:
        print(f"⚠ Missing: {len(missing_drafts)} draft file(s)")
    print(f"✓ Report saved: {report_file}")

    if promoted:
        print(f"\n✅ Promotion complete")
        print(f"\nApprovalRecords created:")
        for item in promoted:
            print(f"  - {item['object_key']}: {item['approval_record_id']}")
            print(f"    Status: {item['status']}")
            print(f"    File: {item['file']}")
    else:
        print(f"\n⚠️ No drafts promoted (all decisions failed validation or missing drafts)")

    print(f"\nNext steps:")
    print(f"  1. Review approval records in {promoted_dir}")
    print(f"  2. Run approval/rejection workflow")
    print(f"  3. Monitor state transitions")


if __name__ == "__main__":
    main()
