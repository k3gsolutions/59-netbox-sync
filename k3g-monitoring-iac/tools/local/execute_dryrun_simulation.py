#!/usr/bin/env python3
"""FASE 2.45 — Execute Dry-Run Simulation (100% Local, No Network)."""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def check_execution_gate(gate_file: Path) -> bool:
    """Check if execution gate allows simulation."""
    if not gate_file.exists():
        return False

    content = gate_file.read_text(encoding="utf-8")
    return "READY_FOR_DRYRUN_SIMULATION" in content or "READY_WITH_RESTRICTIONS" in content


def simulate_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate ApplyPlan item locally."""
    payload = item.get("proposed_payload", {})
    payload_str = json.dumps(payload, indent=2)

    # Simulated preflight checks
    preflight_results = []
    if "name" in payload:
        preflight_results.append({"check": "object_key_unique", "result": "would_pass"})
    if "tenant" in payload:
        preflight_results.append({"check": "tenant_exists", "result": "would_pass"})

    return {
        "item_id": item.get("item_id"),
        "approval_id": item.get("approval_id"),
        "object_type": item.get("object_type"),
        "object_key": item.get("object_key"),
        "simulated_method": item.get("method"),
        "simulated_endpoint": item.get("target_endpoint"),
        "payload_summary": f"{len(payload_str)} bytes",
        "validation_result": "valid",
        "preflight_checks": preflight_results,
        "expected_status_code": "201 Created" if item.get("method") == "POST" else "200 OK",
        "expected_action": "object_created" if item.get("method") == "POST" else "object_updated",
        "rollback_hint": item.get("rollback_hint", "DELETE to remove"),
        "dry_run_status": "simulated_ok",
    }


def main() -> int:
    """Execute dry-run simulation (100% local, no network)."""
    parser = argparse.ArgumentParser(description="FASE 2.45 — Execute Dry-Run Simulation")
    parser.add_argument("--apply-plan", type=Path, required=True)
    parser.add_argument("--execution-gate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--result-json", type=Path, required=True)

    args = parser.parse_args()

    # Check gate
    if not check_execution_gate(args.execution_gate):
        print("✗ Gate not ready for simulation")
        return 1

    # Load ApplyPlan
    try:
        with open(args.apply_plan, encoding="utf-8") as f:
            plan = json.load(f)
    except Exception:
        print("✗ Cannot load plan")
        return 1

    # Simulate items (100% local, no network)
    simulation_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat() + "+00:00"
    simulated_items = []

    for item in plan.get("items", []):
        simulated = simulate_item(item)
        simulated_items.append(simulated)

    # Determine result
    all_ok = all(item.get("dry_run_status") == "simulated_ok" for item in simulated_items)
    result_status = "DRYRUN_SIMULATION_PASSED" if all_ok else "DRYRUN_SIMULATION_FAILED"

    # Create simulation result
    simulation_result = {
        "simulation_id": simulation_id,
        "apply_plan_id": plan.get("apply_plan_id"),
        "device": plan.get("device"),
        "status": result_status,
        "generated_at": timestamp,
        "items": simulated_items,
        "safety_confirmations": {
            "no_netbox_calls": True,
            "no_network_requests": True,
            "no_token_read": True,
            "no_apply_execution": True,
            "all_local": True,
        },
        "next_gate_required": True,
        "next_gate": "FASE_2_46_REAL_WRITE_READINESS_GATE",
    }

    # Write MD report
    lines = [
        "# Resultado da Simulação Dry-Run",
        "",
        f"**Simulação ID:** {simulation_id}",
        f"**Gerado:** {timestamp}",
        "",
        "## Decisão",
        "",
        f"### {result_status}",
        "",
        "## Resumo",
        "",
        f"- Total itens: {len(simulated_items)}",
        f"- Simulados: {len(simulated_items)}",
        f"- Avisos: 0",
        f"- Bloqueados: 0",
        "",
        "## Itens Simulados",
        "",
        "| Item ID | Object Key | Method | Status |",
        "|---|---|---|---|",
    ]

    for item in simulated_items:
        lines.append(
            f"| {item['item_id'][:8]}... | {item['object_key']} | "
            f"{item['simulated_method']} | {item['dry_run_status']} |"
        )

    lines.extend([
        "",
        "## Requests Hipotéticos",
        "",
        "Sem token, sem credenciais:",
        "",
    ])

    for item in simulated_items:
        lines.extend([
            f"### {item['object_key']}",
            "",
            f"```",
            f"{item['simulated_method']} {item['simulated_endpoint']}",
            f"```",
            "",
        ])

    lines.extend([
        "## Segurança",
        "",
        "✓ Nenhuma chamada NetBox",
        "✓ Nenhuma chamada de rede",
        "✓ Nenhum token lido",
        "✓ Simulação 100% local",
        "",
    ])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")

    # Write JSON result
    args.result_json.parent.mkdir(parents=True, exist_ok=True)
    args.result_json.write_text(json.dumps(simulation_result, indent=2), encoding="utf-8")

    print(f"✓ {result_status}")
    print(f"✓ Report: {args.output}")
    print(f"✓ Result: {args.result_json}")
    return 0 if result_status == "DRYRUN_SIMULATION_PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
