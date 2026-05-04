"""
Compliance Real Write Closure Package (FASES COMPLIANCE-REALWRITE-010)

Consolidates evidence from all phases, generates final decision, closes job.
No writes, no external calls. Audit trail complete.
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional


def load_realwrite_execution_result(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Load real-write execution result."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    result_file = jobs_base / job_id / "real-write" / "execution" / "real-write-execution-result.json"
    if not result_file.exists():
        return {}

    with open(result_file, "r") as f:
        return json.load(f)


def load_postwrite_verification(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Load post-write verification result."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    verification_file = jobs_base / job_id / "real-write" / "verification" / "post-write-verification.json"
    if not verification_file.exists():
        return {}

    with open(verification_file, "r") as f:
        return json.load(f)


def load_postwrite_compliance_rerun(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Load post-write compliance re-run result."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    rerun_file = jobs_base / job_id / "real-write" / "compliance-rerun" / "post-write-compliance-rerun.json"
    if not rerun_file.exists():
        return {}

    with open(rerun_file, "r") as f:
        return json.load(f)


def build_realwrite_closure_package(job_id: str, operator: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """REALWRITE-010: Build closure package — consolidate evidence and close."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    # Load all evidence
    execution_result = load_realwrite_execution_result(job_id, jobs_base)
    verification_result = load_postwrite_verification(job_id, jobs_base)
    compliance_result = load_postwrite_compliance_rerun(job_id, jobs_base)

    # Determine closure decision
    closure_decision = _evaluate_closure_decision(execution_result, verification_result, compliance_result)

    result = {
        "job_id": job_id,
        "status": "closure_completed",
        "decision": closure_decision["decision"],
        "reason": closure_decision["reason"],
        "closed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "closed_by": operator,
        "evidence": {
            "execution_status": execution_result.get("status", "NOT_FOUND"),
            "execution_items": execution_result.get("item_count", 0),
            "execution_success": execution_result.get("success_count", 0),
            "verification_status": verification_result.get("decision", "NOT_APPLICABLE"),
            "verification_passed": verification_result.get("verified_count", 0),
            "compliance_status": compliance_result.get("decision", "NOT_APPLICABLE"),
            "compliance_passed": compliance_result.get("passed", 0)
        },
        "gates": {
            "execution_required": True,
            "verification_gate": verification_result != {} if verification_result else False,
            "compliance_gate": compliance_result != {} if compliance_result else False
        },
        "safety": {
            "netbox_write": False,
            "netbox_read": False,
            "device_connection": False,
            "ssh_connection": False,
            "closure_only": True,
            "no_rollback": True
        }
    }

    # Write closure package
    closure_dir = jobs_base / job_id / "real-write" / "closure"
    closure_dir.mkdir(parents=True, exist_ok=True)

    closure_file = closure_dir / "closure-package.json"
    with open(closure_file, "w") as f:
        json.dump(result, f, indent=2)

    # Write markdown
    md_content = _generate_closure_markdown(result)
    md_file = closure_dir / "CLOSURE-PACKAGE.md"
    with open(md_file, "w") as f:
        f.write(md_content)

    return result


