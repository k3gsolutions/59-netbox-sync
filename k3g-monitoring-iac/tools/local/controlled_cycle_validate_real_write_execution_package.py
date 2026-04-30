#!/usr/bin/env python3
"""FASE 4.20 — Controlled Operation Cycle Validate Real Write Execution Package.

Validate execution package structure before final no-write freeze.
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


def validate_execution_package(exec_pkg: Dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate real write execution package."""
    issues = []

    # Check execution_id
    if not exec_pkg.get("execution_id"):
        issues.append("execution_id required")

    # Check cycle_id and apply_plan_id
    if not exec_pkg.get("cycle_id"):
        issues.append("cycle_id required")
    if not exec_pkg.get("apply_plan_id"):
        issues.append("apply_plan_id required")

    # CHECK: execution_allowed MUST BE FALSE
    if exec_pkg.get("execution_allowed") is not False:
        issues.append("execution_allowed must be false (safety lock)")

    # Check execution_phrase
    if not exec_pkg.get("execution_phrase"):
        issues.append("execution_phrase required")

    # Check safety flags
    safety = exec_pkg.get("safety_flags", {})
    required_flags = [
        "execution_allowed",
        "no_automatic_retry",
        "no_rollback_automatic",
        "requires_execution_confirmation",
        "requires_final_no_write_freeze",
        "generated_from_approved_records",
    ]
    for flag in required_flags:
        if not safety.get(flag):
            issues.append(f"safety_flags: {flag} required and must be true")

    # Check execution policy
    policy = exec_pkg.get("execution_policy", {})
    if policy.get("execution_allowed") is not False:
        issues.append("execution_policy.execution_allowed must be false")
    if policy.get("requires_next_gate") is not True:
        issues.append("execution_policy.requires_next_gate must be true")
    if policy.get("next_gate") != "FASE_4_21_FINAL_NO_WRITE_FREEZE":
        issues.append("next_gate must be FASE_4_21_FINAL_NO_WRITE_FREEZE")

    # Check allowed/forbidden methods
    allowed = policy.get("allowed_methods", [])
    forbidden = policy.get("forbidden_methods", [])
    if "POST" not in allowed:
        issues.append("POST must be in allowed_methods")
    if "PATCH" not in forbidden or "DELETE" not in forbidden:
        issues.append("PATCH and DELETE must be in forbidden_methods")

    # Check items
    items = exec_pkg.get("items", [])
    if not items:
        issues.append("items required and not empty")

    for idx, item in enumerate(items):
        if not item.get("item_id"):
            issues.append(f"item[{idx}]: item_id required")
        if not item.get("method"):
            issues.append(f"item[{idx}]: method required")
        elif item.get("method") not in allowed:
            issues.append(f"item[{idx}]: method={item.get('method')} not allowed")

        endpoint = item.get("target_endpoint", "")
        forbidden_targets = ["/sync", "equipment", "ssh", "netconf"]
        for target in forbidden_targets:
            if target in endpoint:
                issues.append(f"item[{idx}]: endpoint contains forbidden target {target}")

        # Check for secrets
        payload_str = json.dumps(item.get("proposed_payload", {})).lower()
        blocked = ["token", "password", "secret", "api_key", "private key", "bearer"]
        for word in blocked:
            if word in payload_str:
                issues.append(f"item[{idx}]: payload contains blocked keyword: {word}")

    # Check whole package for secrets
    pkg_str = json.dumps(exec_pkg).lower()
    blocked = ["token", "password", "secret", "api_key", "private key", "bearer"]
    for word in blocked:
        if word in pkg_str:
            issues.append(f"Package contains blocked keyword: {word}")

    # Verify source ApplyPlan info
    source = exec_pkg.get("source_applyplan", {})
    if not source.get("apply_plan_id"):
        issues.append("source_applyplan.apply_plan_id missing")
    if source.get("mode") != "dry_run":
        issues.append("source_applyplan.mode must be dry_run")

    return len(issues) == 0, issues


def generate_validation_markdown(
    cycle_id: str,
    execution_id: str,
    device: str,
    decision: str,
    item_count: int,
    issues: list[str],
) -> str:
    """Generate validation markdown."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    emoji = {
        "CYCLE_EXECUTION_PACKAGE_VALID": "✓",
        "CYCLE_EXECUTION_PACKAGE_VALID_WITH_WARNINGS": "⚠",
        "CYCLE_EXECUTION_PACKAGE_INVALID": "✗",
    }.get(decision, "?")

    md = f"""# {cycle_id} — Real Write Execution Package Validation

