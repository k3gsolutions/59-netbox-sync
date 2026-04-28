#!/usr/bin/env python3
"""Validate BatchApplyPlan against gates (dry-run, no API)."""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def load_batch_plan(file_path: str) -> Dict:
    """Load BatchApplyPlan JSON."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ValueError(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")


def validate_batch_plan(plan: Dict) -> Tuple[bool, List[str]]:
    """Validate BatchApplyPlan against gates."""
    errors = []

    # Check required fields
    required = ["batch_id", "total_items", "max_items", "device", "device_id", "items", "readiness_status"]
    for field in required:
        if field not in plan:
            errors.append(f"Missing required field: {field}")

    if errors:
        return False, errors

    # Check batch size
    total = plan.get("total_items", 0)
    max_items = plan.get("max_items", 0)

    if total > max_items:
        errors.append(f"total_items ({total}) exceeds max_items ({max_items})")

    if total > 2:
        errors.append(f"Batch size ({total}) exceeds pilot limit of 2 items")

    if total == 0:
        errors.append("Batch has no items")

    # Check readiness_status
    readiness = plan.get("readiness_status")
    if readiness not in ("ready", "blocked"):
        errors.append(f"readiness_status must be 'ready' or 'blocked' (got: {readiness})")

    # Check items
    items = plan.get("items", [])
    approval_ids = set()
    object_keys = set()

    for i, item in enumerate(items):
        # Check required fields
        for field in ["apply_plan_id", "approval_id", "object_key", "object_type"]:
            if not item.get(field):
                errors.append(f"Item {i}: missing {field}")

        # Check object_type
        if item.get("object_type") != "interface":
            errors.append(f"Item {i}: object_type must be 'interface'")

        # Check duplicates
        approval_id = item.get("approval_id")
        object_key = item.get("object_key")

        if approval_id in approval_ids:
            errors.append(f"Item {i}: duplicate approval_id: {approval_id}")
        if object_key in object_keys:
            errors.append(f"Item {i}: duplicate object_key: {object_key}")

        approval_ids.add(approval_id)
        object_keys.add(object_key)

    # Check write policy
    write_policy = plan.get("write_policy", {})
    if write_policy.get("real_apply_enabled"):
        errors.append("write_policy.real_apply_enabled must be False")
    if write_policy.get("write_token_provided"):
        errors.append("write_policy.write_token_provided must be False")

    return len(errors) == 0, errors


def main():
    parser = argparse.ArgumentParser(description="Validate BatchApplyPlan")
    parser.add_argument("--plan", required=True, help="BatchApplyPlan JSON file")
    args = parser.parse_args()

    try:
        plan = load_batch_plan(args.plan)
        valid, errors = validate_batch_plan(plan)

        if valid:
            print("✓ BatchApplyPlan validation PASSED")
            print(f"  - batch_id: {plan['batch_id'][:8]}")
            print(f"  - total_items: {plan['total_items']}")
            print(f"  - device: {plan.get('device')}")
            print(f"  - readiness_status: {plan['readiness_status']}")
            return 0
        else:
            print("❌ BatchApplyPlan validation FAILED:")
            for error in errors:
                print(f"  - {error}")
            return 1

    except ValueError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
