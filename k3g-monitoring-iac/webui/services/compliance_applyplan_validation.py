"""
Compliance ApplyPlan Candidate Validation (FASES COMPLIANCE-APPLYPLAN-002)

Validates ApplyPlan candidate for safety and governance.
No NetBox writes, no SSH/SNMP/NETCONF.
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple, Optional


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


def load_applyplan_candidate(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Load ApplyPlan candidate."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    candidate_file = jobs_base / job_id / "applyplan" / "candidate" / "applyplan-candidate.json"
    if not candidate_file.exists():
        return {}

    with open(candidate_file, "r") as f:
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


def _validate_item(item: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a single ApplyPlan item."""
    issues = []

    # Check write_allowed
    if item.get("write_allowed") is not False:
        issues.append(f"{item.get('item_id')}: write_allowed must be False")

    # Check execution_allowed
    if item.get("execution_allowed") is not False:
        issues.append(f"{item.get('item_id')}: execution_allowed must be False")

    # Check requires_dry_run
    if item.get("requires_dry_run") is not True:
        issues.append(f"{item.get('item_id')}: requires_dry_run must be True")

    # Check requires_real_write_gate
    if item.get("requires_real_write_gate") is not True:
        issues.append(f"{item.get('item_id')}: requires_real_write_gate must be True")

    # Check method if endpoint exists
    endpoint = item.get("endpoint")
    method = item.get("method")
    if endpoint:
        if method not in ALLOWED_METHODS:
            issues.append(f"{item.get('item_id')}: method '{method}' not in allowed methods")

    # Check payload for secrets
    payload = item.get("payload", {})
    payload_str = json.dumps(payload, default=str)
    has_secret, keyword = _contains_secret(payload_str)
    if has_secret:
        issues.append(f"{item.get('item_id')}: secret keyword '{keyword}' in payload")

    # Check for /sync
    if "/sync" in payload_str:
        issues.append(f"{item.get('item_id')}: /sync found in payload")

    return len(issues) == 0, issues


def validate_applyplan_candidate(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Validate ApplyPlan candidate."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    candidate_data = load_applyplan_candidate(job_id, jobs_base)
    if not candidate_data:
        raise ValueError(f"No ApplyPlan candidate found for job {job_id}")

    # Check mode
    if candidate_data.get("mode") != "candidate":
        raise ValueError(f"ApplyPlan candidate mode is '{candidate_data.get('mode')}'; expected 'candidate'")

    # Check write_allowed
    if candidate_data.get("write_allowed") is not False:
        raise ValueError("ApplyPlan candidate write_allowed must be False")

    # Check execution_allowed
    if candidate_data.get("execution_allowed") is not False:
        raise ValueError("ApplyPlan candidate execution_allowed must be False")

    items = candidate_data.get("items", [])
    if not items:
        raise ValueError(f"ApplyPlan candidate has no items for job {job_id}")

    # Validate each item
    all_issues = []
    valid_count = 0

    for item in items:
        is_valid, issues = _validate_item(item)
        if is_valid:
            valid_count += 1
        else:
            all_issues.extend(issues)

    # Determine decision
    if all_issues:
        if len(all_issues) > len(items) * 0.25:
            decision = "APPLYPLAN_CANDIDATE_INVALID"
        else:
            decision = "APPLYPLAN_CANDIDATE_VALID_WITH_WARNINGS"
    else:
        decision = "APPLYPLAN_CANDIDATE_VALID"

    # Create directory
    validation_dir = jobs_base / job_id / "applyplan" / "candidate"
    validation_dir.mkdir(parents=True, exist_ok=True)

    # Build result
    result = {
        "job_id": job_id,
        "status": "validation_completed",
        "decision": decision,
        "validated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "item_count": len(items),
        "valid_count": valid_count,
        "issues": all_issues,
        "issue_count": len(all_issues),
        "safety": {
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "dry_run_required": True,
            "real_write_blocked": True
        }
    }

    # Write JSON
    validation_file = validation_dir / "applyplan-candidate-validation.json"
    with open(validation_file, "w") as f:
        json.dump(result, f, indent=2)

    # Write markdown
    md_content = _generate_validation_markdown(result)
    md_file = validation_dir / "APPLYPLAN-CANDIDATE-VALIDATION.md"
    with open(md_file, "w") as f:
        f.write(md_content)

    return result


def _generate_validation_markdown(result: Dict[str, Any]) -> str:
    """Generate markdown validation report."""
    lines = [
        "# ApplyPlan Candidate Validation",
        "",
        f"**Status:** {result.get('decision')}",
        f"**Validated at:** {result.get('validated_at')}",
        "",
        "## Summary",
        "",
        f"- Total items: {result.get('item_count')}",
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
    lines.append("✗ Dry-run required before real write")
    lines.append("")

    return "\n".join(lines)
