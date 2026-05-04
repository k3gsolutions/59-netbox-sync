"""
Tests for FASES COMPLIANCE-DRYRUN-001–003
Dry-Run Execution Gate + Simulation + Validation
"""

import json
import pytest
from pathlib import Path
from datetime import datetime, timezone


@pytest.fixture
def tmp_compliance_jobs(tmp_path):
    jobs_dir = tmp_path / "reports" / "compliance" / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    return jobs_dir


def _create_dryrun_applyplan(jobs_dir, job_id):
    """Helper to create dry-run ApplyPlan."""
    dryrun_dir = jobs_dir / job_id / "applyplan" / "dry-run"
    dryrun_dir.mkdir(parents=True, exist_ok=True)

    dryrun_data = {
        "job_id": job_id,
        "status": "DRY_RUN_APPLYPLAN_BUILT",
        "mode": "dry_run",
        "execution_allowed": False,
        "can_execute_real_write": False,
        "requires_next_gate": True,
        "created_by": "TestOp",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "items": [
            {
                "item_id": "APC-001",
                "approval_record_id": "PAR-001",
                "device_id": 1890,
                "object_type": "interface",
                "object_name": "Eth-Trunk0/1",
                "method": "POST",
                "endpoint": "/api/dcim/interfaces/",
                "payload": {"name": "Eth-Trunk0/1"},
                "write_allowed": False,
                "execution_allowed": False,
                "requires_dry_run": True
            }
        ]
    }

    dryrun_file = dryrun_dir / "dry-run-applyplan.json"
    with open(dryrun_file, "w") as f:
        json.dump(dryrun_data, f)

    # Create validation
    validation_data = {
        "job_id": job_id,
        "decision": "DRY_RUN_APPLYPLAN_VALID",
        "validated_at": datetime.now(timezone.utc).isoformat()
    }
    validation_file = dryrun_dir / "dry-run-applyplan-validation.json"
    with open(validation_file, "w") as f:
        json.dump(validation_data, f)

    return dryrun_file


def test_dryrun_gate_requires_validation(tmp_compliance_jobs):
    """Block if validation missing."""
    from webui.services.compliance_dryrun_execution import evaluate_dryrun_execution_gate

    job_id = "job-001"
    with pytest.raises(ValueError, match="validation not found"):
        evaluate_dryrun_execution_gate(job_id, "Test", tmp_compliance_jobs)


def test_dryrun_gate_blocks_invalid_validation(tmp_compliance_jobs):
    """Block if validation INVALID."""
    from webui.services.compliance_dryrun_execution import evaluate_dryrun_execution_gate

    job_id = "job-002"
    dryrun_dir = tmp_compliance_jobs / job_id / "applyplan" / "dry-run"
    dryrun_dir.mkdir(parents=True, exist_ok=True)

    validation_data = {
        "job_id": job_id,
        "decision": "DRY_RUN_APPLYPLAN_INVALID"
    }
    validation_file = dryrun_dir / "dry-run-applyplan-validation.json"
    with open(validation_file, "w") as f:
        json.dump(validation_data, f)

    with pytest.raises(ValueError, match="INVALID"):
        evaluate_dryrun_execution_gate(job_id, "Test", tmp_compliance_jobs)


def test_dryrun_gate_ready(tmp_compliance_jobs):
    """Gate ready when validation VALID."""
    from webui.services.compliance_dryrun_execution import evaluate_dryrun_execution_gate

    job_id = "job-003"
    _create_dryrun_applyplan(tmp_compliance_jobs, job_id)

    result = evaluate_dryrun_execution_gate(job_id, "TestOp", tmp_compliance_jobs)

    assert result["decision"] == "DRY_RUN_EXECUTION_GATE_READY"


def test_execute_dryrun_requires_applyplan(tmp_compliance_jobs):
    """Block if no ApplyPlan."""
    from webui.services.compliance_dryrun_execution import execute_dryrun_simulation

    job_id = "job-004"
    with pytest.raises(ValueError, match="Dry-run ApplyPlan not found"):
        execute_dryrun_simulation(job_id, "Test", tmp_compliance_jobs)


def test_execute_dryrun_succeeds(tmp_compliance_jobs):
    """Execute dry-run simulation."""
    from webui.services.compliance_dryrun_execution import execute_dryrun_simulation

    job_id = "job-005"
    _create_dryrun_applyplan(tmp_compliance_jobs, job_id)

    result = execute_dryrun_simulation(job_id, "TestOp", tmp_compliance_jobs)

    assert result["status"] == "DRY_RUN_EXECUTION_PASSED"
    assert result["success_count"] >= 1
    assert result["execution_allowed"] is False or "execution_allowed" not in result


def test_dryrun_no_netbox_writes(tmp_compliance_jobs):
    """Dry-run has no NetBox writes."""
    from webui.services.compliance_dryrun_execution import execute_dryrun_simulation

    job_id = "job-006"
    _create_dryrun_applyplan(tmp_compliance_jobs, job_id)

    result = execute_dryrun_simulation(job_id, "TestOp", tmp_compliance_jobs)

    assert result["safety"]["netbox_write"] is False
    assert result["safety"]["device_write"] is False


def test_validate_dryrun_execution_passed(tmp_compliance_jobs):
    """Validate dry-run execution passed."""
    from webui.services.compliance_dryrun_execution import execute_dryrun_simulation, validate_dryrun_execution_result

    job_id = "job-007"
    _create_dryrun_applyplan(tmp_compliance_jobs, job_id)

    execute_dryrun_simulation(job_id, "TestOp", tmp_compliance_jobs)
    result = validate_dryrun_execution_result(job_id, tmp_compliance_jobs)

    assert result["decision"] == "DRY_RUN_VALIDATION_PASSED"


def test_dryrun_execution_written_to_file(tmp_compliance_jobs):
    """Dry-run execution written to file."""
    from webui.services.compliance_dryrun_execution import execute_dryrun_simulation

    job_id = "job-008"
    _create_dryrun_applyplan(tmp_compliance_jobs, job_id)

    execute_dryrun_simulation(job_id, "TestOp", tmp_compliance_jobs)

    result_file = tmp_compliance_jobs / job_id / "applyplan" / "dry-run" / "dry-run-execution-result.json"
    assert result_file.exists()

    md_file = tmp_compliance_jobs / job_id / "applyplan" / "dry-run" / "DRY-RUN-EXECUTION-RESULT.md"
    assert md_file.exists()
