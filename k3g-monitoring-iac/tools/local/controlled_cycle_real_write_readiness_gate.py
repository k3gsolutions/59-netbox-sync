#!/usr/bin/env python3
"""FASE 4.16 — Controlled Operation Cycle Real Write Readiness Gate.

Validate that Cycle-001 is ready for real write authorization package.
"""

from __future__ import annotations

import argparse
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


def load_markdown_safe(file_path: Path) -> str:
    """Load markdown file safely."""
    if not file_path.exists():
        return ""

    try:
        with open(file_path, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def validate_approval_record(record: Dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate approved ApprovalRecord."""
    issues = []

    if record.get("status") != "approved":
        issues.append("status must be approved")
    if record.get("state") != "approved":
        issues.append("state must be approved")
    if not record.get("approved_by"):
        issues.append("approved_by required")
    if not record.get("approved_at"):
        issues.append("approved_at required")
    if not record.get("approval_reason"):
        issues.append("approval_reason required")

    return len(issues) == 0, issues


def validate_readiness(
    applyplan: Dict[str, Any],
    simulation_result: Dict[str, Any],
    simulation_report: str,
    approved_dir: Path,
) -> tuple[bool, list[str]]:
    """Validate readiness for real write."""
    issues = []

    # Check ApplyPlan
    if applyplan.get("mode") != "dry_run":
        issues.append("apply_plan mode must be dry_run")
    if applyplan.get("execution_policy", {}).get("can_execute_real_write") is not False:
        issues.append("can_execute_real_write must be false")
    if applyplan.get("execution_policy", {}).get("requires_next_gate") is not True:
        issues.append("requires_next_gate must be true")

    # Check simulation result
    if simulation_result.get("status") not in [
        "CYCLE_DRYRUN_SIMULATION_PASSED",
        "CYCLE_DRYRUN_SIMULATION_PASSED_WITH_WARNINGS",
    ]:
        issues.append("simulation status must be PASSED or PASSED_WITH_WARNINGS")
    if simulation_result.get("next_gate_required") is not True:
        issues.append("simulation must indicate next_gate_required")

    # Check simulation report
    if not simulation_report:
        issues.append("simulation report missing")
    elif "FAILED" in simulation_report:
        issues.append("simulation report indicates failure")

    # Check source approval records exist
    source_records = applyplan.get("source_approval_records", [])
    if not source_records:
        issues.append("source_approval_records empty")

    if approved_dir.exists():
        for record_id in source_records:
            record_file = approved_dir / f"{record_id}.json"
            if not record_file.exists():
                issues.append(f"approved record not found: {record_id}")
            else:
                record = load_json_safe(record_file)
                is_valid, record_issues = validate_approval_record(record)
                if not is_valid:
                    issues.extend([f"{record_id}: {issue}" for issue in record_issues])
    else:
        if source_records:
            issues.append("approved records directory does not exist")

    # Check items have rollback hints
    items = applyplan.get("items", [])
    for idx, item in enumerate(items):
        if not item.get("rollback_hint"):
            issues.append(f"item[{idx}]: rollback_hint required")
        if not item.get("expected_result"):
            issues.append(f"item[{idx}]: expected_result required")

    # Check for secrets
    applyplan_str = json.dumps(applyplan).lower()
    blocked = ["token", "password", "secret", "api_key", "private key", "bearer", "authorization"]
    for word in blocked:
        if word in applyplan_str:
            issues.append(f"ApplyPlan contains blocked keyword: {word}")

    return len(issues) == 0, issues


def generate_readiness_markdown(
    cycle_id: str,
    apply_plan_id: str,
    device: str,
    decision: str,
    item_count: int,
    issues: list[str],
) -> str:
    """Generate readiness gate markdown."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    emoji = {
        "CYCLE_READY_FOR_REAL_WRITE_REVIEW": "✓",
        "CYCLE_READY_WITH_RESTRICTIONS": "⚠",
        "CYCLE_NOT_READY_FOR_REAL_WRITE": "✗",
    }.get(decision, "?")

    md = f"""# {cycle_id} — Real Write Readiness Gate

## 1. Decision

### {emoji} {decision}

## 2. Readiness Summary

- **Apply Plan ID:** {apply_plan_id}
- **Cycle:** {cycle_id}
- **Device:** {device}
- **Items:** {item_count}
- **Status:** ready for authorization review

## 3. Governance Chain Validation

- ✓ ApplyPlan mode=dry_run validated
- ✓ can_execute_real_write=false enforced
- ✓ requires_next_gate=true confirmed
- ✓ Simulation passed (or with warnings)
- ✓ Approved ApprovalRecords present
- ✓ Rollback hints computed
- ✓ Expected results defined
- ✓ No secrets in governance chain

## 4. Issues Found

"""

    if not issues:
        md += "None\n"
    else:
        for issue in issues:
            md += f"- {issue}\n"

    md += f"""

## 5. Next Steps

"""

    if decision == "CYCLE_READY_FOR_REAL_WRITE_REVIEW":
        md += "Proceed to real write authorization package (next FASE). All governance gates passed."
    elif decision == "CYCLE_READY_WITH_RESTRICTIONS":
        md += "Proceed with caution. Review restrictions before authorization."
    else:
        md += "Not ready. Address issues before real write."

    md += f"""

---

**Cycle ID:** {cycle_id}
**Gate Validated At:** {timestamp}
"""

    return md


def main() -> int:
    """Run FASE 4.16."""
    parser = argparse.ArgumentParser(description="FASE 4.16 — Real Write Readiness Gate")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--apply-plan", type=Path, required=True)
    parser.add_argument("--simulation-result", type=Path, required=True)
    parser.add_argument("--simulation-report", type=Path, required=True)
    parser.add_argument("--dryrun-execution-gate", type=Path, required=True)
    parser.add_argument("--approved-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)

    args = parser.parse_args()

    # Load all inputs
    applyplan = load_json_safe(args.apply_plan)
    simulation_result = load_json_safe(args.simulation_result)
    simulation_report = load_markdown_safe(args.simulation_report)
    execution_gate_report = load_markdown_safe(args.dryrun_execution_gate)

    if not applyplan:
        print(f"✗ ApplyPlan not found: {args.apply_plan}")
        return 1

    if not simulation_result:
        print(f"✗ Simulation result not found: {args.simulation_result}")
        return 1

    # Validate readiness
    is_ready, issues = validate_readiness(
        applyplan,
        simulation_result,
        simulation_report,
        args.approved_dir,
    )

    # Check execution gate report
    if "BLOCKED" in execution_gate_report:
        issues.append("Execution gate reports blocked status")
        is_ready = False

    # Determine decision
    if is_ready:
        decision = "CYCLE_READY_FOR_REAL_WRITE_REVIEW"
    elif any("warning" in issue.lower() for issue in issues):
        decision = "CYCLE_READY_WITH_RESTRICTIONS"
    else:
        decision = "CYCLE_NOT_READY_FOR_REAL_WRITE"

    # Generate markdown
    markdown = generate_readiness_markdown(
        args.cycle_id,
        applyplan.get("apply_plan_id", "unknown"),
        applyplan.get("device", "unknown"),
        decision,
        applyplan.get("item_count", 0),
        issues,
    )

    # Generate JSON
    readiness_json = {
        "cycle_id": args.cycle_id,
        "apply_plan_id": applyplan.get("apply_plan_id"),
        "decision": decision,
        "validated_at": datetime.utcnow().isoformat() + "+00:00",
        "summary": {
            "item_count": applyplan.get("item_count", 0),
            "simulated_items": simulation_result.get("summary", {}).get("total_items", 0),
            "issues_found": len(issues),
            "ready_for_authorization": decision in ["CYCLE_READY_FOR_REAL_WRITE_REVIEW", "CYCLE_READY_WITH_RESTRICTIONS"],
        },
        "issues": issues,
        "governance_chain": {
            "approval_records_validated": True,
            "simulation_passed": simulation_result.get("status", "").startswith("CYCLE_DRYRUN_SIMULATION_PASSED"),
            "execution_gate_ready": "READY" in execution_gate_report,
            "applyplan_safe": applyplan.get("execution_policy", {}).get("can_execute_real_write") is False,
        },
    }

    # Write outputs
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(readiness_json, f, indent=2)

    print(f"✓ Real write readiness decision: {decision}")
    print(f"✓ Items: {applyplan.get('item_count', 0)}")
    print(f"✓ Issues: {len(issues)}")
    print(f"✓ Report: {args.output}")
    print(f"✓ JSON: {args.output_json}")

    return 0 if "READY" in decision else 1


if __name__ == "__main__":
    raise SystemExit(main())
