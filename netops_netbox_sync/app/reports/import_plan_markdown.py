"""Render ImportPlan as Markdown report."""

from app.schemas.import_plan import ImportPlan, ImportAction


def _format_evidence(evidence: dict) -> str:
    """Format evidence dict as readable text."""
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


def render_import_plan(plan: ImportPlan) -> str:
    """Render ImportPlan as Markdown.

    Structure:
    1. Resumo — overall counts
    2. Safe create staged — candidates for automatic import
    3. Revisão humana obrigatória — requires human decision
    4. Bloqueados — cannot import
    5. Ignorados — not import candidates
    6. Observações de segurança — read-only guarantees
    """
    lines = []

    # Title
    lines.append(f"# ImportPlan — {plan.device}")
    lines.append("")
    lines.append(f"**Gerado em:** {plan.generated_at}")
    if plan.device_id:
        lines.append(f"**Device ID:** {plan.device_id}")
    lines.append("")

    # Section 1: Resumo
    lines.append("## 1. Resumo")
    lines.append("")
    lines.append(f"- **Total de divergências:** {plan.total_items}")
    lines.append(f"- **Safe create staged:** {plan.safe_create_staged_count}")
    lines.append(f"- **Revisão obrigatória:** {plan.needs_review_count}")
    lines.append(f"- **Bloqueados:** {plan.blocked_count}")
    lines.append(f"- **Ignorados:** {plan.ignore_count}")
    lines.append("")

    # Section 2: Safe create staged
    safe_items = [item for item in plan.items if item.action == ImportAction.SAFE_CREATE_STAGED]
    lines.append("## 2. Safe create staged")
    lines.append("")
    if safe_items:
        # Separate base inventory from service
        base_items = [item for item in safe_items if item.category == "base_inventory"]
        service_items = [item for item in safe_items if item.category == "service"]
        other_items = [item for item in safe_items if item.category not in ("base_inventory", "service")]

        # Base inventory section
        if base_items:
            lines.append("### Base Inventory")
            lines.append("")
            lines.append("Interfaces físicas, LAGs, management (infraestrutura base):")
            lines.append("")
            for item in base_items:
                lines.append(f"#### {item.object_type.upper()}: {item.object_key}")
                lines.append("")
                lines.append(f"**Código:** `{item.code}`")
                lines.append(f"**Confiança:** {item.confidence.value}")
                lines.append(f"**Próximo passo:** {item.preferred_next_step}")
                lines.append("")
                lines.append("**Evidência:**")
                lines.append(_format_evidence(item.evidence))
                lines.append("")

        # Service section
        if service_items:
            lines.append("### Service Candidates")
            lines.append("")
            lines.append("Interfaces de serviço, subinterfaces (com naming conforme):")
            lines.append("")
            for item in service_items:
                lines.append(f"#### {item.object_type.upper()}: {item.object_key}")
                lines.append("")
                lines.append(f"**Código:** `{item.code}`")
                lines.append(f"**Confiança:** {item.confidence.value}")
                lines.append(f"**Próximo passo:** {item.preferred_next_step}")
                lines.append("")
                lines.append("**Evidência:**")
                lines.append(_format_evidence(item.evidence))
                lines.append("")

        # Other types
        if other_items:
            lines.append("### Other")
            lines.append("")
            for item in other_items:
                lines.append(f"#### {item.object_type.upper()}: {item.object_key}")
                lines.append("")
                lines.append(f"**Código:** `{item.code}`")
                lines.append(f"**Confiança:** {item.confidence.value}")
                lines.append(f"**Próximo passo:** {item.preferred_next_step}")
                lines.append("")
                lines.append("**Evidência:**")
                lines.append(_format_evidence(item.evidence))
                lines.append("")
    else:
        lines.append("Nenhum candidato a staged import neste relatório.")
        lines.append("")

    # Section 3: Revisão humana obrigatória
    review_items = [item for item in plan.items if item.action == ImportAction.NEEDS_REVIEW]
    lines.append("## 3. Revisão humana obrigatória")
    lines.append("")
    if review_items:
        lines.append("Divergências que requerem decisão humana:")
        lines.append("")
        for item in review_items:
            lines.append(f"### {item.object_type.upper()}: {item.object_key}")
            lines.append("")
            lines.append(f"**Código:** `{item.code}`")
            lines.append(f"**Razão:** {item.reason}")
            lines.append(f"**Confiança:** {item.confidence.value}")
            if item.naming_compliant:
                lines.append("**Naming:** ✓ Conforme")
            else:
                lines.append("**Naming:** ✗ Fora da convention")
            lines.append(f"**Próximo passo:** {item.preferred_next_step}")
            lines.append("")
            lines.append("**Evidência:**")
            lines.append(_format_evidence(item.evidence))
            lines.append("")
    else:
        lines.append("Nenhuma divergência requerendo revisão.")
        lines.append("")

    # Section 4: Bloqueados
    blocked_items = [item for item in plan.items if item.action == ImportAction.BLOCKED]
    lines.append("## 4. Bloqueados")
    lines.append("")
    if blocked_items:
        lines.append("Não podem ser importados (metadados insuficientes ou ambíguos):")
        lines.append("")
        for item in blocked_items:
            lines.append(f"### {item.object_type.upper()}: {item.object_key}")
            lines.append("")
            lines.append(f"**Código:** `{item.code}`")
            lines.append(f"**Razão:** {item.reason}")
            lines.append(f"**Próximo passo:** {item.preferred_next_step}")
            lines.append("")
            lines.append("**Evidência:**")
            lines.append(_format_evidence(item.evidence))
            lines.append("")
    else:
        lines.append("Nenhuma divergência bloqueada.")
        lines.append("")

    # Section 5: Ignorados
    ignore_items = [item for item in plan.items if item.action == ImportAction.IGNORE]
    lines.append("## 5. Ignorados")
    lines.append("")
    if ignore_items:
        lines.append("Não são candidatos a importação:")
        lines.append("")
        for item in ignore_items:
            lines.append(f"- **{item.code}**: {item.reason}")
    else:
        lines.append("Nenhuma divergência ignorada.")
    lines.append("")

    # Section 6: Observações de segurança
    lines.append("## 6. Observações de segurança")
    lines.append("")
    lines.append("✅ **Read-only — Nenhuma ação executada**")
    lines.append("")
    lines.append("- Este relatório é **somente informativo**")
    lines.append("- Nenhuma escrita no NetBox realizada")
    lines.append("- Nenhum comando enviado ao equipamento")
    lines.append("- Nenhuma staged import executada")
    lines.append("- Token de escrita não foi utilizado")
    lines.append("")
    lines.append("**Próximas ações:**")
    lines.append("")
    lines.append("1. Revisar divergências na seção 3 (Revisão humana)")
    lines.append("2. Validar candidates na seção 2 (Safe create staged)")
    lines.append("3. Resolver divergências bloqueadas (seção 4)")
    lines.append("4. Iniciar staged import apenas após aprovação humana")
    lines.append("")

    return "\n".join(lines)
