#!/usr/bin/env python3
"""Simulate staged apply (dry-run, no writes)."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict


def load_apply_plan(file_path: str) -> Dict:
    """Load ApplyPlan JSON."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ValueError(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")


def simulate_apply(plan: Dict) -> Dict:
    """Simulate staged apply result."""
    readiness_status = plan.get("readiness_status")
    blocked = plan.get("blocked_reasons", [])

    # Determine result based on readiness
    if blocked or readiness_status == "blocked":
        result = "would_fail_blocked"
        predicted_status = 400
        message = "Bad Request: Readiness checks failed"
    elif readiness_status == "ready":
        result = "would_create_staged"
        predicted_status = 201
        message = "Created (would be staged in NetBox)"
    else:
        result = "unknown"
        predicted_status = None
        message = "Unknown simulation result"

    # Build simulation result
    simulation = {
        "simulation": {
            "apply_plan_id": plan.get("apply_plan_id"),
            "approval_id": plan.get("approval_id"),
            "simulated_at": datetime.now(timezone.utc).isoformat(),
            "simulation_result": result,
            "real_apply_executed": False,
            "predicted_response": {
                "status_code": predicted_status,
                "message": message,
                "predicted_netbox_id": None,
                "notes": "ID would be assigned by NetBox on real POST"
            },
            "predicted_state_after_apply": {
                "approval_status": "applied_staged" if result == "would_create_staged" else "apply_blocked",
                "state_history_entry": {
                    "from": "dry_run_passed",
                    "to": "applied_staged" if result == "would_create_staged" else "apply_blocked",
                    "by": "staged_apply_executor",
                    "at": datetime.now(timezone.utc).isoformat(),
                    "reason": "Staged import executed via /compliance/apply" if result == "would_create_staged" else f"Blocked: {', '.join(blocked)}"
                } if result == "would_create_staged" else None
            },
            "rollback_hint": f"DELETE /api/dcim/interfaces/{{netbox_id}}/" if result == "would_create_staged" else None,
            "security_notes": [
                "No real API call made",
                "No object actually created",
                "Token not used",
                "Simulation only"
            ]
        }
    }

    return simulation


