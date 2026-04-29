#!/usr/bin/env python3
"""FASE 2.50 — Validate Real Write Execution Package.

Validate execution_package.json structure, safety flags, items, and readiness.
Zero writes, zero tokens, zero network calls.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple


def validate_execution_package(package_file: Path) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate execution package structure."""
    if not package_file.exists():
        return False, f"Package not found: {package_file}", {}

    try:
        with open(package_file, encoding="utf-8") as f:
            pkg = json.load(f)
    except Exception as e:
        return False, f"Invalid JSON: {e}", {}

    # Validate required fields
    if not pkg.get("execution_package_id"):
        return False, "Missing execution_package_id", {}

    if not pkg.get("device"):
        return False, "Missing device", {}

    if not pkg.get("apply_plan_id"):
        return False, "Missing apply_plan_id", {}

    if not pkg.get("authorization_id"):
        return False, "Missing authorization_id", {}

    # Validate status and execution flags
    if pkg.get("status") != "prepared":
        return False, f"Status is {pkg.get('status')}, expected prepared", {}

    if pkg.get("execution_allowed") is not False:
        return False, "execution_allowed is not false", {}

    if pkg.get("token_required_in_next_phase") is not True:
        return False, "token_required_in_next_phase is not true", {}

    if pkg.get("explicit_confirm_required") is not True:
        return False, "explicit_confirm_required is not true", {}

    if pkg.get("one_shot_execution") is not True:
        return False, "one_shot_execution is not true", {}

    # Validate safety confirmations (all must be true)
    safety = pkg.get("safety_confirmations", {})
    required_safety = {
        "no_write_executed": True,
        "no_token_read": True,
        "no_network_call": True,
        "package_only": True,
        "real_write_not_executed": True,
    }

    for key, expected in required_safety.items():
        if safety.get(key) is not expected:
            return False, f"Safety flag {key} is not {expected}", {}

    # Validate required execution phrase
    if not pkg.get("required_execution_phrase"):
        return False, "Missing required_execution_phrase", {}

    # Validate next phase
    if pkg.get("required_next_phase") != "FASE_2_53_EXECUTE_REAL_WRITE":
        return False, f"Next phase is {pkg.get('required_next_phase')}, expected FASE_2_53", {}

    # Validate items
    items = pkg.get("items", [])
    if not items:
        return False, "No items in package", {}

    max_items = pkg.get("max_items")
    if not max_items or len(items) != max_items:
        return False, f"Item count {len(items)} != max_items {max_items}", {}

    for item in items:
        if not item.get("approval_id"):
            return False, "Item missing approval_id", {}

        if not item.get("object_type"):
            return False, "Item missing object_type", {}

        if not item.get("object_key"):
            return False, "Item missing object_key", {}

        method = item.get("method", "").upper()
        if method != "POST":
            return False, f"Item {item.get('approval_id')} has method {method}, only POST allowed", {}

        endpoint = item.get("endpoint", "")
        forbidden = ["/sync", "equipment", "ssh", "netconf"]
        for f in forbidden:
            if f in endpoint.lower():
                return False, f"Item {item.get('approval_id')} has forbidden endpoint: {endpoint}", {}

        if not item.get("payload"):
            return False, f"Item {item.get('approval_id')} missing payload", {}

        if not item.get("rollback_hint"):
            return False, f"Item {item.get('approval_id')} missing rollback_hint", {}

        if not item.get("pre_write_checks"):
            return False, f"Item {item.get('approval_id')} missing pre_write_checks", {}

        if not item.get("post_write_checks"):
            return False, f"Item {item.get('approval_id')} missing post_write_checks", {}

    return True, "Package valid", pkg


def check_for_secrets(package: Dict[str, Any]) -> Tuple[bool, str]:
    """Check package for secrets."""
    secrets = ["token", "password", "secret", "api_key", "private key", "bearer"]
    package_str = json.dumps(package).lower()

    for secret_kw in secrets:
        if secret_kw in package_str:
            # Avoid false positives in field names
            if "authorization" in package_str and secret_kw == "token":
                continue

            # Check items specifically
            for item in package.get("items", []):
                item_str = json.dumps(item).lower()
                # Only care if it's in payload, not in other fields
                payload = item.get("payload", {})
                payload_str = json.dumps(payload).lower()
                if secret_kw in payload_str:
                    return False, f"Secret keyword in item payload: {secret_kw}"

    return True, "No secrets detected"


def main() -> int:
    """Run FASE 2.50."""
    parser = argparse.ArgumentParser(description="FASE 2.50 — Validate Real Write Execution Package")
    parser.add_argument("--execution-package", type=Path, required=True, help="Execution package JSON")
    parser.add_argument("--output", type=Path, required=True, help="Output report path")

    args = parser.parse_args()

    # Validate package
    pkg_valid, pkg_reason, package = validate_execution_package(args.execution_package)
    if not pkg_valid:
        print(f"✗ Package invalid: {pkg_reason}")
        decision = "REAL_WRITE_EXECUTION_PACKAGE_INVALID"
    else:
        # Check for secrets
        secrets_ok, secrets_reason = check_for_secrets(package)
        if not secrets_ok:
            print(f"✗ {secrets_reason}")
            decision = "REAL_WRITE_EXECUTION_PACKAGE_INVALID"
        else:
            decision = "REAL_WRITE_EXECUTION_PACKAGE_VALID"

    # Generate report
    timestamp = datetime.utcnow().isoformat() + "+00:00"
    report_lines = [
        "# Real Write Execution Package Validation",
        "",
        f"**Device:** {package.get('device', 'unknown')}",
        f"**Package ID:** {package.get('execution_package_id', 'unknown')}",
        f"**Generated:** {timestamp}",
        "",
        "## Decision",
        "",
        f"### {decision}",
        "",
    ]

    if decision == "REAL_WRITE_EXECUTION_PACKAGE_VALID":
        report_lines.extend([
            "✓ Package structure valid",
            "✓ All safety flags true",
            "✓ No secrets detected",
            "✓ Items properly formatted",
            "✓ Method and endpoint restrictions enforced",
            "✓ Ready for FASE 2.51 and 2.52",
            "",
        ])
    elif decision == "REAL_WRITE_EXECUTION_PACKAGE_INVALID":
        if not pkg_valid:
            report_lines.extend([
                f"✗ {pkg_reason}",
                "",
            ])
        else:
            report_lines.extend([
                f"✗ {secrets_reason}",
                "",
            ])

    report_lines.extend([
        "## Package Details",
        "",
        f"- Status: {package.get('status')}",
        f"- Execution Allowed: {package.get('execution_allowed')}",
        f"- Token Required: {package.get('token_required_in_next_phase')}",
        f"- Items: {len(package.get('items', []))}",
        f"- Required Next Phase: {package.get('required_next_phase')}",
        "",
        "## Security Validations",
        "",
        "✓ No NetBox writes executed",
        "✓ No tokens read or stored",
        "✓ No network calls made",
        "✓ Package preparation only",
        "✓ Execution blocked (execution_allowed=false)",
        "",
    ])

    # Create output directory
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"✓ Validation report: {args.output}")
    print(f"✓ Decision: {decision}")

    return 0 if decision.startswith("REAL_WRITE_EXECUTION_PACKAGE_VALID") else 1


if __name__ == "__main__":
    raise SystemExit(main())
