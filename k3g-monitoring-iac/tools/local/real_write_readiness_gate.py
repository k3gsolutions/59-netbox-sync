#!/usr/bin/env python3
"""FASE 2.46 — Real Write Readiness Gate (No Execution)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


def validate_governance_chain(
    plan: Dict[str, Any],
    simulation_result: Dict[str, Any],
    approved_dir: Path,
) -> Tuple[bool, List[str]]:
    """Validate complete governance chain."""
    issues = []

    # ApplyPlan checks
    if plan.get("mode") != "dry_run":
        issues.append(f"mode={plan.get('mode')}")
    if plan.get("status") in ("applied",):
        issues.append(f"status={plan.get('status')} (already applied)")
    if plan.get("execution_policy", {}).get("can_execute_real_write") is True:
        issues.append("can_execute_real_write=true (BLOCKER)")

    # Simulation result checks
    if simulation_result.get("status") not in ("DRYRUN_SIMULATION_PASSED", "DRYRUN_SIMULATION_PASSED_WITH_WARNINGS"):
        issues.append(f"simulation status {simulation_result.get('status')}")

    # ApprovalRecord checks
    source_approvals = plan.get("source_approval_records", [])
    if not source_approvals:
        issues.append("No source approval records")

    for approval_id in source_approvals:
        found = False
        for record_file in approved_dir.glob("approval-record-*.json"):
            try:
                with open(record_file, encoding="utf-8") as f:
                    record = json.load(f)
                if record.get("approval_record_id") == approval_id:
                    found = True
                    if record.get("status") != "approved":
                        issues.append(f"ApprovalRecord {approval_id} status {record.get('status')}")
                    break
            except Exception:
                pass

        if not found:
            issues.append(f"ApprovalRecord {approval_id} not found in approved-dir")

    # Safety flags
    flags = plan.get("safety_flags", {})
    if not flags.get("dry_run_only"):
        issues.append("dry_run_only not true")

    return len(issues) == 0, issues


def main() -> int:
    """Real write readiness gate (validation only, no execution)."""
    parser = argparse.ArgumentParser(description="FASE 2.46 — Real Write Readiness Gate")
    parser.add_argument("--apply-plan", type=Path, required=True)
    parser.add_argument("--simulation-result", type=Path, required=True)
    parser.add_argument("--approved-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()

    # Load artifacts
    try:
        with open(args.apply_plan, encoding="utf-8") as f:
            plan = json.load(f)
        with open(args.simulation_result, encoding="utf-8") as f:
            sim_result = json.load(f)
    except Exception:
        print("✗ Cannot load artifacts")
        return 1

    # Validate governance chain
    valid, issues = validate_governance_chain(plan, sim_result, args.approved_dir)

    if not valid and any("BLOCKER" in i for i in issues):
        decision = "NOT_READY_FOR_REAL_WRITE"
    elif not valid:
        decision = "NOT_READY_FOR_REAL_WRITE"
    elif issues:
        decision = "READY_WITH_RESTRICTIONS"
    else:
        decision = "READY_FOR_REAL_WRITE_REVIEW"

    timestamp = datetime.utcnow().isoformat() + "+00:00"

    lines = [
        "# Gate de Prontidão para Escrita Real",
        "",
        f"**Gerado:** {timestamp}",
        "",
        "## Decisão",
        "",
        f"### {decision}",
        "",
        "## Cadeia de Governança",
        "",
        "| Etapa | Status |",
        "|---|---|",
        f"| ApprovalRecord aprovado | {'✓' if not any('ApprovalRecord' in i for i in issues) else '✗'} |",
        f"| ApplyPlan dry-run | {'✓' if plan.get('mode') == 'dry_run' else '✗'} |",
        f"| Simulação passou | {'✓' if 'PASSED' in sim_result.get('status', '') else '✗'} |",
        "",
        "## Checks",
        "",
        "| Check | Status |",
        "|---|---|",
    ]

    lines.append(f"| ApplyPlan modo dry_run | {'✓' if plan.get('mode') == 'dry_run' else '✗'} |")
    lines.append(f"| can_execute_real_write=false | {'✓' if not plan.get('execution_policy', {}).get('can_execute_real_write') else '✗'} |")
    lines.append(f"| Simulação concluída | {'✓' if 'PASSED' in sim_result.get('status', '') else '✗'} |")

    if issues:
        lines.extend(["", "## Issues", ""])
        for issue in issues:
            lines.append(f"- {issue}")

    lines.extend([
        "",
        "## Segurança",
        "",
        "✓ Nenhuma escrita real",
        "✓ Nenhum token lido",
        "✓ Gate apenas avalia",
        "✓ Escrita real exigirá fase futura",
        "",
    ])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")

    print(f"✓ {decision}")
    return 0 if decision != "NOT_READY_FOR_REAL_WRITE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
