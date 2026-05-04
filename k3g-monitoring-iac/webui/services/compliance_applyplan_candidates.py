"""
Compliance ApplyPlan Candidate Builder (FASES COMPLIANCE-APPLYPLAN-001–002)

Builds ApplyPlan candidate from proposed ApprovalRecords.
No NetBox writes, no SSH/SNMP/NETCONF, no execution.
"""

import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


ALLOWED_ENDPOINTS = {
    "/api/dcim/interfaces/",
    "/api/dcim/devices/",
    "/api/dcim/device-types/",
    "/api/dcim/sites/",
    "/api/dcim/regions/",
    "/api/ipam/ip-addresses/",
    "/api/ipam/prefixes/",
    "/api/dcim/cables/",
}

ALLOWED_METHODS = {"POST", "PATCH"}
FORBIDDEN_METHODS = {"DELETE", "PUT"}

FORBIDDEN_KEYWORDS = {
    "token",
    "password",
    "secret",
    "cipher",
    "private_key",
    "api_key",
    "access_key",
}


def load_applyplan_candidate_gate(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Load ApplyPlan candidate gate result."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    gate_path = jobs_base / job_id / "approval-records" / "proposed" / "applyplan-candidate-gate.json"
    if not gate_path.exists():
        return {}

    with open(gate_path, "r") as f:
        return json.load(f)


def load_proposed_approval_records(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Load proposed ApprovalRecords."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    records_file = jobs_base / job_id / "approval-records" / "proposed" / "proposed-approval-records.json"
    if not records_file.exists():
        return {}

    with open(records_file, "r") as f:
        return json.load(f)


def load_approval_record_validation(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Load proposed ApprovalRecord validation."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    validation_file = jobs_base / job_id / "approval-records" / "proposed" / "proposed-approval-record-validation.json"
    if not validation_file.exists():
        return {}

    with open(validation_file, "r") as f:
        return json.load(f)


def _build_applyplan_item_for_record(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Build an ApplyPlan item from a proposed record.

    Returns None if record requires manual review (no auto-generated endpoint).
    """
    # For now, map all to manual_review (safe approach)
    # In production, may map specific scopes to NetBox endpoints

    return {
        "item_id": f"APC-{uuid.uuid4().hex[:8].upper()}",
        "approval_record_id": record.get("approval_record_id"),
        "device_id": record.get("device_id"),
        "object_type": record.get("object_type"),
        "object_name": record.get("object_name"),
        "target": "netbox",
        "method": "POST",
        "endpoint": None,  # No auto mapping yet
        "payload": record.get("proposed_change", {}),
        "write_allowed": False,
        "execution_allowed": False,
        "requires_dry_run": True,
        "requires_real_write_gate": True,
        "status": "candidate",
        "approval_required": True
    }


def build_applyplan_candidate(
    job_id: str, operator: str, jobs_base: Optional[Path] = None
) -> Dict[str, Any]:
    """Build ApplyPlan candidate from proposed ApprovalRecords."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    # Check gate
    gate = load_applyplan_candidate_gate(job_id, jobs_base)
    if not gate:
        raise ValueError(f"ApplyPlan candidate gate not found for job {job_id}")

    gate_decision = gate.get("decision")
    if gate_decision not in ("APPLYPLAN_CANDIDATE_READY", "APPLYPLAN_CANDIDATE_READY_WITH_WARNINGS"):
        raise ValueError(f"ApplyPlan candidate gate decision is {gate_decision}; must be READY or READY_WITH_WARNINGS")

    # Check validation
    validation = load_approval_record_validation(job_id, jobs_base)
    if validation and validation.get("decision") == "PROPOSED_APPROVAL_RECORDS_UNSAFE":
        raise ValueError("Proposed approval records validation marked unsafe; cannot build ApplyPlan")

    # Load records
    records_data = load_proposed_approval_records(job_id, jobs_base)
    if not records_data:
        raise ValueError(f"No proposed ApprovalRecords found for job {job_id}")

    records = records_data.get("records", [])
    if not records:
        raise ValueError(f"Proposed ApprovalRecords list is empty for job {job_id}")

    # Build items
    items = []
    for record in records:
        # Skip approved records
        if record.get("approved"):
            continue

        item = _build_applyplan_item_for_record(record)
        if item:
            items.append(item)

    if not items:
        raise ValueError(f"No ApplyPlan items could be built from proposed records for job {job_id}")

    # Create directory
    candidate_dir = jobs_base / job_id / "applyplan" / "candidate"
    candidate_dir.mkdir(parents=True, exist_ok=True)

    # Build result
    result = {
        "job_id": job_id,
        "status": "APPLYPLAN_CANDIDATE_BUILT",
        "mode": "candidate",
        "created_by": operator,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "records": records,
        "items": items,
        "item_count": len(items),
        "safety": {
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "dry_run_required": True,
            "real_write_blocked": True
        }
    }

    # Write JSON
    candidate_file = candidate_dir / "applyplan-candidate.json"
    with open(candidate_file, "w") as f:
        json.dump(result, f, indent=2)

    # Write markdown
    md_content = _generate_candidate_markdown(result)
    md_file = candidate_dir / "APPLYPLAN-CANDIDATE.md"
    with open(md_file, "w") as f:
        f.write(md_content)

    return result


def _generate_candidate_markdown(result: Dict[str, Any]) -> str:
    """Generate markdown summary of ApplyPlan candidate."""
    lines = [
        "# ApplyPlan Candidate",
        "",
        f"**Status:** {result.get('status')}",
        f"**Mode:** {result.get('mode')}",
        f"**Created at:** {result.get('created_at')}",
        f"**Created by:** {result.get('created_by')}",
        f"**Total items:** {result.get('item_count')}",
        "",
        "## Items",
        ""
    ]

    for item in result.get("items", []):
        lines.append(f"### {item.get('item_id')}")
        lines.append("")
        lines.append(f"- **Approval Record:** {item.get('approval_record_id')}")
        lines.append(f"- **Device:** {item.get('device_id')}")
        lines.append(f"- **Object:** {item.get('object_type')} — {item.get('object_name')}")
        lines.append(f"- **Method:** {item.get('method')}")
        lines.append(f"- **Target:** {item.get('target')}")
        lines.append(f"- **Status:** {item.get('status')}")
        lines.append(f"- **Dry-run required:** {item.get('requires_dry_run')}")
        lines.append(f"- **Real-write gate required:** {item.get('requires_real_write_gate')}")
        lines.append("")

    lines.append("## Safety")
    lines.append("")
    lines.append("✗ No execution at this stage")
    lines.append("✗ No NetBox writes")
    lines.append("✗ Dry-run required before real write")
    lines.append("✗ Real-write gate required")
    lines.append("")

    return "\n".join(lines)


def load_applyplan_candidate(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Load existing ApplyPlan candidate."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    candidate_file = jobs_base / job_id / "applyplan" / "candidate" / "applyplan-candidate.json"
    if not candidate_file.exists():
        return {}

    with open(candidate_file, "r") as f:
        return json.load(f)


def summarize_applyplan_candidate(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Summarize ApplyPlan candidate."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    candidate = load_applyplan_candidate(job_id, jobs_base)
    if not candidate:
        return {
            "job_id": job_id,
            "item_count": 0
        }

    return {
        "job_id": job_id,
        "status": candidate.get("status"),
        "mode": candidate.get("mode"),
        "created_at": candidate.get("created_at"),
        "created_by": candidate.get("created_by"),
        "item_count": len(candidate.get("items", [])),
        "safety": candidate.get("safety", {
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "dry_run_required": True,
            "real_write_blocked": True
        })
    }
