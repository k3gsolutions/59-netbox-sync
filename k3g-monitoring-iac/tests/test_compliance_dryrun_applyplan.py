"""
Tests for FASES COMPLIANCE-APPLYPLAN-003–004
Dry-Run ApplyPlan Builder + Validation
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


def _create_applyplan_candidate(jobs_dir, job_id):
    """Helper to create ApplyPlan candidate."""
    candidate_dir = jobs_dir / job_id / "applyplan" / "candidate"
    candidate_dir.mkdir(parents=True, exist_ok=True)

    candidate_data = {
        "job_id": job_id,
        "status": "APPLYPLAN_CANDIDATE_BUILT",
        "mode": "candidate",
        "created_by": "TestOp",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "items": [
            {
                "item_id": "APC-001",
                "approval_record_id": "PAR-001",
                "device_id": 1890,
                "object_type": "interface",
                "object_name": "Eth-Trunk0/1",
                "target": "netbox",
                "method": "POST",
                "endpoint": "/api/dcim/interfaces/",
                "payload": {"name": "Eth-Trunk0/1"},
                "write_allowed": False,
                "execution_allowed": False,
                "requires_dry_run": True,
                "requires_real_write_gate": True
            }
        ]
    }

    candidate_file = candidate_dir / "applyplan-candidate.json"
    with open(candidate_file, "w") as f:
        json.dump(candidate_data, f)
    return candidate_file


def test_dryrun_requires_candidate(tmp_compliance_jobs):
    """Block if no candidate."""
    from webui.services.compliance_dryrun_applyplan import build_dryrun_applyplan

    job_id = "job-001"
    with pytest.raises(ValueError, match="No ApplyPlan candidate found"):
        build_dryrun_applyplan(job_id, "Test", tmp_compliance_jobs)


def test_build_dryrun_succeeds(tmp_compliance_jobs):
    """Build dry-run ApplyPlan."""
    from webui.services.compliance_dryrun_applyplan import build_dryrun_applyplan

    job_id = "job-002"
    _create_applyplan_candidate(tmp_compliance_jobs, job_id)

    result = build_dryrun_applyplan(job_id, "TestOp", tmp_compliance_jobs)

    assert result["status"] == "DRY_RUN_APPLYPLAN_BUILT"
    assert result["mode"] == "dry_run"
    assert result["execution_allowed"] is False
    assert result["can_execute_real_write"] is False


def test_dryrun_requires_next_gate(tmp_compliance_jobs):
    """Dry-run must require next gate."""
    from webui.services.compliance_dryrun_applyplan import build_dryrun_applyplan

    job_id = "job-003"
    _create_applyplan_candidate(tmp_compliance_jobs, job_id)

    result = build_dryrun_applyplan(job_id, "TestOp", tmp_compliance_jobs)

    assert result["requires_next_gate"] is True


def test_validation_blocks_secret_in_payload(tmp_compliance_jobs):
    """Validation blocks secret."""
    from webui.services.compliance_dryrun_applyplan import build_dryrun_applyplan, validate_dryrun_applyplan

    job_id = "job-004"
    _create_applyplan_candidate(tmp_compliance_jobs, job_id)

    build_dryrun_applyplan(job_id, "TestOp", tmp_compliance_jobs)

    # Manually edit to add secret
    dryrun_file = tmp_compliance_jobs / job_id / "applyplan" / "dry-run" / "dry-run-applyplan.json"
    with open(dryrun_file, "r") as f:
        data = json.load(f)
    data["items"][0]["payload"] = {"password": "secret"}
    with open(dryrun_file, "w") as f:
        json.dump(data, f)

    result = validate_dryrun_applyplan(job_id, tmp_compliance_jobs)
    assert result["decision"] == "DRY_RUN_APPLYPLAN_INVALID"


def test_validation_passes_safe_dryrun(tmp_compliance_jobs):
    """Validation passes for safe dry-run."""
    from webui.services.compliance_dryrun_applyplan import build_dryrun_applyplan, validate_dryrun_applyplan

    job_id = "job-005"
    _create_applyplan_candidate(tmp_compliance_jobs, job_id)

    build_dryrun_applyplan(job_id, "TestOp", tmp_compliance_jobs)
    result = validate_dryrun_applyplan(job_id, tmp_compliance_jobs)

    assert result["decision"] == "DRY_RUN_APPLYPLAN_VALID"
