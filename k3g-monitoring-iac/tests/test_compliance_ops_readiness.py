"""
Tests for FASES COMPLIANCE-OPS-001
End-to-End Job Readiness Check
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


def _create_valid_execution_package(jobs_dir, job_id):
    """Helper to create valid execution package."""
    exec_dir = jobs_dir / job_id / "real-write" / "execution"
    exec_dir.mkdir(parents=True, exist_ok=True)

    exec_pkg = {
        "execution_package_id": "EXEC-001",
        "job_id": job_id,
        "status": "prepared",
        "mode": "real_write_prepared",
        "execution_allowed": False,
        "token_required_in_next_phase": True,
        "explicit_confirm_required": True,
        "one_shot_execution": True,
        "required_execution_phrase": "EXECUTAR_ESCRITA_REAL_TEST",
        "items": [
            {
                "item_id": "APC-001",
                "method": "POST",
                "endpoint": "/api/dcim/interfaces/",
                "payload": {"name": "test-interface"},
                "write_allowed": False,
                "execution_allowed": False
            }
        ],
        "item_count": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": "TestOp",
        "safety": {
            "execution_allowed": False,
            "token_in_memory_only": True,
            "no_retry": True,
            "no_rollback_automatic": True
        }
    }

    exec_file = exec_dir / "execution-package.json"
    with open(exec_file, "w") as f:
        json.dump(exec_pkg, f)

    # Create validation
    validation = {
        "job_id": job_id,
        "status": "validation_completed",
        "decision": "EXECUTION_PACKAGE_VALID",
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "issues": []
    }
    validation_file = exec_dir / "execution-package-validation.json"
    with open(validation_file, "w") as f:
        json.dump(validation, f)

    # Create freeze
    freeze = {
        "job_id": job_id,
        "status": "freeze_evaluated",
        "decision": "READY_FOR_REAL_WRITE_PHASE",
        "evaluated_at": datetime.now(timezone.utc).isoformat()
    }
    freeze_file = exec_dir / "final-no-write-freeze.json"
    with open(freeze_file, "w") as f:
        json.dump(freeze, f)

    return exec_pkg


def test_readiness_check_requires_job(tmp_compliance_jobs):
    """Block if job not found."""
    from webui.services.compliance_ops_readiness import validate_compliance_job_realwrite_readiness

    with pytest.raises(ValueError, match="not found"):
        validate_compliance_job_realwrite_readiness("nonexistent-job", tmp_compliance_jobs)


def test_readiness_blocks_missing_freeze(tmp_compliance_jobs):
    """Block if freeze missing."""
    from webui.services.compliance_ops_readiness import validate_compliance_job_realwrite_readiness

    job_id = "job-001"
    _create_valid_execution_package(tmp_compliance_jobs, job_id)

    # Remove freeze
    freeze_file = tmp_compliance_jobs / job_id / "real-write" / "execution" / "final-no-write-freeze.json"
    freeze_file.unlink()

    result = validate_compliance_job_realwrite_readiness(job_id, tmp_compliance_jobs)

    assert "NOT_READY" in result["decision"]
    assert any("freeze" in b.lower() for b in result["blockers"])


def test_readiness_blocks_execution_allowed_true(tmp_compliance_jobs):
    """Block if execution_allowed is not False."""
    from webui.services.compliance_ops_readiness import validate_compliance_job_realwrite_readiness

    job_id = "job-002"
    _create_valid_execution_package(tmp_compliance_jobs, job_id)

    # Corrupt execution package
    exec_file = tmp_compliance_jobs / job_id / "real-write" / "execution" / "execution-package.json"
    with open(exec_file, "r") as f:
        exec_pkg = json.load(f)
    exec_pkg["execution_allowed"] = True
    with open(exec_file, "w") as f:
        json.dump(exec_pkg, f)

    result = validate_compliance_job_realwrite_readiness(job_id, tmp_compliance_jobs)

    assert "NOT_READY" in result["decision"]
    assert any("execution_allowed" in b.lower() for b in result["blockers"])


def test_readiness_blocks_endpoint_null(tmp_compliance_jobs):
    """Block if endpoint is null."""
    from webui.services.compliance_ops_readiness import validate_compliance_job_realwrite_readiness

    job_id = "job-003"
    _create_valid_execution_package(tmp_compliance_jobs, job_id)

    # Corrupt endpoint
    exec_file = tmp_compliance_jobs / job_id / "real-write" / "execution" / "execution-package.json"
    with open(exec_file, "r") as f:
        exec_pkg = json.load(f)
    exec_pkg["items"][0]["endpoint"] = None
    with open(exec_file, "w") as f:
        json.dump(exec_pkg, f)

    result = validate_compliance_job_realwrite_readiness(job_id, tmp_compliance_jobs)

    assert "NOT_READY" in result["decision"]
    assert any("endpoint" in b.lower() for b in result["blockers"])


def test_readiness_blocks_endpoint_root(tmp_compliance_jobs):
    """Block if endpoint is root."""
    from webui.services.compliance_ops_readiness import validate_compliance_job_realwrite_readiness

    job_id = "job-004"
    _create_valid_execution_package(tmp_compliance_jobs, job_id)

    # Corrupt endpoint
    exec_file = tmp_compliance_jobs / job_id / "real-write" / "execution" / "execution-package.json"
    with open(exec_file, "r") as f:
        exec_pkg = json.load(f)
    exec_pkg["items"][0]["endpoint"] = "/"
    with open(exec_file, "w") as f:
        json.dump(exec_pkg, f)

    result = validate_compliance_job_realwrite_readiness(job_id, tmp_compliance_jobs)

    assert "NOT_READY" in result["decision"]
    assert any("root" in b.lower() for b in result["blockers"])


def test_readiness_blocks_payload_with_token(tmp_compliance_jobs):
    """Block if payload contains token keyword."""
    from webui.services.compliance_ops_readiness import validate_compliance_job_realwrite_readiness

    job_id = "job-005"
    _create_valid_execution_package(tmp_compliance_jobs, job_id)

    # Corrupt payload
    exec_file = tmp_compliance_jobs / job_id / "real-write" / "execution" / "execution-package.json"
    with open(exec_file, "r") as f:
        exec_pkg = json.load(f)
    exec_pkg["items"][0]["payload"]["token"] = "secret123"
    with open(exec_file, "w") as f:
        json.dump(exec_pkg, f)

    result = validate_compliance_job_realwrite_readiness(job_id, tmp_compliance_jobs)

    assert "NOT_READY" in result["decision"]
    assert any("secret" in b.lower() or "payload" in b.lower() for b in result["blockers"])


def test_readiness_blocks_sync_endpoint(tmp_compliance_jobs):
    """Block if endpoint contains /sync."""
    from webui.services.compliance_ops_readiness import validate_compliance_job_realwrite_readiness

    job_id = "job-006"
    _create_valid_execution_package(tmp_compliance_jobs, job_id)

    # Corrupt endpoint
    exec_file = tmp_compliance_jobs / job_id / "real-write" / "execution" / "execution-package.json"
    with open(exec_file, "r") as f:
        exec_pkg = json.load(f)
    exec_pkg["items"][0]["endpoint"] = "/api/dcim/devices/1/sync"
    with open(exec_file, "w") as f:
        json.dump(exec_pkg, f)

    result = validate_compliance_job_realwrite_readiness(job_id, tmp_compliance_jobs)

    assert "NOT_READY" in result["decision"]
    assert any("/sync" in b.lower() for b in result["blockers"])


def test_readiness_accepts_ready(tmp_compliance_jobs):
    """Accept job when all checks pass."""
    from webui.services.compliance_ops_readiness import validate_compliance_job_realwrite_readiness

    job_id = "job-007"
    _create_valid_execution_package(tmp_compliance_jobs, job_id)

    result = validate_compliance_job_realwrite_readiness(job_id, tmp_compliance_jobs)

    assert result["decision"] == "COMPLIANCE_JOB_READY_FOR_MANUAL_REAL_WRITE"
    assert result["blocker_count"] == 0


def test_readiness_written_to_file(tmp_compliance_jobs):
    """Readiness result written to file."""
    from webui.services.compliance_ops_readiness import validate_compliance_job_realwrite_readiness

    job_id = "job-008"
    _create_valid_execution_package(tmp_compliance_jobs, job_id)

    validate_compliance_job_realwrite_readiness(job_id, tmp_compliance_jobs)

    readiness_file = tmp_compliance_jobs / job_id / "ops" / "readiness-check.json"
    assert readiness_file.exists()

    md_file = tmp_compliance_jobs / job_id / "ops" / "READINESS-CHECK.md"
    assert md_file.exists()


def test_readiness_no_netbox_access(tmp_compliance_jobs):
    """Readiness has no NetBox access."""
    from webui.services.compliance_ops_readiness import validate_compliance_job_realwrite_readiness

    job_id = "job-009"
    _create_valid_execution_package(tmp_compliance_jobs, job_id)

    result = validate_compliance_job_realwrite_readiness(job_id, tmp_compliance_jobs)

    assert result["safety"]["netbox_write"] is False
    assert result["safety"]["netbox_read"] is False
    assert result["safety"]["device_connection"] is False
