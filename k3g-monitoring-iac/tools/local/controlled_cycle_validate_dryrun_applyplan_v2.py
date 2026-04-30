#!/usr/bin/env python3
"""FASE 4.50 - Cycle-002 Dry-Run ApplyPlan Validation."""

from __future__ import annotations

import argparse
import json
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
    parser = argparse.ArgumentParser(description="FASE 4.50 - Validate Cycle-002 Dry-Run ApplyPlan")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--apply-plan", type=Path, required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    plan = load_json(args.apply_plan)
    issues: List[str] = []
    if not plan:
        issues.append("apply plan missing or invalid")
    if safe_text(plan.get("cycle_id")) != "cycle-002":
        issues.append("cycle_id must be cycle-002")
    if safe_text(plan.get("mode")) != "dry_run":
        issues.append("mode must be dry_run")
    if safe_text(plan.get("status")) != "generated":
        issues.append("status must be generated")
    if safe_text(plan.get("device")) != args.device:
        issues.append("device mismatch")
    if safe_text(plan.get("device_id")) != args.device_id:
        issues.append("device_id mismatch")
    if not plan.get("source_approval_records"):
        issues.append("source_approval_records required")
    if not plan.get("items"):
        issues.append("items required")
    if int((plan.get("execution_policy") or {}).get("max_items") or 0) > 3:
        issues.append("max_items must be <= 3")

    flags = plan.get("safety_flags") or {}
    required_flags = ["dry_run_only", "no_netbox_write", "no_token_required", "no_apply_execution", "manual_execution_gate_required", "generated_from_approved_records"]
    for flag in required_flags:
        if not flags.get(flag):
            issues.append(f"safety flag missing: {flag}")

    policy = plan.get("execution_policy") or {}
    if policy.get("can_execute_real_write") is not False:
        issues.append("can_execute_real_write must be false")
    if policy.get("requires_next_gate") is not True:
        issues.append("requires_next_gate must be true")
    if policy.get("next_gate") != "FASE_4_51_CYCLE002_DRYRUN_EXECUTION_GATE":
        issues.append("next_gate mismatch")
    if policy.get("allowed_methods") != ["POST"]:
        issues.append("allowed_methods must be POST only")
    if policy.get("forbidden_methods") != ["PATCH", "DELETE"]:
        issues.append("forbidden_methods must be PATCH, DELETE")
    if policy.get("forbidden_targets") != ["/sync", "equipment", "ssh", "netconf"]:
        issues.append("forbidden_targets mismatch")

    text = json.dumps(plan, sort_keys=True).lower()
    if any(term in text for term in ["netbox_write_token", "authorization: token", "token=", "password=", "secret=", "private key", "bearer"]):
        issues.append("secret keyword found")

    item_issues = []
    for item in plan.get("items") or []:
        item_missing = [field for field in ["approval_id", "object_type", "object_key", "proposed_payload", "evidence_hash", "expected_result", "rollback_hint"] if not item.get(field)]
        if item_missing:
            item_issues.append({"item_id": item.get("item_id"), "missing": item_missing})
        if safe_text(item.get("method")) != "POST":
            item_issues.append({"item_id": item.get("item_id"), "missing": ["method must be POST"]})
        if has_secret(json.dumps(item)):
            item_issues.append({"item_id": item.get("item_id"), "missing": ["secret keyword found"]})

    valid = not issues and not item_issues
    if valid:
        decision = "CYCLE_DRYRUN_APPLYPLAN_VALID"
    elif plan and not issues and item_issues:
        decision = "CYCLE_DRYRUN_APPLYPLAN_VALID_WITH_WARNINGS"
    else:
        decision = "CYCLE_DRYRUN_APPLYPLAN_INVALID"

    report_lines = [
        f"# {args.cycle_id.upper()} DRY-RUN APPLYPLAN VALIDATION",
        "",
        f"## Decision: {decision}",
        "",
        f"- apply_plan: {args.apply_plan.name}",
        f"- items: {len(plan.get('items') or [])}",
        f"- issues: {len(issues) + len(item_issues)}",
        "",
        "## Issues",
    ]
    if issues or item_issues:
        for issue in issues:
            report_lines.append(f"- {issue}")
        for issue in item_issues:
            report_lines.append(f"- {issue['item_id']}: {', '.join(issue['missing'])}")
    else:
        report_lines.append("- none")
    report_lines += [
        "",
        "## Safety",
        "- No NetBox write",
        "- No ApplyPlan execution",
        "- No token",
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(report_lines), encoding="utf-8")
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps({
        "cycle_id": args.cycle_id,
        "decision": decision,
        "apply_plan": args.apply_plan.name,
        "issues": issues,
        "item_issues": item_issues,
        "validated_at": safe_text(plan.get("generated_at")) or "",
        "no_netbox_write": True,
        "no_apply_execution": True,
    }, indent=2), encoding="utf-8")

    cycle_status = args.output.parent.parent / "CYCLE-002-STATUS.md"
    cycle_status.write_text(f"# CYCLE-002\n\nStatus: {decision}\n", encoding="utf-8")

    print(f"✓ ApplyPlan validation: {decision}")
    print(f"✓ Report: {args.output}")
    print(f"✓ JSON: {args.output_json}")
    return 0 if decision.startswith("CYCLE_DRYRUN_APPLYPLAN_VALID") else 1


if __name__ == "__main__":
    raise SystemExit(main())
