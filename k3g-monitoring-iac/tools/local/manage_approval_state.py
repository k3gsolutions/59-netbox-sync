#!/usr/bin/env python3
"""Manage ApprovalRecord state transitions (local, no writes)."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import shutil


# Valid state transitions
VALID_TRANSITIONS = {
    "proposed": ["approved", "rejected", "changes_requested", "ignored"],
    "approved": ["dry_run_passed", "expired"],
    "dry_run_passed": [],  # Final state this phase
    "rejected": [],  # Final state
    "changes_requested": [],  # Final state this phase
    "ignored": [],  # Final state
}

# Target directory per state
STATE_DIRS = {
    "proposed": "pending",
    "approved": "approved",
    "rejected": "rejected",
    "changes_requested": "changes_requested",
    "dry_run_passed": "approved",  # Stays in approved/ with updated status
    "ignored": "ignored",
}


def load_approval_record(file_path: str) -> Dict:
    """Load ApprovalRecord JSON."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ValueError(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")


def save_approval_record(file_path: str, record: Dict) -> None:
    """Save ApprovalRecord JSON."""
    output_dir = Path(file_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Backup existing file
    if Path(file_path).exists():
        backup_path = f"{file_path}.backup.{datetime.now(timezone.utc).isoformat()}"
        shutil.copy(file_path, backup_path)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)


def validate_approval_record(record: Dict, action: str) -> List[str]:
    """Validate ApprovalRecord for the given action."""
    errors = []
    proposal = record.get("proposal", {})
    confidence = proposal.get("confidence")
    category = proposal.get("category")
    naming_compliant = proposal.get("naming_compliant")

    if action == "approve":
        # Only safe_create_staged can be approved
        if proposal.get("action") != "safe_create_staged":
            errors.append(
                f"Cannot approve action={proposal.get('action')} (only safe_create_staged)"
            )

        # Service items must have valid naming
        if category == "service" and not naming_compliant:
            errors.append("Cannot approve service item with invalid naming")

        # Confidence must be exact or normalized
        if confidence not in ("exact", "normalized"):
            errors.append(f"Cannot approve confidence={confidence} (only exact/normalized)")

    # Check for secrets in evidence
    evidence = json.dumps(record.get("evidence", {}))
    forbidden = ["password", "token", "secret", "api_key", "ssh"]
    for pattern in forbidden:
        if pattern in evidence.lower():
            errors.append(f"Forbidden pattern in evidence: {pattern}")

    return errors


def add_state_history(record: Dict, from_state: str, to_state: str, by: str, reason: str = None) -> None:
    """Add entry to state_history."""
    if "state_history" not in record:
        record["state_history"] = []

    entry = {
        "from": from_state,
        "to": to_state,
        "by": by,
        "at": datetime.now(timezone.utc).isoformat(),
        "tool_version": "1.0",
    }

    if reason:
        entry["reason"] = reason

    record["state_history"].append(entry)


def move_approval_file(old_path: str, new_path: str) -> None:
    """Move approval file to new location."""
    old_p = Path(old_path)
    new_p = Path(new_path)

    if not old_p.exists():
        raise ValueError(f"Source file not found: {old_path}")

    new_p.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(old_p), str(new_p))


def get_approval_new_path(approval_path: str, new_state: str) -> str:
    """Determine new file path based on state."""
    approval_p = Path(approval_path)
    approval_root = approval_p.parent.parent  # approvals/ directory

    target_dir = STATE_DIRS.get(new_state, "pending")
    return str(approval_root / target_dir / approval_p.name)


