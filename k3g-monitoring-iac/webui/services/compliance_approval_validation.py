"""
Compliance Approval Validation (FASE COMPLIANCE-APPROVAL-003)

Validates approval candidates for safety and security.
No NetBox writes, no SSH/SNMP/NETCONF, no ApprovalRecord creation.
"""

import json
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple


FORBIDDEN_COMMANDS = {
    "system-view",
    "configure",
    "commit",
    "save",
    "delete",
    "undo",
    "shutdown",
    "reboot",
    "reset",
    "patch",
    "sync",
}

FORBIDDEN_KEYWORDS = {
    "token",
    "password",
    "secret",
    "cipher",
    "private_key",
    "api_key",
    "access_key",
}


def load_approval_candidates(job_id: str, jobs_base: Path = None) -> Dict[str, Any]:
    """Load approval candidates."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    candidates_file = jobs_base / job_id / "approval-candidates" / "approval-candidates.json"
    if not candidates_file.exists():
        return {}

    with open(candidates_file, "r") as f:
        return json.load(f)


def _contains_forbidden_command(text: str) -> Tuple[bool, str]:
    """Check if text contains forbidden commands."""
    if not text:
        return False, ""

    text_lower = text.lower()
    for cmd in FORBIDDEN_COMMANDS:
        if cmd in text_lower:
            return True, cmd

    return False, ""


def _contains_secret(text: str) -> Tuple[bool, str]:
    """Check if text contains secret keywords."""
    if not text:
        return False, ""

    text_lower = text.lower()
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in text_lower:
            return True, keyword

    return False, ""


def _validate_candidate(candidate: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a single candidate."""
    issues = []

    # Check write_allowed
    if candidate.get("write_allowed") is not False:
        issues.append(f"{candidate.get('candidate_id')}: write_allowed must be False")

    # Check execution_allowed
    if candidate.get("execution_allowed") is not False:
        issues.append(f"{candidate.get('candidate_id')}: execution_allowed must be False")

    # Check approval_record_created
    if candidate.get("approval_record_created") is not False:
        issues.append(f"{candidate.get('candidate_id')}: approval_record_created must be False")

    # Check apply_plan_created
    if candidate.get("apply_plan_created") is not False:
        issues.append(f"{candidate.get('candidate_id')}: apply_plan_created must be False")

    # Check proposed_change for forbidden commands
    proposed_change = candidate.get("proposed_change", {})
    change_str = json.dumps(proposed_change, default=str)

    has_forbidden, cmd = _contains_forbidden_command(change_str)
    if has_forbidden:
        issues.append(f"{candidate.get('candidate_id')}: forbidden command '{cmd}' in proposed_change")

    # Check proposed_change for secrets
    has_secret, keyword = _contains_secret(change_str)
    if has_secret:
        issues.append(f"{candidate.get('candidate_id')}: secret keyword '{keyword}' in proposed_change")

    # Check approval_intent
    approval_intent = candidate.get("approval_intent", {})
    if approval_intent.get("approval_required") is not True:
        issues.append(f"{candidate.get('candidate_id')}: approval_required must be True")

    # Check safety flags
    safety = candidate.get("safety", {})
    if safety.get("netbox_write") is not False:
        issues.append(f"{candidate.get('candidate_id')}: safety.netbox_write must be False")
    if safety.get("device_write") is not False:
        issues.append(f"{candidate.get('candidate_id')}: safety.device_write must be False")
    if safety.get("sync_called") is not False:
        issues.append(f"{candidate.get('candidate_id')}: safety.sync_called must be False")
    if safety.get("approval_record_created") is not False:
        issues.append(f"{candidate.get('candidate_id')}: safety.approval_record_created must be False")
    if safety.get("apply_plan_created") is not False:
        issues.append(f"{candidate.get('candidate_id')}: safety.apply_plan_created must be False")

    return len(issues) == 0, issues


def validate_approval_candidates(job_id: str, jobs_base: Path = None) -> Dict[str, Any]:
    """Validate all approval candidates."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    candidates_data = load_approval_candidates(job_id, jobs_base)
    if not candidates_data:
        raise ValueError(f"No approval candidates found for job {job_id}")

    candidates = candidates_data.get("candidates", [])
    if not candidates:
        raise ValueError(f"Approval candidates list is empty for job {job_id}")

    # Validate each candidate
    all_issues = []
    valid_count = 0

    for candidate in candidates:
        is_valid, issues = _validate_candidate(candidate)
        if is_valid:
            valid_count += 1
        else:
            all_issues.extend(issues)

    # Determine decision
    if all_issues:
        if len(all_issues) > len(candidates) * 0.25:  # More than 25% issues
            decision = "APPROVAL_CANDIDATES_UNSAFE"
        else:
            decision = "APPROVAL_CANDIDATES_SAFE_WITH_WARNINGS"
    else:
        decision = "APPROVAL_CANDIDATES_SAFE"

    # Create validation directory
    validation_dir = jobs_base / job_id / "approval-candidates"
    validation_dir.mkdir(parents=True, exist_ok=True)

    # Build result
    result = {
        "job_id": job_id,
        "status": "validation_completed",
        "decision": decision,
        "validated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "candidate_count": len(candidates),
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

    # Write validation JSON
    validation_file = validation_dir / "approval-candidate-validation.json"
    with open(validation_file, "w") as f:
        json.dump(result, f, indent=2)

    # Write validation markdown
    md_content = _generate_validation_markdown(result)
    md_file = validation_dir / "APPROVAL-CANDIDATE-VALIDATION.md"
    with open(md_file, "w") as f:
        f.write(md_content)

    return result


def _generate_validation_markdown(result: Dict[str, Any]) -> str:
    """Generate markdown validation report."""
    lines = [
        "# Approval Candidate Validation",
        "",
        f"**Status:** {result.get('decision')}",
        f"**Validated at:** {result.get('validated_at')}",
        "",
        "## Summary",
        "",
        f"- Total candidates: {result.get('candidate_count')}",
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
    lines.append("✗ NetBox writes blocked")
    lines.append("✗ Device writes blocked")
    lines.append("✗ Sync blocked")
    lines.append("✗ ApprovalRecord creation blocked")
    lines.append("✗ ApplyPlan creation blocked")
    lines.append("")

    return "\n".join(lines)
