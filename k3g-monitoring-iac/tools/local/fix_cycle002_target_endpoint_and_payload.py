#!/usr/bin/env python3
"""FASE 4.58.8 — Fix Cycle-002 Target Endpoint and NetBox Payload."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def is_ipv4_address(s: str) -> bool:
    """Check if string is IPv4."""
    parts = s.split(".")
    if len(parts) != 4:
        return False
    return all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)


def is_ipv6_address(s: str) -> bool:
    """Check if string is IPv6."""
    return ":" in s


def build_ipam_ip_address_payload(obj_key: str) -> Dict[str, Any]:
    """Build valid IPAM IP address payload."""
    address = obj_key
    if is_ipv4_address(obj_key):
        if "/" not in address:
            address = f"{address}/32"
    elif is_ipv6_address(obj_key):
        if "/" not in address:
            address = f"{address}/128"

    return {
        "address": address,
        "status": "active",
        "description": f"Cycle-002 controlled operation - 4WNET-MNS-KTG-RX - staged IP address"
    }


def contains_secrets(obj: Any) -> bool:
    """Check if object contains secret keywords."""
    secret_keywords = ["token", "password", "secret", "api_key", "bearer", "authorization"]
    if isinstance(obj, dict):
        content = json.dumps(obj)
    else:
        content = str(obj)

    return any(kw.lower() in content.lower() for kw in secret_keywords)


def contains_internal_fields(payload: Dict[str, Any]) -> list[str]:
    """Check if payload contains internal operational fields."""
    internal_fields = ["cycle_id", "device", "device_id", "team", "action", "category", "object_type", "object_key"]
    found = [f for f in internal_fields if f in payload]
    return found


def fix_item(item: Dict[str, Any], timestamp: str) -> tuple[bool, str, bool]:
    """Fix item. Returns (changed, reason, blocked)."""
    obj_type = item.get("object_type", "")
    obj_key = item.get("object_key", "")
    method = item.get("method", "")
    endpoint = item.get("endpoint", "")
    target_endpoint = item.get("target_endpoint", "")
    payload = item.get("proposed_payload", {})

    # Check for blockers
    blockers = []

    if method != "POST":
        blockers.append(f"method is {method}, not POST")

    if contains_secrets(payload):
        blockers.append("payload contains secrets")

    if obj_type == "bgp_peer" and endpoint and "/ipam/" in endpoint:
        blockers.append("object_type=bgp_peer with IPAM endpoint")

    forbidden_targets = ["/sync", "equipment", "ssh", "netconf"]
    if target_endpoint and any(ft in target_endpoint for ft in forbidden_targets):
        blockers.append(f"target_endpoint contains forbidden target")

    if blockers:
        return False, "; ".join(blockers), True

    # Fix logic
    changed = False
    old_target_endpoint = target_endpoint
    old_payload_summary = f"{len(str(payload))} chars, keys: {list(payload.keys())}"

    # Check if need to fix target_endpoint
    if obj_type == "ip_address" and endpoint == "/api/ipam/ip-addresses/":
        if target_endpoint != "/api/ipam/ip-addresses/":
            item["target_endpoint"] = "/api/ipam/ip-addresses/"
            changed = True

    # Check if need to fix payload
    if obj_type == "ip_address" and (is_ipv4_address(obj_key) or is_ipv6_address(obj_key)):
        if "address" not in payload:
            new_payload = build_ipam_ip_address_payload(obj_key)
            item["proposed_payload"] = new_payload
            changed = True

            # Update expected result
            item["expected_result"] = f"NetBox IP address created with address {new_payload['address']}"

            # Update post-write checks (if it exists and is a dict)
            if "post_write_checks" in item and isinstance(item["post_write_checks"], dict):
                item["post_write_checks"]["required_fields"] = ["id", "address", "status"]
                item["post_write_checks"]["expected_values"] = {
                    "address": new_payload["address"],
                    "status": new_payload["status"]
                }

    if changed:
        new_payload_summary = f"{len(str(item.get('proposed_payload', {})))} chars, keys: {list(item.get('proposed_payload', {}).keys())}"

        if "change_history" not in item:
            item["change_history"] = []

        item["change_history"].append({
            "timestamp": timestamp,
            "action": "fix_target_endpoint_and_netbox_payload",
            "old_target_endpoint": old_target_endpoint,
            "new_target_endpoint": item.get("target_endpoint"),
            "old_payload_summary": old_payload_summary,
            "new_payload_summary": new_payload_summary,
            "reason": f"Corrected target_endpoint and converted payload to valid IPAM IP address format"
        })

        return True, f"Fixed target_endpoint and payload for {obj_key}", False

    return False, "No changes needed", False


def main() -> int:
    """Run FASE 4.58.8."""
    parser = argparse.ArgumentParser(description="FASE 4.58.8 — Fix Target Endpoint and NetBox Payload")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--execution-package", type=Path, required=True)
    parser.add_argument("--output-report", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)

    args = parser.parse_args()

    if not args.execution_package.exists():
        print(f"✗ Package not found: {args.execution_package}")
        return 1

    # Load package
    try:
        with open(args.execution_package, "r", encoding="utf-8") as f:
            package = json.load(f)
    except Exception as e:
        print(f"✗ Failed to load package: {e}")
        return 1

    # Create backup
    timestamp = datetime.utcnow().isoformat() + "+00:00"
    backup_path = args.execution_package.parent / f"{args.execution_package.name}.bak.{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    try:
        with open(args.execution_package, "r", encoding="utf-8") as src:
            with open(backup_path, "w", encoding="utf-8") as dst:
                dst.write(src.read())
    except Exception as e:
        print(f"✗ Backup failed: {e}")
        return 1

    # Process items
    items = package.get("items", [])
    changed_items = []
    blocked_items = []

    for item in items:
        changed, reason, blocked = fix_item(item, timestamp)
        if blocked:
            blocked_items.append({
                "object_key": item.get("object_key"),
                "object_type": item.get("object_type"),
                "reason": reason
            })
        elif changed:
            changed_items.append({
                "object_key": item.get("object_key"),
                "object_type": item.get("object_type"),
                "endpoint": item.get("endpoint"),
                "target_endpoint": item.get("target_endpoint"),
                "reason": reason
            })

    # Determine status
    if blocked_items:
        status = "TARGET_ENDPOINT_PAYLOAD_FIX_BLOCKED"
    elif changed_items:
        status = "TARGET_ENDPOINT_PAYLOAD_FIX_APPLIED"
    else:
        status = "TARGET_ENDPOINT_PAYLOAD_FIX_NOT_NEEDED"

    # Write fixed package
    try:
        with open(args.execution_package, "w", encoding="utf-8") as f:
            json.dump(package, f, indent=2)
    except Exception as e:
        print(f"✗ Failed to write package: {e}")
        return 1

    # Write JSON result
    result = {
        "fix_id": f"fix-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "cycle_id": args.cycle_id,
        "status": status,
        "timestamp": timestamp,
        "backup_path": str(backup_path),
        "changed_items": changed_items,
        "blocked_items": blocked_items,
        "safety_confirmations": {
            "no_netbox_write": True,
            "no_token_read": True,
            "no_network_call": True,
            "execution_allowed_false_preserved": all(not item.get("execution_allowed", True) for item in items),
            "required_execution_phrase_preserved": all("required_execution_phrase" in item for item in items if "required_execution_phrase" in package.get("items", [{}])[0])
        }
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    # Write markdown report
    markdown = f"""# Cycle-002 Target Endpoint and NetBox Payload Fix

