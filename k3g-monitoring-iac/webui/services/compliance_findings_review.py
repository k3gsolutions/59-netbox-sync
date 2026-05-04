"""Compliance findings review and decision workflow.

Local decision storage. No NetBox writes. No SSH/SNMP/NETCONF. No ApprovalRecord/ApplyPlan.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .compliance_jobs import JOBS_BASE, _load_json, _load_text


ALLOWED_DECISIONS = {
    "accepted",
    "false_positive",
    "ignored_temporarily",
    "needs_remediation",
    "needs_more_evidence",
    "blocked",
}

DECISION_STATUS_MAP = {
    "accepted": "reviewed",
    "false_positive": "dismissed",
    "ignored_temporarily": "deferred",
    "needs_remediation": "remediation_candidate",
    "needs_more_evidence": "pending_evidence",
    "blocked": "blocked",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_job_dir(job_id: str, jobs_base: Optional[Path] = None) -> Path:
    return (jobs_base or JOBS_BASE) / job_id


def _load_findings_from_comparison(job_id: str, jobs_base: Optional[Path] = None) -> list[dict[str, Any]]:
    """Load all findings from comparison/devices/*/compliance-findings.json."""
    job_dir = _safe_job_dir(job_id, jobs_base)
    comparison_dir = job_dir / "comparison"
    findings: list[dict[str, Any]] = []

    if not comparison_dir.exists():
        return findings

    for device_dir in sorted(comparison_dir.glob("devices/*")):
        findings_path = device_dir / "compliance-findings.json"
        if findings_path.exists():
            try:
                data = json.loads(findings_path.read_text(encoding="utf-8"))
                findings.extend(data.get("findings") or [])
            except Exception:
                pass

    return findings


def load_findings(job_id: str, jobs_base: Optional[Path] = None) -> list[dict[str, Any]]:
    """Load all findings from comparison artifacts."""
    return _load_findings_from_comparison(job_id, jobs_base)


def load_review_decisions(job_id: str, jobs_base: Optional[Path] = None) -> dict[str, Any]:
    """Load finding-decisions.json."""
    job_dir = _safe_job_dir(job_id, jobs_base)
    review_dir = job_dir / "review"
    decisions_path = review_dir / "finding-decisions.json"

    if not decisions_path.exists():
        return {"decisions": {}}

    return _load_json(decisions_path) or {"decisions": {}}


def validate_finding_decision(decision_payload: dict[str, Any]) -> tuple[bool, str]:
    """Validate finding decision payload."""
    reviewer = str(decision_payload.get("reviewer") or "").strip()
    reason = str(decision_payload.get("reason") or "").strip()
    decision = str(decision_payload.get("decision") or "").strip()

    if not reviewer:
        return False, "reviewer obrigatório"
    if not reason:
        return False, "reason obrigatório"
    if decision not in ALLOWED_DECISIONS:
        return False, f"decision inválida: {decision}"

    return True, ""


def save_finding_decision(
    job_id: str,
    finding_id: str,
    decision_payload: dict[str, Any],
    jobs_base: Optional[Path] = None,
) -> dict[str, Any]:
    """Validate and save a finding decision."""
    job_dir = _safe_job_dir(job_id, jobs_base)
    review_dir = job_dir / "review"
    review_dir.mkdir(parents=True, exist_ok=True)

    # Validate
    valid, error = validate_finding_decision(decision_payload)
    if not valid:
        return {"success": False, "error": error}

    # Load all findings
    findings = load_findings(job_id, jobs_base)
    finding = next((f for f in findings if f.get("finding_id") == finding_id), None)
    if not finding:
        return {"success": False, "error": f"finding {finding_id} não encontrado"}

    # Load existing decisions
    existing = load_review_decisions(job_id, jobs_base)
    decisions_dict = existing.get("decisions") or {}

    # Get previous decision if any
    previous = decisions_dict.get(finding_id)

    # Build decision entry
    decision = str(decision_payload.get("decision")).strip()
    reviewer = str(decision_payload.get("reviewer")).strip()
    reason = str(decision_payload.get("reason")).strip()
    severity_override = decision_payload.get("severity_override")

    entry = {
        "finding_id": finding_id,
        "reviewer": reviewer,
        "decision": decision,
        "reason": reason,
        "severity_override": severity_override,
        "decided_at": _now(),
        "status": DECISION_STATUS_MAP.get(decision, "unknown"),
    }

    decisions_dict[finding_id] = entry

    # Write finding-decisions.json
    decisions_json = {
        "job_id": job_id,
        "decisions": decisions_dict,
        "updated_at": _now(),
        "safety": {
            "netbox_write": False,
            "device_connection": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False,
        },
    }
    decisions_path = review_dir / "finding-decisions.json"
    decisions_path.write_text(json.dumps(decisions_json, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Write audit file
    audit_dir = review_dir / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_timestamp = _now().replace(":", "-").replace("+", "-")
    audit_path = audit_dir / f"{finding_id}-{audit_timestamp}.json"
    audit_entry = {
        "job_id": job_id,
        "finding_id": finding_id,
        "reviewer": reviewer,
        "decision": decision,
        "reason": reason,
        "previous_decision": previous.get("decision") if previous else None,
        "timestamp": _now(),
        "safety": {
            "netbox_write": False,
            "device_connection": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False,
        },
    }
    audit_path.write_text(json.dumps(audit_entry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Write FINDING-DECISIONS.md
    lines = [
        "# FINDING-DECISIONS",
        "",
        f"## Job ID\n`{job_id}`",
        "",
        "## Decisions",
        "",
    ]
    for fid, dec in decisions_dict.items():
        lines.extend([
            f"### {fid}",
            f"- decision: {dec.get('decision')}",
            f"- status: {dec.get('status')}",
            f"- reviewer: {dec.get('reviewer')}",
            f"- reason: {dec.get('reason')}",
            f"- decided_at: {dec.get('decided_at')}",
            "",
        ])

    md_path = review_dir / "FINDING-DECISIONS.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "success": True,
        "finding_id": finding_id,
        "decision": decision,
        "status": entry["status"],
        "audit_path": str(audit_path),
        "safety": {
            "netbox_write": False,
            "device_connection": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False,
        },
    }


def summarize_review(job_id: str, jobs_base: Optional[Path] = None) -> dict[str, Any]:
    """Summarize review status."""
    findings = load_findings(job_id, jobs_base)
    decisions_data = load_review_decisions(job_id, jobs_base)
    decisions_dict = decisions_data.get("decisions") or {}

    total_findings = len(findings)
    reviewed = sum(1 for f in findings if f.get("finding_id") in decisions_dict)
    pending = total_findings - reviewed
    needs_remediation = sum(
        1
        for f in findings
        if decisions_dict.get(f.get("finding_id"), {}).get("decision") == "needs_remediation"
    )
    blocked = sum(
        1
        for f in findings
        if decisions_dict.get(f.get("finding_id"), {}).get("decision") == "blocked"
    )

    return {
        "job_id": job_id,
        "total_findings": total_findings,
        "reviewed": reviewed,
        "needs_remediation": needs_remediation,
        "blocked": blocked,
        "pending": pending,
        "safety": {
            "netbox_write": False,
            "device_connection": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False,
        },
    }


def evaluate_remediation_draft_eligibility(job_id: str, jobs_base: Optional[Path] = None) -> dict[str, Any]:
    """Evaluate eligibility for remediation draft creation."""
    job_dir = _safe_job_dir(job_id, jobs_base)
    review_dir = job_dir / "review"
    review_dir.mkdir(parents=True, exist_ok=True)

    findings = load_findings(job_id, jobs_base)
    decisions_data = load_review_decisions(job_id, jobs_base)
    decisions_dict = decisions_data.get("decisions") or {}

    # Gate checks
    gates = {
        "has_findings": len(findings) > 0,
        "no_blocked_findings": not any(
            d.get("decision") == "blocked" for d in decisions_dict.values()
        ),
        "critical_reviewed": all(
            f.get("finding_id") in decisions_dict
            for f in findings
            if f.get("severity") in {"blocker", "error"}
        ),
        "has_remediation_candidates": any(
            d.get("decision") == "needs_remediation" for d in decisions_dict.values()
        ),
    }

    # Determine status
    all_gates_pass = all(gates.values())
    if not all_gates_pass:
        status = "REMEDIATION_DRAFT_BLOCKED"
    else:
        status = "REMEDIATION_DRAFT_ELIGIBLE"

    result = {
        "job_id": job_id,
        "status": status,
        "decision": status,
        "gates": gates,
        "summary": summarize_review(job_id, jobs_base),
        "checked_at": _now(),
        "safety": {
            "netbox_write": False,
            "device_connection": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False,
        },
    }

    # Write eligibility artifacts
    eligibility_json = {
        "job_id": job_id,
        "status": status,
        "decision": status,
        "gates": gates,
        "summary": result["summary"],
        "checked_at": _now(),
        "safety": result["safety"],
    }
    eligibility_path = review_dir / "remediation-draft-eligibility.json"
    eligibility_path.write_text(json.dumps(eligibility_json, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Write markdown
    lines = [
        "# REMEDIATION-DRAFT-ELIGIBILITY",
        "",
        f"## Job ID\n`{job_id}`",
        "",
        f"## Status\n`{status}`",
        "",
        "## Gates",
        f"- has_findings: {gates['has_findings']}",
        f"- no_blocked_findings: {gates['no_blocked_findings']}",
        f"- critical_reviewed: {gates['critical_reviewed']}",
        f"- has_remediation_candidates: {gates['has_remediation_candidates']}",
        "",
        "## Summary",
        f"- total_findings: {result['summary']['total_findings']}",
        f"- reviewed: {result['summary']['reviewed']}",
        f"- needs_remediation: {result['summary']['needs_remediation']}",
        f"- blocked: {result['summary']['blocked']}",
        f"- pending: {result['summary']['pending']}",
        "",
        "## Safety",
        "- netbox_write=false",
        "- device_connection=false",
        "- sync_called=false",
        "- approval_record_created=false",
        "- apply_plan_created=false",
    ]
    md_path = review_dir / "REMEDIATION-DRAFT-ELIGIBILITY.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return result
