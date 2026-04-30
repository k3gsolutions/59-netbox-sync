#!/usr/bin/env python3
"""FASE 4.52 - Local dry-run simulation for Cycle-002."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def s(value) -> str:
    return str(value or "").strip()


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def sanitize_payload(payload):
    if isinstance(payload, dict):
        return {k: ("<redacted>" if any(term in str(k).lower() for term in ["token", "password", "secret", "bearer", "authorization"]) else sanitize_payload(v)) for k, v in payload.items()}
    if isinstance(payload, list):
        return [sanitize_payload(v) for v in payload]
    return payload


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cycle-id", required=True)
    p.add_argument("--apply-plan", type=Path, required=True)
    p.add_argument("--execution-gate", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--result-json", type=Path, required=True)
    args = p.parse_args()

    plan = load(args.apply_plan)
    gate = args.execution_gate.read_text(encoding="utf-8") if args.execution_gate.exists() else ""
    if "CYCLE_DRYRUN_EXECUTION_BLOCKED" in gate:
        print("✗ dry-run execution gate blocked")
        return 1
    if "CYCLE_DRYRUN_EXECUTION_READY" not in gate and "CYCLE_DRYRUN_EXECUTION_READY_WITH_RESTRICTIONS" not in gate:
        print("✗ dry-run execution gate not ready")
        return 1

    items = []
    for item in plan.get("items") or []:
        payload = item.get("proposed_payload") or {}
        items.append({
            "item_id": item.get("item_id"),
            "approval_id": item.get("approval_id"),
            "object_type": item.get("object_type"),
            "object_key": item.get("object_key"),
            "method": item.get("method"),
            "target_endpoint": item.get("target_endpoint"),
            "expected_result": item.get("expected_result", "dry-run only"),
            "rollback_hint": item.get("rollback_hint", "manual only"),
            "sanitized_payload": sanitize_payload(payload),
        })

    decision = "CYCLE_DRYRUN_SIMULATION_PASSED"
    warnings = []
    if len(items) > 1:
        warnings.append("multiple items present")
        decision = "CYCLE_DRYRUN_SIMULATION_PASSED_WITH_WARNINGS"

    result = {
        "simulation_id": f"simulation-{args.cycle_id}-dryrun",
        "cycle_id": args.cycle_id,
        "apply_plan_id": plan.get("apply_plan_id"),
        "device": plan.get("device"),
        "status": decision,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
        "warnings": warnings,
        "safety_confirmations": {
            "local_only": True,
            "no_network_call": True,
            "no_token_read": True,
            "no_netbox_write": True,
            "no_apply_execution": True,
        },
        "next_gate_required": True,
        "next_gate": "FASE_4_53_CYCLE002_REAL_WRITE_READINESS_GATE",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join([
        f"# {args.cycle_id.upper()} Dry-Run Simulation Result",
        "",
        f"## Decision: {decision}",
        f"- items: {len(items)}",
        f"- apply_plan: {args.apply_plan.name}",
        "",
        "## Safety",
        "- Local only",
        "- No network call",
        "- No token read",
        "- No NetBox write",
    ]), encoding="utf-8")
    args.result_json.parent.mkdir(parents=True, exist_ok=True)
    args.result_json.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"✓ Dry-run simulation: {decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
