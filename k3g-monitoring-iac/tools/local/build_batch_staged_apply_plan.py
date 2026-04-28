#!/usr/bin/env python3
"""Build BatchApplyPlan from multiple ApplyPlan JSONs (dry-run, no API)."""

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def load_apply_plan(file_path: str) -> Dict:
    """Load ApplyPlan JSON."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ValueError(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {file_path}: {e}")


def validate_apply_plan(
    plan: Dict,
    expected_device: Optional[str],
    expected_device_id: Optional[int],
    allowed_object_keys: Optional[List[str]],
) -> Tuple[bool, List[str]]:
    """Validate ApplyPlan before including in batch."""
    errors = []

    # Check required fields
    required = [
        "approval_id",
        "object_type",
        "object_key",
        "action",
        "method",
        "readiness_status",
        "device",
        "device_id",
        "staged_payload",
    ]
    for field in required:
        if not plan.get(field) and plan.get(field) != 0:
            errors.append(f"Missing required field: {field}")

    # Check values
    if plan.get("object_type") != "interface":
        errors.append(f"object_type must be 'interface' (got: {plan.get('object_type')})")

    if plan.get("action") != "safe_create_staged":
        errors.append(f"action must be 'safe_create_staged' (got: {plan.get('action')})")

    if plan.get("method") != "POST":
        errors.append(f"method must be 'POST' (got: {plan.get('method')})")

    if plan.get("readiness_status") != "ready":
        errors.append(f"readiness_status must be 'ready' (got: {plan.get('readiness_status')})")

    # Check for blocked reasons
    if plan.get("blocked_reasons"):
        errors.append(f"ApplyPlan has blocked_reasons: {', '.join(plan.get('blocked_reasons'))}")

    # Check payload for secrets
    payload = plan.get("staged_payload", {})
    payload_str = json.dumps(payload).lower()
    forbidden = ["password", "token", "secret", "api_key", "ssh"]
    if any(p in payload_str for p in forbidden):
        errors.append("Payload contains forbidden patterns (secrets)")

    # Check for Eth-Trunk0 (already created in FASE 2.0)
    object_key = plan.get("object_key", "").lower()
    if object_key == "eth-trunk0":
        errors.append("Eth-Trunk0 already created in FASE 2.0, cannot include in batch")

    # Device consistency checks
    if expected_device and plan.get("device") != expected_device:
        errors.append(
            f"Plan device mismatch: expected {expected_device}, got {plan.get('device')}"
        )

    if expected_device_id is not None and plan.get("device_id") != expected_device_id:
        errors.append(
            f"Plan device_id mismatch: expected {expected_device_id}, got {plan.get('device_id')}"
        )

    if payload.get("device") != plan.get("device_id"):
        errors.append(
            f"Payload.device mismatch: staged_payload.device={payload.get('device')} vs plan.device_id={plan.get('device_id')}"
        )

    if payload.get("name") != plan.get("object_key"):
        errors.append(
            f"Payload.name mismatch: staged_payload.name={payload.get('name')} vs object_key={plan.get('object_key')}"
        )

    if allowed_object_keys and plan.get("object_key") not in allowed_object_keys:
        errors.append(
            f"Object key not allowed: {plan.get('object_key')}"
        )

    return len(errors) == 0, errors


def build_batch_apply_plan(
    apply_plans: List[Dict],
    max_items: int = 3,
    device: Optional[str] = None,
    device_id: Optional[int] = None,
) -> Dict:
    """Build BatchApplyPlan from ApplyPlan items."""
    batch_id = str(uuid.uuid4())

    # Extract device info from first item if not provided
    if not device and apply_plans:
        device = apply_plans[0].get("device")
    if not device_id and apply_plans:
        device_id = apply_plans[0].get("device_id")

    # Build items list
    items = []
    approval_ids = set()
    object_keys = set()

    for plan in apply_plans:
        approval_id = plan.get("approval_id")
        object_key = plan.get("object_key")

        # Check for duplicates
        if approval_id in approval_ids:
            raise ValueError(f"Duplicate approval_id: {approval_id}")
        if object_key in object_keys:
            raise ValueError(f"Duplicate object_key: {object_key}")

        approval_ids.add(approval_id)
        object_keys.add(object_key)

        # Embed complete ApplyPlan data in batch item
        item = {
            "apply_plan_id": plan.get("apply_plan_id"),
            "approval_id": approval_id,
            "object_key": object_key,
            "object_type": plan.get("object_type"),
            "action": plan.get("action"),
            "category": plan.get("category"),
            "device": plan.get("device"),
            "device_id": plan.get("device_id"),
            "method": plan.get("method"),
            "target_endpoint": plan.get("target_endpoint"),
            "staged_payload": plan.get("staged_payload", {}),
            "payload_hash": plan.get("payload_hash"),
            "readiness_status": plan.get("readiness_status"),
        }

        # Validate no null critical fields
        critical = ["device_id", "method", "target_endpoint", "staged_payload"]
        for field in critical:
            if item.get(field) is None:
                raise ValueError(f"ApplyPlan missing critical field '{field}': {object_key}")

        # Validate payload has device and name
        payload = item.get("staged_payload", {})
        if payload.get("device") is None:
            raise ValueError(f"Payload missing 'device' field: {object_key}")
        if payload.get("name") is None:
            raise ValueError(f"Payload missing 'name' field: {object_key}")

        # Validate payload.device matches batch.device_id
        if payload.get("device") != device_id:
            raise ValueError(
                f"Payload device mismatch: {object_key} has device={payload.get('device')}, "
                f"batch expects device_id={device_id}"
            )

        # Validate payload.name matches object_key
        if payload.get("name") != object_key:
            raise ValueError(
                f"Payload name mismatch: {object_key} has payload.name='{payload.get('name')}', "
                f"expected name='{object_key}'"
            )

        items.append(item)

    # Check total items
    if len(items) > max_items:
        raise ValueError(f"Total items ({len(items)}) exceeds max_items ({max_items})")

    return {
        "batch_id": batch_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "max_items": max_items,
        "total_items": len(items),
        "device": device,
        "device_id": device_id,
        "items": items,
        "readiness_status": "ready" if items else "blocked",
        "blocked_reasons": [] if items else ["No items in batch"],
        "write_policy": {
            "real_apply_enabled": False,
            "write_token_provided": False,
            "max_items": max_items,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Build BatchApplyPlan from multiple ApplyPlans")
    parser.add_argument(
        "--plans",
        nargs="+",
        required=True,
        help="ApplyPlan JSON files to include",
    )
    parser.add_argument("--output", required=True, help="Output file for BatchApplyPlan")
    parser.add_argument("--max-items", type=int, default=3, help="Maximum items in batch")
    parser.add_argument("--device", required=True, help="Expected device name for the batch")
    parser.add_argument("--device-id", required=True, type=int, help="Expected device ID for the batch")
    parser.add_argument(
        "--allowed-object-keys",
        nargs="+",
        required=True,
        help="Explicit allowlist of object_key values permitted in this batch",
    )
    args = parser.parse_args()

    try:
        # Load all ApplyPlans
        apply_plans = []
        for plan_file in args.plans:
            plan = load_apply_plan(plan_file)
            valid, errors = validate_apply_plan(
                plan,
                expected_device=args.device,
                expected_device_id=args.device_id,
                allowed_object_keys=args.allowed_object_keys,
            )
            if not valid:
                print(f"❌ Validation failed for {plan_file}:")
                for error in errors:
                    print(f"  - {error}")
                return 1
            apply_plans.append(plan)
            print(f"✓ Loaded and validated: {plan_file}")

        print("")

        # Build BatchApplyPlan
        batch_plan = build_batch_apply_plan(
            apply_plans,
            max_items=args.max_items,
            device=args.device,
            device_id=args.device_id,
        )

        # Save BatchApplyPlan
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(batch_plan, f, indent=2)

        print(f"✓ BatchApplyPlan created: {output_path}")
        print(f"  - batch_id: {batch_plan['batch_id'][:8]}")
        print(f"  - total_items: {batch_plan['total_items']}")
        print(f"  - device: {batch_plan.get('device')}")
        print(f"  - readiness_status: {batch_plan['readiness_status']}")
        print("")

        return 0

    except ValueError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
