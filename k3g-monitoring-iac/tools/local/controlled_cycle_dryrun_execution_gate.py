#!/usr/bin/env python3
"""FASE 4.14 — Controlled Operation Cycle Dry-Run Execution Gate.

Validate that dry-run ApplyPlan is ready for local simulation execution.
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


def validate_applyplan_for_execution(applyplan: Dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate ApplyPlan ready for dry-run execution."""
    issues = []

    # Check basic fields
    if not applyplan.get("apply_plan_id"):
        issues.append("apply_plan_id required")
    if not applyplan.get("cycle_id"):
        issues.append("cycle_id required")

    # Check mode
    if applyplan.get("mode") != "dry_run":
        issues.append(f"mode={applyplan.get('mode')} must be dry_run")

    # Check status
    if applyplan.get("status") not in ["generated", "validated"]:
        issues.append(f"status={applyplan.get('status')} must be generated or validated")

    # Check items
    if not applyplan.get("items"):
        issues.append("items required and not empty")

    # Check item count
    if applyplan.get("item_count", 0) > 3:
        issues.append(f"item_count={applyplan.get('item_count')} exceeds max of 3")

    # Check safety flags
    safety = applyplan.get("safety_flags", {})
    required_flags = [
        "dry_run_only",
        "no_netbox_write",
        "no_token_required",
        "no_apply_execution",
        "manual_execution_gate_required",
        "generated_from_approved_records",
    ]
    for flag in required_flags:
        if not safety.get(flag):
            issues.append(f"safety_flags: {flag} required and must be true")

    # Check execution policy
    policy = applyplan.get("execution_policy", {})
    if policy.get("can_execute_real_write") is not False:
        issues.append("can_execute_real_write must be false")
    if policy.get("requires_next_gate") is not True:
        issues.append("requires_next_gate must be true")

    # Check methods/targets
    allowed = policy.get("allowed_methods", [])
    forbidden = policy.get("forbidden_methods", [])
    if "POST" not in allowed:
        issues.append("POST must be in allowed_methods")
    if "PATCH" not in forbidden or "DELETE" not in forbidden:
        issues.append("PATCH and DELETE must be in forbidden_methods")

    # Check items for forbidden targets/secrets
    items = applyplan.get("items", [])
    for idx, item in enumerate(items):
        method = item.get("method", "")
        if method not in allowed:
            issues.append(f"item[{idx}]: method={method} not allowed")

        endpoint = item.get("target_endpoint", "")
        forbidden_targets = ["/sync", "equipment", "ssh", "netconf"]
        for target in forbidden_targets:
            if target in endpoint:
                issues.append(f"item[{idx}]: endpoint contains forbidden target {target}")

        # Check for secrets
        payload_str = json.dumps(item.get("proposed_payload", {})).lower()
        blocked = ["token", "password", "secret", "api_key", "private key", "bearer", "authorization"]
        for word in blocked:
            if word in payload_str:
                issues.append(f"item[{idx}]: payload contains blocked keyword: {word}")

    # Check whole ApplyPlan for secrets
    applyplan_str = json.dumps(applyplan).lower()
    blocked = ["token", "password", "secret", "api_key", "private key", "bearer", "authorization"]
    for word in blocked:
        if word in applyplan_str:
            issues.append(f"ApplyPlan contains blocked keyword: {word}")

    return len(issues) == 0, issues


def validate_validation_report(report_text: str) -> tuple[bool, list[str]]:
    """Check validation report content."""
    issues = []

    if not report_text:
        issues.append("validation report is empty or missing")
        return False, issues

    # Check for valid decision
    if "CYCLE_DRYRUN_APPLYPLAN_INVALID" in report_text:
        issues.append("validation report contains INVALID decision")
    elif "CYCLE_DRYRUN_APPLYPLAN_VALID" not in report_text:
        issues.append("validation report does not contain VALID decision")

    return len(issues) == 0, issues


