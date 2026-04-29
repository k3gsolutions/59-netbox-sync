#!/usr/bin/env python3
"""FASE 2.43 — Validate Dry-Run ApplyPlan."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def validate_applyplan(plan: Dict[str, Any]) -> tuple[str, List[str], List[str]]:
    """Validate ApplyPlan structure."""
    blockers = []
    warnings = []

    if plan.get("mode") != "dry_run":
        blockers.append(f"mode={plan.get('mode')} (need dry_run)")

    if plan.get("status") != "generated":
        blockers.append(f"status={plan.get('status')}")

    flags = plan.get("safety_flags", {})
    if not flags.get("dry_run_only"):
        blockers.append("dry_run_only not true")
    if not flags.get("no_netbox_write"):
        blockers.append("no_netbox_write not true")
    if not flags.get("no_token_required"):
        blockers.append("no_token_required not true")
    if not flags.get("no_apply_execution"):
        blockers.append("no_apply_execution not true")

    epolicy = plan.get("execution_policy", {})
    if epolicy.get("can_execute_real_write") is not False:
        blockers.append("can_execute_real_write not false")
    if epolicy.get("requires_next_gate") is not True:
        blockers.append("requires_next_gate not true")

    for method in epolicy.get("forbidden_methods", []):
        if method not in ["PATCH", "DELETE"]:
            warnings.append(f"Unexpected forbidden method: {method}")

    items = plan.get("items", [])
    for item in items:
        if not item.get("approval_id"):
            blockers.append(f"Item {item.get('item_id', '?')} missing approval_id")
        if not item.get("proposed_payload"):
            blockers.append(f"Item {item.get('item_id', '?')} missing payload")
        if not item.get("evidence_hash"):
            blockers.append(f"Item {item.get('item_id', '?')} missing hash")

        payload_str = json.dumps(item.get("proposed_payload", {})).lower()
        secrets = ["token", "password", "secret", "api_key", "private key", "bearer", "authorization"]
        if any(s in payload_str for s in secrets):
            blockers.append(f"Item {item.get('item_id', '?')} contains secrets")

    if blockers:
        return "DRYRUN_APPLYPLAN_INVALID", blockers, warnings
    elif warnings:
        return "DRYRUN_APPLYPLAN_VALID_WITH_WARNINGS", [], warnings
    else:
        return "DRYRUN_APPLYPLAN_VALID", [], []


def main() -> int:
    """Validate dry-run ApplyPlan."""
    parser = argparse.ArgumentParser(description="FASE 2.43 — Validate Dry-Run ApplyPlan")
    parser.add_argument("--apply-plan", type=Path, required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True, type=int)
    parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()

    if not args.apply_plan.exists():
        print(f"✗ Plan not found: {args.apply_plan}")
        return 1

    try:
        with open(args.apply_plan, encoding="utf-8") as f:
            plan = json.load(f)
    except Exception as e:
        print(f"✗ Cannot load: {e}")
        return 1

    decision, blockers, warnings = validate_applyplan(plan)

    timestamp = datetime.utcnow().isoformat() + "+00:00"

    report_lines = [
        "# Validação do ApplyPlan Dry-Run",
        "",
        f"**Device:** {args.device}",
        f"**Validado:** {timestamp}",
        "",
        "## Decisão",
        "",
        f"### {decision}",
        "",
        "## Resumo",
        "",
        f"- Total itens: {len(plan.get('items', []))}",
        f"- Bloqueadores: {len(blockers)}",
        f"- Avisos: {len(warnings)}",
        "",
    ]

    if blockers:
        report_lines.extend(["## Bloqueadores", ""])
        for blocker in blockers:
            report_lines.append(f"- ✗ {blocker}")
        report_lines.append("")

    if warnings:
        report_lines.extend(["## Avisos", ""])
        for warning in warnings:
            report_lines.append(f"- ⚠️ {warning}")
        report_lines.append("")

    report_lines.extend([
        "## Segurança",
        "",
        "✓ Nenhuma escrita NetBox",
        "✓ Nenhuma execução",
        "✓ Nenhum token",
        "✓ Validação local apenas",
        "",
    ])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"✓ Decision: {decision}")
    print(f"✓ Report: {args.output}")

    return 0 if decision in ("DRYRUN_APPLYPLAN_VALID", "DRYRUN_APPLYPLAN_VALID_WITH_WARNINGS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
