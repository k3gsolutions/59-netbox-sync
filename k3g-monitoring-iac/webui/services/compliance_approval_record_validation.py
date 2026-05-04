"""
Compliance Proposed ApprovalRecord Validation (FASE COMPLIANCE-APPROVALRECORD-003)

Validates proposed ApprovalRecords for safety and governance.
No NetBox writes, no SSH/SNMP/NETCONF.
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple, Optional


FORBIDDEN_KEYWORDS = {
    "token",
    "password",
    "secret",
    "cipher",
    "private_key",
    "api_key",
    "access_key",
}


def load_proposed_approval_records(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Load proposed ApprovalRecords."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    records_file = jobs_base / job_id / "approval-records" / "proposed" / "proposed-approval-records.json"
    if not records_file.exists():
        return {}

    with open(records_file, "r") as f:
        return json.load(f)


def _contains_secret(text: str) -> Tuple[bool, str]:
    """Check if text contains secret keywords."""
    if not text:
        return False, ""

    text_lower = text.lower()
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in text_lower:
            return True, keyword

    return False, ""


def _validate_record(record: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a single proposed ApprovalRecord."""
    issues = []

    # Check status=proposed
    if record.get("status") != "proposed":
        issues.append(f"{record.get('approval_record_id')}: status must be 'proposed', got '{record.get('status')}'")

    # Check approved=false
    if record.get("approved") is not False:
        issues.append(f"{record.get('approval_record_id')}: approved must be False")

    # Check approved_by=null
    if record.get("approved_by") is not None:
        issues.append(f"{record.get('approval_record_id')}: approved_by must be null")

    # Check approved_at=null
    if record.get("approved_at") is not None:
        issues.append(f"{record.get('approval_record_id')}: approved_at must be null")

    # Check write_allowed=false
    if record.get("write_allowed") is not False:
        issues.append(f"{record.get('approval_record_id')}: write_allowed must be False")

    # Check execution_allowed=false
    if record.get("execution_allowed") is not False:
        issues.append(f"{record.get('approval_record_id')}: execution_allowed must be False")

    # Check apply_plan_created=false
    if record.get("apply_plan_created") is not False:
        issues.append(f"{record.get('approval_record_id')}: apply_plan_created must be False")

    # Check manual_approval_required=true
    if record.get("manual_approval_required") is not True:
        issues.append(f"{record.get('approval_record_id')}: manual_approval_required must be True")

    # Check state_history exists
    if not record.get("state_history"):
        issues.append(f"{record.get('approval_record_id')}: state_history must exist")

    # Check proposed_change for secrets
    proposed_change = record.get("proposed_change", {})
    change_str = json.dumps(proposed_change, default=str)
    has_secret, keyword = _contains_secret(change_str)
    if has_secret:
        issues.append(f"{record.get('approval_record_id')}: secret keyword '{keyword}' in proposed_change")

    # Check safety flags
    safety = record.get("safety", {})
    if safety.get("netbox_write") is not False:
        issues.append(f"{record.get('approval_record_id')}: safety.netbox_write must be False")
    if safety.get("device_write") is not False:
        issues.append(f"{record.get('approval_record_id')}: safety.device_write must be False")
    if safety.get("sync_called") is not False:
        issues.append(f"{record.get('approval_record_id')}: safety.sync_called must be False")

    return len(issues) == 0, issues


def validate_proposed_approval_records(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Validate all proposed ApprovalRecords."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    records_data = load_proposed_approval_records(job_id, jobs_base)
    if not records_data:
        raise ValueError(f"No proposed ApprovalRecords found for job {job_id}")

    records = records_data.get("records", [])
    if not records:
        raise ValueError(f"Proposed ApprovalRecords list is empty for job {job_id}")

    # Validate each record
    all_issues = []
    valid_count = 0

    for record in records:
        is_valid, issues = _validate_record(record)
        if is_valid:
            valid_count += 1
        else:
            all_issues.extend(issues)

    # Determine decision
    if all_issues:
        if len(all_issues) > len(records) * 0.25:
            decision = "PROPOSED_APPROVAL_RECORDS_UNSAFE"
        else:
            decision = "PROPOSED_APPROVAL_RECORDS_SAFE_WITH_WARNINGS"
    else:
        decision = "PROPOSED_APPROVAL_RECORDS_SAFE"

    # Create directory
    validation_dir = jobs_base / job_id / "approval-records" / "proposed"
    validation_dir.mkdir(parents=True, exist_ok=True)

    # Build result
    result = {
        "job_id": job_id,
        "status": "validation_completed",
        "decision": decision,
        "validated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "record_count": len(records),
        "valid_count": valid_count,
        "issues": all_issues,
        "issue_count": len(all_issues),
        "safety": {
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False
        }
    }

    # Write JSON
    validation_file = validation_dir / "proposed-approval-record-validation.json"
    with open(validation_file, "w") as f:
        json.dump(result, f, indent=2)

    # Write markdown
    md_content = _generate_validation_markdown(result)
    md_file = validation_dir / "PROPOSED-APPROVAL-RECORD-VALIDATION.md"
    with open(md_file, "w") as f:
        f.write(md_content)

    return result


def _generate_validation_markdown(result: Dict[str, Any]) -> str:
    """Generate markdown validation report."""
    lines = [
        "# Proposed ApprovalRecord Validation",
        "",
        f"**Status:** {result.get('decision')}",
        f"**Validated at:** {result.get('validated_at')}",
        "",
        "## Summary",
        "",
        f"- Total records: {result.get('record_count')}",
        f"- Valid: {result.get('valid_count')}",
        f"- Issues: {result.get('issue_count')}",
        "",
    ]

    if result.get("issues"):
        lines.append("## Issues")
        lines.append("")
        for issue in result.get("issues"):
            lines.append(f"- {issue}")
        lines.append("")

    lines.append("## Safety")
    lines.append("")
    lines.append("✗ No NetBox writes during validation")
    lines.append("✗ No device connections")
    lines.append("✗ No ApplyPlan creation")
    lines.append("")

    return "\n".join(lines)
