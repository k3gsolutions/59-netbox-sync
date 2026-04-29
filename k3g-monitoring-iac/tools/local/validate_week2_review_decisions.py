#!/usr/bin/env python3
"""
Validate Week 2 human review decisions from CSV.

Enforces:
- Decision must be one of allowed values
- approve_for_approval_record requires: reviewer, reviewed_at (ISO), approval_record_allowed=true
- No automatic promotion
- No automatic approval
- Identifies valid vs invalid rows

Output: Validation report with categorization by decision type
"""

import sys
import csv
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

ALLOWED_DECISIONS = [
    "approve_for_approval_record",
    "request_changes",
    "reject",
    "defer",
    "block",
]

REQUIRED_FOR_APPROVAL = ["reviewer", "reviewed_at", "approval_record_allowed"]


def validate_decisions(decisions_file: Path, drafts_dir: Path) -> Tuple[bool, str]:
    """Validate week2 review decisions CSV."""
    if not decisions_file.exists():
        return False, f"Decisions CSV not found: {decisions_file}"

    results = {
        "validated_at": datetime.now().isoformat(),
        "total_rows": 0,
        "approved_for_approval_record": [],
        "request_changes": [],
        "rejected": [],
        "deferred": [],
        "blocked": [],
        "invalid": [],
    }

    try:
        with open(decisions_file, "r") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return False, "CSV is empty"

            for row_num, row in enumerate(reader, start=2):
                results["total_rows"] += 1

                decision = row.get("decision", "").strip()

                # Validate decision is allowed
                if decision not in ALLOWED_DECISIONS:
                    results["invalid"].append({
                        "row": row_num,
                        "issue": f"Invalid decision: '{decision}'. Allowed: {', '.join(ALLOWED_DECISIONS)}",
                        "row_data": row,
                    })
                    continue

                # Additional validation for approval decisions
                if decision == "approve_for_approval_record":
                    approval_record_allowed = row.get("approval_record_allowed", "").strip().lower()
                    reviewer = row.get("reviewer", "").strip()
                    reviewed_at = row.get("reviewed_at", "").strip()

                    # Check required fields
                    if not reviewer:
                        results["invalid"].append({
                            "row": row_num,
                            "issue": "Missing required field: reviewer",
                            "row_data": row,
                        })
                        continue

                    if not reviewed_at:
                        results["invalid"].append({
                            "row": row_num,
                            "issue": "Missing required field: reviewed_at (ISO datetime)",
                            "row_data": row,
                        })
                        continue

                    if approval_record_allowed not in ["true", "1", "yes"]:
                        results["invalid"].append({
                            "row": row_num,
                            "issue": "approval_record_allowed must be 'true' for approval decisions",
                            "row_data": row,
                        })
                        continue

                    # Validate ISO datetime
                    try:
                        datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
                    except ValueError:
                        results["invalid"].append({
                            "row": row_num,
                            "issue": f"Invalid reviewed_at datetime: '{reviewed_at}' (must be ISO 8601)",
                            "row_data": row,
                        })
                        continue

                    # Check draft exists
                    draft_id = row.get("draft_id", "").strip()
                    if draft_id:
                        draft_file = drafts_dir / f"{draft_id}.json"
                        if not draft_file.exists():
                            results["invalid"].append({
                                "row": row_num,
                                "issue": f"Draft file not found: {draft_file}",
                                "row_data": row,
                            })
                            continue

                    # Valid approval
                    results["approved_for_approval_record"].append({
                        "row": row_num,
                        "reviewer": reviewer,
                        "reviewed_at": reviewed_at,
                        "draft_id": draft_id,
                        "reason": row.get("reason", ""),
                    })

                elif decision == "request_changes":
                    results["request_changes"].append({
                        "row": row_num,
                        "reason": row.get("reason", ""),
                    })

                elif decision == "reject":
                    results["rejected"].append({
                        "row": row_num,
                        "reason": row.get("reason", ""),
                    })

                elif decision == "defer":
                    results["deferred"].append({
                        "row": row_num,
                        "reason": row.get("reason", ""),
                    })

                elif decision == "block":
                    results["blocked"].append({
                        "row": row_num,
                        "reason": row.get("reason", ""),
                    })

        # Generate report
        report = _generate_report(results)
        return True, report

    except Exception as e:
        return False, f"Error reading CSV: {e}"


