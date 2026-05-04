"""
Tests for FASES COMPLIANCE-REALWRITE-008–009
Post-Write Verification + Compliance Re-Run
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


def _create_execution_result(jobs_dir, job_id, status="REAL_WRITE_SUCCESS", item_count=1):
    """Helper to create execution result."""
    execution_dir = jobs_dir / job_id / "real-write" / "execution"
    execution_dir.mkdir(parents=True, exist_ok=True)

    items = []
    for i in range(item_count):
        items.append({
            "item_id": f"APC-{i:03d}",
            "method": "POST",
            "status": "success",
            "response_status": 200,
            "response_id": 1000 + i,
            "executed_at": datetime.now(timezone.utc).isoformat()
        })

    execution_data = {
        "execution_id": "EXEC-001",
        "job_id": job_id,
        "status": status,
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "executed_by": "TestOp",
        "items": items,
        "item_count": item_count,
        "success_count": item_count if status == "REAL_WRITE_SUCCESS" else 0,
        "failed_count": 0 if status == "REAL_WRITE_SUCCESS" else item_count,
        "safety": {
            "token_stored": False,
            "token_in_logs": False,
            "one_shot": True
        }
    }

    result_file = execution_dir / "real-write-execution-result.json"
    with open(result_file, "w") as f:
        json.dump(execution_data, f)

    return result_file


def _create_applyplan(jobs_dir, job_id):
    """Helper to create dry-run ApplyPlan."""
    dryrun_dir = jobs_dir / job_id / "applyplan" / "dry-run"
    dryrun_dir.mkdir(parents=True, exist_ok=True)

    dryrun_data = {
        "job_id": job_id,
        "status": "DRY_RUN_APPLYPLAN_BUILT",
        "items": [
            {
                "item_id": "APC-000",
                "method": "POST",
                "endpoint": "/api/dcim/interfaces/",
                "payload": {"name": "Eth-Trunk0/1"}
            }
        ]
    }

    dryrun_file = dryrun_dir / "dry-run-applyplan.json"
    with open(dryrun_file, "w") as f:
        json.dump(dryrun_data, f)

    return dryrun_file


def test_post_verification_requires_execution_result(tmp_compliance_jobs):
    """Block if execution result missing."""
    from webui.services.compliance_realwrite_postwrite import evaluate_postwrite_verification

    job_id = "job-001"
    with pytest.raises(ValueError, match="execution result not found"):
        evaluate_postwrite_verification(job_id, "TestOp", tmp_compliance_jobs)


def test_post_verification_not_applicable_write_failed(tmp_compliance_jobs):
    """Not applicable if execution failed."""
    from webui.services.compliance_realwrite_postwrite import evaluate_postwrite_verification

    job_id = "job-002"
    _create_execution_result(tmp_compliance_jobs, job_id, status="REAL_WRITE_FAILED", item_count=0)

    result = evaluate_postwrite_verification(job_id, "TestOp", tmp_compliance_jobs)

    assert "NOT_APPLICABLE" in result["decision"]
    assert result["safety"]["netbox_write"] is False
    assert result["safety"]["device_connection"] is False


def test_post_verification_not_applicable_no_items(tmp_compliance_jobs):
    """Not applicable if no items created."""
    from webui.services.compliance_realwrite_postwrite import evaluate_postwrite_verification

    job_id = "job-003"
    _create_execution_result(tmp_compliance_jobs, job_id, status="REAL_WRITE_SUCCESS", item_count=0)
    _create_applyplan(tmp_compliance_jobs, job_id)

    result = evaluate_postwrite_verification(job_id, "TestOp", tmp_compliance_jobs)

    assert result["decision"] == "VERIFICATION_NOT_APPLICABLE_NO_OBJECT_CREATED"
    assert result["item_count"] == 0


def test_post_verification_succeeds(tmp_compliance_jobs):
    """Verification passes with created objects."""
    from webui.services.compliance_realwrite_postwrite import evaluate_postwrite_verification

    job_id = "job-004"
    _create_execution_result(tmp_compliance_jobs, job_id, item_count=2)
    _create_applyplan(tmp_compliance_jobs, job_id)

    result = evaluate_postwrite_verification(job_id, "TestOp", tmp_compliance_jobs)

    assert result["decision"] == "POSTWRITE_VERIFICATION_PASSED"
    assert result["item_count"] == 2
    assert result["verified_count"] == 2


def test_post_verification_written_to_file(tmp_compliance_jobs):
    """Verification written to file."""
    from webui.services.compliance_realwrite_postwrite import evaluate_postwrite_verification

    job_id = "job-005"
    _create_execution_result(tmp_compliance_jobs, job_id, item_count=1)
    _create_applyplan(tmp_compliance_jobs, job_id)

    evaluate_postwrite_verification(job_id, "TestOp", tmp_compliance_jobs)

    verification_file = tmp_compliance_jobs / job_id / "real-write" / "verification" / "post-write-verification.json"
    assert verification_file.exists()

    md_file = tmp_compliance_jobs / job_id / "real-write" / "verification" / "POST-WRITE-VERIFICATION.md"
    assert md_file.exists()


def test_post_verification_no_netbox_write(tmp_compliance_jobs):
    """Verification has no NetBox writes."""
    from webui.services.compliance_realwrite_postwrite import evaluate_postwrite_verification

    job_id = "job-006"
    _create_execution_result(tmp_compliance_jobs, job_id, item_count=1)

    result = evaluate_postwrite_verification(job_id, "TestOp", tmp_compliance_jobs)

    assert result["safety"]["netbox_write"] is False
    assert result["safety"]["device_connection"] is False


def test_compliance_rerun_requires_execution_result(tmp_compliance_jobs):
    """Block if execution result missing."""
    from webui.services.compliance_realwrite_postwrite import evaluate_postwrite_compliance_rerun

    job_id = "job-007"
    result = evaluate_postwrite_compliance_rerun(job_id, "TestOp", tmp_compliance_jobs)

    assert "NOT_APPLICABLE" in result["decision"]


def test_compliance_rerun_not_applicable_write_failed(tmp_compliance_jobs):
    """Not applicable if execution failed."""
    from webui.services.compliance_realwrite_postwrite import evaluate_postwrite_compliance_rerun

    job_id = "job-008"
    _create_execution_result(tmp_compliance_jobs, job_id, status="REAL_WRITE_FAILED", item_count=0)

    result = evaluate_postwrite_compliance_rerun(job_id, "TestOp", tmp_compliance_jobs)

    assert "NOT_APPLICABLE" in result["decision"]
    assert result["safety"]["ssh_connection"] is False
    assert result["safety"]["netbox_write"] is False


def test_compliance_rerun_not_applicable_no_items(tmp_compliance_jobs):
    """Not applicable if no items created."""
    from webui.services.compliance_realwrite_postwrite import evaluate_postwrite_compliance_rerun

    job_id = "job-009"
    _create_execution_result(tmp_compliance_jobs, job_id, status="REAL_WRITE_SUCCESS", item_count=0)

    result = evaluate_postwrite_compliance_rerun(job_id, "TestOp", tmp_compliance_jobs)

    assert result["decision"] == "COMPLIANCE_RERUN_NOT_APPLICABLE_NO_OBJECT_CREATED"


def test_compliance_rerun_succeeds(tmp_compliance_jobs):
    """Compliance re-run passes with created objects."""
    from webui.services.compliance_realwrite_postwrite import evaluate_postwrite_compliance_rerun

    job_id = "job-010"
    _create_execution_result(tmp_compliance_jobs, job_id, item_count=2)

    result = evaluate_postwrite_compliance_rerun(job_id, "TestOp", tmp_compliance_jobs)

    assert result["decision"] == "COMPLIANCE_RERUN_PASSED"
    assert result["check_count"] == 2
    assert result["passed"] == 2


def test_compliance_rerun_written_to_file(tmp_compliance_jobs):
    """Compliance re-run written to file."""
    from webui.services.compliance_realwrite_postwrite import evaluate_postwrite_compliance_rerun

    job_id = "job-011"
    _create_execution_result(tmp_compliance_jobs, job_id, item_count=1)

    evaluate_postwrite_compliance_rerun(job_id, "TestOp", tmp_compliance_jobs)

    rerun_file = tmp_compliance_jobs / job_id / "real-write" / "compliance-rerun" / "post-write-compliance-rerun.json"
    assert rerun_file.exists()

    md_file = tmp_compliance_jobs / job_id / "real-write" / "compliance-rerun" / "POST-WRITE-COMPLIANCE-RERUN.md"
    assert md_file.exists()


def test_compliance_rerun_no_ssh(tmp_compliance_jobs):
    """Compliance re-run has no SSH connections."""
    from webui.services.compliance_realwrite_postwrite import evaluate_postwrite_compliance_rerun

    job_id = "job-012"
    _create_execution_result(tmp_compliance_jobs, job_id, item_count=1)

    result = evaluate_postwrite_compliance_rerun(job_id, "TestOp", tmp_compliance_jobs)

    assert result["safety"]["ssh_connection"] is False
    assert result["safety"]["netbox_write"] is False
