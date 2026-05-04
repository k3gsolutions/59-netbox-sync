"""Local remediation draft generator.

No NetBox writes. No device connections. No /sync.
No ApprovalRecord. No ApplyPlan. Drafts are local artifacts only.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .compliance_findings_review import load_findings, load_review_decisions
from .compliance_jobs import JOBS_BASE, load_compliance_job


REMEDIATION_DRAFTS_DIRNAME = "remediation"
REMEDIATION_DRAFTS_SUBDIR = "drafts"
REMEDIATION_DRAFTS_FILENAME = "remediation-drafts.json"
REMEDIATION_DRAFTS_MARKDOWN = "REMEDIATION-DRAFTS.md"
REMEDIATION_PROMOTION_GATE_FILENAME = "remediation-promotion-gate.json"
REMEDIATION_PROMOTION_GATE_MARKDOWN = "REMEDIATION-PROMOTION-GATE.md"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dump_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _safe_job_dir(job_id: str, jobs_base: Optional[Path] = None) -> Path:
    return (jobs_base or JOBS_BASE) / job_id


def _remediation_drafts_dir(job_id: str, jobs_base: Optional[Path] = None) -> Path:
    return _safe_job_dir(job_id, jobs_base) / REMEDIATION_DRAFTS_DIRNAME / REMEDIATION_DRAFTS_SUBDIR


def _load_json(path: Path) -> dict[str, Any]:
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


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _severity_to_risk_level(severity: str, action_type: str) -> str:
    severity = _safe_text(severity).strip().lower()
    action_type = _safe_text(action_type).strip().lower()
    if action_type == "device_config_candidate":
        return "high"
    if severity in {"error", "blocker"}:
        return "high"
    if severity == "warning":
        return "medium"
    if action_type == "netbox_metadata_update":
        return "medium"
    return "low"


def _has_missing_data(finding: dict[str, Any]) -> bool:
    evidence = finding.get("evidence")
    if not isinstance(evidence, dict):
        return False
    value = evidence.get("value")
    if value in (None, "", [], {}, ()):
        return True
    if isinstance(value, str) and value.strip().lower() in {"none", "null", "missing"}:
        return True
    return bool(
        str(finding.get("title") or "").strip().lower().startswith("nenhum")
        or "sem" in str(finding.get("title") or "").lower()
        and "dados" in str(finding.get("title") or "").lower()
    )


def _is_description_missing(finding: dict[str, Any]) -> bool:
    scope = _safe_text(finding.get("scope")).strip().lower()
    rule_id = _safe_text(finding.get("rule_id")).strip().lower()
    title = _safe_text(finding.get("title")).strip().lower()
    recommendation = _safe_text(finding.get("recommendation")).strip().lower()
    if scope not in {"interface", "bgp"}:
        return False
    return any(
        token in text
        for token in ("description.required", "sem descrição", "without description", "add description")
        for text in (rule_id, title, recommendation)
    )


def _is_informative_finding(finding: dict[str, Any]) -> bool:
    severity = _safe_text(finding.get("severity")).strip().lower()
    finding_type = _safe_text(finding.get("finding_type")).strip().lower()
    return severity == "info" or finding_type == "data_missing_for_check"


def _proposed_action_type(finding: dict[str, Any]) -> str:
    scope = _safe_text(finding.get("scope")).strip().lower()
    if _is_informative_finding(finding) or _has_missing_data(finding):
        return "manual_review"
    if scope in {"route_policy", "prefix_list"}:
        return "manual_review"
    if _is_description_missing(finding):
        return "netbox_metadata_update"
    if scope in {"system", "snmp"}:
        return "documentation_update"
    return "manual_review"


def _proposed_change_for_finding(finding: dict[str, Any], action_type: str) -> dict[str, Any]:
    scope = _safe_text(finding.get("scope")).strip().lower()
    object_type = _safe_text(finding.get("object_type")).strip()
    object_name = _safe_text(finding.get("object_name")).strip()
    current_value = None
    proposed_value = None
    field = "notes"
    target = "manual"

    if action_type == "netbox_metadata_update":
        target = "netbox"
        field = "description"
        current_value = finding.get("evidence", {}).get("value") if isinstance(finding.get("evidence"), dict) else None
        proposed_value = f"Add or normalize description for {object_name or object_type}"
    elif action_type == "documentation_update":
        target = "documentation"
        field = "reference"
        current_value = finding.get("recommendation")
        proposed_value = f"Document review for {scope or object_type}: {object_name or '*'}"
    elif action_type == "device_config_candidate":
        target = "device"
        field = "candidate_change"
        current_value = finding.get("recommendation")
        proposed_value = f"Candidate change for {object_name or object_type}"
    else:
        target = "manual"
        field = "review_notes"
        current_value = finding.get("recommendation") or finding.get("title")
        proposed_value = "Manual review required before any next step"

    return {
        "target": target,
        "field": field,
        "current_value": current_value if current_value is not None else "",
        "proposed_value": proposed_value if proposed_value is not None else "",
        "command_preview": None,
    }


def _draft_id_for_finding(finding_id: str) -> str:
    finding_id = _safe_text(finding_id).strip() or uuid.uuid4().hex[:10].upper()
    return f"RD-{finding_id}"


def load_remediation_eligible_findings(job_id: str, jobs_base: Optional[Path] = None) -> list[dict[str, Any]]:
    """Load findings whose review decision requests remediation."""
    job = load_compliance_job(job_id, jobs_base)
    eligibility = job.get("remediation_draft_eligibility") or {}
    eligibility_decision = _safe_text(eligibility.get("decision") or eligibility.get("status")).strip()
    if eligibility_decision not in {"REMEDIATION_DRAFT_ELIGIBLE", "REMEDIATION_DRAFT_ELIGIBLE_WITH_WARNINGS"}:
        return []

    findings = load_findings(job_id, jobs_base)
    decisions = load_review_decisions(job_id, jobs_base).get("decisions") or {}
    eligible_findings: list[dict[str, Any]] = []
    for finding in findings:
        finding_id = _safe_text(finding.get("finding_id")).strip()
        decision = decisions.get(finding_id) or {}
        if _safe_text(decision.get("decision")).strip() != "needs_remediation":
            continue
        merged = dict(finding)
        merged["review_decision"] = decision
        eligible_findings.append(merged)
    return eligible_findings


def generate_remediation_draft_for_finding(
    job_id: str,
    finding: dict[str, Any],
    decision: dict[str, Any],
    jobs_base: Optional[Path] = None,
) -> dict[str, Any]:
    """Generate a single local remediation draft for one finding."""
    finding_id = _safe_text(finding.get("finding_id")).strip()
    draft_id = _draft_id_for_finding(finding_id)
    action_type = _proposed_action_type(finding)
    risk_level = _severity_to_risk_level(finding.get("severity"), action_type)

    draft = {
        "draft_id": draft_id,
        "finding_id": finding_id,
        "device_id": finding.get("device_id"),
        "scope": finding.get("scope"),
        "object_type": finding.get("object_type"),
        "object_name": finding.get("object_name"),
        "rule_id": finding.get("rule_id"),
        "severity": finding.get("severity"),
        "proposed_action_type": action_type,
        "proposed_change": _proposed_change_for_finding(finding, action_type),
        "risk_level": risk_level,
        "requires_approval": True,
        "requires_apply_plan": False,
        "write_allowed": False,
        "execution_allowed": False,
        "status": "draft",
        "generated_at": _now(),
        "generated_by": decision.get("reviewer") or "unknown",
        "safety": {
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False,
        },
    }
    return draft


def _render_drafts_markdown(job_id: str, generated_by: str, drafts: list[dict[str, Any]], safety: dict[str, Any]) -> str:
    lines = [
        "# REMEDIATION-DRAFTS",
        "",
        f"## Job ID\n`{job_id}`",
        "",
        f"## Generated By\n`{generated_by}`",
        "",
        f"## Draft Count\n`{len(drafts)}`",
        "",
        "## Drafts",
    ]
    if not drafts:
        lines.append("- none")
    for draft in drafts:
        proposed = draft.get("proposed_change") or {}
        lines.extend(
            [
                "",
                f"### {draft.get('draft_id')}",
                f"- finding_id: {draft.get('finding_id')}",
                f"- device_id: {draft.get('device_id')}",
                f"- scope: {draft.get('scope')}",
                f"- object_type: {draft.get('object_type')}",
                f"- object_name: {draft.get('object_name')}",
                f"- proposed_action_type: {draft.get('proposed_action_type')}",
                f"- risk_level: {draft.get('risk_level')}",
                f"- status: {draft.get('status')}",
                f"- target: {proposed.get('target')}",
                f"- field: {proposed.get('field')}",
                f"- current_value: {proposed.get('current_value')}",
                f"- proposed_value: {proposed.get('proposed_value')}",
                f"- command_preview: {proposed.get('command_preview')}",
            ]
        )
    lines.extend(
        [
            "",
            "## Safety",
            f"- netbox_write={safety.get('netbox_write', False)}",
            f"- device_write={safety.get('device_write', False)}",
            f"- sync_called={safety.get('sync_called', False)}",
            f"- approval_record_created={safety.get('approval_record_created', False)}",
            f"- apply_plan_created={safety.get('apply_plan_created', False)}",
        ]
    )
    return "\n".join(lines) + "\n"


def load_remediation_drafts(job_id: str, jobs_base: Optional[Path] = None) -> dict[str, Any]:
    """Load remediation draft artifacts for a job."""
    drafts_dir = _remediation_drafts_dir(job_id, jobs_base)
    drafts_path = drafts_dir / REMEDIATION_DRAFTS_FILENAME
    return _load_json(drafts_path) if drafts_path.exists() else {
        "job_id": job_id,
        "status": "REMEDIATION_DRAFTS_MISSING",
        "generated_at": "",
        "generated_by": "",
        "drafts": [],
        "safety": {
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False,
        },
    }


def summarize_remediation_drafts(job_id: str, jobs_base: Optional[Path] = None) -> dict[str, Any]:
    """Summarize remediation draft artifacts."""
    payload = load_remediation_drafts(job_id, jobs_base)
    drafts = list(payload.get("drafts") or [])
    summary = {
        "job_id": job_id,
        "total_drafts": len(drafts),
        "manual_review": sum(1 for draft in drafts if draft.get("proposed_action_type") == "manual_review"),
        "metadata_updates": sum(1 for draft in drafts if draft.get("proposed_action_type") == "netbox_metadata_update"),
        "documentation_updates": sum(1 for draft in drafts if draft.get("proposed_action_type") == "documentation_update"),
        "device_candidates": sum(1 for draft in drafts if draft.get("proposed_action_type") == "device_config_candidate"),
        "high_risk": sum(1 for draft in drafts if draft.get("risk_level") == "high"),
        "medium_risk": sum(1 for draft in drafts if draft.get("risk_level") == "medium"),
        "low_risk": sum(1 for draft in drafts if draft.get("risk_level") == "low"),
        "safety": payload.get("safety")
        or {
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False,
        },
    }
    return summary


def generate_remediation_drafts(job_id: str, operator: str, jobs_base: Optional[Path] = None) -> dict[str, Any]:
    """Generate all local remediation drafts for a job."""
    if not operator or not str(operator).strip():
        return {"success": False, "error": "operator é obrigatório"}

    job = load_compliance_job(job_id, jobs_base)
    job_dir = _safe_job_dir(job_id, jobs_base)
    drafts_dir = _remediation_drafts_dir(job_id, jobs_base)
    drafts_dir.mkdir(parents=True, exist_ok=True)

    eligibility = job.get("remediation_draft_eligibility") or {}
    eligibility_decision = _safe_text(eligibility.get("decision") or eligibility.get("status")).strip()
    if eligibility_decision not in {"REMEDIATION_DRAFT_ELIGIBLE", "REMEDIATION_DRAFT_ELIGIBLE_WITH_WARNINGS"}:
        return {"success": False, "error": "remediation-draft-eligibility.json ausente ou bloqueado"}

    eligible_findings = load_remediation_eligible_findings(job_id, jobs_base)
    if not eligible_findings:
        return {"success": False, "error": "nenhum finding com decisão needs_remediation disponível"}

    draft_decisions = load_review_decisions(job_id, jobs_base).get("decisions") or {}
    drafts: list[dict[str, Any]] = []
    for finding in eligible_findings:
        finding_id = _safe_text(finding.get("finding_id")).strip()
        decision = draft_decisions.get(finding_id) or {}
        draft = generate_remediation_draft_for_finding(job_id, finding, decision, jobs_base)
        drafts.append(draft)

    payload = {
        "job_id": job_id,
        "status": "REMEDIATION_DRAFTS_GENERATED",
        "generated_at": _now(),
        "generated_by": operator,
        "drafts": drafts,
        "summary": {
            "job_id": job_id,
            "total_drafts": len(drafts),
            "manual_review": sum(1 for draft in drafts if draft.get("proposed_action_type") == "manual_review"),
            "metadata_updates": sum(1 for draft in drafts if draft.get("proposed_action_type") == "netbox_metadata_update"),
            "documentation_updates": sum(1 for draft in drafts if draft.get("proposed_action_type") == "documentation_update"),
            "device_candidates": sum(1 for draft in drafts if draft.get("proposed_action_type") == "device_config_candidate"),
            "high_risk": sum(1 for draft in drafts if draft.get("risk_level") == "high"),
            "medium_risk": sum(1 for draft in drafts if draft.get("risk_level") == "medium"),
            "low_risk": sum(1 for draft in drafts if draft.get("risk_level") == "low"),
            "safety": {
                "netbox_write": False,
                "device_write": False,
                "sync_called": False,
                "approval_record_created": False,
                "apply_plan_created": False,
            },
        },
        "safety": {
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False,
        },
    }

    drafts_json = drafts_dir / REMEDIATION_DRAFTS_FILENAME
    drafts_md = drafts_dir / REMEDIATION_DRAFTS_MARKDOWN
    _dump_json(drafts_json, payload)
    drafts_md.write_text(_render_drafts_markdown(job_id, operator, drafts, payload["safety"]), encoding="utf-8")

    return {
        "success": True,
        "job_id": job_id,
        "status": payload["status"],
        "decision": payload["status"],
        "generated_by": operator,
        "draft_count": len(drafts),
        "drafts": drafts,
        "summary": payload["summary"],
        "files": {
            "remediation_drafts_json": str(drafts_json),
            "remediation_drafts_markdown": str(drafts_md),
        },
        "safety": payload["safety"],
    }


def _render_promotion_gate_markdown(job_id: str, operator: str, decision: str, gate: dict[str, Any]) -> str:
    lines = [
        "# REMEDIATION-PROMOTION-GATE",
        "",
        f"## Job ID\n`{job_id}`",
        "",
        f"## Operator\n`{operator}`",
        "",
        f"## Decision\n`{decision}`",
        "",
        "## Checks",
    ]
    for key, value in (gate.get("checks") or {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Warnings",
        ]
    )
    warnings = gate.get("warnings") or []
    if warnings:
        lines.extend([f"- {warning}" for warning in warnings])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Safety",
            "- no ApprovalRecord",
            "- no ApplyPlan",
            "- no /sync",
            "- no write action",
        ]
    )
    return "\n".join(lines) + "\n"


def evaluate_remediation_promotion_gate(
    job_id: str,
    operator: str,
    confirm_human_reviewed_drafts: bool,
    jobs_base: Optional[Path] = None,
) -> dict[str, Any]:
    """Evaluate whether remediation drafts may move to the next approval-candidate flow."""
    job = load_compliance_job(job_id, jobs_base)
    drafts_dir = _remediation_drafts_dir(job_id, jobs_base)
    drafts_dir.mkdir(parents=True, exist_ok=True)

    drafts_payload = load_remediation_drafts(job_id, jobs_base)
    validation_payload = _load_json(drafts_dir / "remediation-draft-validation.json")
    drafts = list(drafts_payload.get("drafts") or [])
    validation_decision = _safe_text(validation_payload.get("decision") or validation_payload.get("status")).strip()
    summary = summarize_remediation_drafts(job_id, jobs_base)

    checks = {
        "operator_present": bool(_safe_text(operator).strip()),
        "confirm_human_reviewed_drafts": bool(confirm_human_reviewed_drafts) is True,
        "drafts_exist": bool(drafts),
        "validation_exists": bool(validation_payload),
        "validation_not_unsafe": validation_decision != "REMEDIATION_DRAFTS_UNSAFE",
        "no_apply_plan_created": not any(_safe_job_dir(job_id, jobs_base).glob("**/apply-plan.json")),
        "no_approval_record_created": not any(_safe_job_dir(job_id, jobs_base).glob("**/approval-record.json")),
    }

    warnings: list[str] = []
    if validation_decision == "REMEDIATION_DRAFTS_SAFE_WITH_WARNINGS":
        warnings.append("validation reported warnings")
    if any(draft.get("risk_level") == "high" for draft in drafts):
        warnings.append("high risk drafts present")

    if not all(checks.values()):
        decision = "REMEDIATION_PROMOTION_BLOCKED"
    elif warnings:
        decision = "REMEDIATION_PROMOTION_CANDIDATE_READY_WITH_WARNINGS"
    else:
        decision = "REMEDIATION_PROMOTION_CANDIDATE_READY"

    gate = {
        "job_id": job_id,
        "operator": operator,
        "confirm_human_reviewed_drafts": bool(confirm_human_reviewed_drafts),
        "checked_at": _now(),
        "decision": decision,
        "status": decision,
        "checks": checks,
        "warnings": warnings,
        "summary": summary,
        "validation_decision": validation_decision or "missing",
        "safety": {
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False,
        },
    }

    gate_json = drafts_dir / REMEDIATION_PROMOTION_GATE_FILENAME
    gate_md = drafts_dir / REMEDIATION_PROMOTION_GATE_MARKDOWN
    _dump_json(gate_json, gate)
    gate_md.write_text(_render_promotion_gate_markdown(job_id, operator, decision, gate), encoding="utf-8")

    return {
        "success": True,
        "job_id": job_id,
        "status": decision,
        "decision": decision,
        "files": {
            "remediation_promotion_gate": str(gate_json),
            "remediation_promotion_gate_markdown": str(gate_md),
        },
        "remediation_promotion_gate": gate,
        "safety": gate["safety"],
    }
