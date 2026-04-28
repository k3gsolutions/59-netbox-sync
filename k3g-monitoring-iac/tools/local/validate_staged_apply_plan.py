#!/usr/bin/env python3
"""Validate ApplyPlan (dry-run, no writes)."""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def load_apply_plan(file_path: str) -> Dict:
    """Load ApplyPlan JSON."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ValueError(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")


def validate_apply_plan(plan: Dict) -> Tuple[bool, List[str], List[str]]:
    """Validate ApplyPlan against requirements."""
    errors = []
    warnings = []

    # Required fields
    required = [
        "apply_plan_id",
        "approval_id",
        "device",
        "device_id",
        "object_type",
        "object_key",
        "action",
        "target_endpoint",
        "method",
        "staged_payload",
        "payload_hash",
        "readiness_status",
        "readiness_checks",
        "blocked_reasons",
        "write_policy",
    ]

    for field in required:
        if field not in plan:
            errors.append(f"Missing required field: {field}")

    # Validate write policy
    wp = plan.get("write_policy", {})
    if wp.get("real_apply_enabled") != False:
        errors.append("real_apply_enabled must be False")
    if wp.get("write_token_provided") != False:
        errors.append("write_token_provided must be False")

    # Validate action
    if plan.get("action") != "safe_create_staged":
        errors.append("action must be safe_create_staged")

    # Validate method
    if plan.get("method") != "POST":
        errors.append("method must be POST (no PATCH/DELETE)")

    # Validate object_type
    if plan.get("object_type") not in ("interface",):
        errors.append("object_type not supported in FASE 1.9")

    # Validate readiness_status
    valid_status = ("ready", "blocked", "simulated")
    if plan.get("readiness_status") not in valid_status:
        errors.append(f"readiness_status must be one of: {', '.join(valid_status)}")

    # Validate readiness_checks
    checks = plan.get("readiness_checks", [])
    if not checks:
        errors.append("readiness_checks cannot be empty")

    passed_count = sum(1 for c in checks if c.get("result") == "PASSED")
    failed_count = sum(1 for c in checks if c.get("result") == "FAILED")
    warning_count = sum(1 for c in checks if c.get("result") == "WARNING")

    # Check for required pass checks
    critical_checks = {
        "approval_id_present": False,
        "status_dry_run_passed": False,
        "action_safe_create_staged": False,
        "object_type_supported": False,
        "no_secrets_in_payload": False,
        "tags_staged_present": False,
        "tags_approval_present": False,
        "custom_fields_valid": False,
        "confidence_valid": False,
        "naming_follows_pattern": False,
        "write_policy_enforced": False,
        "write_token_not_provided": False,
    }

    for check in checks:
        check_name = check.get("check")
        result = check.get("result")
        severity = check.get("severity")

        if check_name in critical_checks:
            if result == "PASSED":
                critical_checks[check_name] = True
            elif result == "FAILED" and severity == "CRITICAL":
                errors.append(f"Critical check failed: {check_name}")

    # Validate blocked_reasons
    blocked = plan.get("blocked_reasons", [])
    if blocked:
        warnings.append(f"Plan is blocked: {', '.join(blocked)}")

    # Validate payload has no secrets
    payload = json.dumps(plan.get("staged_payload", {}))
    forbidden = ["password", "token", "secret", "api_key", "ssh"]
    if any(p in payload.lower() for p in forbidden):
        errors.append("Forbidden pattern detected in staged_payload")

    # Check if validation passed
    is_valid = len(errors) == 0

    return is_valid, errors, warnings


def main():
    parser = argparse.ArgumentParser(
        description="Validate ApplyPlan (dry-run, no writes)"
    )
    parser.add_argument("--plan", required=True, help="ApplyPlan JSON file")
    args = parser.parse_args()

    try:
        plan = load_apply_plan(args.plan)
        is_valid, errors, warnings = validate_apply_plan(plan)

        print(f"Validating ApplyPlan: {plan.get('apply_plan_id', 'unknown')}")
        print()

        if errors:
            print("❌ Validation FAILED:")
            for error in errors:
                print(f"  - {error}")
            print()
            return 1

        if warnings:
            print("⚠️  Warnings:")
            for warning in warnings:
                print(f"  - {warning}")
            print()

        print("✓ ApplyPlan is valid")
        print(f"  readiness_status: {plan.get('readiness_status')}")
        print(f"  checks: {len(plan.get('readiness_checks', []))} total")
        passed = sum(1 for c in plan.get('readiness_checks', []) if c.get('result') == 'PASSED')
        print(f"  passed: {passed}")
        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
