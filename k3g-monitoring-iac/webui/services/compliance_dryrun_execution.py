"""
Compliance Dry-Run Execution & Validation (FASES COMPLIANCE-DRYRUN-001–003)

Simulates dry-run execution locally without calling NetBox.
No real writes, no tokens, pure simulation.
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional


def load_dryrun_applyplan_validation(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Load dry-run ApplyPlan validation."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    validation_file = jobs_base / job_id / "applyplan" / "dry-run" / "dry-run-applyplan-validation.json"
    if not validation_file.exists():
        return {}

    with open(validation_file, "r") as f:
        return json.load(f)


def load_dryrun_applyplan(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Load dry-run ApplyPlan."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    dryrun_file = jobs_base / job_id / "applyplan" / "dry-run" / "dry-run-applyplan.json"
    if not dryrun_file.exists():
        return {}

    with open(dryrun_file, "r") as f:
        return json.load(f)


def evaluate_dryrun_execution_gate(job_id: str, operator: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """DRYRUN-001: Evaluate dry-run execution gate."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    # Check validation
    validation = load_dryrun_applyplan_validation(job_id, jobs_base)
    if not validation:
        raise ValueError(f"Dry-run ApplyPlan validation not found for job {job_id}")

    if validation.get("decision") == "DRY_RUN_APPLYPLAN_INVALID":
        raise ValueError("Dry-run ApplyPlan validation marked INVALID; cannot execute")

    # Create directory
    execution_dir = jobs_base / job_id / "applyplan" / "dry-run"
    execution_dir.mkdir(parents=True, exist_ok=True)

    # Gate decision based on validation
    decision = "DRY_RUN_EXECUTION_GATE_READY" if validation.get("decision") != "DRY_RUN_APPLYPLAN_INVALID" else "DRY_RUN_EXECUTION_GATE_BLOCKED"

    result = {
        "job_id": job_id,
        "status": "gate_evaluated",
        "decision": decision,
        "evaluated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "evaluated_by": operator,
        "validation_decision": validation.get("decision"),
        "safety": {
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "dry_run_only": True,
            "real_write_blocked": True
        }
    }

    # Write gate
    gate_file = execution_dir / "dry-run-execution-gate.json"
    with open(gate_file, "w") as f:
        json.dump(result, f, indent=2)

    return result


