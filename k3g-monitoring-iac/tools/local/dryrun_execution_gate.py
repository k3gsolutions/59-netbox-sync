#!/usr/bin/env python3
"""FASE 2.44 — Dry-Run Execution Gate."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple, List


def validate_applyplan(plan: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate ApplyPlan for dry-run execution."""
    issues = []

    if plan.get("mode") != "dry_run":
        issues.append(f"mode={plan.get('mode')} (need dry_run)")

    if plan.get("status") not in ("generated", "validated"):
        issues.append(f"status={plan.get('status')}")

    flags = plan.get("safety_flags", {})
    required_flags = {
        "dry_run_only", "no_netbox_write", "no_token_required",
        "no_apply_execution", "manual_execution_gate_required", "generated_from_approved_records"
    }
    for flag in required_flags:
        if not flags.get(flag):
            issues.append(f"safety_flag {flag} not true")

    epolicy = plan.get("execution_policy", {})
    if epolicy.get("can_execute_real_write") is not False:
        issues.append("can_execute_real_write not false")
    if epolicy.get("requires_next_gate") is not True:
        issues.append("requires_next_gate not true")

    items = plan.get("items", [])
    for item in items:
        if item.get("method") in ("PATCH", "DELETE"):
            issues.append(f"Item {item.get('item_id', '?')} has forbidden method {item['method']}")

        forbidden_targets = ["/sync", "equipment", "ssh", "netconf"]
        if any(t in item.get("target_endpoint", "") for t in forbidden_targets):
            issues.append(f"Item {item.get('item_id', '?')} has forbidden target")

        payload_str = json.dumps(item.get("proposed_payload", {})).lower()
        secrets = ["token", "password", "secret", "api_key", "private key", "bearer", "authorization"]
        if any(s in payload_str for s in secrets):
            issues.append(f"Item {item.get('item_id', '?')} contains secrets")

    return len(issues) == 0, issues


def check_validation_report(report_file: Path) -> Tuple[bool, List[str]]:
    """Check validation report."""
    issues = []

    if not report_file.exists():
        return False, ["Validation report missing"]

    content = report_file.read_text(encoding="utf-8")

    if "DRYRUN_APPLYPLAN_INVALID" in content:
        issues.append("ApplyPlan validation invalid")

    if "DRYRUN_APPLYPLAN_VALID" not in content and "DRYRUN_APPLYPLAN_VALID_WITH_WARNINGS" not in content:
        issues.append("Validation report has no VALID decision")

    return len(issues) == 0, issues


def main() -> int:
    """Gate for dry-run execution."""
    parser = argparse.ArgumentParser(description="FASE 2.44 — Dry-Run Execution Gate")
    parser.add_argument("--apply-plan", type=Path, required=True)
    parser.add_argument("--validation-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()

    if not args.apply_plan.exists():
        print(f"✗ Plan not found")
        return 1

    try:
        with open(args.apply_plan, encoding="utf-8") as f:
            plan = json.load(f)
    except Exception:
        print(f"✗ Cannot load plan")
        return 1

    plan_valid, plan_issues = validate_applyplan(plan)
    report_valid, report_issues = check_validation_report(args.validation_report)

    all_issues = plan_issues + report_issues

    if not plan_valid or not report_valid:
        decision = "NOT_READY_FOR_DRYRUN_SIMULATION"
    elif report_issues:
        decision = "READY_WITH_RESTRICTIONS"
    else:
        decision = "READY_FOR_DRYRUN_SIMULATION"

    timestamp = datetime.utcnow().isoformat() + "+00:00"

    lines = [
        "# Gate de Execução Dry-Run",
        "",
        f"**Gerado:** {timestamp}",
        "",
        "## Decisão",
        "",
        f"### {decision}",
        "",
        "## Checks",
        "",
        "| Check | Status |",
        "|---|---|",
    ]

    lines.append(f"| ApplyPlan válido | {'✓' if plan_valid else '✗'} |")
    lines.append(f"| Validação válida | {'✓' if report_valid else '✗'} |")
    lines.append(f"| Itens: {len(plan.get('items', []))} | ✓ |")

    if all_issues:
        lines.extend(["", "## Issues", ""])
        for issue in all_issues:
            lines.append(f"- {issue}")

    lines.extend(["", "## Segurança", "", "✓ Nenhuma execução", "✓ Nenhum token"])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")

    print(f"✓ {decision}")
    return 0 if decision != "NOT_READY_FOR_DRYRUN_SIMULATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
