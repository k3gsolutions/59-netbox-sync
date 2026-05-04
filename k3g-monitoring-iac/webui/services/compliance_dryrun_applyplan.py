"""
Compliance Dry-Run ApplyPlan (FASES COMPLIANCE-APPLYPLAN-003–004)

Builds and validates dry-run ApplyPlan from candidate.
No NetBox writes, no SSH/SNMP/NETCONF, no execution.
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


def load_applyplan_candidate(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Load ApplyPlan candidate."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    candidate_file = jobs_base / job_id / "applyplan" / "candidate" / "applyplan-candidate.json"
    if not candidate_file.exists():
        return {}

    with open(candidate_file, "r") as f:
        return json.load(f)


def load_applyplan_candidate_validation(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Load ApplyPlan candidate validation."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    validation_file = jobs_base / job_id / "applyplan" / "candidate" / "applyplan-candidate-validation.json"
    if not validation_file.exists():
        return {}

    with open(validation_file, "r") as f:
        return json.load(f)


def build_dryrun_applyplan(job_id: str, operator: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Build dry-run ApplyPlan from validated candidate."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    # Load candidate
    candidate = load_applyplan_candidate(job_id, jobs_base)
    if not candidate:
        raise ValueError(f"No ApplyPlan candidate found for job {job_id}")

    # Load validation
    validation = load_applyplan_candidate_validation(job_id, jobs_base)
    if validation and validation.get("decision") == "APPLYPLAN_CANDIDATE_INVALID":
        raise ValueError("ApplyPlan candidate validation marked invalid; cannot build dry-run")

    items = candidate.get("items", [])
    if not items:
        raise ValueError(f"ApplyPlan candidate has no items for job {job_id}")

    # Create directory
    dryrun_dir = jobs_base / job_id / "applyplan" / "dry-run"
    dryrun_dir.mkdir(parents=True, exist_ok=True)

    # Build result
    result = {
        "job_id": job_id,
        "status": "DRY_RUN_APPLYPLAN_BUILT",
        "mode": "dry_run",
        "execution_allowed": False,
        "can_execute_real_write": False,
        "requires_next_gate": True,
        "created_by": operator,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "items": items,
        "item_count": len(items),
        "safety": {
            "dry_run_only": True,
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "real_write_blocked": True
        }
    }

    # Write JSON
    dryrun_file = dryrun_dir / "dry-run-applyplan.json"
    with open(dryrun_file, "w") as f:
        json.dump(result, f, indent=2)

    # Write markdown
    md_content = _generate_dryrun_markdown(result)
    md_file = dryrun_dir / "DRY-RUN-APPLYPLAN.md"
    with open(md_file, "w") as f:
        f.write(md_content)

    return result


def _generate_dryrun_markdown(result: Dict[str, Any]) -> str:
    """Generate markdown summary of dry-run ApplyPlan."""
    lines = [
        "# Dry-Run ApplyPlan",
        "",
        f"**Status:** {result.get('status')}",
        f"**Mode:** {result.get('mode')}",
        f"**Created at:** {result.get('created_at')}",
        f"**Created by:** {result.get('created_by')}",
        f"**Total items:** {result.get('item_count')}",
        f"**Execution allowed:** {result.get('execution_allowed')}",
        f"**Can execute real write:** {result.get('can_execute_real_write')}",
        "",
        "## Items",
        ""
    ]

    for item in result.get("items", []):
        lines.append(f"- {item.get('item_id')}: {item.get('object_type')} — {item.get('object_name')} ({item.get('method')})")

    lines.append("")
    lines.append("## Safety")
    lines.append("")
    lines.append("✗ No actual execution")
    lines.append("✗ No NetBox writes")
    lines.append("✗ Dry-run only")
    lines.append("✗ Real-write blocked at this stage")
    lines.append("")

    return "\n".join(lines)


def load_dryrun_applyplan(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Load dry-run ApplyPlan."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    dryrun_file = jobs_base / job_id / "applyplan" / "dry-run" / "dry-run-applyplan.json"
    if not dryrun_file.exists():
        return {}

    with open(dryrun_file, "r") as f:
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


def _validate_dryrun_item(item: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a single dry-run item."""
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


def validate_dryrun_applyplan(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Validate dry-run ApplyPlan."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    dryrun_data = load_dryrun_applyplan(job_id, jobs_base)
    if not dryrun_data:
        raise ValueError(f"No dry-run ApplyPlan found for job {job_id}")

    # Check mode
    if dryrun_data.get("mode") != "dry_run":
        raise ValueError(f"Mode is '{dryrun_data.get('mode')}'; expected 'dry_run'")

    # Check execution_allowed
    if dryrun_data.get("execution_allowed") is not False:
        raise ValueError("execution_allowed must be False")

    # Check can_execute_real_write
    if dryrun_data.get("can_execute_real_write") is not False:
        raise ValueError("can_execute_real_write must be False")

    # Check requires_next_gate
    if dryrun_data.get("requires_next_gate") is not True:
        raise ValueError("requires_next_gate must be True")

    items = dryrun_data.get("items", [])
    if not items:
        raise ValueError(f"Dry-run ApplyPlan has no items for job {job_id}")

    # Validate each item
    all_issues = []
    valid_count = 0

    for item in items:
        is_valid, issues = _validate_dryrun_item(item)
        if is_valid:
            valid_count += 1
        else:
            all_issues.extend(issues)

    # Determine decision
    if all_issues:
        if len(all_issues) > len(items) * 0.25:
            decision = "DRY_RUN_APPLYPLAN_INVALID"
        else:
            decision = "DRY_RUN_APPLYPLAN_VALID_WITH_WARNINGS"
    else:
        decision = "DRY_RUN_APPLYPLAN_VALID"

    # Create directory
    validation_dir = jobs_base / job_id / "applyplan" / "dry-run"
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
            "dry_run_only": True,
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "real_write_blocked": True
        }
    }

    # Write JSON
    validation_file = validation_dir / "dry-run-applyplan-validation.json"
    with open(validation_file, "w") as f:
        json.dump(result, f, indent=2)

    # Write markdown
    md_content = _generate_validation_markdown(result)
    md_file = validation_dir / "DRY-RUN-APPLYPLAN-VALIDATION.md"
    with open(md_file, "w") as f:
        f.write(md_content)

    return result


def _generate_validation_markdown(result: Dict[str, Any]) -> str:
    """Generate markdown validation report."""
    lines = [
        "# Dry-Run ApplyPlan Validation",
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
    lines.append("✗ No execution at this stage")
    lines.append("✗ No NetBox writes")
    lines.append("✗ Real-write blocked")
    lines.append("")

    return "\n".join(lines)