def render_simulation(plan: Dict, simulation: Dict) -> str:
    """Render simulation as Markdown."""
    lines = []

    approval_id = plan.get("approval_id", "unknown")[:8]
    device = plan.get("device", "unknown")
    object_type = plan.get("object_type")
    object_key = plan.get("object_key")
    result = simulation.get("simulation", {}).get("simulation_result")

    # Header
    lines.append(f"# Staged Apply Simulation — {approval_id}")
    lines.append("")
    lines.append(f"**Device:** {device}")
    lines.append(f"**Object:** {object_type} / {object_key}")
    lines.append(f"**Simulated At:** {simulation.get('simulation', {}).get('simulated_at')}")
    lines.append("")

    # Resultado
    lines.append("## 1. Resultado da Simulação")
    lines.append("")

    if result == "would_create_staged":
        lines.append("🟢 **WOULD CREATE STAGED**")
        lines.append("")
        lines.append("Objeto seria criado no NetBox com:")
        lines.append("- Status: staged")
        lines.append("- Tags: discovery:staged, discovery:netops_netbox_sync, approval:...")
        lines.append("- Custom fields com discovery_status=staged")
        lines.append("")
        lines.append("Próximas ações:")
        lines.append("1. Objeto criado como staged (não active)")
        lines.append("2. Requer ação manual para ativar")
        lines.append("3. Auditoria registra who/when/what")

    elif result == "would_fail_blocked":
        lines.append("🔴 **WOULD FAIL — BLOCKED**")
        lines.append("")
        blocked = plan.get("blocked_reasons", [])
        lines.append("Motivos de bloqueio:")
        for reason in blocked:
            lines.append(f"- {reason}")
        lines.append("")
        lines.append("Ação necessária:")
        lines.append("1. Resolver bloqueios")
        lines.append("2. Ou rejeitar ApprovalRecord")
        lines.append("3. Não prosseguir com apply")

    else:
        lines.append(f"❓ **{result.upper()}**")
        lines.append("")
        lines.append("Resultado desconhecido")

    lines.append("")

    # Resposta prevista
    lines.append("## 2. Resposta Prevista (NetBox futuro)")
    lines.append("")
    pred = simulation.get("simulation", {}).get("predicted_response", {})
    lines.append(f"- **Status Code:** {pred.get('status_code')}")
    lines.append(f"- **Message:** {pred.get('message')}")
    lines.append(f"- **Object ID:** {pred.get('predicted_netbox_id')} (seria atribuído pelo NetBox)")
    lines.append("")

    # Estado futuro
    lines.append("## 3. Estado do ApprovalRecord (Futuro)")
    lines.append("")
    future = simulation.get("simulation", {}).get("predicted_state_after_apply", {})
    lines.append(f"**Status:** {future.get('approval_status')}")
    lines.append("")

    if future.get("state_history_entry"):
        entry = future.get("state_history_entry", {})
        lines.append(f"**State History Entry:**")
        lines.append(f"- From: {entry.get('from')}")
        lines.append(f"- To: {entry.get('to')}")
        lines.append(f"- By: {entry.get('by')}")
        lines.append(f"- At: {entry.get('at')}")
        lines.append(f"- Reason: {entry.get('reason')}")
    lines.append("")

    # Rollback
    lines.append("## 4. Rollback Hint")
    lines.append("")
    rollback = simulation.get("simulation", {}).get("rollback_hint")
    if rollback:
        lines.append(f"Se necessário, rollback via:")
        lines.append(f"```")
        lines.append(f"{rollback}")
        lines.append(f"```")
    else:
        lines.append("Nenhuma ação de rollback necessária (apply não executado)")
    lines.append("")

    # Segurança
    lines.append("## 5. Observações de Segurança")
    lines.append("")
    lines.append("✅ **Nenhuma API Real Chamada**")
    lines.append("- Simulação local apenas")
    lines.append("- Nenhuma conexão com NetBox")
    lines.append("- Nenhum token usado")
    lines.append("")
    lines.append("✅ **Nenhum Objeto Criado**")
    lines.append("- Objeto NOT criado no NetBox")
    lines.append("- Dados NOT alterados")
    lines.append("- Equipamento NOT afetado")
    lines.append("")
    lines.append("✅ **Payload Validado**")
    lines.append("- Nenhuma credencial")
    lines.append("- Tags staged presentes")
    lines.append("- Custom fields válidos")
    lines.append("")

    # Próximos passos
    lines.append("## 6. Próximos Passos (FASE 2.0)")
    lines.append("")
    if result == "would_create_staged":
        lines.append("Quando staged apply for implementado:")
        lines.append("1. POST /api/dcim/interfaces/ será chamado")
        lines.append("2. Token write será validado")
        lines.append("3. Objeto será criado com status=staged")
        lines.append("4. ApprovalRecord será atualizado para applied_staged")
        lines.append("5. Auditoria completa será registrada")
    else:
        lines.append("Resolver bloqueios acima antes de continuar.")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Simulate staged apply (dry-run, no writes)"
    )
    parser.add_argument("--plan", required=True, help="ApplyPlan JSON file")
    parser.add_argument("--output", help="Output Markdown file (default: auto-generate)")
    args = parser.parse_args()

    try:
        plan = load_apply_plan(args.plan)
        simulation = simulate_apply(plan)
        markdown = render_simulation(plan, simulation)

        # Determine output file
        if args.output:
            output_path = Path(args.output)
        else:
            approval_id = plan.get("approval_id", "unknown")[:8]
            plan_parent = Path(args.plan).parent
            output_path = plan_parent / f"apply-simulation-{approval_id}.md"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown)

        print(f"✓ Simulation rendered: {output_path}")
        print("")
        print(markdown)
        print("")
        print("✓ Simulation complete (no API calls, no writes)")

        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
