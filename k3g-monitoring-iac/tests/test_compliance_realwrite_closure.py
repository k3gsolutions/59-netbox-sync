"""
Tests for FASES COMPLIANCE-REALWRITE-010
Closure Package
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
    }

    result_file = execution_dir / "real-write-execution-result.json"
    with open(result_file, "w") as f:
        json.dump(execution_data, f)

    return result_file


def _create_verification(jobs_dir, job_id, decision="POSTWRITE_VERIFICATION_PASSED"):
    """Helper to create verification result."""
    verification_dir = jobs_dir / job_id / "real-write" / "verification"
    verification_dir.mkdir(parents=True, exist_ok=True)

    verification_data = {
        "job_id": job_id,
        "status": "verification_completed",
        "decision": decision,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "verified_by": "TestOp",
        "items": [
            {
                "item_id": "APC-000",
                "status": "object_verified" if decision == "POSTWRITE_VERIFICATION_PASSED" else "verification_failed",
                "response_id": 1000 if decision == "POSTWRITE_VERIFICATION_PASSED" else None,
                "verified_at": datetime.now(timezone.utc).isoformat()
            }
        ],
        "item_count": 1,
        "verified_count": 1 if decision == "POSTWRITE_VERIFICATION_PASSED" else 0,
        "failed_count": 0 if decision == "POSTWRITE_VERIFICATION_PASSED" else 1
    }

    verification_file = verification_dir / "post-write-verification.json"
    with open(verification_file, "w") as f:
        json.dump(verification_data, f)

    return verification_file


def _create_compliance_rerun(jobs_dir, job_id, decision="COMPLIANCE_RERUN_PASSED"):
    """Helper to create compliance re-run result."""
    rerun_dir = jobs_dir / job_id / "real-write" / "compliance-rerun"
    rerun_dir.mkdir(parents=True, exist_ok=True)

    rerun_data = {
        "job_id": job_id,
        "status": "compliance_rerun_completed",
        "decision": decision,
        "rerun_at": datetime.now(timezone.utc).isoformat(),
        "rerun_by": "TestOp",
        "checks": [
            {
                "item_id": "APC-000",
                "local_policy_status": "compliant_with_policy" if decision == "COMPLIANCE_RERUN_PASSED" else "non_compliant",
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
        ],
        "check_count": 1,
        "passed": 1 if decision == "COMPLIANCE_RERUN_PASSED" else 0,
        "failed": 0 if decision == "COMPLIANCE_RERUN_PASSED" else 1
    }

    rerun_file = rerun_dir / "post-write-compliance-rerun.json"
    with open(rerun_file, "w") as f:
        json.dump(rerun_data, f)

    return rerun_file


def test_closure_no_execution_result(tmp_compliance_jobs):
    """Closure blocked if no execution result."""
    from webui.services.compliance_realwrite_closure import build_realwrite_closure_package

    job_id = "job-001"
    result = build_realwrite_closure_package(job_id, "TestOp", tmp_compliance_jobs)

    assert result["decision"] == "COMPLIANCE_JOB_CLOSED_ACTION_REQUIRED"
    assert "execution not found" in result["reason"].lower()


def test_closure_execution_failed(tmp_compliance_jobs):
    """Closure action required if execution failed."""
    from webui.services.compliance_realwrite_closure import build_realwrite_closure_package

    job_id = "job-002"
    _create_execution_result(tmp_compliance_jobs, job_id, status="REAL_WRITE_FAILED", item_count=0)

    result = build_realwrite_closure_package(job_id, "TestOp", tmp_compliance_jobs)

    assert result["decision"] == "COMPLIANCE_JOB_CLOSED_ACTION_REQUIRED"
    assert "failed" in result["reason"].lower()


def test_closure_no_items_executed(tmp_compliance_jobs):
    """Closure not applicable if no items executed."""
    from webui.services.compliance_realwrite_closure import build_realwrite_closure_package

    job_id = "job-003"
    _create_execution_result(tmp_compliance_jobs, job_id, status="REAL_WRITE_SUCCESS", item_count=0)

    result = build_realwrite_closure_package(job_id, "TestOp", tmp_compliance_jobs)

    assert result["decision"] == "COMPLIANCE_JOB_CLOSED_NOT_APPLICABLE"


def test_closure_success_all_gates_passed(tmp_compliance_jobs):
    """Closure success when execution + verification + compliance all pass."""
    from webui.services.compliance_realwrite_closure import build_realwrite_closure_package

    job_id = "job-004"
    _create_execution_result(tmp_compliance_jobs, job_id, item_count=1)
    _create_verification(tmp_compliance_jobs, job_id, decision="POSTWRITE_VERIFICATION_PASSED")
    _create_compliance_rerun(tmp_compliance_jobs, job_id, decision="COMPLIANCE_RERUN_PASSED")

    result = build_realwrite_closure_package(job_id, "TestOp", tmp_compliance_jobs)

    assert result["decision"] == "COMPLIANCE_JOB_CLOSED_SUCCESS"
    assert "all passed" in result["reason"].lower()


def test_closure_with_warnings_verification_failed(tmp_compliance_jobs):
    """Closure with warnings if verification failed."""
    from webui.services.compliance_realwrite_closure import build_realwrite_closure_package

    job_id = "job-005"
    _create_execution_result(tmp_compliance_jobs, job_id, item_count=1)
    _create_verification(tmp_compliance_jobs, job_id, decision="POSTWRITE_VERIFICATION_FAILED")

    result = build_realwrite_closure_package(job_id, "TestOp", tmp_compliance_jobs)

    assert result["decision"] == "COMPLIANCE_JOB_CLOSED_WITH_WARNINGS"
    assert "verification" in result["reason"].lower()


def test_closure_with_warnings_compliance_rerun_failed(tmp_compliance_jobs):
    """Closure with warnings if compliance re-run failed."""
    from webui.services.compliance_realwrite_closure import build_realwrite_closure_package

    job_id = "job-006"
    _create_execution_result(tmp_compliance_jobs, job_id, item_count=1)
    _create_verification(tmp_compliance_jobs, job_id, decision="POSTWRITE_VERIFICATION_PASSED")
    _create_compliance_rerun(tmp_compliance_jobs, job_id, decision="COMPLIANCE_RERUN_PARTIAL_FAILED")

    result = build_realwrite_closure_package(job_id, "TestOp", tmp_compliance_jobs)

    assert result["decision"] == "COMPLIANCE_JOB_CLOSED_WITH_WARNINGS"
    assert "compliance" in result["reason"].lower()


def test_closure_written_to_file(tmp_compliance_jobs):
    """Closure package written to file."""
    from webui.services.compliance_realwrite_closure import build_realwrite_closure_package

    job_id = "job-007"
    _create_execution_result(tmp_compliance_jobs, job_id, item_count=1)

    build_realwrite_closure_package(job_id, "TestOp", tmp_compliance_jobs)

    closure_file = tmp_compliance_jobs / job_id / "real-write" / "closure" / "closure-package.json"
    assert closure_file.exists()

    md_file = tmp_compliance_jobs / job_id / "real-write" / "closure" / "CLOSURE-PACKAGE.md"
    assert md_file.exists()


def test_closure_no_writes(tmp_compliance_jobs):
    """Closure has no NetBox writes."""
    from webui.services.compliance_realwrite_closure import build_realwrite_closure_package

    job_id = "job-008"
    _create_execution_result(tmp_compliance_jobs, job_id, item_count=1)

    result = build_realwrite_closure_package(job_id, "TestOp", tmp_compliance_jobs)

    assert result["safety"]["netbox_write"] is False
    assert result["safety"]["device_connection"] is False
    assert result["safety"]["ssh_connection"] is False


def test_closure_evidence_consolidated(tmp_compliance_jobs):
    """Closure consolidates evidence from all phases."""
    from webui.services.compliance_realwrite_closure import build_realwrite_closure_package

    job_id = "job-009"
    _create_execution_result(tmp_compliance_jobs, job_id, item_count=2)
    _create_verification(tmp_compliance_jobs, job_id, decision="POSTWRITE_VERIFICATION_PASSED")
    _create_compliance_rerun(tmp_compliance_jobs, job_id, decision="COMPLIANCE_RERUN_PASSED")

    result = build_realwrite_closure_package(job_id, "TestOp", tmp_compliance_jobs)

    evidence = result["evidence"]
    assert evidence["execution_status"] == "REAL_WRITE_SUCCESS"
    assert evidence["execution_items"] == 2
    assert evidence["verification_status"] == "POSTWRITE_VERIFICATION_PASSED"
    assert evidence["compliance_status"] == "COMPLIANCE_RERUN_PASSED"
