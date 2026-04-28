from __future__ import annotations

from typing import Dict, List

from app.schemas.analyze import AnalyzeResult, AppliedInventorySummary
from app.schemas.compliance import ComplianceDivergence, SummaryDiffItem


def _format_bool(value: bool) -> str:
    return "Sim" if value else "Não"


def _render_summary_table(summary: AppliedInventorySummary) -> str:
    return (
        "| Métrica | Valor |\n"
        "|---|---|\n"
        f"| Interfaces | {summary.interfaces} |\n"
        f"| IPs | {summary.ip_addresses} |\n"
        f"| VRFs | {summary.vrfs} |\n"
        f"| VLANs | {summary.vlans} |\n"
        f"| Sessões BGP | {summary.bgp_sessions} |\n"
        f"| Route policies | {summary.route_policies} |\n"
        f"| Prefix lists | {summary.prefix_lists} |\n"
        f"| AS-path filters | {summary.as_path_filters} |\n"
        f"| Communities | {summary.communities} |\n"
        f"| Community lists | {summary.community_lists} |\n"
    )


def _render_summary_diff_table(diff_items: List[SummaryDiffItem]) -> str:
    if not diff_items:
        return "Nenhum diff agregado disponível."

    rows = ["| Métrica | Aplicado | Documentado | Delta | Status |\n|---|---|---|---|---|\n"]
    for item in diff_items:
        rows.append(
            f"| {item.metric} | {item.applied} | {item.documented} | {item.delta} | {item.status} |\n"
        )
    return "".join(rows)


def _separate_divergences(divergences: List[ComplianceDivergence]) -> tuple[List[ComplianceDivergence], List[ComplianceDivergence]]:
    """Separate aggregated divergences (no object_type) from object-level ones."""
    aggregated = []
    object_level = []
    for div in divergences:
        if not div.object_type or div.object_type.strip() in ("", "-"):
            aggregated.append(div)
        else:
            object_level.append(div)
    return aggregated, object_level


def _render_aggregated_divergences(divergences: List[ComplianceDivergence]) -> str:
    if not divergences:
        return "Nenhuma divergência agregada detectada."

    rows = [
        "| Severidade | Código | Escopo | Ação preferida | Mensagem |\n|---|---|---|---|---|\n"
    ]
    for div in divergences:
        rows.append(
            f"| {div.severity} | {div.code} | {div.scope} | {div.preferred_action} | {div.message} |\n"
        )
    return "".join(rows)


def _render_object_divergences(divergences: List[ComplianceDivergence]) -> str:
    if not divergences:
        return "Nenhuma divergência por objeto detectada."

    rows = [
        "| Severidade | Código | Tipo de objeto | Chave do objeto | Ação preferida | Mensagem |\n|---|---|---|---|---|---|\n"
    ]
    for div in divergences:
        rows.append(
            f"| {div.severity} | {div.code} | {div.object_type or '-'} | {div.object_key or '-'} | {div.preferred_action} | {div.message} |\n"
        )
    return "".join(rows)


def _render_warnings(warnings: List[Dict[str, str]]) -> str:
    if not warnings:
        return "Nenhum warning gerado."

    rows = ["| Severidade | Código | Mensagem |\n|---|---|---|\n"]
    for warning in warnings:
        rows.append(
            f"| {warning.get('severity')} | {warning.get('code')} | {warning.get('message')} |\n"
        )
    return "".join(rows)


def _group_actions(divergences: List[ComplianceDivergence]) -> Dict[str, List[str]]:
    """Group divergences by preferred_action, removing duplicates."""
    actions = {"fix_netbox": [], "fix_device": [], "review": []}
    seen = set()
    for div in divergences:
        action = div.preferred_action
        # Description includes code, type, key, message for uniqueness
        key = (div.code, div.object_type, div.object_key)
        if key not in seen:
            seen.add(key)
            description = f"{div.code}"
            if div.object_type and div.object_type.strip() not in ("", "-"):
                description += f" ({div.object_type}"
                if div.object_key and div.object_key.strip() not in ("", "-"):
                    description += f": {div.object_key}"
                description += ")"
            description += f" — {div.message}"
            actions.setdefault(action, []).append(description)
    return actions


def render_compliance_report(result: AnalyzeResult) -> str:
    status_geral = result.compliance_summary.status if result.compliance_summary else "não disponível"
    total_divergences = len(result.divergences)
    highest_severity = "Nenhuma"
    if result.divergences:
        severity_order = {"high": 3, "medium": 2, "low": 1, "info": 0}
        highest_severity = max(result.divergences, key=lambda d: severity_order.get(d.severity, 0)).severity

    report_lines = [
        f"# Relatório de Compliance — {result.hostname}\n",
        "## 1. Resumo executivo\n",
        f"- Hostname: {result.hostname}\n",
        f"- Device ID: {result.device_id or 'não informado'}\n",
        f"- Modo: {result.mode}\n",
        f"- NetBox carregado: {_format_bool(result.netbox_loaded)}\n",
        f"- Compliance habilitado: {_format_bool(result.compliance_enabled)}\n",
        f"- Status geral: {status_geral}\n",
        f"- Total de divergências: {total_divergences}\n",
        f"- Severidade mais alta: {highest_severity}\n",
        "\n## 2. Sumário aplicado no dispositivo\n",
        _render_summary_table(result.applied_summary),
        "\n## 3. Sumário documentado no NetBox\n",
    ]

    if result.documented_summary is None:
        report_lines.append("NetBox não foi carregado ou não foi possível obter o sumário documentado.\n")
    else:
        report_lines.append(_render_summary_table(result.documented_summary))

    report_lines.extend([
        "\n## 4. Diff agregado (por métrica)\n",
        _render_summary_diff_table(result.summary_diff),
    ])

    # Separate aggregated vs object-level divergences
    aggregated_divs, object_divs = _separate_divergences(result.divergences)

    report_lines.extend([
        "\n## 5. Divergências agregadas\n",
        _render_aggregated_divergences(aggregated_divs),
        "\n## 6. Divergências por objeto\n",
        _render_object_divergences(object_divs),
        "\n## 7. Warnings\n",
        _render_warnings([warning.model_dump() if hasattr(warning, 'model_dump') else warning for warning in result.warnings]),
        "\n## 8. Ações recomendadas\n",
    ])

    actions = _group_actions(result.divergences)
    for action, action_label in [
        ("fix_netbox", "Corrigir NetBox"),
        ("fix_device", "Corrigir equipamento"),
        ("review", "Revisão manual"),
    ]:
        report_lines.append(f"### {action_label}\n")
        if actions.get(action):
            for item in actions[action]:
                report_lines.append(f"- {item}\n")
        else:
            report_lines.append("- Nenhuma ação recomendada.\n")
        report_lines.append("\n")

    report_lines.extend([
        "## 9. Observações de segurança\n",
        "- Relatório gerado em modo read-only.\n",
        "- Nenhuma escrita no NetBox.\n",
        "- Nenhuma configuração aplicada no dispositivo.\n",
        "- /sync não foi usado neste relatório.\n",
        "- Comandos futuros exigem aprovação humana antes de execução.\n",
    ])

    return "".join(report_lines)