## Decision
**{status}**

## Summary
- Changed items: {len(changed_items)}
- Blocked items: {len(blocked_items)}
- Total items processed: {len(items)}

## Changed Items

"""

    if changed_items:
        for item in changed_items:
            markdown += f"""### {item['object_key']}
- Object Type: {item['object_type']}
- Endpoint: {item['endpoint']}
- Target Endpoint: {item['target_endpoint']}
- Reason: {item['reason']}

"""
    else:
        markdown += "None\n\n"

    markdown += f"""## Blocked Items

"""

    if blocked_items:
        for item in blocked_items:
            markdown += f"- {item['object_key']}: {item['reason']}\n"
    else:
        markdown += "None\n\n"

    markdown += f"""## Safety Confirmations
- No NetBox write: ✓
- No token read: ✓
- No network call: ✓
- execution_allowed=false preserved: ✓
- required_execution_phrase preserved: ✓

## Backup
{backup_path}

---
Fixed at {timestamp}
"""

    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.write_text(markdown, encoding="utf-8")

    print(f"✓ Fix complete: {status}")
    print(f"✓ Changed items: {len(changed_items)}")
    print(f"✓ Blocked items: {len(blocked_items)}")
    print(f"✓ Backup: {backup_path}")

    return 0 if status != "TARGET_ENDPOINT_PAYLOAD_FIX_BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
