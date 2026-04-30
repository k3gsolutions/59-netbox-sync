#!/usr/bin/env python3
"""FASE 4.95 — Cycle-003 Retry-001 Package Clone.

Clone execution package from parent Cycle-003 with retry-001 metadata.
"""

from __future__ import annotations

import argparse
import json
import uuid
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


def build_retry_package(
    cycle_id: str,
    parent_execution_id: str,
    source_package: Dict[str, Any],
) -> Dict[str, Any]:
    """Build retry package from source package."""
    retry_id = f"{cycle_id}-retry-001"
    new_execution_id = str(uuid.uuid4())

    # Generate new execution phrase
    device = source_package.get("device", "unknown")
    plan_id = source_package.get("plan_id", "unknown")
    new_execution_phrase = f"EXECUTAR_ESCRITA_REAL_{retry_id}_{device}_{new_execution_id[:8]}"

    # Clone and update
    retry_pkg = {
        "retry_id": retry_id,
        "retry_attempt": 1,
        "parent_cycle_id": cycle_id,
        "parent_execution_id": parent_execution_id,
        "execution_id": new_execution_id,
        "cycle_id": cycle_id,
        "device": source_package.get("device"),
        "device_id": source_package.get("device_id"),
        "plan_id": source_package.get("plan_id"),
        "created_at": datetime.utcnow().isoformat() + "+00:00",
        "status": "prepared",
        "execution_allowed": False,
        "execution_phrase": new_execution_phrase,
        "safety_flags": {
            "requires_final_no_write_freeze": True,
            "requires_execution_confirmation": True,
            "no_automatic_retry": True,
            "no_automatic_rollback": True,
        },
        "items": [],
        "required_next_phase": "FASE_4_98_CYCLE003_RETRY001_EXECUTE_REAL_WRITE_ONCE",
    }

    # Clone items, preserving critical fields
    for item in source_package.get("items", []):
        cloned_item = {
            "item_id": item.get("item_id"),
            "approval_id": item.get("approval_id"),
            "object_type": item.get("object_type"),
            "object_key": item.get("object_key"),
            "method": item.get("method"),
            "target_endpoint": item.get("target_endpoint"),
            "proposed_payload": item.get("proposed_payload", {}),
            "rollback_hint": item.get("rollback_hint"),
            "expected_result": item.get("expected_result"),
        }
        retry_pkg["items"].append(cloned_item)

    return retry_pkg


def main() -> int:
    """Run FASE 4.95."""
    parser = argparse.ArgumentParser(
        description="FASE 4.95 — Build Cycle-003 Retry-001 Package"
    )
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--parent-execution-id", required=True)
    parser.add_argument("--source-package", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)

    args = parser.parse_args()

    # Load source
    source = load_json_safe(args.source_package)
    if not source:
        print(f"✗ Source package not found: {args.source_package}")
        return 1

    # Build retry package
    retry_pkg = build_retry_package(
        args.cycle_id,
        args.parent_execution_id,
        source,
    )

    # Validate clone
    issues = []
    if retry_pkg.get("execution_allowed") is not False:
        issues.append("execution_allowed not false")
    if not retry_pkg.get("items"):
        issues.append("no items in retry package")
    for item in retry_pkg.get("items", []):
        if not item.get("target_endpoint"):
            issues.append(f"item {item.get('item_id')} missing target_endpoint")
        payload_str = json.dumps(item.get("proposed_payload", {})).lower()
        if any(kw in payload_str for kw in ["token", "password", "secret", "api_key"]):
            issues.append(f"item {item.get('item_id')} contains secret keyword")

    if issues:
        print(f"✗ Validation failed: {issues}")
        return 1

    # Write JSON
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(retry_pkg, f, indent=2)

    # Write markdown
    markdown = f"""# Cycle-{args.cycle_id} — Retry-001 Execution Package

## Package Info
- Retry ID: {retry_pkg["retry_id"]}
- Retry Attempt: {retry_pkg["retry_attempt"]}
- Parent Execution: {args.parent_execution_id}
- New Execution ID: {retry_pkg["execution_id"]}
- Status: {retry_pkg["status"]}

## Safety Flags
- Requires Final No-Write Freeze: ✓
- Requires Execution Confirmation: ✓
- No Automatic Retry: ✓
- No Automatic Rollback: ✓
- Execution Allowed: ✗ (locked: {retry_pkg["execution_allowed"]})

## Execution Phrase
```
{retry_pkg["execution_phrase"]}
```

## Items ({len(retry_pkg["items"])} total)
"""

    for item in retry_pkg.get("items", []):
        markdown += f"""
### {item["item_id"]}
- Approval: {item["approval_id"]}
- Type: {item["object_type"]}
- Key: {item["object_key"]}
- Method: {item["method"]}
- Endpoint: {item["target_endpoint"]}
"""

    markdown += f"""
## Next Phase
FASE 4.96 — Retry-001 Package Validation
"""

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(markdown, encoding="utf-8")

    print(f"✓ Retry package cloned: {retry_pkg['retry_id']}")
    print(f"✓ Items: {len(retry_pkg['items'])}")
    print(f"✓ Execution phrase: {retry_pkg['execution_phrase']}")
    print(f"✓ Result: {args.output_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
