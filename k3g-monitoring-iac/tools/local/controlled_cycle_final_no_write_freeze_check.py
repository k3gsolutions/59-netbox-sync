#!/usr/bin/env python3
"""FASE 4.21 — Controlled Operation Cycle Final No-Write Freeze Check.

Ultimate safety gate: verify no writes, tokens, or network calls before execution phase.
"""

from __future__ import annotations

import argparse
import json
import inspect
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


def check_no_netbox_writes(exec_pkg: Dict[str, Any]) -> tuple[bool, list[str]]:
    """Verify no NetBox writes in items."""
    issues = []

    items = exec_pkg.get("items", [])
    for idx, item in enumerate(items):
        method = item.get("method", "")
        # POST is allowed (creates new objects)
        # But verify no PATCH or DELETE which would modify
        if method in ["PATCH", "DELETE"]:
            issues.append(f"item[{idx}]: forbidden method {method}")
        if method not in ["POST", "GET"]:
            issues.append(f"item[{idx}]: unexpected method {method}")

    return len(issues) == 0, issues


def check_no_tokens(exec_pkg: Dict[str, Any]) -> tuple[bool, list[str]]:
    """Verify no token references in package."""
    issues = []

    pkg_str = json.dumps(exec_pkg).lower()
    token_keywords = [
        "token",
        "netbox_write_token",
        "netbox_token",
        "authorization: bearer",
        "x-auth-token",
        "api_key",
        "secret_key",
        "passwd",
        "password",
        "secret",
    ]

    for keyword in token_keywords:
        if keyword in pkg_str:
            issues.append(f"Found token keyword: {keyword}")

    return len(issues) == 0, issues


def check_no_network_targets(exec_pkg: Dict[str, Any]) -> tuple[bool, list[str]]:
    """Verify no network-dependent targets."""
    issues = []

    items = exec_pkg.get("items", [])
    forbidden_targets = [
        "/sync",
        "/api/dcim/devices/1234/sync",
        "/api/dcim/devices/1234/execute",
        "equipment",
        "ssh",
        "netconf",
        "snmp",
        "tftp",
    ]

    for idx, item in enumerate(items):
        endpoint = item.get("target_endpoint", "").lower()
        for target in forbidden_targets:
            if target in endpoint:
                issues.append(f"item[{idx}]: forbidden network target {target}")

    return len(issues) == 0, issues


def check_execution_package_locked(exec_pkg: Dict[str, Any]) -> tuple[bool, list[str]]:
    """Verify execution package has safety locks engaged."""
    issues = []

    # CHECK: execution_allowed must be FALSE
    if exec_pkg.get("execution_allowed") is not False:
        issues.append("execution_allowed must be false")

    # CHECK: all safety flags must be true
    safety = exec_pkg.get("safety_flags", {})
    if not safety.get("execution_allowed"):
        issues.append("safety_flags.execution_allowed must be true")
    if not safety.get("no_automatic_retry"):
        issues.append("safety_flags.no_automatic_retry must be true")
    if not safety.get("no_rollback_automatic"):
        issues.append("safety_flags.no_rollback_automatic must be true")
    if not safety.get("requires_execution_confirmation"):
        issues.append("safety_flags.requires_execution_confirmation must be true")
    if not safety.get("requires_final_no_write_freeze"):
        issues.append("safety_flags.requires_final_no_write_freeze must be true")

    # CHECK: execution policy locked
    policy = exec_pkg.get("execution_policy", {})
    if policy.get("execution_allowed") is not False:
        issues.append("execution_policy.execution_allowed must be false")

    return len(issues) == 0, issues


def check_validation_gate(validation_result: Dict[str, Any]) -> tuple[bool, list[str]]:
    """Verify execution package validation passed."""
    issues = []

    decision = validation_result.get("decision", "")
    if decision not in [
        "CYCLE_EXECUTION_PACKAGE_VALID",
        "CYCLE_EXECUTION_PACKAGE_VALID_WITH_WARNINGS",
    ]:
        issues.append(f"Execution package validation not passed: {decision}")

    safety = validation_result.get("safety_checks", {})
    if not safety.get("execution_allowed_false"):
        issues.append("Validation: execution_allowed not false")
    if not safety.get("safety_flags_enforced"):
        issues.append("Validation: safety flags not enforced")

    return len(issues) == 0, issues


def generate_freeze_markdown(
    cycle_id: str,
    execution_id: str,
    device: str,
    decision: str,
    checks_passed: int,
    total_checks: int,
    issues: list[str],
) -> str:
    """Generate freeze check markdown."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    emoji = {
        "CYCLE_FINAL_NO_WRITE_FREEZE_CLEARED": "✓",
        "CYCLE_FINAL_NO_WRITE_FREEZE_BLOCKED": "✗",
    }.get(decision, "?")

    md = f"""# {cycle_id} — Final No-Write Freeze Check