def approve_approval(approval_path: str, by: str, comment: str = None) -> None:
    """Transition approval to approved state."""
    record = load_approval_record(approval_path)
    current_state = record.get("review", {}).get("status")

    if current_state not in VALID_TRANSITIONS:
        raise ValueError(f"Unknown current state: {current_state}")

    if "approved" not in VALID_TRANSITIONS.get(current_state, []):
        raise ValueError(f"Cannot transition from {current_state} to approved")

    # Validate
    errors = validate_approval_record(record, "approve")
    if errors:
        raise ValueError(f"Validation failed:\n" + "\n".join(errors))

    # Update record
    record["review"]["status"] = "approved"
    record["review"]["reviewed_by"] = by
    record["review"]["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    record["review"]["decision"] = "approve"
    if comment:
        record["review"]["comment"] = comment

    add_state_history(record, current_state, "approved", by, comment or "Approved")

    # Save and move
    new_path = get_approval_new_path(approval_path, "approved")

    if approval_path != new_path:
        save_approval_record(new_path, record)
        Path(approval_path).unlink()  # Delete old file
    else:
        save_approval_record(approval_path, record)

    print(f"✓ Approved: {new_path}")
    print(f"  Reviewed by: {by}")
    print(f"  Timestamp: {record['review']['reviewed_at']}")


def reject_approval(approval_path: str, by: str, reason: str = None) -> None:
    """Transition approval to rejected state."""
    record = load_approval_record(approval_path)
    current_state = record.get("review", {}).get("status")

    if current_state not in VALID_TRANSITIONS:
        raise ValueError(f"Unknown current state: {current_state}")

    if "rejected" not in VALID_TRANSITIONS.get(current_state, []):
        raise ValueError(f"Cannot transition from {current_state} to rejected")

    # Update record
    record["review"]["status"] = "rejected"
    record["review"]["reviewed_by"] = by
    record["review"]["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    record["review"]["decision"] = "reject"
    if reason:
        record["review"]["rejection_reason"] = reason

    add_state_history(record, current_state, "rejected", by, reason or "Rejected")

    # Save and move
    new_path = get_approval_new_path(approval_path, "rejected")

    if approval_path != new_path:
        save_approval_record(new_path, record)
        Path(approval_path).unlink()  # Delete old file
    else:
        save_approval_record(approval_path, record)

    print(f"✓ Rejected: {new_path}")
    print(f"  Reviewed by: {by}")
    if reason:
        print(f"  Reason: {reason}")
    print(f"  Timestamp: {record['review']['reviewed_at']}")


def request_changes(approval_path: str, by: str, reason: str = None) -> None:
    """Transition approval to changes_requested state."""
    record = load_approval_record(approval_path)
    current_state = record.get("review", {}).get("status")

    if current_state not in VALID_TRANSITIONS:
        raise ValueError(f"Unknown current state: {current_state}")

    if "changes_requested" not in VALID_TRANSITIONS.get(current_state, []):
        raise ValueError(f"Cannot transition from {current_state} to changes_requested")

    # Update record
    record["review"]["status"] = "changes_requested"
    record["review"]["reviewed_by"] = by
    record["review"]["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    record["review"]["decision"] = "request_changes"
    if reason:
        record["review"]["rejection_reason"] = reason

    add_state_history(record, current_state, "changes_requested", by, reason or "Changes requested")

    # Save and move
    new_path = get_approval_new_path(approval_path, "changes_requested")

    if approval_path != new_path:
        save_approval_record(new_path, record)
        Path(approval_path).unlink()  # Delete old file
    else:
        save_approval_record(approval_path, record)

    print(f"✓ Changes requested: {new_path}")
    print(f"  Reviewed by: {by}")
    if reason:
        print(f"  Reason: {reason}")
    print(f"  Timestamp: {record['review']['reviewed_at']}")


def mark_dry_run_passed(approval_path: str, by: str, dry_run_report: str = None) -> None:
    """Transition approved to dry_run_passed state."""
    record = load_approval_record(approval_path)
    current_state = record.get("review", {}).get("status")

    if current_state != "approved":
        raise ValueError(f"Can only mark dry_run_passed from approved state (current: {current_state})")

    # Update record
    record["review"]["status"] = "dry_run_passed"
    record["review"]["dry_run_by"] = by
    record["review"]["dry_run_at"] = datetime.now(timezone.utc).isoformat()

    if dry_run_report:
        record["audit"]["dry_run_report"] = dry_run_report

    add_state_history(record, current_state, "dry_run_passed", by, dry_run_report or "Dry-run passed")

    # Save (stays in approved/)
    save_approval_record(approval_path, record)

    print(f"✓ Dry-run marked passed: {approval_path}")
    print(f"  By: {by}")
    if dry_run_report:
        print(f"  Dry-run report: {dry_run_report}")
    print(f"  Timestamp: {record['review']['dry_run_at']}")


def main():
    parser = argparse.ArgumentParser(
        description="Manage ApprovalRecord state transitions (local, no API calls)"
    )
    subparsers = parser.add_subparsers(dest="command", help="State transition command")

    # Approve
    approve_p = subparsers.add_parser("approve", help="Approve an ApprovalRecord")
    approve_p.add_argument("--approval", required=True, help="ApprovalRecord file path")
    approve_p.add_argument("--by", required=True, help="Operator name")
    approve_p.add_argument("--comment", help="Optional approval comment")

    # Reject
    reject_p = subparsers.add_parser("reject", help="Reject an ApprovalRecord")
    reject_p.add_argument("--approval", required=True, help="ApprovalRecord file path")
    reject_p.add_argument("--by", required=True, help="Operator name")
    reject_p.add_argument("--reason", help="Rejection reason")

    # Request changes
    changes_p = subparsers.add_parser("request-changes", help="Request changes to an ApprovalRecord")
    changes_p.add_argument("--approval", required=True, help="ApprovalRecord file path")
    changes_p.add_argument("--by", required=True, help="Operator name")
    changes_p.add_argument("--reason", help="Changes requested reason")

    # Mark dry-run passed
    dryrun_p = subparsers.add_parser("mark-dry-run-passed", help="Mark dry-run as passed")
    dryrun_p.add_argument("--approval", required=True, help="ApprovalRecord file path")
    dryrun_p.add_argument("--by", required=True, help="Operator name")
    dryrun_p.add_argument("--dry-run-report", help="Path to dry-run report")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == "approve":
            approve_approval(args.approval, args.by, args.comment)
        elif args.command == "reject":
            reject_approval(args.approval, args.by, args.reason)
        elif args.command == "request-changes":
            request_changes(args.approval, args.by, args.reason)
        elif args.command == "mark-dry-run-passed":
            mark_dry_run_passed(args.approval, args.by, args.dry_run_report)
        else:
            parser.print_help()
            return 1

        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