def _generate_report(results: Dict) -> str:
    """Generate validation report."""
    report = f"""# Week 2 Review Decision Validation Report

**Generated:** {results['validated_at']}

## Summary

| Category | Count |
|---|---:|
| **Total Rows** | {results['total_rows']} |
| **Valid Approvals** | {len(results['approved_for_approval_record'])} |
| **Request Changes** | {len(results['request_changes'])} |
| **Rejected** | {len(results['rejected'])} |
| **Deferred** | {len(results['deferred'])} |
| **Blocked** | {len(results['blocked'])} |
| **Invalid** | {len(results['invalid'])} |

## Valid Approval Decisions

Items approved for ApprovalRecord creation (will proceed to promotion):

"""
    if results["approved_for_approval_record"]:
        report += "| Row | Reviewer | Reviewed At | Draft ID |\n"
        report += "|---|---|---|---|\n"
        for item in results["approved_for_approval_record"]:
            report += f"| {item['row']} | {item['reviewer']} | {item['reviewed_at']} | {item['draft_id']} |\n"
    else:
        report += "*(None)*\n"

    report += f"\n## Request Changes\n\n"
    if results["request_changes"]:
        report += "Items requiring changes before approval:\n\n"
        for item in results["request_changes"]:
            report += f"- Row {item['row']}: {item['reason']}\n"
    else:
        report += "*(None)*\n"

    report += f"\n## Rejected\n\n"
    if results["rejected"]:
        report += "Items rejected from promotion:\n\n"
        for item in results["rejected"]:
            report += f"- Row {item['row']}: {item['reason']}\n"
    else:
        report += "*(None)*\n"

    report += f"\n## Deferred\n\n"
    if results["deferred"]:
        report += "Items deferred to later review:\n\n"
        for item in results["deferred"]:
            report += f"- Row {item['row']}: {item['reason']}\n"
    else:
        report += "*(None)*\n"

    report += f"\n## Blocked\n\n"
    if results["blocked"]:
        report += "Items blocked from promotion:\n\n"
        for item in results["blocked"]:
            report += f"- Row {item['row']}: {item['reason']}\n"
    else:
        report += "*(None)*\n"

    report += f"\n## Validation Errors\n\n"
    if results["invalid"]:
        report += "Invalid rows that cannot be processed:\n\n"
        for item in results["invalid"]:
            report += f"- Row {item['row']}: {item['issue']}\n"
    else:
        report += "*(None - all rows valid)*\n"

    report += f"""
## Recommendations

- **Approved items:** {len(results['approved_for_approval_record'])} ready for promotion to ApprovalRecord (proposed status)
- **Needs review:** {len(results['request_changes'])} items need changes
- **Do not promote:** {len(results['rejected']) + len(results['blocked'])} items rejected/blocked
- **Invalid rows:** Fix {len(results['invalid'])} validation errors before retry

## Safety Notes

- No ApprovalRecord is automatically approved
- No ApplyPlan created
- No NetBox writes executed
- All approvals remain in `proposed` status
- Manual verification required before any field deployment
"""

    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate Week 2 human review decisions"
    )
    parser.add_argument(
        "--decisions",
        required=True,
        type=Path,
        help="Path to week2-review-decisions.csv"
    )
    parser.add_argument(
        "--drafts-dir",
        required=True,
        type=Path,
        help="Path to week2-approval-drafts directory"
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output validation report file"
    )

    args = parser.parse_args()

    success, report = validate_decisions(args.decisions, args.drafts_dir)

    with open(args.output, "w") as f:
        f.write(report)

    if success:
        print(f"✓ Validation report generated: {args.output}")
        sys.exit(0)
    else:
        print(f"✗ Validation failed: {report}", file=sys.stderr)
        sys.exit(1)