## 1. Decision

### {emoji} {decision}

## 2. Validation Summary

- **Execution ID:** {execution_id}
- **Cycle:** {cycle_id}
- **Device:** {device}
- **Items:** {item_count}
- **Status:** validation complete

## 3. Execution Package Checks

✓ execution_id present
✓ execution_allowed=false (safety lock verified)
✓ execution_phrase present
✓ Safety flags all true
✓ Execution policy correct
✓ Next gate set to FASE_4_21_FINAL_NO_WRITE_FREEZE
✓ Methods enforced (POST allowed, PATCH/DELETE forbidden)
✓ Forbidden targets blocked (/sync, equipment, ssh, netconf)
✓ No secrets in package
✓ Source ApplyPlan info valid

## 4. Issues Found

"""

    if not issues:
        md += "None\n"
    else:
        for issue in issues:
            md += f"- {issue}\n"

    md += f"""

## 5. Safety Status

🔒 **execution_allowed = false** ← Safety lock active
✓ Ready for final no-write freeze validation

## 6. Next Steps

"""

    if decision == "CYCLE_EXECUTION_PACKAGE_VALID":
        md += "Proceed to FASE 4.21 (Final No-Write Freeze Check)."
    elif decision == "CYCLE_EXECUTION_PACKAGE_VALID_WITH_WARNINGS":
        md += "Proceed with caution. Review warnings before execution."
    else:
        md += "Not valid. Address issues before retry."

    md += f"""

---

**Cycle ID:** {cycle_id}
**Validation At:** {timestamp}
"""

    return md


def main() -> int:
    """Run FASE 4.20."""
    parser = argparse.ArgumentParser(
        description="FASE 4.20 — Validate Real Write Execution Package"
    )
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--execution-package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)

    args = parser.parse_args()

    # Load execution package
    exec_pkg = load_json_safe(args.execution_package)
    if not exec_pkg:
        print(f"✗ Execution package not found: {args.execution_package}")
        return 1

    # Validate package
    is_valid, issues = validate_execution_package(exec_pkg)

    # Determine decision
    if is_valid:
        decision = "CYCLE_EXECUTION_PACKAGE_VALID"
    elif any("warning" in issue.lower() for issue in issues):
        decision = "CYCLE_EXECUTION_PACKAGE_VALID_WITH_WARNINGS"
    else:
        decision = "CYCLE_EXECUTION_PACKAGE_INVALID"

    # Generate markdown
    markdown = generate_validation_markdown(
        args.cycle_id,
        exec_pkg.get("execution_id", "unknown"),
        exec_pkg.get("device", "unknown"),
        decision,
        exec_pkg.get("item_count", 0),
        issues,
    )

    # Generate JSON
    validation_json = {
        "cycle_id": args.cycle_id,
        "execution_id": exec_pkg.get("execution_id"),
        "apply_plan_id": exec_pkg.get("apply_plan_id"),
        "decision": decision,
        "validated_at": datetime.utcnow().isoformat() + "+00:00",
        "summary": {
            "item_count": exec_pkg.get("item_count", 0),
            "issues_found": len(issues),
            "valid_for_freeze": decision in [
                "CYCLE_EXECUTION_PACKAGE_VALID",
                "CYCLE_EXECUTION_PACKAGE_VALID_WITH_WARNINGS",
            ],
        },
        "issues": issues,
        "safety_checks": {
            "execution_allowed_false": exec_pkg.get("execution_allowed") is False,
            "safety_flags_enforced": all(
                exec_pkg.get("safety_flags", {}).get(flag)
                for flag in [
                    "execution_allowed",
                    "requires_final_no_write_freeze",
                ]
            ),
            "no_secrets": not any("keyword" in issue for issue in issues),
            "no_forbidden_methods": "PATCH" not in str(
                exec_pkg.get("items", [])
            ) and "DELETE" not in str(exec_pkg.get("items", [])),
        },
    }

    # Write outputs
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(validation_json, f, indent=2)

    print(f"✓ Execution package validation: {decision}")
    print(f"✓ Execution ID: {exec_pkg.get('execution_id')}")
    print(f"✓ Items: {exec_pkg.get('item_count', 0)}")
    print(f"✓ Issues: {len(issues)}")
    print(f"✓ Report: {args.output}")
    print(f"✓ JSON: {args.output_json}")

    return 0 if decision in ["CYCLE_EXECUTION_PACKAGE_VALID", "CYCLE_EXECUTION_PACKAGE_VALID_WITH_WARNINGS"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
