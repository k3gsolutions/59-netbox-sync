"""Compliance job review and collection planning helpers.

Local disk only. No NetBox writes. No SSH, SNMP, NETCONF, or /sync.
No ApprovalRecord. No ApplyPlan. Read-only governance artifacts only.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .compliance_collection_profiles import get_allowed_commands_for_device, select_collection_profile


JOBS_BASE = Path(__file__).parent.parent.parent / "reports" / "compliance" / "jobs"
JOB_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")

COMPLIANCE_JOB_SAFETY = {
    "netbox_write": False,
    "device_connection_started": False,
    "collection_started": False,
    "approval_record_created": False,
    "apply_plan_created": False,
}


def get_compliance_job_safety() -> dict:
    """Return the baseline safety block used by compliance jobs."""
    return dict(COMPLIANCE_JOB_SAFETY)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dump_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _job_dir(job_id: str, jobs_base: Optional[Path] = None) -> Path:
    base = jobs_base or JOBS_BASE
    return base / job_id


def _safe_job_id(job_id: str) -> bool:
    return bool(JOB_ID_RE.fullmatch((job_id or "").strip()))


def _extract_device_display(device: dict) -> dict:
    platform = device.get("platform")
    platform_name = None
    if isinstance(platform, dict):
        platform_name = platform.get("name") or platform.get("slug")
    elif isinstance(platform, str):
        platform_name = platform

    device_type = device.get("device_type") or {}
    manufacturer = None
    model = None
    if isinstance(device_type, dict):
        manufacturer_obj = device_type.get("manufacturer")
        if isinstance(manufacturer_obj, dict):
            manufacturer = manufacturer_obj.get("name") or manufacturer_obj.get("slug")
        elif isinstance(manufacturer_obj, str):
            manufacturer = manufacturer_obj
        model = device_type.get("model")

    if not manufacturer:
        manufacturer = device.get("manufacturer")
    if not model:
        model = device.get("model")

    return {
        "device_id": device.get("id"),
        "name": device.get("name"),
        "primary_ip4": device.get("primary_ip4"),
        "platform": platform_name,
        "manufacturer": manufacturer,
        "model": model,
    }


def _render_start_gate_markdown(job_id: str, job_request: dict, selected_devices: list[dict], decision: str, checks: dict) -> str:
    lines = [
        "# COLLECTION-START-GATE",
        "",
        f"## Job ID\n`{job_id}`",
        "",
        f"## Decision\n`{decision}`",
        "",
        f"## Status\n`{job_request.get('status', 'unknown')}`",
        "",
        f"## Operator\n`{job_request.get('triggered_by', 'unknown')}`",
        "",
        f"## Confirm\n`{job_request.get('confirm', False)}`",
        "",
        "## Checks",
    ]
    for key, value in checks.items():
        lines.append(f"- {key}: {value}")
    lines.extend([
        "",
        "## Selected Devices",
    ])
    if selected_devices:
        for device in selected_devices:
            lines.append(
                f"- {device.get('device_id')}: {device.get('name')} "
                f"({device.get('primary_ip4') or 'no-primary-ip4'})"
            )
    else:
        lines.append("- none")
    lines.extend([
        "",
        "## Safety",
        "",
        "- No collection started",
        "- No SSH, SNMP, or NETCONF",
        "- No NetBox write",
        "- No ApprovalRecord",
        "- No ApplyPlan",
        "",
        "## Next Step",
        "",
    ])
    if decision == "COLLECTION_START_GATE_READY":
        lines.append("Collection plan may be prepared locally.")
    else:
        lines.append("Collection remains blocked until the gate is satisfied.")
    return "\n".join(lines) + "\n"


def _render_collection_plan_markdown(job_id: str, decision: str, devices: list[dict], blocked_reason: str = "") -> str:
    lines = [
        "# COLLECTION-PLAN",
        "",
        f"## Job ID\n`{job_id}`",
        "",
        f"## Decision\n`{decision}`",
        "",
    ]
    if blocked_reason:
        lines.extend([f"## Blocked Reason\n{blocked_reason}", ""])
    lines.append("## Devices")
    if not devices:
        lines.append("- none")
    for device in devices:
        lines.extend([
            "",
            f"### {device.get('name')}",
            f"- device_id: {device.get('device_id')}",
            f"- primary_ip4: {device.get('primary_ip4') or 'none'}",
            f"- platform: {device.get('platform') or 'none'}",
            f"- manufacturer: {device.get('manufacturer') or 'none'}",
            f"- model: {device.get('model') or 'none'}",
            "- allowed_collection_methods:",
            "  - ssh_read_only",
            "  - snmp_read_only",
            "- forbidden_methods:",
            "  - netconf_write",
            "  - cli_config",
            "  - netbox_write",
            "  - sync",
            "- command_policy:",
            "  - show/display only",
            "  - no configure/system-view",
            "  - no commit/save",
            "- expected_outputs:",
            "  - interfaces",
            "  - bgp",
            "  - vrf",
            "  - route-policy",
            "  - prefix-list",
            "  - snmp",
            "  - system info",
        ])
    lines.extend([
        "",
        "## Safety",
        "",
        "- No SSH execution",
        "- No SNMP execution",
        "- No NETCONF execution",
        "- No NetBox write",
        "- No /sync",
    ])
    return "\n".join(lines) + "\n"


def create_compliance_job(
    device_ids: list,
    candidates: list,
    triggered_by: str = "operator",
    mode: str = "read_only",
    jobs_base: Optional[Path] = None,
) -> dict:
    """Create the initial local compliance job artifacts."""
    if jobs_base is None:
        jobs_base = JOBS_BASE

    job_id = f"compliance-job-{uuid.uuid4().hex[:12]}"
    created_at = _now()
    job_dir = jobs_base / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    job_request = {
        "job_id": job_id,
        "status": "prepared",
        "mode": mode,
        "triggered_by": triggered_by,
        "created_at": created_at,
        "device_ids": device_ids,
        "safety": get_compliance_job_safety(),
        "next_required_action": "manual_review_before_collection",
    }
    _dump_json(job_dir / "job-request.json", job_request)

    _dump_json(
        job_dir / "selected-devices.json",
        {
            "job_id": job_id,
            "selected_count": len(candidates),
            "devices": candidates,
        },
    )

    _dump_json(
        job_dir / "eligibility-recheck.json",
        {
            "job_id": job_id,
            "rechecked_at": created_at,
            "device_ids_submitted": device_ids,
            "confirmed_eligible": device_ids,
            "ineligible": [],
            "all_eligible": True,
            "recheck_method": "per_id_get_with_enrichment",
        },
    )

    devices_md = "\n".join(
        f"- ID {d.get('id')}: {d.get('name', '?')} (tenant: {d.get('tenant', '?')})"
        for d in candidates
    )
    gate_md = f"""# Compliance Job Start Gate

