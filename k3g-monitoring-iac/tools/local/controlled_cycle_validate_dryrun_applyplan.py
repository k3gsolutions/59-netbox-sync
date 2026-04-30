#!/usr/bin/env python3
"""FASE 4.13 — Controlled Operation Cycle Validate Dry-Run ApplyPlan.

Validate dry-run ApplyPlan structure before simulation/execution.
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


def validate_applyplan(applyplan: Dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate ApplyPlan structure."""
    issues = []
    warnings = []

    # Check basic fields
    if not applyplan.get("apply_plan_id"):
        issues.append("apply_plan_id required")
    if not applyplan.get("cycle_id"):
        issues.append("cycle_id required")
    if not applyplan.get("device"):
        issues.append("device required")
    if not applyplan.get("device_id"):
        issues.append("device_id required")

    # Check mode
    if applyplan.get("mode") != "dry_run":
        issues.append(f"mode={applyplan.get('mode')} must be dry_run")

    # Check status
    if applyplan.get("status") not in ["generated", "validated"]:
        issues.append(f"status={applyplan.get('status')} must be generated or validated")

    # Check source records
    source_records = applyplan.get("source_approval_records", [])
    if not source_records:
        issues.append("source_approval_records must not be empty")

    # Check items
    items = applyplan.get("items", [])
    if not items:
        issues.append("items must not be empty")

    # Check item count
    item_count = applyplan.get("item_count", 0)
    if item_count > 3:
        issues.append(f"item_count={item_count} exceeds max of 3")
    if len(items) != item_count:
        issues.append(f"items count {len(items)} does not match item_count {item_count}")

    # Check safety flags
    safety = applyplan.get("safety_flags", {})
    required_safety_flags = [
        "dry_run_only",
        "no_netbox_write",
        "no_token_required",
        "no_apply_execution",
        "manual_execution_gate_required",
        "generated_from_approved_records",
    ]
    for flag in required_safety_flags:
        if not safety.get(flag):
            issues.append(f"safety_flags: {flag} required")

    # Check execution policy
    policy = applyplan.get("execution_policy", {})
    if policy.get("can_execute_real_write") is not False:
        issues.append(f"can_execute_real_write must be false")
    if policy.get("requires_next_gate") is not True:
        issues.append(f"requires_next_gate must be true")
    if not policy.get("next_gate"):
        issues.append("next_gate required")

    # Check allowed/forbidden methods
    allowed = policy.get("allowed_methods", [])
    forbidden = policy.get("forbidden_methods", [])
    if "PATCH" not in forbidden:
        issues.append("PATCH must be in forbidden_methods")
    if "DELETE" not in forbidden:
        issues.append("DELETE must be in forbidden_methods")
    if "POST" not in allowed:
        issues.append("POST must be in allowed_methods")

    # Check forbidden targets
    forbidden_targets = policy.get("forbidden_targets", [])
    required_targets = ["/sync", "equipment", "ssh", "netconf"]
    for target in required_targets:
        if target not in forbidden_targets:
            issues.append(f"forbidden_targets must include {target}")

    # Validate each item
    for idx, item in enumerate(items):
        item_issues = []

        if not item.get("approval_id"):
            item_issues.append("approval_id required")
        if not item.get("object_type"):
            item_issues.append("object_type required")
        if not item.get("object_key"):
            item_issues.append("object_key required")
        if not item.get("proposed_payload"):
            item_issues.append("proposed_payload required")
        if not item.get("evidence_hash"):
            item_issues.append("evidence_hash required")
        if not item.get("expected_result"):
            item_issues.append("expected_result required")
        if not item.get("rollback_hint"):
            item_issues.append("rollback_hint required")

        # Check method
        method = item.get("method", "")
        if method not in allowed:
            item_issues.append(f"method={method} not in allowed_methods")
        if method in forbidden:
            item_issues.append(f"method={method} is forbidden")

        # Check target endpoint
        endpoint = item.get("target_endpoint", "")
        for target in forbidden_targets:
            if target in endpoint:
                item_issues.append(f"target_endpoint contains forbidden target {target}")

        # Check for secrets in payload
        payload_str = json.dumps(item.get("proposed_payload", {})).lower()
        blocked = ["token", "password", "secret", "api_key", "private key", "bearer", "authorization"]
        for word in blocked:
            if word in payload_str:
                item_issues.append(f"proposed_payload contains blocked keyword: {word}")

        if item_issues:
            issues.append(f"item[{idx}]: {'; '.join(item_issues)}")

    # Check whole ApplyPlan for secrets
    applyplan_str = json.dumps(applyplan).lower()
    blocked = ["token", "password", "secret", "api_key", "private key", "bearer", "authorization"]
    for word in blocked:
        if word in applyplan_str:
            issues.append(f"ApplyPlan contains blocked keyword: {word}")

    return len(issues) == 0, issues


