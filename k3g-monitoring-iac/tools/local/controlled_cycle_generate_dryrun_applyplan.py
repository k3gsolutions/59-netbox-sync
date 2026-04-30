#!/usr/bin/env python3
"""FASE 4.12 — Controlled Operation Cycle Generate Dry-Run ApplyPlan.

Generate dry-run ApplyPlan from approved ApprovalRecords.
"""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def load_json_safe(file_path: Path) -> Dict[str, Any]:
    """Load JSON file safely."""
    if not file_path.exists():
        return {}

    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def validate_approved_record(record: Dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate approved ApprovalRecord."""
    issues = []

    # Check status/state
    if record.get("status") != "approved":
        issues.append(f"status={record.get('status')} must be approved")
    if record.get("state") != "approved":
        issues.append(f"state={record.get('state')} must be approved")

    # Check required fields
    if not record.get("approval_id"):
        issues.append("approval_id required")
    if not record.get("object_type"):
        issues.append("object_type required")
    if not record.get("object_id"):
        issues.append("object_id required")
    if not record.get("proposed_payload"):
        issues.append("proposed_payload required")
    if not record.get("evidence_hash"):
        issues.append("evidence_hash required")

    # Check approval decision fields
    if not record.get("approved_by"):
        issues.append("approved_by required")
    if not record.get("approved_at"):
        issues.append("approved_at required")
    if not record.get("approval_reason"):
        issues.append("approval_reason required")

    # Check state_history for approval events
    history = record.get("state_history", [])
    if not any(e.get("event") == "approved_for_cycle_dryrun_applyplan" for e in history):
        issues.append("state_history must contain approved_for_cycle_dryrun_applyplan event")

    # Check for secrets
    record_str = json.dumps(record).lower()
    blocked = ["token", "password", "secret", "api_key", "private key", "bearer", "authorization"]
    for word in blocked:
        if word in record_str:
            issues.append(f"blocked keyword: {word}")

    return len(issues) == 0, issues


def generate_applyplan_item(record: Dict[str, Any]) -> Dict[str, Any]:
    """Generate ApplyPlan item from approved record."""
    payload = record.get("proposed_payload", {})

    # Determine method and endpoint
    method = payload.get("method", "POST")
    endpoint = payload.get("endpoint", "")

    return {
        "item_id": str(uuid.uuid4())[:8],
        "approval_id": record.get("approval_id"),
        "object_type": record.get("object_type"),
        "object_key": record.get("object_id"),
        "action": payload.get("action", "create"),
        "method": method,
        "target_endpoint": endpoint,
        "proposed_payload": payload.get("payload", {}),
        "expected_result": {
            "status_code": 201 if method == "POST" else 204,
            "contains_fields": list(payload.get("payload", {}).keys()) if method == "POST" else [],
        },
        "rollback_hint": f"DELETE {endpoint}/{record.get('object_id')}" if method == "POST" else "N/A",
        "evidence_hash": record.get("evidence_hash"),
    }


def generate_applyplan(
    cycle_id: str,
    device: str,
    device_id: str,
    approved_records: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Create ApplyPlan from approved records."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"
    apply_plan_id = f"applyplan-{cycle_id}-{str(uuid.uuid4())[:8]}"

    items = [generate_applyplan_item(record) for record in approved_records]

    return {
        "apply_plan_id": apply_plan_id,
        "cycle_id": cycle_id,
        "device": device,
        "device_id": device_id,
        "mode": "dry_run",
        "status": "generated",
        "generated_at": timestamp,
        "source_approval_records": [r.get("approval_id") for r in approved_records],
        "items": items,
        "item_count": len(items),
        "safety_flags": {
            "dry_run_only": True,
            "no_netbox_write": True,
            "no_token_required": True,
            "no_apply_execution": True,
            "manual_execution_gate_required": True,
            "generated_from_approved_records": True,
        },
        "execution_policy": {
            "can_execute_real_write": False,
            "requires_next_gate": True,
            "next_gate": "FASE_4_13_CYCLE_DRYRUN_APPLYPLAN_VALIDATION",
            "max_items": 3,
            "allowed_methods": ["POST"],
            "forbidden_methods": ["PATCH", "DELETE"],
            "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
        },
    }


def generate_applyplan_markdown(
    cycle_id: str,
    device: str,
    apply_plan_id: str,
    item_count: int,
    approved_count: int,
) -> str:
    """Generate ApplyPlan generation markdown report."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    md = f"""# {cycle_id} — Dry-Run ApplyPlan Generation

## 1. Decision

### ✓ CYCLE_DRYRUN_APPLYPLAN_GENERATED

## 2. ApplyPlan Summary

- **Apply Plan ID:** {apply_plan_id}
- **Mode:** dry_run
- **Cycle:** {cycle_id}
- **Device:** {device}
- **Items:** {item_count}
- **Source Records:** {approved_count} approved ApprovalRecords

## 3. Safety Flags

- ✓ dry_run_only=true
- ✓ no_netbox_write=true
- ✓ no_token_required=true
- ✓ no_apply_execution=true
- ✓ manual_execution_gate_required=true
- ✓ generated_from_approved_records=true

## 4. Execution Policy

- ✓ can_execute_real_write=false
- ✓ requires_next_gate=true
- ✓ Next gate: FASE_4_13 (Validation)
- ✓ Max items: 3
- ✓ Allowed methods: [POST]
- ✓ Forbidden methods: [PATCH, DELETE]
- ✓ Forbidden targets: [/sync, equipment, ssh, netconf]

## 5. Next Steps

1. Validate ApplyPlan structure (FASE 4.13)
2. Review validation results
3. Approve for simulation (FASE 4.14 pending)

---

**Apply Plan ID:** {apply_plan_id}
**Generated At:** {timestamp}
"""

    return md


def main() -> int:
    """Run FASE 4.12."""
    parser = argparse.ArgumentParser(description="FASE 4.12 — Generate Dry-Run ApplyPlan")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--approved-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)

    args = parser.parse_args()

    # Load approved records
    approved_records = []
    invalid_records = []

    if args.approved_dir.exists():
        for record_file in args.approved_dir.glob("*.json"):
            record = load_json_safe(record_file)

            is_valid, issues = validate_approved_record(record)
            if is_valid:
                approved_records.append(record)
            else:
                invalid_records.append({
                    "file": record_file.name,
                    "approval_id": record.get("approval_id"),
                    "issues": issues,
                })

    # Check preconditions
    if len(approved_records) == 0:
        print("✗ No approved records found")
        print(f"✗ Invalid records: {len(invalid_records)}")
        if invalid_records:
            for inv in invalid_records:
                print(f"  - {inv['approval_id']}: {inv['issues']}")
        return 1

    if len(approved_records) > 3:
        print(f"✗ Too many approved records: {len(approved_records)} (max 3)")
        return 1

    # Generate ApplyPlan
    applyplan = generate_applyplan(
        args.cycle_id,
        args.device,
        args.device_id,
        approved_records,
    )

    # Write ApplyPlan
    args.output_dir.mkdir(parents=True, exist_ok=True)
    applyplan_file = args.output_dir / f"{applyplan['apply_plan_id']}.json"
    with open(applyplan_file, "w", encoding="utf-8") as f:
        json.dump(applyplan, f, indent=2)

    # Generate report
    markdown = generate_applyplan_markdown(
        args.cycle_id,
        args.device,
        applyplan["apply_plan_id"],
        applyplan["item_count"],
        len(approved_records),
    )

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(markdown, encoding="utf-8")

    print(f"✓ Dry-run ApplyPlan generated: {applyplan['apply_plan_id']}")
    print(f"✓ Items: {applyplan['item_count']}")
    print(f"✓ Location: {applyplan_file}")
    print(f"✓ Report: {args.report}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
