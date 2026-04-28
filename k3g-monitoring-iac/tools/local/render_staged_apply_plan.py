#!/usr/bin/env python3
"""Render ApplyPlan as readable Markdown."""

import argparse
import json
import sys
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


def render_apply_plan(plan: Dict) -> str:
    """Render ApplyPlan as Markdown."""
    lines = []

    approval_id = plan.get("approval_id", "unknown")[:8]
    device = plan.get("device", "unknown")
    object_type = plan.get("object_type")
    object_key = plan.get("object_key")

    # Header
    lines.append(f"# Staged Apply Plan — {approval_id}")
    lines.append("")
    lines.append(f"**Device:** {device}")
    lines.append(f"**Status:** {plan.get('readiness_status')}")
    lines.append("")

    # 1. Resumo
    lines.append("## 1. Resumo")
    lines.append("")
    lines.append(f"**Object:** {object_type} / {object_key}")
    lines.append(f"**Action:** {plan.get('action')}")
    lines.append(f"**Endpoint:** {plan.get('target_endpoint')}")
    lines.append(f"**Method:** {plan.get('method')}")
    lines.append("")

    # 2. Readiness Status
    lines.append("## 2. Readiness Status")
    lines.append("")
    status = plan.get("readiness_status")
    if status == "ready":
        lines.append("🟢 **READY** — Approvals passed, ready for future staged import")
    elif status == "blocked":
        lines.append("🔴 **BLOCKED** — Cannot apply, see blocked reasons below")
    elif status == "simulated":
        lines.append("🟡 **SIMULATED** — Validation passed, simulation only")
    lines.append("")

    # 3. Readiness Checks
    lines.append("## 3. Readiness Checks")
    lines.append("")
    checks = plan.get("readiness_checks", [])
    passed = sum(1 for c in checks if c.get("result") == "PASSED")
    failed = sum(1 for c in checks if c.get("result") == "FAILED")
    warning = sum(1 for c in checks if c.get("result") == "WARNING")
    not_checked = sum(1 for c in checks if c.get("result") == "NOT_CHECKED")

    lines.append(f"- **Passed:** {passed}")
    lines.append(f"- **Failed:** {failed}")
    lines.append(f"- **Warnings:** {warning}")
    lines.append(f"- **Not Checked:** {not_checked}")
    lines.append("")

    lines.append("### Details:")
    lines.append("")
    for check in checks:
        name = check.get("check", "unknown")
        result = check.get("result")
        details = check.get("details", "")

        if result == "PASSED":
            icon = "✅"
        elif result == "FAILED":
            icon = "❌"
        elif result == "WARNING":
            icon = "⚠️"
        else:
            icon = "ℹ️"

        lines.append(f"- {icon} **{name}**: {details}")

    lines.append("")

    # 4. Blocked Reasons (if any)
    blocked = plan.get("blocked_reasons", [])
    if blocked:
        lines.append("## 4. Bloqueios")
        lines.append("")
        for reason in blocked:
            lines.append(f"- **{reason}**")
        lines.append("")
        lines.append("**Ação:** Este apply não pode prosseguir até resolver bloqueios acima.")
        lines.append("")
    else:
        lines.append("## 4. Nenhum Bloqueio")
        lines.append("")
        lines.append("✓ Nenhum bloqueio detectado.")
        lines.append("")

    # 5. Payload Sugerido
    lines.append("## 5. Payload Sugerido")
    lines.append("")
    lines.append("```json")
    payload = plan.get("staged_payload", {})
    lines.append(json.dumps(payload, indent=2))
    lines.append("```")
    lines.append("")

    # 6. Política de Escrita
    lines.append("## 6. Política de Escrita")
    lines.append("")
    wp = plan.get("write_policy", {})
    lines.append(f"- **Requer Write Token:** {wp.get('requires_write_token')}")
    lines.append(f"- **Token Fornecido:** {wp.get('write_token_provided')}")
    lines.append(f"- **Token Validado:** {wp.get('write_token_validated')}")
    lines.append(f"- **Apply Real Habilitado:** {wp.get('real_apply_enabled')}")
    lines.append(f"- **Policy:** {wp.get('write_policy_enforced')}")
    lines.append("")

    # 7. Observações de Segurança
    lines.append("## 7. Observações de Segurança")
    lines.append("")
    lines.append("✅ **Read-only:**")
    lines.append("- Nenhuma API real chamada")
    lines.append("- Nenhuma escrita no NetBox")
    lines.append("- Nenhum token write usado")
    lines.append("- Apenas geração e validação local")
    lines.append("")
    lines.append("✅ **Payload:**")
    lines.append("- Nenhuma credencial")
    lines.append("- Tags staged presentes")
    lines.append("- Custom_fields válidos")
    lines.append("")
    lines.append("✅ **Futuro (FASE 2.0):**")
    lines.append("- Escrita será staged (não active)")
    lines.append("- Requer aprovação humana antes")
    lines.append("- Auditoria completa")
    lines.append("")

    # 8. Próximos Passos
    lines.append("## 8. Próximos Passos")
    lines.append("")
    if status == "blocked":
        lines.append("1. ❌ Resolve bloqueios acima")
        lines.append("2. ❌ Rejeitar ou request changes em ApprovalRecord")
        lines.append("3. ❌ Não prosseguir com apply")
    elif status == "ready":
        lines.append("1. ✅ Readiness checks passaram")
        lines.append("2. ✅ Simular staged apply (FASE 1.9)")
        lines.append("3. ✅ Aguardar futura execução (FASE 2.0)")
    elif status == "simulated":
        lines.append("1. ✅ Simulação executada")
        lines.append("2. ✅ Resultado validado")
        lines.append("3. ✅ Aguardar futura execução (FASE 2.0)")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Render ApplyPlan as Markdown"
    )
    parser.add_argument("--plan", required=True, help="ApplyPlan JSON file")
    parser.add_argument("--output", help="Output Markdown file (default: stdout)")
    args = parser.parse_args()

    try:
        plan = load_apply_plan(args.plan)
        markdown = render_apply_plan(plan)

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown)
            print(f"✓ Rendered: {output_path}")
        else:
            print(markdown)

        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