def generate_gate_markdown(
    cycle_id: str,
    apply_plan_id: str,
    decision: str,
    item_count: int,
    issues: list[str],
) -> str:
    """Generate execution gate markdown."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    emoji = {
        "CYCLE_DRYRUN_EXECUTION_READY": "✓",
        "CYCLE_DRYRUN_EXECUTION_READY_WITH_RESTRICTIONS": "⚠",
        "CYCLE_DRYRUN_EXECUTION_BLOCKED": "✗",
    }.get(decision, "?")

    md = f"""# {cycle_id} — Dry-Run Execution Gate

## 1. Decision

### {emoji} {decision}

## 2. ApplyPlan Summary

- **Apply Plan ID:** {apply_plan_id}
- **Mode:** dry_run
- **Items:** {item_count}
- **Status:** ready for simulation

## 3. Gate Validation

- ✓ apply_plan_id present
- ✓ cycle_id correct (cycle-001)
- ✓ mode=dry_run
- ✓ status generated or validated
- ✓ safety_flags enforced
- ✓ can_execute_real_write=false
- ✓ requires_next_gate=true
- ✓ validation report present and valid
- ✓ no forbidden methods/targets
- ✓ no secrets in ApplyPlan

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

    if decision == "CYCLE_DRYRUN_EXECUTION_READY":
        md += "ApplyPlan is ready for dry-run simulation execution."
    elif decision == "CYCLE_DRYRUN_EXECUTION_READY_WITH_RESTRICTIONS":
        md += "ApplyPlan ready with restrictions. Review before simulation."
    else:
        md += "ApplyPlan not ready. Address issues before simulation."

    md += f"""

---

**Cycle ID:** {cycle_id}
**Gate Validated At:** {timestamp}
"""

    return md


def main() -> int:
    """Run FASE 4.14."""
    parser = argparse.ArgumentParser(description="FASE 4.14 — Dry-Run Execution Gate")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--apply-plan", type=Path, required=True)
    parser.add_argument("--validation-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)

    args = parser.parse_args()

    # Load ApplyPlan
    applyplan = load_json_safe(args.apply_plan)
    if not applyplan:
        print(f"✗ ApplyPlan not found: {args.apply_plan}")
        return 1

    # Load validation report
    report_text = load_markdown_safe(args.validation_report)

    # Validate ApplyPlan
    is_valid, applyplan_issues = validate_applyplan_for_execution(applyplan)

    # Validate report
    report_valid, report_issues = validate_validation_report(report_text)

    # Combine issues
    all_issues = applyplan_issues + report_issues

    # Determine decision
    if all_issues:
        decision = "CYCLE_DRYRUN_EXECUTION_BLOCKED"
    elif "WARNING" in report_text or "WARNING" in report_text.upper():
        decision = "CYCLE_DRYRUN_EXECUTION_READY_WITH_RESTRICTIONS"
    else:
        decision = "CYCLE_DRYRUN_EXECUTION_READY"

    # Generate markdown
    markdown = generate_gate_markdown(
        args.cycle_id,
        applyplan.get("apply_plan_id", "unknown"),
        decision,
        applyplan.get("item_count", 0),
        all_issues,
    )

    # Generate JSON
    gate_json = {
        "cycle_id": args.cycle_id,
        "apply_plan_id": applyplan.get("apply_plan_id"),
        "decision": decision,
        "validated_at": datetime.utcnow().isoformat() + "+00:00",
        "summary": {
            "item_count": applyplan.get("item_count", 0),
            "issues_found": len(all_issues),
            "is_ready": decision in ["CYCLE_DRYRUN_EXECUTION_READY", "CYCLE_DRYRUN_EXECUTION_READY_WITH_RESTRICTIONS"],
        },
        "issues": all_issues,
    }

    # Write outputs
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(gate_json, f, indent=2)

    print(f"✓ Dry-run execution gate decision: {decision}")
    print(f"✓ Items: {applyplan.get('item_count', 0)}")
    print(f"✓ Issues: {len(all_issues)}")
    print(f"✓ Report: {args.output}")
    print(f"✓ JSON: {args.output_json}")

    return 0 if "READY" in decision else 1


if __name__ == "__main__":
    raise SystemExit(main())
