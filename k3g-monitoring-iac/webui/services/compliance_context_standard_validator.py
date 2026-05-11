"""Context standard validation for compliance analysis artifacts."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .compliance_context_classifier import CONTEXTS, classify_job_contexts
from .compliance_jobs import JOBS_BASE
from .compliance_policy_loader import get_policy, load_compliance_policy_registry
from .validators import parse_interface_description


STATUS_WITHIN_STANDARD = "WITHIN_STANDARD"
STATUS_OUT_OF_STANDARD = "OUT_OF_STANDARD"
STATUS_NEEDS_STANDARDIZATION = "NEEDS_STANDARDIZATION"
STATUS_INFORMATIONAL_ALERT = "INFORMATIONAL_ALERT"

STATUS_LABELS = {
    STATUS_WITHIN_STANDARD: "Dentro do padrão",
    STATUS_OUT_OF_STANDARD: "Fora do padrão",
    STATUS_NEEDS_STANDARDIZATION: "Precisa padronizar",
    STATUS_INFORMATIONAL_ALERT: "Alerta informativo",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _safe_job_dir(job_id: str, jobs_base: Optional[Path] = None) -> Path:
    return (jobs_base or JOBS_BASE) / job_id


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _standard_declared(context_id: str, registry: dict[str, Any]) -> bool:
    if context_id == "security_access":
        return bool(get_policy(registry, "snmp-policy.yaml") or get_policy(registry, "ssh-readonly-collection-policy.yaml"))
    if context_id == "interfaces":
        return bool(get_policy(registry, "interface-policy.yaml") or get_policy(registry, "naming-conventions.yaml"))
    if context_id == "vpns":
        return bool(get_policy(registry, "vrf-policy.yaml"))
    if context_id == "bgp":
        return bool(
            get_policy(registry, "bgp-policy.yaml")
            or get_policy(registry, "route-policy-policy.yaml")
            or get_policy(registry, "ip-prefix-policy.yaml")
            or get_policy(registry, "community-policy.yaml")
        )
    return False


def validate_job_contexts(
    job_id: str,
    jobs_base: Optional[Path] = None,
    policy_dir: str | Path = "policies/compliance",
) -> dict[str, Any]:
    """Validate classified contexts against declared standards."""
    job_dir = _safe_job_dir(job_id, jobs_base)
    inventory = _load_json(job_dir / "analysis" / "context-inventory.json") or classify_job_contexts(job_id, jobs_base)
    registry = load_compliance_policy_registry(policy_dir)

    devices: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for device in inventory.get("devices") or []:
        context_results: list[dict[str, Any]] = []
        for context in device.get("contexts") or []:
            result = validate_context(device, context, registry)
            context_results.append(result)
            findings.extend(_findings_for_context(device, result))
        devices.append(
            {
                "device_id": device.get("device_id"),
                "name": device.get("name"),
                "contexts": context_results,
            }
        )

    summary = _summary(devices)
    payload = {
        "job_id": job_id,
        "validated_at": _now(),
        "layer": "post_parser_pre_compare",
        "summary": summary,
        "devices": devices,
        "findings": findings,
        "safety": _safety(),
        "files": {
            "context_validation": str(job_dir / "analysis" / "context-validation.json"),
            "context_findings": str(job_dir / "analysis" / "context-findings.json"),
        },
    }
    _dump_json(job_dir / "analysis" / "context-validation.json", payload)
    _dump_json(
        job_dir / "analysis" / "context-findings.json",
        {
            "job_id": job_id,
            "generated_at": payload["validated_at"],
            "summary": {"findings_total": len(findings), **summary["statuses"]},
            "findings": findings,
            "safety": payload["safety"],
        },
    )
    return payload


def validate_context(device: dict[str, Any], context: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    context_id = str(context.get("context_id") or "")
    optional = bool(context.get("optional"))
    items = list(context.get("items") or [])
    checks: list[dict[str, Any]] = []

    if optional:
        status = STATUS_INFORMATIONAL_ALERT
        checks.append(_check("optional_context", True, "Contexto opcional mapeado apenas para visibilidade operacional."))
    elif not _standard_declared(context_id, registry):
        status = STATUS_NEEDS_STANDARDIZATION
        checks.append(_check("standard_declared", False, "Nao ha padrao declarado ou validavel para este contexto."))
    else:
        checks.extend(_run_declared_checks(context_id, items, registry))
        failed = [item for item in checks if item.get("result") is False]
        unknown = [item for item in checks if item.get("result") is None]
        if not checks or unknown:
            status = STATUS_NEEDS_STANDARDIZATION
        elif failed:
            status = STATUS_OUT_OF_STANDARD
        else:
            status = STATUS_WITHIN_STANDARD

    return {
        "context_id": context_id,
        "label": context.get("label") or CONTEXTS.get(context_id, {}).get("label") or context_id,
        "description": context.get("description"),
        "optional": optional,
        "present": bool(context.get("present")),
        "items_count": int(context.get("items_count") or 0),
        "status": status,
        "status_label": STATUS_LABELS[status],
        "blocking": status == STATUS_OUT_OF_STANDARD and not optional,
        "human_summary": _human_summary(context, status),
        "checks": checks,
        "items": items,
    }


def _run_declared_checks(context_id: str, items: list[dict[str, Any]], registry: dict[str, Any]) -> list[dict[str, Any]]:
    if context_id == "security_access":
        return _validate_security(items)
    if context_id == "interfaces":
        return _validate_interfaces(items, registry)
    if context_id == "vpns":
        return _validate_vpns(items)
    if context_id == "bgp":
        return _validate_bgp(items, registry)
    return [_check("standard_declared", None, "Padrao declarado, mas sem validador especifico para este contexto.")]


def _validate_security(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not items:
        return [_check("security_visibility", False, "Nao foram encontrados sinais de SNMP, SSH, AAA, ACL ou usuario local na coleta parseada.")]
    checks = [_check("security_context_present", True, "Itens de seguranca/acesso detectados na coleta.")]
    blocked = [item for item in items if re.search(r"\b(public|private|secret|admin)\b", json.dumps(item, ensure_ascii=False), re.I)]
    checks.append(_check("blocked_access_terms_absent", not blocked, "Nao expor ou aceitar comunidades/termos inseguros conhecidos."))
    return checks


def _validate_interfaces(items: list[dict[str, Any]], registry: dict[str, Any]) -> list[dict[str, Any]]:
    if not items:
        return [_check("interface_inventory_present", False, "Nenhuma interface foi classificada.")]
    checks = [_check("interface_inventory_present", True, "Interfaces foram classificadas por tipo operacional.")]
    customer_like = [
        item for item in items
        if item.get("type") in {"physical", "subinterface", "eth_trunk", "vlanif"} and item.get("description")
    ]
    invalid_descriptions = []
    for item in customer_like:
        description = str(item.get("description") or "")
        if re.fullmatch(r"[\d.%\s]+", description):
            invalid_descriptions.append(item)
            continue
        valid, _, _ = parse_interface_description(description)
        if not valid:
            invalid_descriptions.append(item)
    checks.append(_check("interface_description_standard", not invalid_descriptions, "Descricoes de interfaces de servico devem seguir o padrao operacional."))
    return checks


def _validate_vpns(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not items:
        return [_check("vpn_context_visibility", None, "Nao ha elementos VPN detectados; confirmar se o dispositivo deveria declarar L2VC/VSI/VPLS/VPWS.")]
    return [_check("vpn_context_present", True, "Elementos VPN foram detectados e separados para revisao contextual.")]


def _validate_bgp(items: list[dict[str, Any]], registry: dict[str, Any]) -> list[dict[str, Any]]:
    peers = [item for item in items if item.get("type") == "bgp_peer"]
    policies = [item for item in items if item.get("type") == "route_policy"]
    prefixes = [item for item in items if item.get("type") == "ip_prefix"]
    checks: list[dict[str, Any]] = []
    if not peers:
        checks.append(_check("bgp_peer_present", False, "Nenhum peering BGP foi classificado."))
    else:
        checks.append(_check("bgp_peer_present", True, "Peerings BGP detectados."))
        checks.append(_check("bgp_remote_asn_present", all(peer.get("remote_asn") for peer in peers), "Todo peer deve ter ASN remoto."))
        checks.append(_check("bgp_peer_state_established", all(str(peer.get("state") or "").lower() == "established" for peer in peers), "Peers devem estar em Established ou documentados para revisao."))
        checks.append(_check("bgp_peer_description_present", all(peer.get("description") for peer in peers), "Todo peer deve ter descricao operacional."))
        checks.append(_check("bgp_import_export_policy_present", all(peer.get("import_policy") and peer.get("export_policy") for peer in peers), "Peers externos devem declarar politicas de import/export."))
    checks.append(_check("bgp_policy_inventory_present", bool(policies or prefixes), "Route-policy, ip-prefix, community-filter ou community-list devem estar visiveis quando usados pelo BGP."))
    return checks


def _findings_for_context(device: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    status = result.get("status")
    if status == STATUS_WITHIN_STANDARD:
        return []
    severity = "info" if status == STATUS_INFORMATIONAL_ALERT else "warning" if status == STATUS_NEEDS_STANDARDIZATION else "error"
    return [
        {
            "finding_id": f"CTX-{uuid.uuid4().hex[:10].upper()}",
            "device_id": device.get("device_id"),
            "device_name": device.get("name"),
            "context_id": result.get("context_id"),
            "context_label": result.get("label"),
            "status": status,
            "status_label": result.get("status_label"),
            "severity": severity,
            "blocking": bool(result.get("blocking")),
            "title": result.get("status_label"),
            "description": result.get("human_summary"),
            "recommendation": _recommendation(status),
            "write_required": False,
            "approval_required": False,
        }
    ]


def _summary(devices: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = {label: 0 for label in STATUS_LABELS}
    contexts_total = 0
    blocking = 0
    for device in devices:
        for context in device.get("contexts") or []:
            statuses[str(context.get("status"))] = statuses.get(str(context.get("status")), 0) + 1
            contexts_total += 1
            blocking += 1 if context.get("blocking") else 0
    return {"devices": len(devices), "contexts_total": contexts_total, "blocking_contexts": blocking, "statuses": statuses}


def _check(name: str, result: bool | None, message: str) -> dict[str, Any]:
    return {"name": name, "result": result, "message": message}


def _human_summary(context: dict[str, Any], status: str) -> str:
    label = context.get("label") or context.get("context_id")
    count = int(context.get("items_count") or 0)
    if status == STATUS_WITHIN_STANDARD:
        return f"{label}: {count} item(ns) classificados e aderentes ao padrao conhecido."
    if status == STATUS_OUT_OF_STANDARD:
        return f"{label}: ha item(ns) fora do padrao declarado e a revisao humana deve tratar antes de promover correcoes."
    if status == STATUS_NEEDS_STANDARDIZATION:
        return f"{label}: nao ha padrao validavel suficiente; registrar necessidade de padronizacao."
    return f"{label}: contexto opcional detectado ou ausente, mantido como alerta informativo."


def _recommendation(status: str) -> str:
    if status == STATUS_OUT_OF_STANDARD:
        return "Revisar o contexto com o time responsavel antes de qualquer proposta de ajuste."
    if status == STATUS_NEEDS_STANDARDIZATION:
        return "Declarar um padrao operacional ou ajustar a policy/parser para permitir validacao objetiva."
    if status == STATUS_INFORMATIONAL_ALERT:
        return "Manter visivel para diagnostico; nao bloquear o avanco do fluxo."
    return "Sem acao requerida."


def _safety() -> dict[str, bool]:
    return {
        "netbox_write": False,
        "sync_called": False,
        "apply_plan_created": False,
        "approval_record_created": False,
        "ssh_write": False,
        "config_mode": False,
        "netconf_write": False,
        "snmp_write": False,
    }