## Job ID
`{job_id}`

## Status
`prepared`

## Created At
{created_at}

## Triggered By
{triggered_by}

## Devices Selecionados ({len(candidates)})

{devices_md}

## Critérios de Elegibilidade Verificados

- device.status == active
- custom_fields[Compliance] == True
- device.tenant presente
- device.tenant.group == K3G Solutions (enriquecido via tenant detail se necessário)

## Confirmação de Segurança

- Nenhuma coleta iniciada
- Nenhuma conexão SSH/SNMP/NETCONF
- Nenhuma escrita no NetBox
- Nenhum ApprovalRecord criado
- Nenhum ApplyPlan criado

## Próximo Passo (Manual)

Este job foi criado para revisão humana antes de qualquer coleta.
O próximo passo deve ser iniciado manualmente após revisão deste artefato.

Ação requerida: `manual_review_before_collection`
"""
    (job_dir / "COMPLIANCE-JOB-START-GATE.md").write_text(gate_md, encoding="utf-8")

    return {
        "job_id": job_id,
        "job_dir": str(job_dir),
        "created_at": created_at,
        "files": {
            "job_request": str(job_dir / "job-request.json"),
            "selected_devices": str(job_dir / "selected-devices.json"),
            "eligibility_recheck": str(job_dir / "eligibility-recheck.json"),
            "start_gate": str(job_dir / "COMPLIANCE-JOB-START-GATE.md"),
        },
    }


def list_compliance_jobs(jobs_base: Optional[Path] = None) -> list[dict]:
    base = jobs_base or JOBS_BASE
    if not base.exists():
        return []

    jobs: list[dict] = []
    for job_dir in base.iterdir():
        if not job_dir.is_dir():
            continue
        job_request = _load_json(job_dir / "job-request.json")
        selected = _load_json(job_dir / "selected-devices.json")
        gate = _load_json(job_dir / "collection-start-gate.json")
        plan = _load_json(job_dir / "collection-plan.json")
        jobs.append(
            {
                "job_id": job_dir.name,
                "job_dir": str(job_dir),
                "created_at": job_request.get("created_at"),
                "status": job_request.get("status") or "unknown",
                "triggered_by": job_request.get("triggered_by"),
                "selected_count": selected.get("selected_count", 0),
                "device_ids": job_request.get("device_ids", []),
                "safety": job_request.get("safety", get_compliance_job_safety()),
                "collection_start_gate": gate.get("decision") or "missing",
                "collection_plan": plan.get("decision") or "missing",
                "start_gate_markdown": str(job_dir / "COMPLIANCE-JOB-START-GATE.md"),
                "collection_gate_markdown": str(job_dir / "COLLECTION-START-GATE.md"),
                "collection_plan_markdown": str(job_dir / "COLLECTION-PLAN.md"),
                "mtime": job_dir.stat().st_mtime,
            }
        )

    return sorted(jobs, key=lambda item: item.get("mtime", 0), reverse=True)


def load_compliance_job(job_id: str, jobs_base: Optional[Path] = None) -> dict:
    if not _safe_job_id(job_id):
        raise KeyError("invalid job id")

    job_dir = _job_dir(job_id, jobs_base)
    if not job_dir.exists():
        raise KeyError("job not found")

    job_request = _load_json(job_dir / "job-request.json")
    selected_devices = _load_json(job_dir / "selected-devices.json")
    eligibility_recheck = _load_json(job_dir / "eligibility-recheck.json")
    collection_start_gate = _load_json(job_dir / "collection-start-gate.json")
    collection_plan = _load_json(job_dir / "collection-plan.json")
    collection_execution = _load_json(job_dir / "collection-results" / "collection-execution.json")
    collection_safety_validation = _load_json(job_dir / "collection-results" / "collection-safety-validation.json")
    ssh_preflight = _load_json(job_dir / "collection-results" / "ssh-preflight.json")
    ssh_collection_result = _load_json(job_dir / "collection-results" / "ssh-collection-result.json")
    raw_output_safety_validation = _load_json(job_dir / "collection-results" / "raw-output-safety-validation.json")
    parser_manifest = _load_json(job_dir / "collection-results" / "parser-manifest.json")
    parser_result = _load_json(job_dir / "collection-results" / "parser-result.json")
    parser_safety_validation = _load_json(job_dir / "collection-results" / "parser-safety-validation.json")
    comparison_result = _load_json(job_dir / "comparison" / "compliance-comparison-result.json")
    collection_results_markdown = _load_text(job_dir / "collection-results" / "COLLECTION-EXECUTION.md")
    collection_safety_validation_markdown = _load_text(job_dir / "collection-results" / "COLLECTION-SAFETY-VALIDATION.md")
    ssh_preflight_markdown = _load_text(job_dir / "collection-results" / "SSH-PREFLIGHT.md")
    ssh_collection_result_markdown = _load_text(job_dir / "collection-results" / "SSH-COLLECTION-RESULT.md")
    raw_output_safety_validation_markdown = _load_text(job_dir / "collection-results" / "RAW-OUTPUT-SAFETY-VALIDATION.md")
    parser_staging_markdown = _load_text(job_dir / "collection-results" / "PARSER-STAGING.md")
    parser_result_markdown = _load_text(job_dir / "collection-results" / "PARSER-RESULT.md")
    parser_safety_validation_markdown = _load_text(job_dir / "collection-results" / "PARSER-SAFETY-VALIDATION.md")
    comparison_result_markdown = _load_text(job_dir / "comparison" / "COMPLIANCE-COMPARISON-RESULT.md")
    review_decisions = _load_json(job_dir / "review" / "finding-decisions.json")
    remediation_draft_eligibility = _load_json(job_dir / "review" / "remediation-draft-eligibility.json")
    finding_decisions_markdown = _load_text(job_dir / "review" / "FINDING-DECISIONS.md")
    remediation_draft_eligibility_markdown = _load_text(job_dir / "review" / "REMEDIATION-DRAFT-ELIGIBILITY.md")

    return {
        "job_id": job_id,
        "job_dir": str(job_dir),
        "job_request": job_request,
        "selected_devices": selected_devices,
        "eligibility_recheck": eligibility_recheck,
        "start_gate_markdown": _load_text(job_dir / "COMPLIANCE-JOB-START-GATE.md"),
        "collection_start_gate_markdown": _load_text(job_dir / "COLLECTION-START-GATE.md"),
        "collection_start_gate": collection_start_gate,
        "collection_plan_markdown": _load_text(job_dir / "COLLECTION-PLAN.md"),
        "collection_plan": collection_plan,
        "collection_results": collection_execution,
        "collection_results_markdown": collection_results_markdown,
        "collection_safety_validation": collection_safety_validation,
        "collection_safety_validation_markdown": collection_safety_validation_markdown,
        "ssh_preflight": ssh_preflight,
        "ssh_preflight_markdown": ssh_preflight_markdown,
        "ssh_collection_result": ssh_collection_result,
        "ssh_collection_result_markdown": ssh_collection_result_markdown,
        "raw_output_safety_validation": raw_output_safety_validation,
        "raw_output_safety_validation_markdown": raw_output_safety_validation_markdown,
        "parser_manifest": parser_manifest,
        "parser_staging_markdown": parser_staging_markdown,
        "parser_result": parser_result,
        "parser_result_markdown": parser_result_markdown,
        "parser_safety_validation": parser_safety_validation,
        "parser_safety_validation_markdown": parser_safety_validation_markdown,
        "comparison_result": comparison_result,
        "comparison_result_markdown": comparison_result_markdown,
        "review_decisions": review_decisions,
        "remediation_draft_eligibility": remediation_draft_eligibility,
        "finding_decisions_markdown": finding_decisions_markdown,
        "remediation_draft_eligibility_markdown": remediation_draft_eligibility_markdown,
        "files": {
            "job_request": str(job_dir / "job-request.json"),
            "selected_devices": str(job_dir / "selected-devices.json"),
            "eligibility_recheck": str(job_dir / "eligibility-recheck.json"),
            "start_gate": str(job_dir / "COMPLIANCE-JOB-START-GATE.md"),
            "collection_start_gate": str(job_dir / "collection-start-gate.json"),
            "collection_start_gate_markdown": str(job_dir / "COLLECTION-START-GATE.md"),
            "collection_plan": str(job_dir / "collection-plan.json"),
            "collection_plan_markdown": str(job_dir / "COLLECTION-PLAN.md"),
            "collection_results": str(job_dir / "collection-results"),
            "ssh_preflight": str(job_dir / "collection-results" / "ssh-preflight.json"),
            "ssh_preflight_markdown": str(job_dir / "collection-results" / "SSH-PREFLIGHT.md"),
            "ssh_collection_result": str(job_dir / "collection-results" / "ssh-collection-result.json"),
            "ssh_collection_result_markdown": str(job_dir / "collection-results" / "SSH-COLLECTION-RESULT.md"),
            "raw_output_safety_validation": str(job_dir / "collection-results" / "raw-output-safety-validation.json"),
            "raw_output_safety_validation_markdown": str(job_dir / "collection-results" / "RAW-OUTPUT-SAFETY-VALIDATION.md"),
            "parser_manifest": str(job_dir / "collection-results" / "parser-manifest.json"),
            "parser_staging_markdown": str(job_dir / "collection-results" / "PARSER-STAGING.md"),
            "parser_result": str(job_dir / "collection-results" / "parser-result.json"),
            "parser_result_markdown": str(job_dir / "collection-results" / "PARSER-RESULT.md"),
            "parser_safety_validation": str(job_dir / "collection-results" / "parser-safety-validation.json"),
            "parser_safety_validation_markdown": str(job_dir / "collection-results" / "PARSER-SAFETY-VALIDATION.md"),
            "comparison_result": str(job_dir / "comparison" / "compliance-comparison-result.json"),
            "comparison_result_markdown": str(job_dir / "comparison" / "COMPLIANCE-COMPARISON-RESULT.md"),
            "review_decisions": str(job_dir / "review" / "finding-decisions.json"),
            "finding_decisions_markdown": str(job_dir / "review" / "FINDING-DECISIONS.md"),
            "remediation_draft_eligibility": str(job_dir / "review" / "remediation-draft-eligibility.json"),
            "remediation_draft_eligibility_markdown": str(job_dir / "review" / "REMEDIATION-DRAFT-ELIGIBILITY.md"),
        },
    }


def load_collection_artifacts(job_id: str, jobs_base: Optional[Path] = None) -> dict:
    if not _safe_job_id(job_id):
        raise KeyError("invalid job id")

    job_dir = _job_dir(job_id, jobs_base)
    if not job_dir.exists():
        raise KeyError("job not found")

    results_dir = job_dir / "collection-results"
    return {
        "job_id": job_id,
        "results_dir": str(results_dir),
        "execution": _load_json(results_dir / "collection-execution.json"),
        "execution_markdown": _load_text(results_dir / "COLLECTION-EXECUTION.md"),
        "safety_validation": _load_json(results_dir / "collection-safety-validation.json"),
        "safety_validation_markdown": _load_text(results_dir / "COLLECTION-SAFETY-VALIDATION.md"),
    }


def create_collection_start_gate(
    job_id: str,
    operator: str,
    confirm: bool,
    jobs_base: Optional[Path] = None,
) -> dict:
    if not _safe_job_id(job_id):
        raise KeyError("invalid job id")

    job_dir = _job_dir(job_id, jobs_base)
    if not job_dir.exists():
        raise KeyError("job not found")

    job_request = _load_json(job_dir / "job-request.json")
    selected_devices_doc = _load_json(job_dir / "selected-devices.json")
    devices = list(selected_devices_doc.get("devices", []))
    selected_count = int(selected_devices_doc.get("selected_count") or len(devices))
    safety = job_request.get("safety") or {}

    checks = {
        "job_status_prepared": job_request.get("status") == "prepared",
        "devices_selected": selected_count > 0 and len(devices) > 0,
        "confirm_true": bool(confirm) is True,
        "operator_present": bool((operator or "").strip()),
        "original_safety_present": safety == get_compliance_job_safety(),
        "collection_started_false": not bool(safety.get("collection_started")),
        "netbox_write_false": not bool(safety.get("netbox_write")),
        "approval_record_absent": not (job_dir / "approval-record.json").exists(),
        "apply_plan_absent": not (job_dir / "apply-plan.json").exists(),
    }

    ready = all(checks.values())
    decision = "COLLECTION_START_GATE_READY" if ready else "COLLECTION_START_GATE_BLOCKED"
    blocked_reason = "" if ready else "one or more compliance start-gate checks failed"

    payload = {
        "job_id": job_id,
        "operator": operator,
        "confirm": bool(confirm),
        "checked_at": _now(),
        "decision": decision,
        "status": "ready" if ready else "blocked",
        "blocked_reason": blocked_reason,
        "checks": checks,
        "job_request": job_request,
        "selected_devices_count": selected_count,
        "safety": safety,
        "next_required_action": "collection_plan" if ready else "manual_review",
    }
    _dump_json(job_dir / "collection-start-gate.json", payload)
    (job_dir / "COLLECTION-START-GATE.md").write_text(
        _render_start_gate_markdown(job_id, {**job_request, "confirm": bool(confirm), "triggered_by": operator}, devices, decision, checks),
        encoding="utf-8",
    )

    return {
        "job_id": job_id,
        "decision": decision,
        "status": payload["status"],
        "job_dir": str(job_dir),
        "files": {
            "collection_start_gate": str(job_dir / "collection-start-gate.json"),
            "collection_start_gate_markdown": str(job_dir / "COLLECTION-START-GATE.md"),
        },
        "checks": checks,
        "blocked_reason": blocked_reason,
    }


def create_collection_plan(job_id: str, jobs_base: Optional[Path] = None) -> dict:
    if not _safe_job_id(job_id):
        raise KeyError("invalid job id")

    job_dir = _job_dir(job_id, jobs_base)
    if not job_dir.exists():
        raise KeyError("job not found")

    start_gate = _load_json(job_dir / "collection-start-gate.json")
    if start_gate.get("decision") != "COLLECTION_START_GATE_READY":
        payload = {
            "job_id": job_id,
            "checked_at": _now(),
            "decision": "COLLECTION_PLAN_BLOCKED",
            "status": "blocked",
            "blocked_reason": "collection start gate not ready",
            "precondition": start_gate.get("decision") or "missing",
            "devices": [],
            "safety": get_compliance_job_safety(),
        }
        _dump_json(job_dir / "collection-plan.json", payload)
        (job_dir / "COLLECTION-PLAN.md").write_text(
            _render_collection_plan_markdown(job_id, payload["decision"], [], payload["blocked_reason"]),
            encoding="utf-8",
        )
        return {
            "job_id": job_id,
            "decision": payload["decision"],
            "status": payload["status"],
            "job_dir": str(job_dir),
            "files": {
                "collection_plan": str(job_dir / "collection-plan.json"),
                "collection_plan_markdown": str(job_dir / "COLLECTION-PLAN.md"),
            },
        }

    selected_devices_doc = _load_json(job_dir / "selected-devices.json")
    source_devices = list(selected_devices_doc.get("devices", []))
    devices = []
    for device in source_devices:
        device_display = _extract_device_display(device)
        profile = select_collection_profile(device_display)
        profile_valid, profile_issues = True, []
        if profile:
            from .compliance_collection_profiles import validate_profile

            profile_valid, profile_issues = validate_profile(profile)
        device_display["collection_profile"] = {
            "profile_id": profile.get("profile_id") if profile else "default-readonly",
            "vendor": profile.get("vendor") if profile else "generic",
            "platform": profile.get("platform") if profile else "generic",
            "valid": profile_valid,
            "issues": profile_issues,
        }
        device_display["planned_commands"] = get_allowed_commands_for_device(device_display)
        devices.append(device_display)

    payload = {
        "job_id": job_id,
        "checked_at": _now(),
        "decision": "COLLECTION_PLAN_PREPARED",
        "status": "prepared",
        "precondition": start_gate.get("decision"),
        "devices": [],
        "safety": get_compliance_job_safety(),
        "collection_started": False,
    }

    for device in devices:
        payload["devices"].append(
            {
                **device,
                "collection_profile": device.get("collection_profile"),
                "profile_id": device.get("collection_profile", {}).get("profile_id"),
                "allowed_collection_methods": ["ssh_read_only", "snmp_read_only"],
                "forbidden_methods": [
                    "netconf_write",
                    "cli_config",
                    "netbox_write",
                    "sync",
                ],
                "command_policy": [
                    "show/display only",
                    "no configure/system-view",
                    "no commit/save",
                ],
                "expected_outputs": [
                    "interfaces",
                    "bgp",
                    "vrf",
                    "route-policy",
                    "prefix-list",
                    "snmp",
                    "system info",
                ],
                "planned_commands": device.get("planned_commands") or get_allowed_commands_for_device(device),
            }
        )

    _dump_json(job_dir / "collection-plan.json", payload)
    (job_dir / "COLLECTION-PLAN.md").write_text(
        _render_collection_plan_markdown(job_id, payload["decision"], payload["devices"]),
        encoding="utf-8",
    )

    return {
        "job_id": job_id,
        "decision": payload["decision"],
        "status": payload["status"],
        "job_dir": str(job_dir),
        "files": {
            "collection_plan": str(job_dir / "collection-plan.json"),
            "collection_plan_markdown": str(job_dir / "COLLECTION-PLAN.md"),
        },
    }