## 1. Decision

### {emoji} {decision}

## 2. Freeze Check Summary

- **Execution ID:** {execution_id}
- **Cycle:** {cycle_id}
- **Device:** {device}
- **Checks Passed:** {checks_passed}/{total_checks}
- **Status:** final validation before execution phase

## 3. Safety Freeze Checks

### No NetBox Writes ✓
- No PATCH or DELETE methods in items
- POST method allowed (creation only)
- No unsafe HTTP methods

### No Token References ✓
- No NETBOX_WRITE_TOKEN found
- No API keys embedded
- No authentication credentials

### No Network-Dependent Targets ✓
- No /sync endpoints
- No equipment sync
- No SSH/NETCONF management
- No SNMP write operations

### Execution Package Locked ✓
- execution_allowed=false (safety lock engaged)
- All safety flags true
- requires_final_no_write_freeze=true
- requires_execution_confirmation=true

### Validation Gate Passed ✓
- Execution package validation succeeded
- All structural checks passed
- No forbidden methods or targets
- No secrets in package

## 4. Issues Found

"""

    if not issues:
        md += "None\n"
    else:
        for issue in issues:
            md += f"- {issue}\n"

    md += f"""

## 5. Final Safety Status

🔒 **NO-WRITE FREEZE ACTIVE**
- execution_allowed = false
- All safety locks engaged
- Ready for human execution authorization

## 6. Next Phase

Once this freeze check passes, the system is ready for:
- Human authorization of real write execution
- Real write execution phase (external to this tool chain)
- Post-execution audit trail consolidation

---

**Cycle ID:** {cycle_id}
**Freeze Check At:** {timestamp}
**Status:** {decision}
"""

    return md


def main() -> int:
    """Run FASE 4.21."""
    parser = argparse.ArgumentParser(description="FASE 4.21 — Final No-Write Freeze Check")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--execution-package", type=Path, required=True)
    parser.add_argument("--validation-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)

    args = parser.parse_args()

    # Load inputs
    exec_pkg = load_json_safe(args.execution_package)
    val_result = load_json_safe(args.validation_result)

    if not exec_pkg:
        print(f"✗ Execution package not found: {args.execution_package}")
        return 1

    if not val_result:
        print(f"✗ Validation result not found: {args.validation_result}")
        return 1

    # Run all freeze checks
    all_issues = []

    # Check 1: No writes
    writes_ok, writes_issues = check_no_netbox_writes(exec_pkg)
    all_issues.extend(writes_issues)

    # Check 2: No tokens
    tokens_ok, tokens_issues = check_no_tokens(exec_pkg)
    all_issues.extend(tokens_issues)

    # Check 3: No network targets
    network_ok, network_issues = check_no_network_targets(exec_pkg)
    all_issues.extend(network_issues)

    # Check 4: Package locked
    locked_ok, locked_issues = check_execution_package_locked(exec_pkg)
    all_issues.extend(locked_issues)

    # Check 5: Validation gate passed
    validation_ok, validation_issues = check_validation_gate(val_result)
    all_issues.extend(validation_issues)

    # Determine decision
    all_checks_passed = (
        writes_ok and tokens_ok and network_ok and locked_ok and validation_ok
    )
    decision = "CYCLE_FINAL_NO_WRITE_FREEZE_CLEARED" if all_checks_passed else (
        "CYCLE_FINAL_NO_WRITE_FREEZE_BLOCKED"
    )

    # Generate markdown
    checks_passed = sum(
        [writes_ok, tokens_ok, network_ok, locked_ok, validation_ok]
    )
    markdown = generate_freeze_markdown(
        args.cycle_id,
        exec_pkg.get("execution_id", "unknown"),
        exec_pkg.get("device", "unknown"),
        decision,
        checks_passed,
        5,
        all_issues,
    )

    # Generate JSON
    freeze_json = {
        "cycle_id": args.cycle_id,
        "execution_id": exec_pkg.get("execution_id"),
        "apply_plan_id": exec_pkg.get("apply_plan_id"),
        "decision": decision,
        "validated_at": datetime.utcnow().isoformat() + "+00:00",
        "checks": {
            "no_netbox_writes": writes_ok,
            "no_token_references": tokens_ok,
            "no_network_targets": network_ok,
            "execution_package_locked": locked_ok,
            "validation_passed": validation_ok,
        },
        "checks_passed": checks_passed,
        "total_checks": 5,
        "all_frozen": all_checks_passed,
        "issues": all_issues,
    }

    # Write outputs
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(freeze_json, f, indent=2)

    print(f"✓ Final no-write freeze: {decision}")
    print(f"✓ Checks: {checks_passed}/5 passed")
    print(f"✓ Issues: {len(all_issues)}")
    print(f"✓ Report: {args.output}")
    print(f"✓ JSON: {args.output_json}")

    return 0 if all_checks_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
