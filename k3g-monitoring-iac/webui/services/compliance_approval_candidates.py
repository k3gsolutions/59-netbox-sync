"""
Compliance Approval Candidates Builder (FASE COMPLIANCE-APPROVAL-001)

Builds approval candidates from safe remediation drafts.
No NetBox writes, no SSH/SNMP/NETCONF, no ApprovalRecord creation, no ApplyPlan.
"""

import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


def load_remediation_promotion_gate(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Load remediation promotion gate result."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    gate_path = jobs_base / job_id / "remediation" / "remediation-promotion-gate.json"
    if not gate_path.exists():
        return {}

    with open(gate_path, "r") as f:
        return json.load(f)


def load_safe_remediation_drafts(job_id: str, jobs_base: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load remediation drafts from drafts directory."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    drafts_dir = jobs_base / job_id / "remediation" / "drafts"
    if not drafts_dir.exists():
        return []

    drafts = []
    for draft_file in sorted(drafts_dir.glob("*-draft.json")):
        try:
            with open(draft_file, "r") as f:
                draft = json.load(f)
                # Only include safe drafts (validation marked safe)
                if draft.get("write_allowed") is False and draft.get("execution_allowed") is False:
                    drafts.append(draft)
        except Exception:
            pass

    return drafts


def load_remediation_draft_validation(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Load remediation draft validation result."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    validation_path = jobs_base / job_id / "remediation" / "remediation-draft-validation.json"
    if not validation_path.exists():
        return {}

    with open(validation_path, "r") as f:
        return json.load(f)


def build_approval_candidate_for_draft(job_id: str, draft: Dict[str, Any]) -> Dict[str, Any]:
    """Build a single approval candidate from a draft."""
    candidate_id = f"AC-{uuid.uuid4().hex[:8].upper()}"

    return {
        "candidate_id": candidate_id,
        "draft_id": draft.get("draft_id"),
        "finding_id": draft.get("finding_id"),
        "device_id": draft.get("device_id"),
        "device_name": draft.get("device_name"),
        "scope": draft.get("scope"),
        "object_type": draft.get("object_type"),
        "object_name": draft.get("object_name"),
        "rule_id": draft.get("rule_id"),
        "severity": draft.get("severity"),
        "risk_level": draft.get("risk_level"),
        "proposed_action_type": draft.get("proposed_action_type"),
        "proposed_change": draft.get("proposed_change", {}),
        "approval_intent": {
            "approval_type": "manual_review_required",
            "approval_required": True,
            "reason": "Draft requires human approval before any proposed record."
        },
        "status": "candidate",
        "write_allowed": False,
        "execution_allowed": False,
        "approval_record_created": False,
        "apply_plan_created": False,
        "safety": {
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False
        }
    }


def build_approval_candidates(job_id: str, operator: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Build approval candidates from safe remediation drafts."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    # Check promotion gate
    gate = load_remediation_promotion_gate(job_id, jobs_base)
    if not gate:
        raise ValueError(f"Promotion gate not found for job {job_id}")

    gate_decision = gate.get("decision")
    if gate_decision not in ("REMEDIATION_PROMOTION_CANDIDATE_READY", "REMEDIATION_PROMOTION_CANDIDATE_READY_WITH_WARNINGS"):
        raise ValueError(f"Promotion gate decision is {gate_decision}; must be READY or READY_WITH_WARNINGS")

    # Load validation
    validation = load_remediation_draft_validation(job_id, jobs_base)
    if validation and validation.get("decision") == "REMEDIATION_DRAFT_VALIDATION_UNSAFE":
        raise ValueError("Draft validation marked unsafe; cannot build candidates")

    # Load drafts
    drafts = load_safe_remediation_drafts(job_id, jobs_base)
    if not drafts:
        raise ValueError(f"No safe remediation drafts found for job {job_id}")

    # Build candidates
    candidates = []
    for draft in drafts:
        # Skip if marked as needs additional review
        if draft.get("requires_additional_review"):
            continue

        candidate = build_approval_candidate_for_draft(job_id, draft)
        candidates.append(candidate)

    # Create approval-candidates directory
    candidates_dir = jobs_base / job_id / "approval-candidates"
    candidates_dir.mkdir(parents=True, exist_ok=True)

    # Build result
    result = {
        "job_id": job_id,
        "status": "APPROVAL_CANDIDATES_BUILT",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "generated_by": operator,
        "candidates": candidates,
        "candidate_count": len(candidates),
        "safety": {
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False
        }
    }

    # Write candidates JSON
    candidates_file = candidates_dir / "approval-candidates.json"
    with open(candidates_file, "w") as f:
        json.dump(result, f, indent=2)

    # Write candidates markdown
    md_content = _generate_approval_candidates_markdown(result)
    md_file = candidates_dir / "APPROVAL-CANDIDATES.md"
    with open(md_file, "w") as f:
        f.write(md_content)

    return result


def _generate_approval_candidates_markdown(result: Dict[str, Any]) -> str:
    """Generate markdown summary of approval candidates."""
    lines = [
        "# Approval Candidates",
        "",
        f"**Status:** {result.get('status')}",
        f"**Generated at:** {result.get('generated_at')}",
        f"**Generated by:** {result.get('generated_by')}",
        f"**Total candidates:** {result.get('candidate_count')}",
        "",
        "## Candidates",
        ""
    ]

    for candidate in result.get("candidates", []):
        lines.append(f"### {candidate.get('candidate_id')}")
        lines.append("")
        lines.append(f"- **Draft ID:** {candidate.get('draft_id')}")
        lines.append(f"- **Finding ID:** {candidate.get('finding_id')}")
        lines.append(f"- **Device:** {candidate.get('device_name')} ({candidate.get('device_id')})")
        lines.append(f"- **Severity:** {candidate.get('severity')}")
        lines.append(f"- **Risk Level:** {candidate.get('risk_level')}")
        lines.append(f"- **Scope:** {candidate.get('scope')}")
        lines.append(f"- **Object:** {candidate.get('object_type')} — {candidate.get('object_name')}")
        lines.append(f"- **Action Type:** {candidate.get('proposed_action_type')}")
        lines.append(f"- **Status:** {candidate.get('status')}")
        lines.append("")

    lines.append("## Safety")
    lines.append("")
    lines.append("✗ NetBox writes disabled")
    lines.append("✗ Device writes disabled")
    lines.append("✗ Sync disabled")
    lines.append("✗ ApprovalRecord creation disabled")
    lines.append("✗ ApplyPlan creation disabled")
    lines.append("")

    return "\n".join(lines)


def load_approval_candidates(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Load existing approval candidates."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    candidates_file = jobs_base / job_id / "approval-candidates" / "approval-candidates.json"
    if not candidates_file.exists():
        return {}

    with open(candidates_file, "r") as f:
        return json.load(f)


def summarize_approval_candidates(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Summarize approval candidates and validation status."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    candidates = load_approval_candidates(job_id, jobs_base)
    if not candidates:
        return {
            "job_id": job_id,
            "candidate_count": 0,
            "validation_status": None,
            "safety": {
                "netbox_write": False,
                "device_write": False,
                "sync_called": False,
                "approval_record_created": False,
                "apply_plan_created": False
            }
        }

    return {
        "job_id": job_id,
        "status": candidates.get("status"),
        "generated_at": candidates.get("generated_at"),
        "generated_by": candidates.get("generated_by"),
        "candidate_count": len(candidates.get("candidates", [])),
        "safety": candidates.get("safety", {
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False
        })
    }
