"""
Compliance ApprovalRecord Proposal Gate (FASE COMPLIANCE-APPROVAL-004)

Validates approval candidates and gates to ApprovalRecord proposal.
No NetBox writes, no SSH/SNMP/NETCONF, no ApprovalRecord creation.
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional


def load_approval_candidates(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Load approval candidates."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    candidates_file = jobs_base / job_id / "approval-candidates" / "approval-candidates.json"
    if not candidates_file.exists():
        return {}

    with open(candidates_file, "r") as f:
        return json.load(f)


def load_approval_validation(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Load approval candidate validation result."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    validation_file = jobs_base / job_id / "approval-candidates" / "approval-candidate-validation.json"
    if not validation_file.exists():
        return {}

    with open(validation_file, "r") as f:
        return json.load(f)


def evaluate_approvalrecord_proposal_gate(
    job_id: str, operator: str, confirm_human_reviewed: bool = False, jobs_base: Optional[Path] = None
) -> Dict[str, Any]:
    """Evaluate gate to ApprovalRecord proposal.

    Pre-conditions:
    1. approval-candidates.json exists
    2. approval-candidate-validation.json exists
    3. validation decision is not UNSAFE
    4. confirm_human_reviewed=true

    Doesn't create ApprovalRecord — just signals gate status.
    """
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    # Load candidates
    candidates = load_approval_candidates(job_id, jobs_base)
    if not candidates:
        raise ValueError(f"No approval candidates found for job {job_id}")

    # Load validation
    validation = load_approval_validation(job_id, jobs_base)
    if not validation:
        raise ValueError(f"No approval candidate validation found for job {job_id}")

    # Check validation decision
    validation_decision = validation.get("decision")
    if validation_decision == "APPROVAL_CANDIDATES_UNSAFE":
        raise ValueError(f"Approval candidate validation is UNSAFE; cannot proceed to proposal")

    # Require human confirmation
    if not confirm_human_reviewed:
        raise ValueError("confirm_human_reviewed must be true")

    # Determine gate decision
    if validation_decision == "APPROVAL_CANDIDATES_SAFE":
        gate_decision = "APPROVALRECORD_PROPOSAL_READY"
        warnings = []
    elif validation_decision == "APPROVAL_CANDIDATES_SAFE_WITH_WARNINGS":
        gate_decision = "APPROVALRECORD_PROPOSAL_READY_WITH_WARNINGS"
        warnings = validation.get("issues", [])
    else:
        gate_decision = "APPROVALRECORD_PROPOSAL_BLOCKED"
        warnings = validation.get("issues", [])

    # Create gate directory
    gate_dir = jobs_base / job_id / "approval-candidates"
    gate_dir.mkdir(parents=True, exist_ok=True)

    # Build result
    result = {
        "job_id": job_id,
        "status": "gate_evaluated",
        "decision": gate_decision,
        "evaluated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "evaluated_by": operator,
        "candidate_count": len(candidates.get("candidates", [])),
        "validation_decision": validation_decision,
        "warnings": warnings,
        "safety": {
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False
        }
    }

    # Write gate JSON
    gate_file = gate_dir / "approvalrecord-proposal-gate.json"
    with open(gate_file, "w") as f:
        json.dump(result, f, indent=2)

    # Write gate markdown
    md_content = _generate_proposal_gate_markdown(result)
    md_file = gate_dir / "APPROVALRECORD-PROPOSAL-GATE.md"
    with open(md_file, "w") as f:
        f.write(md_content)

    return result


def _generate_proposal_gate_markdown(result: Dict[str, Any]) -> str:
    """Generate markdown proposal gate report."""
    lines = [
        "# ApprovalRecord Proposal Gate",
        "",
        f"**Status:** {result.get('decision')}",
        f"**Evaluated at:** {result.get('evaluated_at')}",
        f"**Evaluated by:** {result.get('evaluated_by')}",
        "",
        "## Summary",
        "",
        f"- Candidates: {result.get('candidate_count')}",
        f"- Validation decision: {result.get('validation_decision')}",
        f"- Warnings: {len(result.get('warnings', []))}",
        "",
    ]

    if result.get("warnings"):
        lines.append("## Warnings")
        lines.append("")
        for warning in result.get("warnings"):
            lines.append(f"- {warning}")
        lines.append("")

    lines.append("## Next Step")
    lines.append("")

    decision = result.get("decision")
    if decision == "APPROVALRECORD_PROPOSAL_READY":
        lines.append("✓ Ready for ApprovalRecord proposal")
    elif decision == "APPROVALRECORD_PROPOSAL_READY_WITH_WARNINGS":
        lines.append("⚠ Ready for ApprovalRecord proposal (with warnings)")
    else:
        lines.append("✗ Blocked from ApprovalRecord proposal")

    lines.append("")
    lines.append("## Safety")
    lines.append("")
    lines.append("✗ No ApprovalRecord created at this stage")
    lines.append("✗ No ApplyPlan created")
    lines.append("✗ No NetBox writes")
    lines.append("✗ No device connections")
    lines.append("")

    return "\n".join(lines)
