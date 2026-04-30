#!/usr/bin/env python3
"""FASE 4.51 - Dry-run execution gate for Cycle-002."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


BLOCKED = ["PATCH", "DELETE", "/sync", "equipment", "ssh", "netconf"]
SECRET_TERMS = ["netbox_write_token", "authorization: token", "token=", "password=", "secret=", "api_key", "private key", "bearer"]


def s(value) -> str:
    return str(value or "").strip()


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cycle-id", required=True)
    p.add_argument("--apply-plan", type=Path, required=True)
    p.add_argument("--validation-report", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--output-json", type=Path, required=True)
    args = p.parse_args()

    plan = load(args.apply_plan)
    report_text = args.validation_report.read_text(encoding="utf-8") if args.validation_report.exists() else ""
    issues = []
    if s(plan.get("cycle_id")) != "cycle-002":
        issues.append("cycle_id must be cycle-002")
    if s(plan.get("mode")) != "dry_run":
        issues.append("mode must be dry_run")
    if s(plan.get("status")) not in {"generated", "validated"}:
        issues.append("status must be generated or validated")
    if "CYCLE_DRYRUN_APPLYPLAN_VALID" not in report_text and "CYCLE_DRYRUN_APPLYPLAN_VALID_WITH_WARNINGS" not in report_text:
        issues.append("validation report must be valid or warnings")
    if "CYCLE_DRYRUN_APPLYPLAN_INVALID" in report_text:
        issues.append("validation report invalid")
    flags = plan.get("safety_flags") or {}
    for key in ["dry_run_only", "no_netbox_write", "no_token_required", "no_apply_execution", "manual_execution_gate_required", "generated_from_approved_records"]:
        if not flags.get(key):
            issues.append(f"missing flag {key}")
    policy = plan.get("execution_policy") or {}
    if policy.get("can_execute_real_write") is not False:
        issues.append("can_execute_real_write must be false")
    if policy.get("requires_next_gate") is not True:
        issues.append("requires_next_gate must be true")
    if not s(policy.get("next_gate")):
        issues.append("next_gate required")
    if policy.get("allowed_methods") != ["POST"]:
        issues.append("allowed_methods must be POST")
    if policy.get("forbidden_methods") != ["PATCH", "DELETE"]:
        issues.append("forbidden_methods must be PATCH/DELETE")
    if policy.get("forbidden_targets") != ["/sync", "equipment", "ssh", "netconf"]:
        issues.append("forbidden_targets mismatch")
    if len(plan.get("items") or []) == 0:
        issues.append("items required")
    if int(policy.get("max_items") or 0) > 3:
        issues.append("max_items must be <= 3")
    text = json.dumps(plan, sort_keys=True).lower()
    if any(term in text for term in SECRET_TERMS):
        issues.append("secret keyword found")
    for item in plan.get("items") or []:
        if s(item.get("method")) != "POST":
            issues.append(f"{item.get('item_id')}: method must be POST")
        if any(term.lower() in json.dumps(item).lower() for term in SECRET_TERMS):
            issues.append(f"{item.get('item_id')}: secret keyword found")

    decision = "CYCLE_DRYRUN_EXECUTION_READY" if not issues else "CYCLE_DRYRUN_EXECUTION_READY_WITH_RESTRICTIONS"
    if issues and any("secret keyword" in issue.lower() for issue in issues):
        decision = "CYCLE_DRYRUN_EXECUTION_BLOCKED"

    report = "\n".join([
        f"# {args.cycle_id.upper()} Dry-Run Execution Gate",
        "",
        f"## Decision: {decision}",
        "",
        f"- apply_plan: {args.apply_plan.name}",
        f"- validation_report: {args.validation_report.name}",
        f"- items: {len(plan.get('items') or [])}",
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
        "apply_plan": args.apply_plan.name,
        "validation_report": args.validation_report.name,
        "issues": issues,
        "safety_confirmations": {
            "dry_run_only": True,
            "no_netbox_write": True,
            "no_token_required": True,
            "no_apply_execution": True,
            "manual_execution_gate_required": True,
            "generated_from_approved_records": True,
        },
        "next_gate_required": True,
        "next_gate": "FASE_4_52_CYCLE002_EXECUTE_DRY_RUN_SIMULATION",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"✓ Dry-run execution gate: {decision}")
    return 0 if decision == "CYCLE_DRYRUN_EXECUTION_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
