#!/usr/bin/env python3
"""FASE 4.49 - Cycle-002 Dry-Run ApplyPlan Generation."""

from __future__ import annotations

import argparse
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def safe_text(value: Any) -> str:
    return str(value or "").strip()


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def has_secret(text: str) -> bool:
    lowered = safe_text(text).lower()
    blocked = ["netbox_write_token", "authorization: token", "token=", "password=", "secret=", "api_key", "private key", "bearer"]
    return any(term in lowered for term in blocked)


def main() -> int:
    parser = argparse.ArgumentParser(description="FASE 4.49 - Generate Cycle-002 Dry-Run ApplyPlan")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--approved-dir", type=Path, required=True)
    parser.add_argument("--approval-review", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    if args.cycle_id != "cycle-002":
        print("✗ cycle_id must be cycle-002")
        return 1
    if not args.approval_review.exists():
        print("✗ approval review missing")
        return 1

    approved_records: List[Dict[str, Any]] = []
    if args.approved_dir.exists():
        for path in sorted(args.approved_dir.glob("*.json")):
            record = load_json(path)
            if safe_text(record.get("status")) != "approved":
                continue
            if safe_text(record.get("state")) != "approved":
                continue
            if not safe_text(record.get("approved_by")) or not safe_text(record.get("approved_at")) or not safe_text(record.get("approval_reason")):
                continue
            if not record.get("proposed_payload") or not safe_text(record.get("evidence_hash")):
                continue
            history = record.get("state_history") or []
            if not any(safe_text(item.get("event")) == "approved_for_cycle_dryrun_applyplan" for item in history):
                continue
            approved_records.append({"file": path.name, "record": record})

    if not approved_records:
        report = "# CYCLE-002 DRY-RUN APPLYPLAN GENERATION\n\nDecision: CYCLE_DRYRUN_APPLYPLAN_BLOCKED\n\n- no approved records\n"
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report, encoding="utf-8")
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps({
            "cycle_id": args.cycle_id,
            "decision": "CYCLE_DRYRUN_APPLYPLAN_BLOCKED",
            "reason": "no approved records",
            "no_netbox_write": True,
        }, indent=2), encoding="utf-8")
        cycle_status = args.output_dir.parents[2] / "CYCLE-002-STATUS.md"
        cycle_status.write_text("# CYCLE-002\n\nStatus: CYCLE_DRYRUN_APPLYPLAN_BLOCKED\n", encoding="utf-8")
        return 1

    items: List[Dict[str, Any]] = []
    for entry in approved_records:
        record = entry["record"]
        proposed_payload = record["proposed_payload"]
        object_key = safe_text(record.get("object_key"))
        item_id = safe_text(record.get("object_id") or object_key)
        items.append({
            "item_id": item_id,
            "approval_id": record.get("approval_id"),
            "object_type": record.get("object_type"),
            "object_key": object_key,
            "action": proposed_payload.get("action", "safe_create_staged"),
            "method": "POST",
            "target_endpoint": "/",
            "proposed_payload": proposed_payload,
            "expected_result": "dry-run only",
            "rollback_hint": "manual only",
            "evidence_hash": record.get("evidence_hash"),
        })

    apply_plan_id = f"apply-plan-{args.cycle_id}-{uuid.uuid4().hex[:8]}"
    generated_at = datetime.now(timezone.utc).isoformat()
    plan = {
        "apply_plan_id": apply_plan_id,
        "cycle_id": args.cycle_id,
        "device": args.device,
        "device_id": args.device_id,
        "mode": "dry_run",
        "status": "generated",
        "generated_at": generated_at,
        "source_approval_records": [entry["file"] for entry in approved_records],
        "items": items,
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
            "next_gate": "FASE_4_51_CYCLE002_DRYRUN_EXECUTION_GATE",
            "max_items": 3,
            "allowed_methods": ["POST"],
            "forbidden_methods": ["PATCH", "DELETE"],
            "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
        },
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    plan_path = args.output_dir / f"{apply_plan_id}.json"
    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    report_lines = [
        "# CYCLE-002 DRY-RUN APPLYPLAN GENERATION",
        "",
        "## Decision",
        "CYCLE_DRYRUN_APPLYPLAN_GENERATED",
        "",
        f"- apply_plan_id: {apply_plan_id}",
        f"- records: {len(approved_records)}",
        f"- items: {len(items)}",
        f"- file: {plan_path.name}",
        "",
        "## Safety",
        "- No NetBox write",
        "- No ApplyPlan execution",
        "- No token use",
        "- Next gate required",
    ]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(report_lines), encoding="utf-8")

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps({
        "cycle_id": args.cycle_id,
        "decision": "CYCLE_DRYRUN_APPLYPLAN_GENERATED",
        "apply_plan_id": apply_plan_id,
        "apply_plan_file": plan_path.name,
        "generated_at": generated_at,
        "items": len(items),
        "source_approval_records": [entry["file"] for entry in approved_records],
        "no_netbox_write": True,
        "no_apply_execution": True,
    }, indent=2), encoding="utf-8")

    cycle_status = args.output_dir.parents[2] / "CYCLE-002-STATUS.md"
    cycle_status.write_text("# CYCLE-002\n\nStatus: CYCLE_DRYRUN_APPLYPLAN_GENERATED\n", encoding="utf-8")

    print(f"✓ Dry-run ApplyPlan generated: {plan_path}")
    print(f"✓ Report: {args.report}")
    print(f"✓ JSON: {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
