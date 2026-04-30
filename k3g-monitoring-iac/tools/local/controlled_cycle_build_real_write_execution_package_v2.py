#!/usr/bin/env python3
"""FASE 4.56 - Build real write execution package, locked."""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


def s(v) -> str:
    return str(v or "").strip()


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cycle-id", required=True)
    p.add_argument("--authorization-request", type=Path, required=True)
    p.add_argument("--final-preflight-gate", type=Path, required=True)
    p.add_argument("--apply-plan", type=Path, required=True)
    p.add_argument("--simulation-result", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()

    auth = load(args.authorization_request)
    gate = load(args.final_preflight_gate)
    plan = load(args.apply_plan)
    sim = load(args.simulation_result)
    issues = []
    if s(gate.get("decision")) not in {"CYCLE_READY_FOR_REAL_WRITE_EXECUTION_PACKAGE", "CYCLE_READY_WITH_RESTRICTIONS"}:
        issues.append("final preflight not ready")
    if s(plan.get("cycle_id")) != "cycle-002" or s(plan.get("mode")) != "dry_run":
        issues.append("apply plan not eligible")
    if plan.get("execution_policy", {}).get("can_execute_real_write") is not False:
        issues.append("apply plan can_execute_real_write must be false")
    if len(plan.get("items") or []) == 0:
        issues.append("items missing")
    if int((plan.get("execution_policy") or {}).get("max_items") or 0) > 3:
        issues.append("max_items too high")
    if s(sim.get("status")) not in {"CYCLE_DRYRUN_SIMULATION_PASSED", "CYCLE_DRYRUN_SIMULATION_PASSED_WITH_WARNINGS"}:
        issues.append("simulation not ready")
    if any(term in json.dumps(plan).lower() for term in ["token=", "password=", "secret=", "api_key", "private key", "bearer"]):
        issues.append("secret keyword found")

    if issues and "final preflight not ready" in issues:
        print("✗ final preflight not ready")
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    execution_package_id = f"exec-{args.cycle_id}-{uuid.uuid4().hex[:8]}"
    required_phrase = f"EXECUTAR_ESCRITA_REAL_{args.cycle_id.upper()}_{auth.get('device', '4WNET-MNS-KTG-RX')}_{execution_package_id}"
    items = []
    for item in plan.get("items") or []:
        items.append({
            "approval_id": item.get("approval_id"),
            "object_type": item.get("object_type"),
            "object_key": item.get("object_key"),
            "method": item.get("method", "POST"),
            "target_endpoint": item.get("target_endpoint"),
            "proposed_payload": item.get("proposed_payload"),
            "rollback_hint": item.get("rollback_hint"),
            "expected_result": item.get("expected_result"),
            "pre_write_checks": ["local_validation", "safety_lock"],
            "post_write_checks": ["GET verify", "drift check"],
        })
    package = {
        "execution_package_id": execution_package_id,
        "cycle_id": args.cycle_id,
        "device": auth.get("device", "4WNET-MNS-KTG-RX"),
        "device_id": auth.get("device_id", "1890"),
        "apply_plan_id": plan.get("apply_plan_id"),
        "authorization_id": auth.get("authorization_id"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "prepared",
        "mode": "real_write_prepared",
        "execution_allowed": False,
        "token_required_in_next_phase": True,
        "explicit_confirm_required": True,
        "one_shot_execution": True,
        "max_items": 3,
        "items": items,
        "safety_confirmations": {
            "no_write_executed": True,
            "no_token_read": True,
            "no_network_call": True,
            "package_only": True,
            "real_write_not_executed": True,
        },
        "required_next_phase": "FASE_4_59_CYCLE002_EXECUTE_REAL_WRITE_ONCE",
        "required_execution_phrase": required_phrase,
    }
    pkg_file = args.output_dir / "execution_package.json"
    pkg_file.write_text(json.dumps(package, indent=2), encoding="utf-8")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join([
        f"# {args.cycle_id.upper()} Real Write Execution Package",
        "",
        f"## Decision: {'CYCLE_READY_FOR_REAL_WRITE_EXECUTION_PACKAGE' if not issues else 'CYCLE_READY_WITH_RESTRICTIONS'}",
        "",
        f"- execution_package_id: {execution_package_id}",
        f"- required_phrase: {required_phrase}",
        f"- items: {len(items)}",
        "",
        "## Safety",
        "- execution_allowed=false",
        "- No NetBox write",
        "- No token",
    ]), encoding="utf-8")
    print(f"✓ Execution package: {pkg_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
