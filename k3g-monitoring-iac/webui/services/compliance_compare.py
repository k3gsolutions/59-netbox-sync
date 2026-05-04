"""Local compliance compare engine.

No NetBox writes. No SSH/SNMP/NETCONF. No auto-remediation.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .compliance_jobs import JOBS_BASE, load_compliance_job
from .compliance_policy_loader import (
    get_policy,
    load_compliance_policy_registry,
    summarize_policy_registry,
)


COMPARE_PREFIX = "CMP"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dump_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _safe_job_dir(job_id: str, jobs_base: Optional[Path] = None) -> Path:
    return (jobs_base or JOBS_BASE) / job_id


def _new_finding_id() -> str:
    return f"{COMPARE_PREFIX}-{uuid.uuid4().hex[:10].upper()}"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _reports_root() -> Path:
    return JOBS_BASE.parents[1]


def _report_path(path: Path) -> str:
    try:
        return str(path.relative_to(_reports_root()))
    except Exception:
        return str(path)


def _severity_rank(severity: str) -> int:
    order = {"info": 0, "warning": 1, "error": 2, "blocker": 3}
    return order.get(str(severity).lower(), 0)


def classify_finding(finding: dict[str, Any], severity_policy: dict[str, Any]) -> dict[str, Any]:
    """Normalize finding severity using the severity policy registry."""
    finding = dict(finding)
    rule_id = str(finding.get("rule_id") or "").strip()
    severity = str(finding.get("severity") or "").strip().lower()
    default_mapping = (severity_policy or {}).get("default_mapping") or {}
    overrides = (severity_policy or {}).get("rule_severity_overrides") or {}
    if rule_id in overrides:
        severity = str(overrides[rule_id]).strip().lower()
    elif not severity:
        finding_type = str(finding.get("finding_type") or "optional_enrichment").strip().lower()
        severity = str(default_mapping.get(finding_type) or default_mapping.get("optional_enrichment") or "info").lower()
    if severity not in {"info", "warning", "error", "blocker"}:
        severity = "info"
    finding["severity"] = severity
    finding["severity_rank"] = _severity_rank(severity)
    return finding


def _make_finding(
    device_id: Any,
    scope: str,
    object_type: str,
    object_name: str,
    rule_id: str,
    severity: str,
    title: str,
    description: str,
    evidence: dict[str, Any],
    recommendation: str,
    finding_type: str = "optional_enrichment",
) -> dict[str, Any]:
    return {
        "finding_id": _new_finding_id(),
        "device_id": device_id,
        "scope": scope,
        "object_type": object_type,
        "object_name": object_name,
        "rule_id": rule_id,
        "severity": severity,
        "status": "open",
        "title": title,
        "description": description,
        "evidence": evidence,
        "recommendation": recommendation,
        "write_required": False,
        "approval_required": False,
        "finding_type": finding_type,
    }


def _name_matches_any(name: str, patterns: list[str]) -> bool:
    return any(re.match(pattern, name) for pattern in patterns if pattern)


def compare_interfaces(parsed_inventory: dict[str, Any], registry: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    naming = get_policy(registry, "naming-conventions.yaml")
    patterns = list((((naming.get("interface") or {}).get("base_inventory_patterns")) or []))
    service_patterns = list((((naming.get("interface") or {}).get("service_interface_patterns")) or []))
    interfaces = list(parsed_inventory.get("interfaces") or [])
    if not interfaces:
        findings.append(
            _make_finding(
                parsed_inventory.get("device_id"),
                "interface",
                "interface",
                "*",
                "interface.inventory.missing",
                "info",
                "Nenhuma interface parseada",
                "Parsed inventory sem interfaces para avaliar.",
                {"source": "parsed_inventory", "field": "interfaces", "value": None},
                "Verificar se a coleta/parse capturou os comandos de interface.",
                "data_missing_for_check",
            )
        )
        return findings

    for item in interfaces:
        name = str(item.get("name") or "")
        description = item.get("description")
        physical = str(item.get("physical") or "").lower()
        protocol = str(item.get("protocol") or "").lower()
        if not description:
            findings.append(
                _make_finding(
                    parsed_inventory.get("device_id"),
                    "interface",
                    "interface",
                    name,
                    "interface.description.required",
                    "warning",
                    "Interface sem descrição",
                    "Interface parseada sem campo description.",
                    {"source": "parsed_inventory", "field": "interfaces[].description", "value": description},
                    "Adicionar descrição na interface.",
                )
            )
        if physical and protocol and physical != protocol:
            findings.append(
                _make_finding(
                    parsed_inventory.get("device_id"),
                    "interface",
                    "interface",
                    name,
                    "interface.state.mismatch",
                    "warning",
                    "Estado físico/protocolo inconsistente",
                    "Physical e protocol não batem no resumo parseado.",
                    {
                        "source": "parsed_inventory",
                        "field": "interfaces[].physical/protocol",
                        "value": {"physical": physical, "protocol": protocol},
                    },
                    "Revisar estado operacional da interface.",
                )
            )
        if "." in name:
            if not _name_matches_any(name, service_patterns):
                findings.append(
                    _make_finding(
                        parsed_inventory.get("device_id"),
                        "interface",
                        "interface",
                        name,
                        "interface.naming.invalid",
                        "error",
                        "Nomenclatura de subinterface fora do padrão",
                        "Subinterface não segue naming convention.",
                        {"source": "parsed_inventory", "field": "interfaces[].name", "value": name},
                        "Ajustar nome conforme naming-conventions.yaml.",
                    )
                )
        elif not _name_matches_any(name, patterns):
            findings.append(
                _make_finding(
                    parsed_inventory.get("device_id"),
                    "interface",
                    "interface",
                    name,
                    "interface.naming.invalid",
                    "warning",
                    "Nomenclatura de interface fora do padrão",
                    "Nome de interface não bate com base_inventory_patterns.",
                    {"source": "parsed_inventory", "field": "interfaces[].name", "value": name},
                    "Revisar nomenclatura da interface.",
                )
            )
    return findings


def compare_bgp(parsed_inventory: dict[str, Any], registry: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    bgp_policy = get_policy(registry, "bgp-policy.yaml")
    naming = get_policy(registry, "naming-conventions.yaml")
    peer_patterns = list((((bgp_policy.get("bgp_peer") or {}).get("validation_rules") or [])))
    peers = list(parsed_inventory.get("bgp_peers") or [])
    if not peers:
        findings.append(
            _make_finding(
                parsed_inventory.get("device_id"),
                "bgp",
                "bgp_peer",
                "*",
                "bgp.peer.missing",
                "info",
                "Nenhum peer BGP parseado",
                "Parsed inventory sem peers BGP.",
                {"source": "parsed_inventory", "field": "bgp_peers", "value": None},
                "Verificar se o comando display bgp peer foi coletado.",
                "data_missing_for_check",
            )
        )
        return findings

    import_export_policy = (bgp_policy.get("bgp_policy_requirements") or {})
    for item in peers:
        peer_ip = str(item.get("peer_ip") or "")
        state = str(item.get("state") or "").strip()
        if not item.get("description"):
            findings.append(
                _make_finding(
                    parsed_inventory.get("device_id"),
                    "bgp",
                    "bgp_peer",
                    peer_ip,
                    "bgp.peer.description.required",
                    "warning",
                    "BGP peer sem descrição",
                    "Peer BGP sem description no inventário parseado.",
                    {"source": "parsed_inventory", "field": "bgp_peers[].description", "value": item.get("description")},
                    "Revisar cadastro/descrição do peer.",
                )
            )
        if not item.get("import_policy") or not item.get("export_policy"):
            findings.append(
                _make_finding(
                    parsed_inventory.get("device_id"),
                    "bgp",
                    "bgp_peer",
                    peer_ip,
                    "bgp.peer.policy.missing",
                    "warning",
                    "BGP peer sem política import/export",
                    "Peer sem import_policy ou export_policy detectada.",
                    {
                        "source": "parsed_inventory",
                        "field": "bgp_peers[].import_policy/export_policy",
                        "value": {"import_policy": item.get("import_policy"), "export_policy": item.get("export_policy")},
                    },
                    "Confirmar políticas de importação e exportação.",
                )
            )
        if state and state.lower() != "established":
            findings.append(
                _make_finding(
                    parsed_inventory.get("device_id"),
                    "bgp",
                    "bgp_peer",
                    peer_ip,
                    "bgp.peer.state.not_established",
                    "warning",
                    "Peer BGP fora de Established",
                    f"Peer em estado {state or 'unknown'}.",
                    {"source": "parsed_inventory", "field": "bgp_peers[].state", "value": state},
                    "Validar sessão BGP e estabilidade do peer.",
                )
            )
        # Naming convention reference on peer_group/import/export names if present.
        for field in ("peer_group", "import_policy", "export_policy"):
            value = item.get(field)
            if value and not re.match(naming.get("route_policy", {}).get("pattern", r".+"), str(value)):
                findings.append(
                    _make_finding(
                        parsed_inventory.get("device_id"),
                        "bgp",
                        "bgp_peer",
                        peer_ip,
                        "bgp.peer.policy.naming.invalid",
                        "info",
                        f"Nome fora do padrão em {field}",
                        f"{field} não parece seguir a nomenclatura esperada.",
                        {"source": "parsed_inventory", "field": f"bgp_peers[].{field}", "value": value},
                        "Revisar nomenclatura do peer/policy.",
                    )
                )
    return findings


def compare_route_policies(parsed_inventory: dict[str, Any], registry: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    route_policy_policy = get_policy(registry, "route-policy-policy.yaml")
    naming = get_policy(registry, "naming-conventions.yaml")
    route_policies = dict(parsed_inventory.get("route_policies") or {})
    prefix_lists = set((parsed_inventory.get("ip_prefixes") or {}).keys()) | set((parsed_inventory.get("ipv6_prefixes") or {}).keys())
    if not route_policies:
        findings.append(
            _make_finding(
                parsed_inventory.get("device_id"),
                "route_policy",
                "route_policy",
                "*",
                "route_policy.missing",
                "info",
                "Nenhuma route-policy parseada",
                "Parsed inventory sem route-policies.",
                {"source": "parsed_inventory", "field": "route_policies", "value": None},
                "Verificar se o comando display route-policy foi coletado.",
                "data_missing_for_check",
            )
        )
        return findings

    for name, policy in route_policies.items():
        nodes = list(policy.get("nodes") or [])
        if not nodes:
            findings.append(
                _make_finding(
                    parsed_inventory.get("device_id"),
                    "route_policy",
                    "route_policy",
                    name,
                    "route_policy.nodes.missing",
                    "warning",
                    "Route-policy sem nodes",
                    "Route-policy presente sem nodes parseados.",
                    {"source": "parsed_inventory", "field": "route_policies[].nodes", "value": []},
                    "Adicionar nodes na route-policy.",
                )
            )
        if not re.match(naming.get("route_policy", {}).get("pattern", r".+"), name):
            findings.append(
                _make_finding(
                    parsed_inventory.get("device_id"),
                    "route_policy",
                    "route_policy",
                    name,
                    "route_policy.naming.invalid",
                    "warning",
                    "Route-policy fora do padrão",
                    "Nome não segue naming convention.",
                    {"source": "parsed_inventory", "field": "route_policies[].name", "value": name},
                    "Revisar nomenclatura da route-policy.",
                )
            )
        for node in nodes:
            statements = node.get("statements") or []
            for statement in statements:
                match = re.search(r"if-match\s+ip-prefix\s+(\S+)", str(statement), re.I)
                if match and match.group(1) not in prefix_lists:
                    findings.append(
                        _make_finding(
                            parsed_inventory.get("device_id"),
                            "route_policy",
                            "route_policy",
                            name,
                            "route_policy.reference.broken",
                            "error",
                            "Referência quebrada em route-policy",
                            "Node referencia ip-prefix inexistente.",
                            {
                                "source": "parsed_inventory",
                                "field": "route_policies[].nodes[].statements",
                                "value": statement,
                            },
                            "Criar ou ajustar o prefix-list referenciado.",
                        )
                    )
                if re.search(r"if-match\s+community", str(statement), re.I):
                    # Minimal check: community reference exists when any community list policy is present.
                    if not (get_policy(registry, "community-policy.yaml") or {}).get("community_filter"):
                        findings.append(
                            _make_finding(
                                parsed_inventory.get("device_id"),
                                "route_policy",
                                "route_policy",
                                name,
                                "route_policy.reference.broken",
                                "warning",
                                "Referência de community não validada",
                                "Community filter não localizado no registry.",
                                {
                                    "source": "parsed_inventory",
                                    "field": "route_policies[].nodes[].statements",
                                    "value": statement,
                                },
                                "Revisar community filters no registry.",
                            )
                        )
    return findings


def compare_prefix_lists(parsed_inventory: dict[str, Any], registry: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    naming = get_policy(registry, "naming-conventions.yaml")
    ip_policy = get_policy(registry, "ip-prefix-policy.yaml")
    all_prefixes = {}
    all_prefixes.update(parsed_inventory.get("ip_prefixes") or {})
    all_prefixes.update(parsed_inventory.get("ipv6_prefixes") or {})
    if not all_prefixes:
        findings.append(
            _make_finding(
                parsed_inventory.get("device_id"),
                "prefix_list",
                "prefix_list",
                "*",
                "prefix_list.missing",
                "info",
                "Nenhum prefix-list parseado",
                "Parsed inventory sem prefix-lists.",
                {"source": "parsed_inventory", "field": "ip_prefixes/ipv6_prefixes", "value": None},
                "Verificar se os comandos display ip ip-prefix / display ipv6 prefix foram coletados.",
                "data_missing_for_check",
            )
        )
        return findings

    patterns = list((naming.get("ip_prefix") or {}).get("patterns") or [])
    for name, data in all_prefixes.items():
        entries = list(data.get("entries") or [])
        if not entries:
            findings.append(
                _make_finding(
                    parsed_inventory.get("device_id"),
                    "prefix_list",
                    "prefix_list",
                    name,
                    "prefix_list.entries.missing",
                    "warning",
                    "Prefix-list vazia",
                    "Prefix-list presente sem entries.",
                    {"source": "parsed_inventory", "field": "ip_prefixes[].entries", "value": []},
                    "Adicionar entries válidas ao prefix-list.",
                )
            )
        if patterns and not _name_matches_any(name, patterns):
            findings.append(
                _make_finding(
                    parsed_inventory.get("device_id"),
                    "prefix_list",
                    "prefix_list",
                    name,
                    "prefix_list.naming.invalid",
                    "warning",
                    "Prefix-list fora do padrão",
                    "Nome de prefix-list não segue naming convention.",
                    {"source": "parsed_inventory", "field": "ip_prefixes[].name", "value": name},
                    "Revisar naming convention do prefix-list.",
                )
            )
    return findings


def compare_snmp(parsed_inventory: dict[str, Any], registry: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    snmp_policy = get_policy(registry, "snmp-policy.yaml")
    snmp = parsed_inventory.get("snmp") or {}
    if not snmp:
        findings.append(
            _make_finding(
                parsed_inventory.get("device_id"),
                "snmp",
                "snmp",
                "*",
                "snmp.sys_info.missing",
                "warning",
                "SNMP sys-info ausente",
                "Nenhum bloco SNMP encontrado no inventário parseado.",
                {"source": "parsed_inventory", "field": "snmp", "value": None},
                "Verificar se o comando display snmp-agent sys-info foi coletado.",
                "data_missing_for_check",
            )
        )
        return findings

    if not snmp.get("sys_name") and not snmp.get("lines"):
        findings.append(
            _make_finding(
                parsed_inventory.get("device_id"),
                "snmp",
                "snmp",
                "*",
                "snmp.sys_info.missing",
                "info",
                "SNMP sys-info parcial",
                "SNMP parseado sem sys_name.",
                {"source": "parsed_inventory", "field": "snmp.sys_name", "value": snmp.get("sys_name")},
                "Completar dados de SNMP no inventário.",
                "data_missing_for_check",
            )
        )
    return findings


def compare_device_inventory_to_policy(parsed_inventory: dict[str, Any], registry: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    findings.extend(compare_interfaces(parsed_inventory, registry))
    findings.extend(compare_bgp(parsed_inventory, registry))
    findings.extend(compare_route_policies(parsed_inventory, registry))
    findings.extend(compare_prefix_lists(parsed_inventory, registry))
    findings.extend(compare_snmp(parsed_inventory, registry))

    severity_policy = get_policy(registry, "compliance-severity-policy.yaml")
    return [classify_finding(finding, severity_policy) for finding in findings]


def _load_parsed_inventory_files(job_id: str, jobs_base: Optional[Path] = None) -> list[dict[str, Any]]:
    job_dir = _safe_job_dir(job_id, jobs_base)
    results_dir = job_dir / "collection-results"
    inventories: list[dict[str, Any]] = []
    for path in sorted(results_dir.glob("devices/*/parsed/parsed-inventory.json")):
        inventory = _load_json(path)
        if inventory:
            inventories.append({"path": path, "inventory": inventory})
    return inventories


def compare_job(job_id: str, jobs_base: Optional[Path] = None, policy_dir: str | Path = "policies/compliance") -> dict[str, Any]:
    """Compare parsed inventory against compliance policies."""
    job = load_compliance_job(job_id, jobs_base)
    job_dir = _safe_job_dir(job_id, jobs_base)
    results_dir = job_dir / "comparison"
    results_dir.mkdir(parents=True, exist_ok=True)

    parser_result = job.get("parser_result") or {}
    parser_validation = job.get("parser_safety_validation") or {}
    if not parser_result or parser_validation.get("decision") == "PARSER_SAFETY_INVALID":
        raise ValueError("parser preconditions not satisfied")

    registry = load_compliance_policy_registry(policy_dir)
    validation = registry.get("validation") or {}
    if not validation.get("valid"):
        raise ValueError("policy registry invalid")

    inventories = _load_parsed_inventory_files(job_id, jobs_base)
    if not inventories:
        raise ValueError("parsed inventory missing")

    device_results: list[dict[str, Any]] = []
    findings_total: list[dict[str, Any]] = []
    for item in inventories:
        inventory = item["inventory"]
        device_findings = compare_device_inventory_to_policy(inventory, registry)
        findings_total.extend(device_findings)
        device_id = str(inventory.get("device_id") or "unknown")
        device_payload = {
            "device_id": inventory.get("device_id"),
            "name": inventory.get("name"),
            "profile": inventory.get("profile"),
            "findings": device_findings,
            "summary": {
                "findings_total": len(device_findings),
                "blockers": sum(1 for finding in device_findings if finding.get("severity") == "blocker"),
                "errors": sum(1 for finding in device_findings if finding.get("severity") == "error"),
                "warnings": sum(1 for finding in device_findings if finding.get("severity") == "warning"),
                "info": sum(1 for finding in device_findings if finding.get("severity") == "info"),
            },
            "safety": {
                "netbox_write": False,
                "device_connection": False,
                "sync_called": False,
                "approval_record_created": False,
                "apply_plan_created": False,
            },
            "files": {
                "findings_json": str(results_dir / "devices" / device_id / "compliance-findings.json"),
                "findings_markdown": str(results_dir / "devices" / device_id / "COMPLIANCE-FINDINGS.md"),
                "findings_markdown_report_path": _report_path(results_dir / "devices" / device_id / "COMPLIANCE-FINDINGS.md"),
            },
        }
        device_results.append(device_payload)

        device_out_dir = results_dir / "devices" / device_id
        device_out_dir.mkdir(parents=True, exist_ok=True)
        _dump_json(device_out_dir / "compliance-findings.json", device_payload)
        lines = [
            "# COMPLIANCE-FINDINGS",
            "",
            f"## Device\n`{device_payload['name']}`",
            "",
            "## Summary",
            f"- findings_total: {device_payload['summary']['findings_total']}",
            f"- blockers: {device_payload['summary']['blockers']}",
            f"- errors: {device_payload['summary']['errors']}",
            f"- warnings: {device_payload['summary']['warnings']}",
            f"- info: {device_payload['summary']['info']}",
            "",
            "## Findings",
        ]
        if device_findings:
            for finding in device_findings:
                lines.extend(
                    [
                        "",
                        f"### {finding.get('severity')} - {finding.get('title')}",
                        f"- scope: {finding.get('scope')}",
                        f"- object: {finding.get('object_name')}",
                        f"- rule: {finding.get('rule_id')}",
                        f"- recommendation: {finding.get('recommendation')}",
                    ]
                )
        else:
            lines.append("- none")
        (device_out_dir / "COMPLIANCE-FINDINGS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    summary = {
        "devices": len(device_results),
        "findings_total": len(findings_total),
        "blockers": sum(1 for finding in findings_total if finding.get("severity") == "blocker"),
        "errors": sum(1 for finding in findings_total if finding.get("severity") == "error"),
        "warnings": sum(1 for finding in findings_total if finding.get("severity") == "warning"),
        "info": sum(1 for finding in findings_total if finding.get("severity") == "info"),
    }
    status = "COMPLIANCE_COMPARE_COMPLETED"
    if summary["blockers"] > 0:
        status = "COMPLIANCE_COMPARE_BLOCKED"
    elif summary["findings_total"] > 0:
        status = "COMPLIANCE_COMPARE_COMPLETED_WITH_FINDINGS"

    result_json = results_dir / "compliance-comparison-result.json"
    result_md = results_dir / "COMPLIANCE-COMPARISON-RESULT.md"
    job_result = {
        "job_id": job_id,
        "status": status,
        "decision": status,
        "parser_result": bool(parser_result),
        "parser_safety_validation": bool(parser_validation),
        "summary": summary,
        "safety": {
            "netbox_write": False,
            "device_connection": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False,
        },
        "registry": summarize_policy_registry(registry),
        "devices": device_results,
        "checked_at": _now(),
        "files": {
            "comparison_result": str(result_json),
            "comparison_result_markdown": str(result_md),
            "comparison_result_report_path": _report_path(result_md),
        },
    }

    _dump_json(result_json, job_result)
    lines = [
        "# COMPLIANCE-COMPARISON-RESULT",
        "",
        f"## Job ID\n`{job_id}`",
        "",
        f"## Status\n`{status}`",
        "",
        "## Summary",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Safety",
            "- netbox_write=false",
            "- device_connection=false",
            "- sync_called=false",
            "- approval_record_created=false",
            "- apply_plan_created=false",
        ]
    )
    result_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "job_id": job_id,
        "status": status,
        "decision": status,
        "summary": summary,
        "safety": job_result["safety"],
        "files": job_result["files"],
        "comparison_result": job_result,
    }
