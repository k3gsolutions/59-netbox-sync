#!/usr/bin/env python3
"""FASE 4.53 - Real write readiness gate for Cycle-002."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def s(value) -> str:
    return str(value or "").strip()


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def approved_records_from_dirs(dirs):
    records = []
    for d in dirs:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.json")):
            data = load(f)
            if s(data.get("status")) == "approved" and s(data.get("state")) == "approved":
                records.append((f, data))
    return records


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cycle-id", required=True)
    p.add_argument("--apply-plan", type=Path, required=True)
    p.add_argument("--simulation-result", type=Path, required=True)
    p.add_argument("--simulation-report", type=Path, required=True)
    p.add_argument("--dryrun-execution-gate", type=Path, required=True)
    p.add_argument("--approved-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--output-json", type=Path, required=True)
    args = p.parse_args()

    plan = load(args.apply_plan)
    sim = load(args.simulation_result)
    sim_report = args.simulation_report.read_text(encoding="utf-8") if args.simulation_report.exists() else ""
    gate = args.dryrun_execution_gate.read_text(encoding="utf-8") if args.dryrun_execution_gate.exists() else ""
    approved = approved_records_from_dirs([args.approved_dir, args.approved_dir / "approved"])
    issues = []
    if s(plan.get("cycle_id")) != "cycle-002":
        issues.append("cycle_id mismatch")
    if s(plan.get("mode")) != "dry_run" or plan.get("execution_policy", {}).get("can_execute_real_write") is not False:
        issues.append("apply plan not dry_run locked")
    if s(sim.get("status")) not in {"CYCLE_DRYRUN_SIMULATION_PASSED", "CYCLE_DRYRUN_SIMULATION_PASSED_WITH_WARNINGS"}:
        issues.append("simulation not passed")
    if sim.get("next_gate_required") is not True:
        issues.append("simulation next_gate_required false")
    if "CYCLE_DRYRUN_EXECUTION_READY" not in gate and "CYCLE_DRYRUN_EXECUTION_READY_WITH_RESTRICTIONS" not in gate:
        issues.append("dryrun gate not ready")
    if not approved:
        issues.append("no approved records")
    approved_names = {f.name for f, _ in approved}
    for ref in plan.get("source_approval_records") or []:
        if ref not in approved_names:
            issues.append(f"missing approved record: {ref}")
    for _, record in approved:
        review = record.get("review") or {}
        if not (s(record.get("approved_by")) and s(record.get("approved_at")) and s(record.get("approval_reason"))):
            issues.append(f"{record.get('approval_id')}: approval fields incomplete")
        if not record.get("proposed_payload") or not s(record.get("evidence_hash")):
            issues.append(f"{record.get('approval_id')}: payload/evidence missing")
        if not any(s(item.get("event")) == "approved_for_cycle_dryrun_applyplan" for item in record.get("state_history") or []):
            issues.append(f"{record.get('approval_id')}: state_history missing approved_for_cycle_dryrun_applyplan")
    if len(plan.get("items") or []) == 0:
        issues.append("items missing")
    if int((plan.get("execution_policy") or {}).get("max_items") or 0) > 3:
        issues.append("max_items too high")
    if "CYCLE_DRYRUN_APPLYPLAN_INVALID" in sim_report:
        issues.append("simulation report invalid")

    decision = "CYCLE_READY_FOR_REAL_WRITE_REVIEW" if not issues else "CYCLE_READY_WITH_RESTRICTIONS"
    if any("missing approved record" in i or "simulation not passed" in i for i in issues):
        decision = "CYCLE_NOT_READY_FOR_REAL_WRITE"

    report = "\n".join([
        f"# {args.cycle_id.upper()} Real Write Readiness Gate",
        "",
        f"## Decision: {decision}",
        "",
        f"- apply_plan: {args.apply_plan.name}",
        f"- simulation_result: {args.simulation_result.name}",
        f"- approved_records: {len(approved)}",
        "",
        "## Issues",
    ] + ([f"- {i}" for i in issues] if issues else ["- none"]) + [
        "",
        "## Safety",
        "- No NetBox write",
        "- No ApplyPlan execution",
        "- No token",
    ])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    payload = {
        "cycle_id": args.cycle_id,
        "decision": decision,
        "issues": issues,
        "approved_records": [f.name for f, _ in approved],
        "no_netbox_write": True,
        "no_apply_plan_created": True,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"✓ Real write readiness gate: {decision}")
    return 0 if decision.startswith("CYCLE_READY") else 1


if __name__ == "__main__":
    raise SystemExit(main())
