"""Compliance findings triage helpers.

Local only. No NetBox writes. No SSH/SNMP/NETCONF. No ApprovalRecord/ApplyPlan.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .compliance_jobs import JOBS_BASE, load_compliance_job


TRIAGE_DIR_NAME = "triage"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_job_dir(job_id: str, jobs_base: Optional[Path] = None) -> Path:
    return (jobs_base or JOBS_BASE) / job_id


def _dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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


def _triage_dir(job_id: str, jobs_base: Optional[Path] = None) -> Path:
    return _safe_job_dir(job_id, jobs_base) / TRIAGE_DIR_NAME


def _is_huawei_logical_interface(name: str) -> bool:
    text = (name or "").strip()
    if not text:
        return False
    return bool(
        re.match(
            r"^(?:"
            r"Virtual-Ethernet\d+(?:/\d+)*(?:\.\d+)?"
            r"|Eth-Trunk\d+(?:\.\d+)?"
            r"|GigabitEthernet\d+(?:/\d+)*(?:\.\d+)?(?:\(\d+[A-Za-z]*\))?"
            r"|Ethernet\d+(?:/\d+)*(?:\.\d+)?"
            r"|XGigabitEthernet\d+(?:/\d+)*(?:\.\d+)?"
            r"|FastEthernet\d+(?:/\d+)*(?:\.\d+)?"
            r"|LoopBack\d+"
            r"|Tunnel\d+"
            r"|NULL0"
            r"|MEth\d+(?:/\d+)*(?:\.\d+)?"
            r"|Virtual-Template\d+"
            r")$",
            text,
            re.I,
        )
    )


def _looks_like_header_or_legend(text: str) -> bool:
    lowered = (text or "").strip().lower()
    return lowered.startswith(
        (
            "display ",
            "the number",
            "phy:",
            "interface",
            "*down:",
            "^down:",
            "!down:",
            "(",
            "<",
        )
    )


def _load_findings_from_comparison(job_id: str, jobs_base: Optional[Path] = None) -> list[dict[str, Any]]:
    job_dir = _safe_job_dir(job_id, jobs_base)
    comparison_dir = job_dir / "comparison"
    findings: list[dict[str, Any]] = []
    if not comparison_dir.exists():
        return findings

    for device_dir in sorted(comparison_dir.glob("devices/*")):
        findings_path = device_dir / "compliance-findings.json"
        if not findings_path.exists():
            continue
        data = _load_json(findings_path)
        findings.extend(list(data.get("findings") or []))
    return findings


def load_compliance_findings(job_id: str, device_id: str | int | None = None, jobs_base: Optional[Path] = None) -> list[dict[str, Any]]:
    """Load findings for a job, optionally filtered by device_id."""
    findings = _load_findings_from_comparison(job_id, jobs_base)
    if device_id is None:
        return findings
    device_key = str(device_id)
    return [finding for finding in findings if str(finding.get("device_id")) == device_key]


def _suspicious_object_name(object_name: str) -> bool:
    text = (object_name or "").strip()
    if not text:
        return True
    if _looks_like_header_or_legend(text):
        return True
    if text.lower().startswith(("slot", "board", "card", "device", "warning", "info")):
        return True
    return False


def _finding_bucket_payload(
    finding: dict[str, Any],
    triage_bucket: str,
    confidence: str,
    reason: str,
    suggested_human_action: str,
) -> dict[str, Any]:
    return {
        "finding_id": finding.get("finding_id"),
        "device_id": finding.get("device_id"),
        "scope": finding.get("scope"),
        "object_type": finding.get("object_type"),
        "object_name": finding.get("object_name"),
        "rule_id": finding.get("rule_id"),
        "original_severity": finding.get("severity"),
        "title": finding.get("title"),
        "evidence": finding.get("evidence"),
        "recommendation": finding.get("recommendation"),
        "triage_bucket": triage_bucket,
        "confidence": confidence,
        "reason": reason,
        "suggested_human_action": suggested_human_action,
        "remediation_allowed": False,
    }


def classify_finding_noise_or_action(finding: dict[str, Any]) -> dict[str, Any]:
    """Classify a single finding into a triage bucket."""
    rule_id = str(finding.get("rule_id") or "").strip()
    object_name = str(finding.get("object_name") or "").strip()
    scope = str(finding.get("scope") or "").strip()
    evidence = finding.get("evidence") or {}
    recommendation = str(finding.get("recommendation") or "").strip()

    if not evidence and rule_id not in {"route_policy.missing", "prefix_list.missing"}:
        return _finding_bucket_payload(
            finding,
            "blocked_from_remediation",
            "low",
            "Sem evidência suficiente para avançar com revisão de remediação.",
            "Manter bloqueado e pedir mais evidência ou mais contexto operacional.",
        )

    if _suspicious_object_name(object_name):
        return _finding_bucket_payload(
            finding,
            "likely_parser_noise",
            "high",
            "Nome do objeto parece header, legenda ou artefato de parsing.",
            "Revisar parser e normalização antes de considerar qualquer ação.",
        )

    if rule_id == "interface.naming.invalid":
        if _is_huawei_logical_interface(object_name):
            return _finding_bucket_payload(
                finding,
                "likely_policy_too_strict",
                "high",
                "Interface Huawei válida parece bater em policy interna rígida demais.",
                "Revisar allowlist e naming policy para tipos Huawei legítimos.",
            )
        return _finding_bucket_payload(
            finding,
            "needs_human_review",
            "medium",
            "Nome da interface precisa revisão manual.",
            "Validar se o nome é real ou se a regra interna deve ser ajustada.",
        )

    if rule_id == "interface.state.mismatch":
        if "." in object_name or _is_huawei_logical_interface(object_name):
            return _finding_bucket_payload(
                finding,
                "likely_parser_noise",
                "medium",
                "Mismatch aparece em interface lógica/subinterface e pode vir de parsing incompleto.",
                "Revisar parser e validação de brief para interfaces lógicas.",
            )
        return _finding_bucket_payload(
            finding,
            "needs_human_review",
            "medium",
            "Estado físico/protocolo precisa validação humana.",
            "Confirmar estado operacional da interface antes de qualquer ação.",
        )

    if rule_id == "interface.description.required":
        if _suspicious_object_name(object_name):
            return _finding_bucket_payload(
                finding,
                "likely_policy_too_strict",
                "medium",
                "Descrição ausente em interface Huawei potencialmente válida.",
                "Rever se a policy exige descrição onde o inventário ainda está incompleto.",
            )
        return _finding_bucket_payload(
            finding,
            "needs_human_review",
            "high",
            "Interface real sem descrição precisa revisão humana.",
            "Confirmar se a descrição falta por documentação ou por política interna.",
        )

    if rule_id in {"bgp.peer.state.not_established", "bgp.peer.policy.missing", "bgp.peer.description.required"}:
        return _finding_bucket_payload(
            finding,
            "needs_human_review",
            "high",
            "BGP pede validação manual antes de qualquer mudança.",
            "Validar sessão, política e descrição do peer com operador humano.",
        )

    if rule_id in {"route_policy.missing", "prefix_list.missing"}:
        return _finding_bucket_payload(
            finding,
            "needs_human_review",
            "high",
            "Ausência de route-policy/prefix-list precisa validação humana.",
            "Conferir se ausência é esperada ou se falta cadastro/documentação.",
        )

    if recommendation and any(token in recommendation.lower() for token in ("metadata", "documentation", "description")):
        return _finding_bucket_payload(
            finding,
            "remediation_candidate",
            "medium",
            "Recomendação é de metadata/documentação e a evidência é suficiente.",
            "Pode virar candidato de correção manual após revisão humana.",
        )

    return _finding_bucket_payload(
        finding,
        "blocked_from_remediation",
        "medium",
        "Sem regra clara para promover remediação segura.",
        "Manter bloqueado até revisão manual ou ajuste de policy/parser.",
    )


def _bucket_rank(entry: dict[str, Any]) -> tuple[int, int, str]:
    priority = {
        "bgp.peer.state.not_established": 0,
        "bgp.peer.policy.missing": 1,
        "bgp.peer.description.required": 2,
        "interface.description.required": 3,
        "route_policy.missing": 4,
        "prefix_list.missing": 5,
    }
    rule_id = str(entry.get("rule_id") or "")
    severity = str(entry.get("original_severity") or "").lower()
    severity_rank = {"error": 0, "warning": 1, "info": 2}.get(severity, 3)
    return (priority.get(rule_id, 99), severity_rank, str(entry.get("finding_id") or ""))


def _build_top_review_items(classified_findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selections: list[dict[str, Any]] = []
    quotas = [
        ("bgp.peer.state.not_established", 3),
        ("bgp.peer.policy.missing", 2),
        ("bgp.peer.description.required", 2),
        ("interface.description.required", 1),
        ("route_policy.missing", 1),
        ("prefix_list.missing", 1),
    ]

    pool = {
        rule_id: sorted(
            [item for item in classified_findings if item.get("rule_id") == rule_id],
            key=_bucket_rank,
        )
        for rule_id, _ in quotas
    }

    for rule_id, amount in quotas:
        for item in pool.get(rule_id, [])[:amount]:
            if len(selections) >= 10:
                break
            selections.append(item)
        if len(selections) >= 10:
            break

    if len(selections) < 10:
        leftovers = sorted(
            [
                item
                for item in classified_findings
                if item not in selections
                and item.get("triage_bucket") in {"needs_human_review", "remediation_candidate"}
            ],
            key=_bucket_rank,
        )
        for item in leftovers:
            if len(selections) >= 10:
                break
            selections.append(item)

    top_review_items: list[dict[str, Any]] = []
    why_this_matters = {
        "bgp.peer.state.not_established": "Sessão BGP fora de Established impacta troca de rotas.",
        "bgp.peer.policy.missing": "Sem import/export policy, a política de troca fica incompleta.",
        "bgp.peer.description.required": "Peer sem descrição atrapalha revisão e governança.",
        "interface.description.required": "Interface sem descrição reduz rastreabilidade e operação.",
        "route_policy.missing": "Ausência de route-policy pode indicar documentação ou cadastro faltante.",
        "prefix_list.missing": "Ausência de prefix-list pode esconder dependências de roteamento.",
    }
    for index, item in enumerate(selections[:10], start=1):
        top_review_items.append(
            {
                "rank": index,
                "finding_id": item.get("finding_id"),
                "original_severity": item.get("original_severity"),
                "triage_bucket": item.get("triage_bucket"),
                "scope": item.get("scope"),
                "object_name": item.get("object_name"),
                "rule_id": item.get("rule_id"),
                "title": item.get("title"),
                "evidence": item.get("evidence"),
                "suggested_human_action": item.get("suggested_human_action"),
                "why_this_matters": why_this_matters.get(str(item.get("rule_id") or ""), "Revisar manualmente antes de promover qualquer mudança."),
            }
        )
    return top_review_items


def _build_policy_adjustment_candidates(classified_findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in classified_findings:
        if item.get("triage_bucket") != "likely_policy_too_strict":
            continue
        candidates.append(
            {
                "finding_id": item.get("finding_id"),
                "rule_id": item.get("rule_id"),
                "object_name": item.get("object_name"),
                "confidence": item.get("confidence"),
                "reason": item.get("reason"),
                "policy_suggestion": "Criar allowlist para interfaces Huawei válidas e revisar nomenclatura interna.",
                "severity_suggestion": "warning",
            }
        )
    return candidates


def _build_parser_adjustment_candidates(classified_findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in classified_findings:
        if item.get("triage_bucket") != "likely_parser_noise":
            continue
        candidates.append(
            {
                "finding_id": item.get("finding_id"),
                "rule_id": item.get("rule_id"),
                "object_name": item.get("object_name"),
                "confidence": item.get("confidence"),
                "reason": item.get("reason"),
                "parser_suggestion": "Aprimorar parsing de brief para interfaces lógicas, headers e legendas.",
                "severity_suggestion": "warning",
            }
        )
    return candidates


def _build_virtual_ethernet_review(classified_findings: list[dict[str, Any]]) -> dict[str, Any]:
    target_names = {
        "Virtual-Ethernet0/2/100.100",
        "Virtual-Ethernet0/2/101.100",
        "Virtual-Ethernet0/2/200.100",
    }
    target_findings = [item for item in classified_findings if str(item.get("object_name") or "") in target_names]
    suggested_policy = "Adicionar allowlist para Virtual-Ethernet e subinterfaces Huawei legítimas."
    suggested_parser = "Manter parser; a separação de brief parece correta. Tratar logical_interface como categoria própria."
    reviewed = []
    for item in target_findings:
        reviewed.append(
            {
                "finding_id": item.get("finding_id"),
                "object_name": item.get("object_name"),
                "rule_id": item.get("rule_id"),
                "triage_bucket": item.get("triage_bucket"),
                "confidence": item.get("confidence"),
                "reason": item.get("reason"),
                "policy_suggestion": suggested_policy,
                "parser_suggestion": suggested_parser,
                "severity_suggestion": "warning" if item.get("original_severity") == "error" else item.get("original_severity"),
            }
        )
    return {
        "job_id": None,
        "status": "VIRTUAL_ETHERNET_REVIEW_COMPLETED",
        "evaluated_at": _now(),
        "findings_total": len(reviewed),
        "reviewed_findings": reviewed,
        "overall_policy_suggestion": suggested_policy,
        "overall_parser_suggestion": suggested_parser,
        "overall_severity_suggestion": "warning",
        "decision": "VIRTUAL_ETHERNET_REVIEW_COMPLETED",
    }


def write_triage_artifacts(job_id: str, triage_result: dict[str, Any], jobs_base: Optional[Path] = None) -> dict[str, Any]:
    """Write triage JSON and markdown artifacts."""
    triage_dir = _triage_dir(job_id, jobs_base)
    triage_dir.mkdir(parents=True, exist_ok=True)

    triage_json = triage_dir / "findings-triage.json"
    triage_md = triage_dir / "FINDINGS-TRIAGE.md"
    virtual_review_json = triage_dir / "virtual-ethernet-review.json"
    virtual_review_md = triage_dir / "VIRTUAL-ETHERNET-REVIEW.md"

    payload = dict(triage_result)
    payload["job_id"] = job_id
    payload["files"] = {
        "findings_triage": str(triage_json),
        "findings_triage_markdown": str(triage_md),
        "virtual_ethernet_review": str(virtual_review_json),
        "virtual_ethernet_review_markdown": str(virtual_review_md),
        "findings_triage_report_path": _report_path(triage_md),
        "virtual_ethernet_review_report_path": _report_path(virtual_review_md),
    }
    _dump_json(triage_json, payload)

    lines = [
        "# FINDINGS-TRIAGE",
        "",
        f"## Job ID\n`{job_id}`",
        "",
        f"## Status\n`{payload.get('status', 'TRIAGE_COMPLETED')}`",
        "",
        "## Summary",
    ]
    summary = payload.get("summary") or {}
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Top 10 para Revisão Humana",
        ]
    )
    for item in payload.get("top_review_items") or []:
        lines.extend(
            [
                "",
                f"### #{item.get('rank')} {item.get('object_name')}",
                f"- finding_id: {item.get('finding_id')}",
                f"- severity: {item.get('original_severity')}",
                f"- scope: {item.get('scope')}",
                f"- rule_id: {item.get('rule_id')}",
                f"- title: {item.get('title')}",
                f"- evidence: {json.dumps(item.get('evidence'), ensure_ascii=False)}",
                f"- suggested_human_action: {item.get('suggested_human_action')}",
                f"- why_this_matters: {item.get('why_this_matters')}",
            ]
        )
    lines.extend(
        [
            "",
            "## Parser Noise",
        ]
    )
    parser_candidates = payload.get("parser_adjustment_candidates") or []
    if parser_candidates:
        for item in parser_candidates:
            lines.extend(
                [
                    f"- {item.get('finding_id')} | {item.get('object_name')} | {item.get('reason')}",
                ]
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Policy Too Strict",
        ]
    )
    policy_candidates = payload.get("policy_adjustment_candidates") or []
    if policy_candidates:
        for item in policy_candidates:
            lines.extend(
                [
                    f"- {item.get('finding_id')} | {item.get('object_name')} | {item.get('reason')}",
                ]
            )
    else:
        lines.append("- none")
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
    triage_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    virtual_review = payload.get("virtual_ethernet_review") or {}
    virtual_review["files"] = {
        "virtual_ethernet_review": str(virtual_review_json),
        "virtual_ethernet_review_markdown": str(virtual_review_md),
        "virtual_ethernet_review_report_path": _report_path(virtual_review_md),
    }
    _dump_json(virtual_review_json, virtual_review)
    ve_lines = [
        "# VIRTUAL-ETHERNET-REVIEW",
        "",
        f"## Job ID\n`{job_id}`",
        "",
        "## Findings",
    ]
    for item in virtual_review.get("reviewed_findings") or []:
        ve_lines.extend(
            [
                "",
                f"### {item.get('object_name')}",
                f"- finding_id: {item.get('finding_id')}",
                f"- rule_id: {item.get('rule_id')}",
                f"- triage_bucket: {item.get('triage_bucket')}",
                f"- confidence: {item.get('confidence')}",
                f"- reason: {item.get('reason')}",
                f"- policy_suggestion: {item.get('policy_suggestion')}",
                f"- parser_suggestion: {item.get('parser_suggestion')}",
                f"- severity_suggestion: {item.get('severity_suggestion')}",
            ]
        )
    ve_lines.extend(
        [
            "",
            "## Overall Suggestions",
            f"- policy: {virtual_review.get('overall_policy_suggestion')}",
            f"- parser: {virtual_review.get('overall_parser_suggestion')}",
            f"- severity: {virtual_review.get('overall_severity_suggestion')}",
        ]
    )
    virtual_review_md.write_text("\n".join(ve_lines) + "\n", encoding="utf-8")

    payload["virtual_ethernet_review"] = virtual_review
    payload["files"] = {
        "findings_triage": str(triage_json),
        "findings_triage_markdown": str(triage_md),
        "virtual_ethernet_review": str(virtual_review_json),
        "virtual_ethernet_review_markdown": str(virtual_review_md),
        "findings_triage_report_path": _report_path(triage_md),
        "virtual_ethernet_review_report_path": _report_path(virtual_review_md),
    }
    _dump_json(triage_json, payload)
    return {
        "job_id": job_id,
        "status": payload.get("status", "TRIAGE_COMPLETED"),
        "decision": payload.get("status", "TRIAGE_COMPLETED"),
        "files": payload["files"],
        "triage": payload,
        "virtual_ethernet_review": virtual_review,
    }


def triage_findings(job_id: str, jobs_base: Optional[Path] = None) -> dict[str, Any]:
    """Classify findings for human review."""
    job = load_compliance_job(job_id, jobs_base)
    findings = load_compliance_findings(job_id, None, jobs_base)
    if not findings:
        raise ValueError("no findings available for triage")

    classified = [classify_finding_noise_or_action(finding) for finding in findings]
    summary = {
        "likely_parser_noise": sum(1 for item in classified if item.get("triage_bucket") == "likely_parser_noise"),
        "likely_policy_too_strict": sum(1 for item in classified if item.get("triage_bucket") == "likely_policy_too_strict"),
        "needs_human_review": sum(1 for item in classified if item.get("triage_bucket") == "needs_human_review"),
        "remediation_candidate": sum(1 for item in classified if item.get("triage_bucket") == "remediation_candidate"),
        "blocked_from_remediation": sum(1 for item in classified if item.get("triage_bucket") == "blocked_from_remediation"),
    }

    triage_result = {
        "job_id": job_id,
        "status": "TRIAGE_COMPLETED",
        "findings_total": len(classified),
        "summary": summary,
        "findings": classified,
        "top_review_items": _build_top_review_items(classified),
        "policy_adjustment_candidates": _build_policy_adjustment_candidates(classified),
        "parser_adjustment_candidates": _build_parser_adjustment_candidates(classified),
        "virtual_ethernet_review": _build_virtual_ethernet_review(classified),
        "safety": {
            "netbox_write": False,
            "device_connection": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False,
        },
        "comparison_result_present": bool(job.get("comparison_result")),
        "comparison_result_decision": job.get("comparison_result", {}).get("decision"),
        "triaged_at": _now(),
    }
    return write_triage_artifacts(job_id, triage_result, jobs_base)


def summarize_triage(job_id: str, jobs_base: Optional[Path] = None) -> dict[str, Any]:
    """Load the current triage summary if available."""
    triage_json = _triage_dir(job_id, jobs_base) / "findings-triage.json"
    payload = _load_json(triage_json)
    if not payload:
        return {
            "job_id": job_id,
            "status": "TRIAGE_MISSING",
            "decision": "TRIAGE_MISSING",
            "summary": {
                "likely_parser_noise": 0,
                "likely_policy_too_strict": 0,
                "needs_human_review": 0,
                "remediation_candidate": 0,
                "blocked_from_remediation": 0,
            },
            "top_review_items": [],
            "policy_adjustment_candidates": [],
            "parser_adjustment_candidates": [],
            "safety": {
                "netbox_write": False,
                "device_connection": False,
                "sync_called": False,
                "approval_record_created": False,
                "apply_plan_created": False,
            },
            "files": {},
        }

    return {
        "job_id": job_id,
        "status": payload.get("status", "TRIAGE_COMPLETED"),
        "decision": payload.get("status", "TRIAGE_COMPLETED"),
        "findings_total": payload.get("findings_total", 0),
        "summary": payload.get("summary") or {},
        "top_review_items": payload.get("top_review_items") or [],
        "policy_adjustment_candidates": payload.get("policy_adjustment_candidates") or [],
        "parser_adjustment_candidates": payload.get("parser_adjustment_candidates") or [],
        "safety": payload.get("safety") or {
            "netbox_write": False,
            "device_connection": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False,
        },
        "files": payload.get("files") or {},
        "triage": payload,
        "virtual_ethernet_review": payload.get("virtual_ethernet_review") or {},
    }