def execute_dryrun_simulation(job_id: str, operator: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """DRYRUN-002: Execute dry-run simulation locally."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    # Load ApplyPlan
    applyplan = load_dryrun_applyplan(job_id, jobs_base)
    if not applyplan:
        raise ValueError(f"Dry-run ApplyPlan not found for job {job_id}")

    items = applyplan.get("items", [])
    if not items:
        raise ValueError(f"Dry-run ApplyPlan has no items for job {job_id}")

    # Simulate each item
    execution_items = []
    for item in items:
        sim_item = {
            "item_id": item.get("item_id"),
            "approval_record_id": item.get("approval_record_id"),
            "method": item.get("method"),
            "endpoint": item.get("endpoint"),
            "status": "dry_run_success",  # Simulation success (no real call)
            "simulated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "simulated_response_status": 200,  # Mock success response
            "simulated_response_id": None  # Dry-run doesn't create actual objects
        }
        execution_items.append(sim_item)

    # Create directory
    execution_dir = jobs_base / job_id / "applyplan" / "dry-run"
    execution_dir.mkdir(parents=True, exist_ok=True)

    # Build result
    result = {
        "job_id": job_id,
        "status": "DRY_RUN_EXECUTION_PASSED",
        "mode": "dry_run",
        "executed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "executed_by": operator,
        "items": execution_items,
        "item_count": len(execution_items),
        "success_count": len([i for i in execution_items if i.get("status") == "dry_run_success"]),
        "failed_count": 0,
        "safety": {
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "dry_run_only": True,
            "real_write_blocked": True
        }
    }

    # Write execution result
    execution_file = execution_dir / "dry-run-execution-result.json"
    with open(execution_file, "w") as f:
        json.dump(result, f, indent=2)

    # Write markdown
    md_content = _generate_execution_markdown(result)
    md_file = execution_dir / "DRY-RUN-EXECUTION-RESULT.md"
    with open(md_file, "w") as f:
        f.write(md_content)

    return result


def _generate_execution_markdown(result: Dict[str, Any]) -> str:
    """Generate markdown execution result."""
    lines = [
        "# Dry-Run Execution Result",
        "",
        f"**Status:** {result.get('status')}",
        f"**Executed at:** {result.get('executed_at')}",
        f"**Executed by:** {result.get('executed_by')}",
        "",
        "## Summary",
        "",
        f"- Total items: {result.get('item_count')}",
        f"- Success: {result.get('success_count')}",
        f"- Failed: {result.get('failed_count')}",
        "",
        "## Items",
        ""
    ]

    for item in result.get("items", []):
        lines.append(f"- {item.get('item_id')}: {item.get('status')} (HTTP {item.get('simulated_response_status')})")

    lines.append("")
    lines.append("## Safety")
    lines.append("")
    lines.append("✗ Simulation only (no real NetBox writes)")
    lines.append("✗ No actual objects created")
    lines.append("✗ Dry-run mode")
    lines.append("")

    return "\n".join(lines)


def load_dryrun_execution_result(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Load dry-run execution result."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    result_file = jobs_base / job_id / "applyplan" / "dry-run" / "dry-run-execution-result.json"
    if not result_file.exists():
        return {}

    with open(result_file, "r") as f:
        return json.load(f)


def validate_dryrun_execution_result(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """DRYRUN-003: Validate dry-run execution result."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    result = load_dryrun_execution_result(job_id, jobs_base)
    if not result:
        raise ValueError(f"Dry-run execution result not found for job {job_id}")

    # Check execution status
    if result.get("status") == "DRY_RUN_EXECUTION_FAILED":
        decision = "DRY_RUN_VALIDATION_FAILED"
    elif result.get("failed_count", 0) > 0:
        decision = "DRY_RUN_VALIDATION_FAILED"
    elif result.get("success_count", 0) == result.get("item_count", 0):
        decision = "DRY_RUN_VALIDATION_PASSED"
    else:
        decision = "DRY_RUN_VALIDATION_PARTIAL_FAILED"

    # Create directory
    validation_dir = jobs_base / job_id / "applyplan" / "dry-run"
    validation_dir.mkdir(parents=True, exist_ok=True)

    # Build result
    validation_result = {
        "job_id": job_id,
        "status": "validation_completed",
        "decision": decision,
        "validated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "execution_status": result.get("status"),
        "item_count": result.get("item_count"),
        "success_count": result.get("success_count"),
        "failed_count": result.get("failed_count"),
        "safety": {
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "dry_run_only": True,
            "real_write_blocked": True
        }
    }

    # Write validation
    validation_file = validation_dir / "dry-run-execution-validation.json"
    with open(validation_file, "w") as f:
        json.dump(validation_result, f, indent=2)

    # Write markdown
    md_content = _generate_validation_markdown(validation_result)
    md_file = validation_dir / "DRY-RUN-EXECUTION-VALIDATION.md"
    with open(md_file, "w") as f:
        f.write(md_content)

    return validation_result


def _generate_validation_markdown(result: Dict[str, Any]) -> str:
    """Generate markdown validation result."""
    lines = [
        "# Dry-Run Execution Validation",
        "",
        f"**Status:** {result.get('decision')}",
        f"**Validated at:** {result.get('validated_at')}",
        "",
        "## Summary",
        "",
        f"- Execution status: {result.get('execution_status')}",
        f"- Items: {result.get('item_count')}",
        f"- Success: {result.get('success_count')}",
        f"- Failed: {result.get('failed_count')}",
        "",
        "## Next Step",
        ""
    ]

    decision = result.get("decision")
    if decision == "DRY_RUN_VALIDATION_PASSED":
        lines.append("✓ Dry-run passed. Ready for real-write readiness gate.")
    elif decision == "DRY_RUN_VALIDATION_FAILED":
        lines.append("✗ Dry-run failed. Cannot proceed to real write.")
    else:
        lines.append("⚠ Dry-run partial failure. Review and retry.")

    lines.append("")
    return "\n".join(lines)
