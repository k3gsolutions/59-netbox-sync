#!/usr/bin/env python3
"""FASE 2.42 — Generate Dry-Run ApplyPlan."""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple


def parse_readiness_gate(gate_file: Path) -> Tuple[str, str]:
    """Parse readiness gate decision."""
    if not gate_file.exists():
        return "UNKNOWN", "Gate file not found"
    
    content = gate_file.read_text(encoding="utf-8")
    if "READY_FOR_DRYRUN_APPLYPLAN" in content:
        return "READY_FOR_DRYRUN_APPLYPLAN", "Gate passed"
    elif "READY_WITH_RESTRICTIONS" in content:
        return "READY_WITH_RESTRICTIONS", "Gate passed with warnings"
    elif "NOT_READY_FOR_DRYRUN_APPLYPLAN" in content:
        return "NOT_READY_FOR_DRYRUN_APPLYPLAN", "Gate blocked"
    else:
        return "UNKNOWN", "Cannot parse gate"


def check_approved_record(record: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate approved record for ApplyPlan."""
    if record.get("status") != "approved":
        return False, f"Status {record.get('status')}"
    
    if not record.get("approved_by"):
        return False, "No approved_by"
    
    if not record.get("proposed_payload"):
        return False, "No payload"
    
    if not record.get("evidence_hash"):
        return False, "No hash"
    
    state_history = record.get("state_history", [])
    states = [s.get("to", "").lower() for s in state_history if isinstance(s, dict)]
    if "approved_for_dry_run_applyplan" not in states:
        return False, "Missing approved_for_dry_run_applyplan (BLOCKER)"
    
    payload_str = json.dumps(record.get("proposed_payload", {})).lower()
    secrets = ["token", "password", "secret", "api_key", "private key", "bearer", "authorization"]
    if any(s in payload_str for s in secrets):
        return False, "Secrets in payload"
    
    return True, ""


def create_applyplan_item(record: Dict[str, Any]) -> Dict[str, Any]:
    """Create ApplyPlan item from approved record."""
    return {
        "item_id": str(uuid.uuid4()),
        "approval_id": record.get("approval_record_id", "?"),
        "object_type": record.get("object_type", "?"),
        "object_key": record.get("object_key", "?"),
        "action": record.get("action", "POST"),
        "target_endpoint": "/api/dcim/interfaces/",
        "method": "POST",
        "proposed_payload": record.get("proposed_payload", {}),
        "preflight_checks": ["object_key_unique", "tenant_exists", "interface_type_valid"],
        "expected_result": "201 Created",
        "rollback_hint": "DELETE to remove if created",
        "evidence_hash": record.get("evidence_hash", "?"),
    }


def main() -> int:
    """Generate dry-run ApplyPlan."""
    parser = argparse.ArgumentParser(description="FASE 2.42 — Generate Dry-Run ApplyPlan")
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True, type=int)
    parser.add_argument("--approved-dir", type=Path, required=True)
    parser.add_argument("--readiness-gate", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)

    args = parser.parse_args()

    gate_status, gate_reason = parse_readiness_gate(args.readiness_gate)
    if gate_status == "NOT_READY_FOR_DRYRUN_APPLYPLAN":
        report = f"# ApplyPlan Generation — {args.device}\n\nBLOCKED: {gate_reason}\n\n✓ No ApplyPlan created\n"
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report, encoding="utf-8")
        print(f"✗ Blocked: {gate_reason}")
        return 1

    included_items = []
    excluded_items = []

    if args.approved_dir.exists():
        for record_file in args.approved_dir.glob("approval-record-*.json"):
            try:
                with open(record_file, encoding="utf-8") as f:
                    record = json.load(f)
            except Exception:
                continue

            valid, reason = check_approved_record(record)
            if valid:
                item = create_applyplan_item(record)
                included_items.append(item)
            else:
                excluded_items.append({
                    "approval_id": record.get("approval_record_id", "?"),
                    "reason": reason,
                })

    if not included_items:
        report = f"# ApplyPlan Generation — {args.device}\n\nBLOCKED: No valid records\n\n✓ No ApplyPlan created\n"
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report, encoding="utf-8")
        print("✗ No valid records")
        return 1

    apply_plan_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    apply_plan = {
        "apply_plan_id": apply_plan_id,
        "device": args.device,
        "device_id": args.device_id,
        "mode": "dry_run",
        "status": "generated",
        "generated_at": timestamp,
        "source_approval_records": [item["approval_id"] for item in included_items],
        "source_readiness_gate": str(args.readiness_gate),
        "items": included_items,
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
            "next_gate": "FASE_2_44_DRYRUN_EXECUTION_GATE",
            "allowed_methods": ["POST"],
            "forbidden_methods": ["PATCH", "DELETE"],
            "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
        },
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    plan_file = args.output_dir / f"dryrun-{apply_plan_id[:8]}.json"
    plan_file.write_text(json.dumps(apply_plan, indent=2), encoding="utf-8")

    report_lines = [
        "# ApplyPlan Dry-Run Generation",
        "",
        f"**Device:** {args.device}",
        f"**Generated:** {timestamp}",
        "",
        "## Result",
        "",
        "GENERATED",
        "",
        f"- apply_plan_id: {apply_plan_id}",
        f"- file: {plan_file.name}",
        f"- items: {len(included_items)}",
        f"- mode: dry_run",
        "",
        "## Items Included",
        "",
        "| Item ID | Approval ID | Object Type | Key |",
        "|---|---|---|---|",
    ]

    for item in included_items:
        report_lines.append(
            f"| {item['item_id'][:8]}... | {item['approval_id'][:8]}... | "
            f"{item['object_type']} | {item['object_key']} |"
        )

    if excluded_items:
        report_lines.extend(["", "## Excluded", "", "| Approval ID | Reason |", "|---|---|"])
        for item in excluded_items:
            report_lines.append(f"| {item['approval_id']} | {item['reason']} |")

    report_lines.extend(["", "## Security", "", "✓ No NetBox writes", "✓ mode=dry_run", "✓ can_execute_real_write=false"])

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"✓ Generated: {plan_file}")
    print(f"✓ Report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
