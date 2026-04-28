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


def validate_apply_plan(plan: Dict) -> Tuple[bool, List[str]]:
    """Validate ApplyPlan before including in batch."""
    errors = []

    # Check required fields
    required = ["approval_id", "object_type", "object_key", "action", "method", "readiness_status"]
    for field in required:
        if not plan.get(field):
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
    payload_str = json.dumps(plan.get("staged_payload", {})).lower()
    forbidden = ["password", "token", "secret", "api_key", "ssh"]
    if any(p in payload_str for p in forbidden):
        errors.append("Payload contains forbidden patterns (secrets)")

    # Check for Eth-Trunk0 (already created in FASE 2.0)
    object_key = plan.get("object_key", "").lower()
    if object_key == "eth-trunk0":
        errors.append("Eth-Trunk0 already created in FASE 2.0, cannot include in batch")

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

        items.append({
            "apply_plan_id": plan.get("apply_plan_id"),
            "approval_id": approval_id,
            "object_key": object_key,
            "object_type": plan.get("object_type"),
        })

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
    parser.add_argument("--device", help="Device name (auto-detect if omitted)")
    parser.add_argument("--device-id", type=int, help="Device ID (auto-detect if omitted)")
    args = parser.parse_args()

    try:
        # Load all ApplyPlans
        apply_plans = []
        for plan_file in args.plans:
            plan = load_apply_plan(plan_file)
            valid, errors = validate_apply_plan(plan)
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
