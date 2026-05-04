"""
Compliance Proposed ApprovalRecords (FASE COMPLIANCE-APPROVALRECORD-001)

Builds proposed ApprovalRecord artifacts from approval candidates.
No NetBox writes, no SSH/SNMP/NETCONF, no actual ApprovalRecord creation.
"""

import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


def load_applyplan_candidate_gate(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Load ApplyPlan candidate gate result."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    gate_path = jobs_base / job_id / "approval-candidates" / "approvalrecord-proposal-gate.json"
    if not gate_path.exists():
        return {}

    with open(gate_path, "r") as f:
        return json.load(f)


def load_safe_approval_candidates(job_id: str, jobs_base: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load safe approval candidates."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    candidates_file = jobs_base / job_id / "approval-candidates" / "approval-candidates.json"
    if not candidates_file.exists():
        return []

    try:
        with open(candidates_file, "r") as f:
            data = json.load(f)
            return data.get("candidates", [])
    except Exception:
        return []


def load_approval_validation(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Load approval candidate validation."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    validation_file = jobs_base / job_id / "approval-candidates" / "approval-candidate-validation.json"
    if not validation_file.exists():
        return {}

    with open(validation_file, "r") as f:
        return json.load(f)


def build_proposed_approval_record_for_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Build a single proposed ApprovalRecord from a candidate."""
    record_id = f"PAR-{uuid.uuid4().hex[:8].upper()}"

    return {
        "approval_record_id": record_id,
        "candidate_id": candidate.get("candidate_id"),
        "finding_id": candidate.get("finding_id"),
        "device_id": candidate.get("device_id"),
        "device_name": candidate.get("device_name"),
        "scope": candidate.get("scope"),
        "object_type": candidate.get("object_type"),
        "object_name": candidate.get("object_name"),
        "rule_id": candidate.get("rule_id"),
        "severity": candidate.get("severity"),
        "risk_level": candidate.get("risk_level"),
        "proposed_action_type": candidate.get("proposed_action_type"),
        "proposed_change": candidate.get("proposed_change", {}),
        "status": "proposed",
        "approved": False,
        "approved_by": None,
        "approved_at": None,
        "write_allowed": False,
        "execution_allowed": False,
        "apply_plan_created": False,
        "manual_approval_required": True,
        "state_history": [
            {
                "status": "proposed",
                "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "created_by": None,
                "reason": "Proposed from candidate"
            }
        ],
        "safety": {
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False
        }
    }


def build_proposed_approval_records(job_id: str, operator: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Build proposed ApprovalRecords from safe approval candidates."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    # Check proposal gate
    gate = load_applyplan_candidate_gate(job_id, jobs_base)
    if not gate:
        raise ValueError(f"ApprovalRecord proposal gate not found for job {job_id}")

    gate_decision = gate.get("decision")
    if gate_decision not in ("APPROVALRECORD_PROPOSAL_READY", "APPROVALRECORD_PROPOSAL_READY_WITH_WARNINGS"):
        raise ValueError(f"Proposal gate decision is {gate_decision}; must be READY or READY_WITH_WARNINGS")

    # Check validation
    validation = load_approval_validation(job_id, jobs_base)
    if validation and validation.get("decision") == "APPROVAL_CANDIDATES_UNSAFE":
        raise ValueError("Approval candidate validation marked unsafe; cannot build proposed records")

    # Load candidates
    candidates = load_safe_approval_candidates(job_id, jobs_base)
    if not candidates:
        raise ValueError(f"No approval candidates found for job {job_id}")

    # Build records
    records = []
    for candidate in candidates:
        record = build_proposed_approval_record_for_candidate(candidate)
        records.append(record)

    # Create directory
    proposed_dir = jobs_base / job_id / "approval-records" / "proposed"
    proposed_dir.mkdir(parents=True, exist_ok=True)

    # Build result
    result = {
        "job_id": job_id,
        "status": "PROPOSED_APPROVAL_RECORDS_BUILT",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "created_by": operator,
        "records": records,
        "record_count": len(records),
        "safety": {
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False
        }
    }

    # Write JSON
    records_file = proposed_dir / "proposed-approval-records.json"
    with open(records_file, "w") as f:
        json.dump(result, f, indent=2)

    # Write markdown
    md_content = _generate_proposed_records_markdown(result)
    md_file = proposed_dir / "PROPOSED-APPROVAL-RECORDS.md"
    with open(md_file, "w") as f:
        f.write(md_content)

    return result


def _generate_proposed_records_markdown(result: Dict[str, Any]) -> str:
    """Generate markdown summary of proposed records."""
    lines = [
        "# Proposed ApprovalRecords",
        "",
        f"**Status:** {result.get('status')}",
        f"**Created at:** {result.get('created_at')}",
        f"**Created by:** {result.get('created_by')}",
        f"**Total records:** {result.get('record_count')}",
        "",
        "## Records",
        ""
    ]

    for record in result.get("records", []):
        lines.append(f"### {record.get('approval_record_id')}")
        lines.append("")
        lines.append(f"- **Candidate ID:** {record.get('candidate_id')}")
        lines.append(f"- **Finding ID:** {record.get('finding_id')}")
        lines.append(f"- **Status:** {record.get('status')}")
        lines.append(f"- **Device:** {record.get('device_name')} ({record.get('device_id')})")
        lines.append(f"- **Object:** {record.get('object_type')} — {record.get('object_name')}")
        lines.append(f"- **Approved:** {record.get('approved')}")
        lines.append(f"- **Manual approval required:** {record.get('manual_approval_required')}")
        lines.append("")

    lines.append("## Safety")
    lines.append("")
    lines.append("✗ No NetBox writes")
    lines.append("✗ No device writes")
    lines.append("✗ No ApplyPlan created")
    lines.append("")

    return "\n".join(lines)


def load_proposed_approval_records(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Load existing proposed ApprovalRecords."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    records_file = jobs_base / job_id / "approval-records" / "proposed" / "proposed-approval-records.json"
    if not records_file.exists():
        return {}

    with open(records_file, "r") as f:
        return json.load(f)


def summarize_proposed_approval_records(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Summarize proposed ApprovalRecords."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    records = load_proposed_approval_records(job_id, jobs_base)
    if not records:
        return {
            "job_id": job_id,
            "record_count": 0,
            "approved_count": 0,
            "pending_count": 0
        }

    record_list = records.get("records", [])
    approved_count = sum(1 for r in record_list if r.get("approved"))
    pending_count = len(record_list) - approved_count

    return {
        "job_id": job_id,
        "status": records.get("status"),
        "created_at": records.get("created_at"),
        "created_by": records.get("created_by"),
        "record_count": len(record_list),
        "approved_count": approved_count,
        "pending_count": pending_count,
        "safety": records.get("safety", {
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False
        })
    }
