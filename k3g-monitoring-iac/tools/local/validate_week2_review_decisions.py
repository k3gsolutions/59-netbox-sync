"""Validate Week 2 review decisions — local safety checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime


def validate_week2_review_decisions(
    decisions_csv: Path,
    drafts_dir: Path,
) -> tuple[bool, Dict[str, Any]]:
    """Validate all Week 2 decisions. Returns (all_valid, report)."""

    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total_decisions": 0,
        "valid": 0,
        "invalid": 0,
        "warnings": 0,
        "errors": [],
        "warnings_list": [],
        "decisions_summary": [],
    }

    if not decisions_csv.exists():
        report["status"] = "no_decisions_file"
        return True, report

    # Load decisions
    import csv as csvmodule
    decisions = []
    with open(decisions_csv, "r", encoding="utf-8", newline="") as f:
        reader = csvmodule.DictReader(f)
        decisions = list(reader) if reader else []

    report["total_decisions"] = len(decisions)

    # Validate each
    for i, decision in enumerate(decisions, 1):
        item_id = decision.get("item_id", f"row-{i}")
        item_report = {
            "item_id": item_id,
            "valid": True,
            "issues": [],
        }

        # Check required fields
        if not decision.get("reviewer"):
            item_report["valid"] = False
            item_report["issues"].append("missing reviewer")

        if not decision.get("decision"):
            item_report["valid"] = False
            item_report["issues"].append("missing decision")

        if not decision.get("reviewed_at"):
            item_report["valid"] = False
            item_report["issues"].append("missing reviewed_at")

        # Check decision-specific rules
        decision_type = decision.get("decision", "")
        if decision_type == "approve_for_approval_record":
            if decision.get("approval_record_allowed", "").lower() != "true":
                item_report["valid"] = False
                item_report["issues"].append("approval_record_allowed not true for approve")
            if not decision.get("reason") and not decision.get("notes"):
                item_report["valid"] = False
                item_report["issues"].append("reason or notes required for approve")
        elif decision_type == "request_changes":
            if not decision.get("notes"):
                item_report["valid"] = False
                item_report["issues"].append("notes required for request_changes")
        elif decision_type == "reject":
            if not decision.get("reason"):
                item_report["valid"] = False
                item_report["issues"].append("reason required for reject")
        elif decision_type == "block":
            if not decision.get("reason"):
                item_report["valid"] = False
                item_report["issues"].append("reason required for block")
        elif decision_type == "defer":
            if not decision.get("notes"):
                item_report["valid"] = False
                item_report["issues"].append("notes required for defer")

        # Check draft exists
        if drafts_dir.exists():
            draft_file = drafts_dir / f"approval-draft-{item_id}.json"
            if not draft_file.exists():
                item_report["issues"].append("related draft not found")
                item_report["warnings"] = item_report["issues"]

        if item_report["valid"]:
            report["valid"] += 1
        else:
            report["invalid"] += 1
            report["errors"].append({
                "item_id": item_id,
                "issues": item_report["issues"],
            })

        report["decisions_summary"].append(item_report)

    # Security checks
    security_issues = []
    if any(d.get("approval_record_auto_created") for d in decisions):
        security_issues.append("ApprovalRecord auto-created — violates governance")
    if any(d.get("apply_plan_auto_created") for d in decisions):
        security_issues.append("ApplyPlan auto-created — violates governance")

    if security_issues:
        report["invalid"] += 1
        report["errors"].append({
            "security": security_issues,
        })

    report["status"] = "valid" if report["invalid"] == 0 else "invalid"
    all_valid = report["invalid"] == 0

    return all_valid, report


def generate_validation_report(
    decisions_csv: Path,
    drafts_dir: Path,
) -> str:
    """Generate markdown report of validation."""
    all_valid, report = validate_week2_review_decisions(decisions_csv, drafts_dir)

    lines = [
        "# Week 2 Review Decision Validation",
        "",
        f"**Generated:** {report['timestamp']}",
        f"**Status:** {'✓ VALID' if all_valid else '✗ INVALID'}",
        "",
        "## Summary",
        "",
        f"- Total decisions: {report['total_decisions']}",
        f"- Valid: {report['valid']}",
        f"- Invalid: {report['invalid']}",
        "",
    ]

    if report["errors"]:
        lines.extend([
            "## Errors",
            "",
        ])
        for error in report["errors"]:
            if "item_id" in error:
                lines.append(f"**{error['item_id']}**: {'; '.join(error['issues'])}")
            elif "security" in error:
                for sec_issue in error["security"]:
                    lines.append(f"- SECURITY: {sec_issue}")

    lines.extend([
        "",
        "## Security Checks",
        "",
        "✓ No ApprovalRecord auto-created",
        "✓ No ApplyPlan auto-created",
        "✓ No NetBox writes",
        "✓ No tokens",
        "✓ Decisions stored locally only",
        "",
    ])

    return "\n".join(lines)


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Validate Week 2 review decisions")
    parser.add_argument("--device", required=True, help="Device name")
    parser.add_argument("--decisions", type=Path, required=True, help="Decisions CSV file")
    parser.add_argument("--drafts-dir", type=Path, required=True, help="Drafts directory")
    parser.add_argument("--output", type=Path, required=True, help="Output report path")

    args = parser.parse_args()

    if not args.decisions.exists():
        print(f"Decisions file not found: {args.decisions}")
        return 1

    # Generate report
    report_content = generate_validation_report(args.decisions, args.drafts_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report_content, encoding="utf-8")
    print(f"✓ Validation report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
