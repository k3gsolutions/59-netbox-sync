#!/usr/bin/env python3
"""Validate BatchApplyPlan against gates (dry-run, no API)."""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def load_batch_plan(file_path: str) -> Dict:
    """Load BatchApplyPlan JSON."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ValueError(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")


def validate_batch_plan(
    plan: Dict,
    expected_device: Optional[str],
    expected_device_id: Optional[int],
    allowed_object_keys: Optional[List[str]],
) -> Tuple[bool, List[str]]:
    """Validate BatchApplyPlan against gates."""
    errors = []

    # Check required fields
    required = [
        "batch_id",
        "total_items",
        "max_items",
        "device",
        "device_id",
        "items",
        "readiness_status",
    ]
    for field in required:
        if field not in plan:
            errors.append(f"Missing required field: {field}")

    if errors:
        return False, errors

    # Check expected device identity
    if expected_device and plan.get("device") != expected_device:
        errors.append(
            f"Batch device mismatch: expected {expected_device}, got {plan.get('device')}"
        )

    if expected_device_id is not None and plan.get("device_id") != expected_device_id:
        errors.append(
            f"Batch device_id mismatch: expected {expected_device_id}, got {plan.get('device_id')}"
        )

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
        # Check required fields (CRITICAL)
        for field in ["apply_plan_id", "approval_id", "object_key", "object_type", "device", "device_id",
                     "method", "target_endpoint", "staged_payload", "action", "category"]:
            if item.get(field) is None:
                errors.append(f"Item {i}: CRITICAL missing field '{field}'")

        # Check object_type
        if item.get("object_type") != "interface":
            errors.append(f"Item {i}: object_type must be 'interface'")

        # Check method and endpoint
        if item.get("method") != "POST":
            errors.append(f"Item {i}: method must be 'POST' (got: {item.get('method')})")
        if item.get("target_endpoint") != "/api/dcim/interfaces/":
            errors.append(f"Item {i}: target_endpoint must be '/api/dcim/interfaces/' (got: {item.get('target_endpoint')})")

        # Check action and category
        if item.get("action") != "safe_create_staged":
            errors.append(f"Item {i}: action must be 'safe_create_staged'")
        if item.get("category") != "base_inventory":
            errors.append(f"Item {i}: category must be 'base_inventory'")

        # Check duplicates
        approval_id = item.get("approval_id")
        object_key = item.get("object_key")

        if approval_id in approval_ids:
            errors.append(f"Item {i}: duplicate approval_id: {approval_id}")
        if object_key in object_keys:
            errors.append(f"Item {i}: duplicate object_key: {object_key}")

        approval_ids.add(approval_id)
        object_keys.add(object_key)

        # Check batch/device consistency per item
        if item.get("device") != plan.get("device"):
            errors.append(
                f"Item {i}: device mismatch: {item.get('device')} vs batch device {plan.get('device')}"
            )
        if item.get("device_id") != plan.get("device_id"):
            errors.append(
                f"Item {i}: device_id mismatch: {item.get('device_id')} vs batch device_id {plan.get('device_id')}"
            )

        # Allowed object keys
        if allowed_object_keys and item.get("object_key") not in allowed_object_keys:
            errors.append(
                f"Item {i}: object_key not in allowlist: {item.get('object_key')}"
            )

        staged_payload = item.get("staged_payload", {})
        if staged_payload:
            if staged_payload.get("device") != item.get("device_id"):
                errors.append(
                    f"Item {i}: staged_payload.device mismatch: {staged_payload.get('device')} vs item.device_id {item.get('device_id')}"
                )
            if staged_payload.get("name") != item.get("object_key"):
                errors.append(
                    f"Item {i}: staged_payload.name mismatch: {staged_payload.get('name')} vs object_key {item.get('object_key')}"
                )

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
    parser.add_argument("--expected-device", required=True, help="Expected device name for the batch")
    parser.add_argument("--expected-device-id", required=True, type=int, help="Expected device ID for the batch")
    parser.add_argument(
        "--allowed-object-keys",
        nargs="+",
        required=True,
        help="Explicit allowlist of object_key values permitted in this batch",
    )
    args = parser.parse_args()

    try:
        plan = load_batch_plan(args.plan)
        valid, errors = validate_batch_plan(
            plan,
            expected_device=args.expected_device,
            expected_device_id=args.expected_device_id,
            allowed_object_keys=args.allowed_object_keys,
        )

        if valid:
            print("✓ BatchApplyPlan validation PASSED")
            print(f"  - batch_id: {plan['batch_id'][:8]}")
            print(f"  - total_items: {plan['total_items']}")
            print(f"  - device: {plan.get('device')}")
            print(f"  - device_id: {plan.get('device_id')}")
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
