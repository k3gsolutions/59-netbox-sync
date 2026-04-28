#!/usr/bin/env python3
"""Render ApprovalRecord as readable Markdown summary."""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Optional


def format_evidence(evidence: Dict) -> str:
    """Format evidence as readable markdown."""
    if not evidence:
        return "N/A"

    lines = []
    for key, value in evidence.items():
        if isinstance(value, dict):
            value_str = ", ".join(f"{k}={v}" for k, v in value.items())
        elif isinstance(value, (list, tuple)):
            value_str = ", ".join(str(v) for v in value)
        else:
            value_str = str(value)
        lines.append(f"- {key}: {value_str}")

    return "\n".join(lines) if lines else "N/A"


def render_approval_summary(record: Dict) -> str:
    """Render ApprovalRecord as Markdown summary."""
    lines = []

    device = record.get("device", "unknown")
    approval_id = record.get("approval_id", "unknown")[:8]
    proposal = record.get("proposal", {})
    review = record.get("review", {})
    audit = record.get("audit", {})

    # Header
    lines.append(f"# Approval Summary — {approval_id}")
    lines.append("")
    lines.append(f"**Device:** {device}")
    lines.append(f"**Status:** {review.get('status', 'unknown')}")
    lines.append("")

    # Proposal
    lines.append("## 1. Proposta")
    lines.append("")
    lines.append(f"- **Objeto:** {proposal.get('object_type')} / {proposal.get('object_key')}")
    lines.append(f"- **Código:** `{proposal.get('code')}`")
    lines.append(f"- **Ação:** {proposal.get('action')}")
    lines.append(f"- **Categoria:** {proposal.get('category', 'N/A')}")
    lines.append(f"- **Confiança:** {proposal.get('confidence')}")
    lines.append(f"- **Naming Conforme:** {'✓ Sim' if proposal.get('naming_compliant') else '✗ Não'}")
    lines.append("")
    lines.append(f"**Razão:** {proposal.get('reason', 'N/A')}")
    lines.append("")

    # Evidence
    lines.append("## 2. Evidência")
    lines.append("")
    lines.append(format_evidence(record.get("evidence", {})))
    lines.append("")

    # Riscos
    lines.append("## 3. Avaliação de Risco")
    lines.append("")

    action = proposal.get("action")
    category = proposal.get("category")
    naming_ok = proposal.get("naming_compliant")

    if action == "safe_create_staged" and category == "base_inventory":
        lines.append("🟢 **BAIXO RISCO**")
        lines.append("- Interface base (sem dependências de serviço)")
        lines.append("- Naming válido")
        lines.append("- Pode ser aprovado rapidamente")

    elif action == "safe_create_staged" and category == "service":
        if naming_ok:
            lines.append("🟡 **MÉDIO RISCO**")
            lines.append("- Interface de serviço (tem dependências)")
            lines.append("- Naming válido")
            lines.append("- Requer revisão de contexto (tenant, service_type)")
        else:
            lines.append("🔴 **ALTO RISCO — NÃO PODE APROVAR**")
            lines.append("- Interface de serviço")
            lines.append("- Naming INVÁLIDO")
            lines.append("- Deve ser rejeitado ou corrigido")

    elif action == "needs_review":
        lines.append("🔴 **ALTO RISCO**")
        lines.append("- Requer decisão humana")
        lines.append("- Dados insuficientes ou naming inválido")
        lines.append("- NÃO pode ser aprovado como está")

    lines.append("")

    # Checklist de aprovação
    lines.append("## 4. Checklist de Aprovação")
    lines.append("")

    if action == "safe_create_staged" and category == "base_inventory":
        lines.append("- [ ] Nome segue padrão base? (Ethernet, Eth-Trunk, Management)")
        lines.append("- [ ] Não é subinterface (sem ponto)?")
        lines.append("- [ ] Status UP ou esperado na topologia?")
        lines.append("- [ ] Não há conflito óbvio no NetBox?")
        lines.append("")
        lines.append("**Decisão:** APPROVE se todos os itens acima forem OK")

    elif action == "safe_create_staged" and category == "service":
        lines.append("- [ ] Nome segue padrão base.vlan_id? (ex: Eth-Trunk0.1580)")
        lines.append("- [ ] Tenant identificado?")
        lines.append("- [ ] Service_type identificado?")
        lines.append("- [ ] Criticality conhecido?")
        lines.append("- [ ] Não sobrescreve objeto existente?")
        lines.append("")
        if not naming_ok:
            lines.append("**Decisão:** REJECT — naming inválido, REQUEST_CHANGES")
        else:
            lines.append("**Decisão:** REQUEST_CHANGES se faltam metadados, APPROVE se tudo OK")

    else:
        lines.append("- [ ] Motivo de bloqueio está claro?")
        lines.append("- [ ] Pode ser desbloquei?")
        lines.append("")
        lines.append("**Decisão:** NÃO APROVAR (exige ação antes)")

    lines.append("")

    # Decisão pendente
    lines.append("## 5. Decisão Pendente")
    lines.append("")
    lines.append(f"**Status:** {review.get('status')}")
    lines.append(f"**Próximo Passo:** {proposal.get('preferred_next_step', 'N/A')}")
    lines.append("")

    lines.append("### Responda:")
    lines.append("1. Approve? Comment: (motivo da aprovação)")
    lines.append("2. Reject? Comment: (motivo da rejeição)")
    lines.append("3. Request Changes? Changes: (lista de mudanças solicitadas)")
    lines.append("")

    # Auditoria
    lines.append("## 6. Auditoria")
    lines.append("")
    lines.append(f"- **Criado em:** {record.get('generated_at')}")
    lines.append(f"- **Relatório:** {audit.get('report_path')}")
    lines.append(f"- **Timestamp Relatório:** {audit.get('report_timestamp')}")
    lines.append(f"- **Evidence Hash:** `{audit.get('evidence_hash', 'N/A')[:20]}...`")
    lines.append("")

    lines.append("## 7. Segurança")
    lines.append("")
    lines.append("✅ **Read-only — Nenhuma escrita no NetBox**")
    lines.append("✅ **Nenhuma credencial em ApprovalRecord**")
    lines.append("✅ **Auditável (approval_id, timestamp, hash)**")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Render ApprovalRecord as readable Markdown summary"
    )
    parser.add_argument("approval_record", help="ApprovalRecord JSON file path")
    parser.add_argument(
        "--output",
        help="Output file path (default: stdout)",
    )
    args = parser.parse_args()

    # Read approval record
    try:
        with open(args.approval_record, "r", encoding="utf-8") as f:
            record = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {args.approval_record}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        return 1

    # Render
    summary = render_approval_summary(record)

    # Output
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(summary)
        print(f"✓ Rendered: {output_path}")
    else:
        print(summary)

    return 0


if __name__ == "__main__":
    sys.exit(main())
