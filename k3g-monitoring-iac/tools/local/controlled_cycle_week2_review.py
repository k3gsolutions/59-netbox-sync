#!/usr/bin/env python3
"""FASE 4.8 — Controlled Operation Cycle Week 2 Human Review.

Validate human review decisions from Week 2.
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


def load_decisions_csv(csv_file: Path) -> list[Dict[str, Any]]:
    """Load decisions CSV."""
    decisions = []

    if not csv_file.exists():
        return decisions

    try:
        with open(csv_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                decisions.append(row)
    except Exception:
        pass

    return decisions


def validate_decision(decision: Dict[str, str]) -> tuple[bool, list[str]]:
    """Validate single decision."""
    issues = []

    # Check decision
    valid_decisions = ["approve_for_approval_record", "request_changes", "rejected", "deferred", "pending"]
    if decision.get("decision", "pending") not in valid_decisions:
        issues.append(f"invalid decision: {decision.get('decision')}")

    # Check reviewer for approve
    if decision.get("decision") == "approve_for_approval_record":
        if not decision.get("reviewed_by"):
            issues.append("reviewer required for approve")

        if not decision.get("approval_record_allowed") or decision.get("approval_record_allowed", "").lower() != "true":
            issues.append("approval_record_allowed must be true for approve")

    return len(issues) == 0, issues


def evaluate_review(decisions: list[Dict[str, Any]]) -> str:
    """Evaluate week 2 review result."""
    approved_count = 0
    blocked_count = 0
    valid_count = 0
    total = len(decisions)

    for decision in decisions:
        is_valid, _issues = validate_decision(decision)
        if is_valid:
            valid_count += 1
            if decision.get("decision") == "approve_for_approval_record":
                approved_count += 1
        else:
            blocked_count += 1

    if blocked_count > 0:
        return "WEEK2_REVIEW_BLOCKED"

    if approved_count > 0:
        if valid_count == total:
            return "WEEK2_REVIEW_PASSED"
        else:
            return "WEEK2_REVIEW_PASSED_WITH_RESTRICTIONS"

    return "WEEK2_REVIEW_BLOCKED"


def generate_review_markdown(
    cycle_id: str,
    device: str,
    decision: str,
    decisions: list[Dict[str, Any]],
) -> str:
    """Generate review markdown report."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    emoji = {
        "WEEK2_REVIEW_PASSED": "✓",
        "WEEK2_REVIEW_PASSED_WITH_RESTRICTIONS": "⚠",
        "WEEK2_REVIEW_BLOCKED": "✗",
    }.get(decision, "?")

    approved = sum(1 for d in decisions if d.get("decision") == "approve_for_approval_record")
    rejected = sum(1 for d in decisions if d.get("decision") == "rejected")
    requested = sum(1 for d in decisions if d.get("decision") == "request_changes")
    pending = sum(1 for d in decisions if d.get("decision") in ["pending", "deferred", ""])

    md = f"""# {cycle_id} — Week 2 Human Review

## 1. Decision

### {emoji} {decision}

## 2. Review Results

- **Total Items:** {len(decisions)}
- **Approved for ApprovalRecord:** {approved}
- **Rejected:** {rejected}
- **Request Changes:** {requested}
- **Pending:** {pending}

## 3. Review Summary

"""

    if approved > 0:
        md += f"✓ {approved} item(s) ready for ApprovalRecord promotion\n"
    if requested > 0:
        md += f"⚠ {requested} item(s) require changes\n"
    if rejected > 0:
        md += f"✗ {rejected} item(s) rejected\n"
    if pending > 0:
        md += f"? {pending} item(s) pending review\n"

    md += f"""

## 4. Next Steps

"""
    if decision == "WEEK2_REVIEW_PASSED":
        md += "Proceed to promote approved items to proposed ApprovalRecords."
    elif decision == "WEEK2_REVIEW_PASSED_WITH_RESTRICTIONS":
        md += "Promote approved items. Address restrictions before final approval."
    else:
        md += "Address blocked items before proceeding."

    md += f"""

---

**Cycle ID:** {cycle_id}
**Device:** {device}
**Decision:** {decision}
**Review At:** {timestamp}
"""

    return md


def main() -> int:
    """Run FASE 4.8."""
    parser = argparse.ArgumentParser(description="FASE 4.8 — Controlled Operation Cycle Week 2 Review")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--cycle-dir", type=Path, required=True)
    parser.add_argument("--week2-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)

    args = parser.parse_args()

    # Load decisions CSV
    decisions_file = args.week2_dir / f"{args.cycle_id.upper()}-WEEK2-DECISIONS.csv"
    decisions = load_decisions_csv(decisions_file)

    # Validate decisions
    valid_decisions = []
    invalid_decisions = []

    for decision in decisions:
        is_valid, issues = validate_decision(decision)
        if is_valid:
            valid_decisions.append(decision)
        else:
            invalid_decisions.append({"decision": decision, "issues": issues})

    # Evaluate
    decision = evaluate_review(decisions)

    # Generate markdown
    markdown = generate_review_markdown(args.cycle_id, args.device, decision, decisions)

    # Generate JSON
    review_json = {
        "cycle_id": args.cycle_id,
        "device": args.device,
        "device_id": args.device_id,
        "decision": decision,
        "reviewed_at": datetime.utcnow().isoformat() + "+00:00",
        "summary": {
            "total_items": len(decisions),
            "approved": sum(1 for d in decisions if d.get("decision") == "approve_for_approval_record"),
            "rejected": sum(1 for d in decisions if d.get("decision") == "rejected"),
            "request_changes": sum(1 for d in decisions if d.get("decision") == "request_changes"),
            "pending": sum(1 for d in decisions if d.get("decision") in ["pending", "deferred", ""]),
            "valid": len(valid_decisions),
            "invalid": len(invalid_decisions),
        },
        "decisions": decisions,
        "invalid_decisions": invalid_decisions,
    }

    # Write outputs
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(review_json, f, indent=2)

    print(f"✓ Week 2 review decision: {decision}")
    print(f"✓ Total items: {len(decisions)}")
    print(f"✓ Approved: {review_json['summary']['approved']}")
    print(f"✓ Report: {args.output}")
    print(f"✓ JSON: {args.output_json}")

    return 0 if "PASSED" in decision else 1


if __name__ == "__main__":
    raise SystemExit(main())
