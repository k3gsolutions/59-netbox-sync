#!/usr/bin/env python3
"""FASE 4.54 - Build real write authorization package for Cycle-002."""

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


def approved_records(dirs):
    rows = []
    for d in dirs:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.json")):
            data = load(f)
            if s(data.get("status")) == "approved" and s(data.get("state")) == "approved":
                rows.append((f, data))
    return rows


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cycle-id", required=True)
    p.add_argument("--device", required=True)
    p.add_argument("--device-id", required=True)
    p.add_argument("--apply-plan", type=Path, required=True)
    p.add_argument("--simulation-result", type=Path, required=True)
    p.add_argument("--real-write-readiness-gate", type=Path, required=True)
    p.add_argument("--approved-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()

    plan = load(args.apply_plan)
    sim = load(args.simulation_result)
    gate = load(args.real_write_readiness_gate)
    approved = approved_records([args.approved_dir, args.approved_dir / "approved"])
    issues = []
    if s(gate.get("decision")) not in {"CYCLE_READY_FOR_REAL_WRITE_REVIEW", "CYCLE_READY_WITH_RESTRICTIONS"}:
        issues.append("real write readiness gate not ready")
    if s(sim.get("status")) not in {"CYCLE_DRYRUN_SIMULATION_PASSED", "CYCLE_DRYRUN_SIMULATION_PASSED_WITH_WARNINGS"}:
        issues.append("simulation not ready")
    if not approved:
        issues.append("no approved records")
    approved_names = {f.name for f, _ in approved}
    for ref in plan.get("source_approval_records") or []:
        if ref not in approved_names:
            issues.append(f"missing approved record: {ref}")
    if s(plan.get("cycle_id")) != "cycle-002" or s(plan.get("mode")) != "dry_run":
        issues.append("apply plan not eligible")
    if not plan.get("items"):
        issues.append("items missing")
    if int((plan.get("execution_policy") or {}).get("max_items") or 0) > 3:
        issues.append("max_items too high")
    if any(term in json.dumps(plan).lower() for term in ["token=", "password=", "secret=", "api_key", "private key", "bearer"]):
        issues.append("secret keyword found")

    if s(gate.get("decision")) == "CYCLE_NOT_READY_FOR_REAL_WRITE" or issues:
        decision = "CYCLE_NOT_READY_FOR_REAL_WRITE" if "real write readiness gate not ready" in issues or "no approved records" in issues else "CYCLE_READY_WITH_RESTRICTIONS"
    else:
        decision = "CYCLE_READY_FOR_REAL_WRITE_REVIEW"

    if decision == "CYCLE_NOT_READY_FOR_REAL_WRITE":
        args.output_dir.mkdir(parents=True, exist_ok=True)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text("\n".join([
            f"# {args.cycle_id.upper()} Real Write Authorization Package",
            "",
            f"## Decision: {decision}",
            "",
            "- blocked",
            "",
            "## Safety",
            "- No NetBox write",
            "- No ApplyPlan",
            "- No token",
        ]), encoding="utf-8")
        print(f"✗ {decision}")
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    auth_id = f"auth-{args.cycle_id}-{uuid.uuid4().hex[:8]}"
    required_phrase = f"AUTORIZO_PRE_FLIGHT_ESCRITA_REAL_{args.cycle_id.upper()}_{args.device}_{plan.get('apply_plan_id')}"
    payload = {
        "authorization_id": auth_id,
        "cycle_id": args.cycle_id,
        "device": args.device,
        "device_id": args.device_id,
        "apply_plan_id": plan.get("apply_plan_id"),
        "simulation_result_id": sim.get("simulation_id"),
        "real_write_readiness_gate": args.real_write_readiness_gate.name,
        "required_phrase": required_phrase,
        "status": "prepared",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_approval_records": [f.name for f, _ in approved],
        "safety_confirmations": {
            "no_write_executed": True,
            "no_token_read": True,
            "no_network_call": True,
            "final_preflight_required": True,
            "explicit_operator_authorization_required": True,
        },
    }
    auth_file = args.output_dir / "authorization_request.json"
    auth_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join([
        f"# {args.cycle_id.upper()} Real Write Authorization Package",
        "",
        f"## Decision: {decision}",
        "",
        f"- authorization_id: {auth_id}",
        f"- required_phrase: {required_phrase}",
        f"- approved_records: {len(approved)}",
        "",
        "## Safety",
        "- No NetBox write",
        "- No ApplyPlan",
        "- Human authorization required",
    ]), encoding="utf-8")
    print(f"✓ Authorization package: {auth_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