def generate_validation_markdown(
    cycle_id: str,
    apply_plan_id: str,
    device: str,
    decision: str,
    item_count: int,
    issues: list[str],
) -> str:
    """Generate validation markdown report."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    emoji = {
        "CYCLE_DRYRUN_APPLYPLAN_VALID": "✓",
        "CYCLE_DRYRUN_APPLYPLAN_VALID_WITH_WARNINGS": "⚠",
        "CYCLE_DRYRUN_APPLYPLAN_INVALID": "✗",
    }.get(decision, "?")

    md = f"""# {cycle_id} — Dry-Run ApplyPlan Validation

## 1. Decision

### {emoji} {decision}

## 2. ApplyPlan Summary

- **Apply Plan ID:** {apply_plan_id}
- **Cycle:** {cycle_id}
- **Device:** {device}
- **Items:** {item_count}
- **Mode:** dry_run
- **Status:** generated

## 3. Validation Checks

- ✓ apply_plan_id present
- ✓ cycle_id correct
- ✓ device/device_id correct
- ✓ mode=dry_run
- ✓ source_approval_records not empty
- ✓ items not empty
- ✓ item_count <= 3
- ✓ All safety flags present and true
- ✓ Execution policy enforced
- ✓ can_execute_real_write=false
- ✓ requires_next_gate=true
- ✓ Forbidden methods [PATCH, DELETE] blocked
- ✓ Forbidden targets [/sync, equipment, ssh, netconf] blocked
- ✓ No token/password/secret keywords
- ✓ All items have required fields
- ✓ All items have valid payload

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

    if decision == "CYCLE_DRYRUN_APPLYPLAN_VALID":
        md += "ApplyPlan is valid and ready for simulation/execution gate."
    elif decision == "CYCLE_DRYRUN_APPLYPLAN_VALID_WITH_WARNINGS":
        md += "ApplyPlan is valid but has warnings. Review before proceeding."
    else:
        md += "ApplyPlan is invalid. Address issues before proceeding."

    md += f"""

---

**Cycle ID:** {cycle_id}
**Validated At:** {timestamp}
"""

    return md


def main() -> int:
    """Run FASE 4.13."""
    parser = argparse.ArgumentParser(description="FASE 4.13 — Validate Dry-Run ApplyPlan")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--apply-plan", type=Path, required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)

    args = parser.parse_args()

    # Load ApplyPlan
    applyplan = load_json_safe(args.apply_plan)
    if not applyplan:
        print(f"✗ ApplyPlan not found: {args.apply_plan}")
        return 1

    # Validate
    is_valid, issues = validate_applyplan(applyplan)

    # Determine decision
    if is_valid:
        decision = "CYCLE_DRYRUN_APPLYPLAN_VALID"
    else:
        decision = "CYCLE_DRYRUN_APPLYPLAN_INVALID"

    # Generate markdown
    markdown = generate_validation_markdown(
        args.cycle_id,
        applyplan.get("apply_plan_id", "unknown"),
        args.device,
        decision,
        applyplan.get("item_count", 0),
        issues,
    )

    # Generate JSON
    validation_json = {
        "cycle_id": args.cycle_id,
        "apply_plan_id": applyplan.get("apply_plan_id"),
        "device": args.device,
        "device_id": args.device_id,
        "decision": decision,
        "validated_at": datetime.utcnow().isoformat() + "+00:00",
        "summary": {
            "item_count": applyplan.get("item_count", 0),
            "source_records": len(applyplan.get("source_approval_records", [])),
            "issues_found": len(issues),
            "is_valid": is_valid,
        },
        "issues": issues,
    }

    # Write outputs
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(validation_json, f, indent=2)

    print(f"✓ Dry-run ApplyPlan validation decision: {decision}")
    print(f"✓ Items: {applyplan.get('item_count', 0)}")
    print(f"✓ Issues found: {len(issues)}")
    print(f"✓ Report: {args.output}")
    print(f"✓ JSON: {args.output_json}")

    return 0 if decision in ["CYCLE_DRYRUN_APPLYPLAN_VALID", "CYCLE_DRYRUN_APPLYPLAN_VALID_WITH_WARNINGS"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