def _evaluate_closure_decision(
    execution_result: Dict[str, Any],
    verification_result: Dict[str, Any],
    compliance_result: Dict[str, Any]
) -> Dict[str, str]:
    """Determine closure decision from evidence."""

    # No execution = cannot close
    if not execution_result:
        return {
            "decision": "COMPLIANCE_JOB_CLOSED_ACTION_REQUIRED",
            "reason": "Real-write execution not found. Review and retry."
        }

    exec_status = execution_result.get("status")
    if exec_status != "REAL_WRITE_SUCCESS":
        return {
            "decision": "COMPLIANCE_JOB_CLOSED_ACTION_REQUIRED",
            "reason": f"Real-write execution failed: {exec_status}"
        }

    # Execution succeeded, but no items executed
    if execution_result.get("item_count", 0) == 0:
        return {
            "decision": "COMPLIANCE_JOB_CLOSED_NOT_APPLICABLE",
            "reason": "No items were executed."
        }

    # Execution succeeded with items
    # Verification not applicable (objects not created)
    if verification_result and verification_result.get("decision", "").startswith("VERIFICATION_NOT_APPLICABLE"):
        return {
            "decision": "COMPLIANCE_JOB_CLOSED_NOT_APPLICABLE",
            "reason": f"Verification: {verification_result.get('decision')}"
        }

    # Verification failed
    if verification_result and verification_result.get("decision") == "POSTWRITE_VERIFICATION_FAILED":
        return {
            "decision": "COMPLIANCE_JOB_CLOSED_WITH_WARNINGS",
            "reason": f"Verification failed: {verification_result.get('failed_count')} items failed verification."
        }

    # Compliance re-run not applicable
    if compliance_result and compliance_result.get("decision", "").startswith("COMPLIANCE_RERUN_NOT_APPLICABLE"):
        return {
            "decision": "COMPLIANCE_JOB_CLOSED_NOT_APPLICABLE",
            "reason": f"Compliance re-run: {compliance_result.get('decision')}"
        }

    # Compliance re-run failed
    if compliance_result and compliance_result.get("decision") == "COMPLIANCE_RERUN_PARTIAL_FAILED":
        return {
            "decision": "COMPLIANCE_JOB_CLOSED_WITH_WARNINGS",
            "reason": f"Compliance re-run partial failure: {compliance_result.get('failed')} checks failed."
        }

    # All gates passed
    return {
        "decision": "COMPLIANCE_JOB_CLOSED_SUCCESS",
        "reason": "Execution, verification, and compliance re-run all passed."
    }


def _generate_closure_markdown(result: Dict[str, Any]) -> str:
    """Generate closure package markdown."""
    lines = [
        "# Compliance Job Closure Package",
        "",
        f"**Job ID:** {result.get('job_id')}",
        f"**Status:** {result.get('decision')}",
        f"**Closed at:** {result.get('closed_at')}",
        f"**Closed by:** {result.get('closed_by')}",
        "",
        "## Reason",
        "",
        f"{result.get('reason')}",
        "",
        "## Evidence Summary",
        ""
    ]

    evidence = result.get("evidence", {})
    lines.append(f"### Execution")
    lines.append(f"- Status: {evidence.get('execution_status')}")
    lines.append(f"- Items: {evidence.get('execution_items')}")
    lines.append(f"- Success: {evidence.get('execution_success')}")
    lines.append("")

    lines.append(f"### Verification")
    lines.append(f"- Status: {evidence.get('verification_status')}")
    lines.append(f"- Verified: {evidence.get('verification_passed')}")
    lines.append("")

    lines.append(f"### Compliance Re-Run")
    lines.append(f"- Status: {evidence.get('compliance_status')}")
    lines.append(f"- Passed: {evidence.get('compliance_passed')}")
    lines.append("")

    lines.append("## Safety")
    lines.append("")
    lines.append("✓ No NetBox writes")
    lines.append("✓ No SSH/SNMP/NETCONF")
    lines.append("✓ No automatic rollback")
    lines.append("✓ Closure only")
    lines.append("")

    decision = result.get("decision")
    lines.append("## Next Step")
    lines.append("")
    if decision == "COMPLIANCE_JOB_CLOSED_SUCCESS":
        lines.append("✓ Job completed successfully. All gates passed.")
    elif decision == "COMPLIANCE_JOB_CLOSED_WITH_WARNINGS":
        lines.append("⚠ Job closed with warnings. Review evidence and take action if needed.")
    elif decision == "COMPLIANCE_JOB_CLOSED_NOT_APPLICABLE":
        lines.append("ℹ Job closed as not applicable. No action needed.")
    else:
        lines.append("✗ Job closure failed. Manual review required.")
    lines.append("")

    return "\n".join(lines)
