"""
Compliance Ops Readiness Check (FASES COMPLIANCE-OPS-001)

Pre-execution validation: all artifacts in place, gates cleared, payload safe.
No writes, no tokens, local validation only.
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple


def _load_json_artifact(path: Path) -> Dict[str, Any]:
    """Load JSON artifact, return empty dict if missing."""
    if not path.exists():
        return {}
    with open(path, "r") as f:
        return json.load(f)


def _validate_endpoint(endpoint: str) -> Tuple[bool, str]:
    """Validate endpoint."""
    if not endpoint:
        return (False, "Endpoint null or empty")
    if endpoint == "/":
        return (False, "Endpoint is root path")
    if not endpoint.startswith("/"):
        return (False, "Endpoint must start with /")
    return (True, "")


def _validate_payload_safety(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Check payload for secrets."""
    issues = []
    forbidden_keys = {"token", "password", "secret", "cipher", "private_key", "api_key", "access_key", "bearer", "authorization"}
    payload_str = json.dumps(payload).lower()

    if any(keyword in payload_str for keyword in forbidden_keys):
        issues.append("Payload contains secret keywords")

    return (len(issues) == 0, issues)


def validate_compliance_job_realwrite_readiness(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """COMPLIANCE-OPS-001: Validate job readiness for real-write execution."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    job_dir = jobs_base / job_id
    if not job_dir.exists():
        raise ValueError(f"Job {job_id} not found")

    artifacts = _check_artifacts(job_dir)
    validations = _validate_artifacts(job_dir)
    gates = _check_gates(job_dir)
    payload_checks = _check_payload(job_dir)

    # Determine readiness decision
    blockers = _find_blockers(artifacts, validations, gates, payload_checks)
    warnings = _find_warnings(artifacts, validations, gates)

    if blockers:
        decision = "COMPLIANCE_JOB_NOT_READY"
    elif warnings:
        decision = "COMPLIANCE_JOB_READY_WITH_RESTRICTIONS"
    else:
        decision = "COMPLIANCE_JOB_READY_FOR_MANUAL_REAL_WRITE"

    result = {
        "job_id": job_id,
        "status": "readiness_check_completed",
        "decision": decision,
        "checked_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "artifacts": artifacts,
        "validations": validations,
        "gates": gates,
        "payload_checks": payload_checks,
        "blockers": blockers,
        "warnings": warnings,
        "blocker_count": len(blockers),
        "warning_count": len(warnings),
        "safety": {
            "netbox_write": False,
            "netbox_read": False,
            "device_connection": False,
            "ssh_connection": False,
            "validation_only": True
        }
    }

    # Write result
    ops_dir = job_dir / "ops"
    ops_dir.mkdir(parents=True, exist_ok=True)

    result_file = ops_dir / "readiness-check.json"
    with open(result_file, "w") as f:
        json.dump(result, f, indent=2)

    # Write markdown
    md_content = _generate_readiness_markdown(result)
    md_file = ops_dir / "READINESS-CHECK.md"
    with open(md_file, "w") as f:
        f.write(md_content)

    return result


def _check_artifacts(job_dir: Path) -> Dict[str, Dict[str, bool]]:
    """Check existence of required artifacts."""
    artifacts = {
        "candidates": {},
        "collection": {},
        "compare": {},
        "review": {},
        "remediation": {},
        "approval": {},
        "applyplan": {},
        "dryrun": {},
        "realwrite": {}
    }

    # Candidates
    artifacts["candidates"]["job_request"] = (job_dir / "job-request.json").exists()
    artifacts["candidates"]["selected_devices"] = (job_dir / "selected-devices.json").exists()
    artifacts["candidates"]["eligibility_recheck"] = (job_dir / "eligibility-recheck.json").exists()

    # Collection
    artifacts["collection"]["plan"] = (job_dir / "collection/plan.json").exists()
    artifacts["collection"]["start_gate"] = (job_dir / "collection/start-gate.json").exists()

    # Compare
    artifacts["compare"]["result"] = (job_dir / "comparison/compliance-comparison-result.json").exists()
    artifacts["compare"]["findings"] = (job_dir / "comparison/devices").exists() and len(list((job_dir / "comparison/devices").glob("*/compliance-findings.json"))) > 0

    # Review
    artifacts["review"]["decisions"] = (job_dir / "review/finding-decisions.json").exists()
    artifacts["review"]["eligibility"] = (job_dir / "review/remediation-draft-eligibility.json").exists()

    # Remediation
    artifacts["remediation"]["drafts"] = (job_dir / "remediation/remediation-drafts.json").exists()
    artifacts["remediation"]["validation"] = (job_dir / "remediation/remediation-draft-validation.json").exists()
    artifacts["remediation"]["promotion_gate"] = (job_dir / "remediation/remediation-promotion-gate.json").exists()

    # Approval
    artifacts["approval"]["candidates"] = (job_dir / "approval-candidates/approval-candidates.json").exists()
    artifacts["approval"]["validation"] = (job_dir / "approval-candidates/approval-candidate-validation.json").exists()
    artifacts["approval"]["proposal_gate"] = (job_dir / "approval-candidates/approvalrecord-proposal-gate.json").exists()
    artifacts["approval"]["proposed_records"] = (job_dir / "approvalrecord/proposed-approval-records.json").exists()

    # ApplyPlan
    artifacts["applyplan"]["candidate"] = (job_dir / "applyplan/applyplan-candidate.json").exists()
    artifacts["applyplan"]["validation"] = (job_dir / "applyplan/applyplan-candidate-validation.json").exists()

    # Dry-run
    artifacts["dryrun"]["applyplan"] = (job_dir / "applyplan/dry-run/dry-run-applyplan.json").exists()
    artifacts["dryrun"]["applyplan_validation"] = (job_dir / "applyplan/dry-run/dry-run-applyplan-validation.json").exists()
    artifacts["dryrun"]["gate"] = (job_dir / "applyplan/dry-run/dry-run-execution-gate.json").exists()
    artifacts["dryrun"]["execution"] = (job_dir / "applyplan/dry-run/dry-run-execution-result.json").exists()
    artifacts["dryrun"]["validation"] = (job_dir / "applyplan/dry-run/dry-run-execution-validation.json").exists()

    # Real-write
    artifacts["realwrite"]["readiness_gate"] = (job_dir / "real-write/real-write-readiness-gate.json").exists()
    artifacts["realwrite"]["authorization"] = (job_dir / "real-write/authorization/authorization-request.json").exists()
    artifacts["realwrite"]["preflight"] = (job_dir / "real-write/authorization/final-preflight-gate.json").exists()
    artifacts["realwrite"]["execution_package"] = (job_dir / "real-write/execution/execution-package.json").exists()
    artifacts["realwrite"]["execution_validation"] = (job_dir / "real-write/execution/execution-package-validation.json").exists()
    artifacts["realwrite"]["freeze"] = (job_dir / "real-write/execution/final-no-write-freeze.json").exists()

    return artifacts


def _validate_artifacts(job_dir: Path) -> Dict[str, Any]:
    """Check validation statuses of key artifacts."""
    validations = {}

    # Dry-run validation
    dryrun_validation = _load_json_artifact(job_dir / "applyplan/dry-run/dry-run-applyplan-validation.json")
    validations["dryrun_applyplan"] = {
        "exists": dryrun_validation != {},
        "decision": dryrun_validation.get("decision", "MISSING")
    }

    # Dry-run execution validation
    dryrun_exec_validation = _load_json_artifact(job_dir / "applyplan/dry-run/dry-run-execution-validation.json")
    validations["dryrun_execution"] = {
        "exists": dryrun_exec_validation != {},
        "decision": dryrun_exec_validation.get("decision", "MISSING")
    }

    # Execution package validation
    exec_pkg_validation = _load_json_artifact(job_dir / "real-write/execution/execution-package-validation.json")
    validations["execution_package"] = {
        "exists": exec_pkg_validation != {},
        "decision": exec_pkg_validation.get("decision", "MISSING")
    }

    return validations


def _check_gates(job_dir: Path) -> Dict[str, Any]:
    """Check gate decisions."""
    gates = {}

    # Freeze gate
    freeze = _load_json_artifact(job_dir / "real-write/execution/final-no-write-freeze.json")
    gates["final_freeze"] = {
        "exists": freeze != {},
        "decision": freeze.get("decision", "MISSING")
    }

    return gates


def _check_payload(job_dir: Path) -> Dict[str, Any]:
    """Check execution package payload."""
    payload_checks = {}

    exec_pkg = _load_json_artifact(job_dir / "real-write/execution/execution-package.json")
    if exec_pkg:
        items = exec_pkg.get("items", [])
        payload_checks["item_count"] = len(items)

        safe = True
        issues = []
        for item in items:
            endpoint = item.get("endpoint", "") or ""
            payload = item.get("payload", {})
            method = item.get("method", "")

            # Validate endpoint
            ep_safe, ep_issue = _validate_endpoint(endpoint)
            if not ep_safe:
                safe = False
                issues.append(f"Item {item.get('item_id')}: {ep_issue}")

            # Check for /sync
            if endpoint and "/sync" in endpoint:
                safe = False
                issues.append(f"Item {item.get('item_id')}: Endpoint contains /sync")

            # Validate payload
            p_safe, p_issues = _validate_payload_safety(payload)
            if not p_safe:
                safe = False
                issues.extend([f"Item {item.get('item_id')}: {issue}" for issue in p_issues])

            # Check method
            if method not in ["POST", "PATCH", "DELETE"]:
                safe = False
                issues.append(f"Item {item.get('item_id')}: Invalid method {method}")

        payload_checks["payload_safe"] = safe
        payload_checks["issues"] = issues
        payload_checks["execution_allowed"] = exec_pkg.get("execution_allowed", None)
        payload_checks["token_required"] = exec_pkg.get("token_required_in_next_phase", None)
        payload_checks["one_shot"] = exec_pkg.get("one_shot_execution", None)
        payload_checks["required_phrase"] = "present" if exec_pkg.get("required_execution_phrase") else "missing"
    else:
        payload_checks = {"error": "Execution package not found"}

    return payload_checks


def _find_blockers(artifacts: Dict, validations: Dict, gates: Dict, payload_checks: Dict) -> List[str]:
    """Identify blockers that prevent execution."""
    blockers = []

    # Check critical artifacts
    if not artifacts.get("realwrite", {}).get("freeze"):
        blockers.append("Final freeze not found")

    if not artifacts.get("realwrite", {}).get("execution_package"):
        blockers.append("Execution package not found")

    # Check validation decisions
    if validations.get("execution_package", {}).get("decision") not in ["EXECUTION_PACKAGE_VALID", "EXECUTION_PACKAGE_VALID_WITH_WARNINGS"]:
        blockers.append(f"Execution package validation: {validations.get('execution_package', {}).get('decision')}")

    if gates.get("final_freeze", {}).get("decision") != "READY_FOR_REAL_WRITE_PHASE":
        blockers.append(f"Final freeze: {gates.get('final_freeze', {}).get('decision')}")

    # Check payload safety
    if payload_checks.get("execution_allowed") is not False:
        blockers.append("execution_allowed must be False")

    if payload_checks.get("token_required") is not True:
        blockers.append("token_required_in_next_phase must be True")

    if payload_checks.get("one_shot") is not True:
        blockers.append("one_shot_execution must be True")

    if payload_checks.get("required_phrase") == "missing":
        blockers.append("required_execution_phrase missing")

    if payload_checks.get("payload_safe") is False:
        blockers.extend(payload_checks.get("issues", []))

    return blockers


def _find_warnings(artifacts: Dict, validations: Dict, gates: Dict) -> List[str]:
    """Identify warnings (non-blocking issues)."""
    warnings = []

    # Check for partial failures in earlier phases
    if validations.get("dryrun_execution", {}).get("decision") == "DRY_RUN_VALIDATION_PARTIAL_FAILED":
        warnings.append("Dry-run had partial failures (informational)")

    return warnings


def _generate_readiness_markdown(result: Dict[str, Any]) -> str:
    """Generate readiness check markdown."""
    lines = [
        "# Compliance Job Readiness Check",
        "",
        f"**Job ID:** {result.get('job_id')}",
        f"**Decision:** {result.get('decision')}",
        f"**Checked at:** {result.get('checked_at')}",
        "",
        "## Summary",
        "",
        f"- Blockers: {result.get('blocker_count')}",
        f"- Warnings: {result.get('warning_count')}",
        ""
    ]

    if result.get("blockers"):
        lines.append("## Blockers (Must Fix)")
        lines.append("")
        for blocker in result.get("blockers", []):
            lines.append(f"✗ {blocker}")
        lines.append("")

    if result.get("warnings"):
        lines.append("## Warnings (Informational)")
        lines.append("")
        for warning in result.get("warnings", []):
            lines.append(f"⚠ {warning}")
        lines.append("")

    lines.append("## Artifact Status")
    lines.append("")

    artifacts = result.get("artifacts", {})
    for section, items in artifacts.items():
        found = sum(1 for v in items.values() if v)
        total = len(items)
        lines.append(f"**{section}:** {found}/{total} artifacts present")

    lines.append("")
    lines.append("## Next Step")
    lines.append("")

    decision = result.get("decision")
    if decision == "COMPLIANCE_JOB_READY_FOR_MANUAL_REAL_WRITE":
        lines.append("✓ Job ready. Follow REAL-WRITE-OPERATOR-RUNBOOK.md for execution.")
    elif decision == "COMPLIANCE_JOB_READY_WITH_RESTRICTIONS":
        lines.append("⚠ Job ready with warnings. Review warnings before execution.")
    else:
        lines.append("✗ Job not ready. Fix blockers and recheck.")

    lines.append("")
    return "\n".join(lines)
