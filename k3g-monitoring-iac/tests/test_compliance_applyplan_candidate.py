"""
Tests for FASES COMPLIANCE-APPLYPLAN-001–002
ApplyPlan Candidate Builder + Validation
"""

import json
import pytest
from pathlib import Path
from datetime import datetime, timezone


@pytest.fixture
def tmp_compliance_jobs(tmp_path):
    """Create temporary compliance jobs directory."""
    jobs_dir = tmp_path / "reports" / "compliance" / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    return jobs_dir


def _create_applyplan_candidate_gate(jobs_dir, job_id, decision="APPLYPLAN_CANDIDATE_READY"):
    """Helper to create ApplyPlan candidate gate."""
    gate_dir = jobs_dir / job_id / "approval-records" / "proposed"
    gate_dir.mkdir(parents=True, exist_ok=True)
    gate_file = gate_dir / "applyplan-candidate-gate.json"
    gate_data = {
        "job_id": job_id,
        "decision": decision,
        "evaluated_at": datetime.now(timezone.utc).isoformat()
    }
    with open(gate_file, "w") as f:
        json.dump(gate_data, f)
    return gate_file


def _create_approval_record_validation(jobs_dir, job_id, decision="PROPOSED_APPROVAL_RECORDS_SAFE"):
    """Helper to create approval record validation."""
    validation_dir = jobs_dir / job_id / "approval-records" / "proposed"
    validation_dir.mkdir(parents=True, exist_ok=True)
    validation_file = validation_dir / "proposed-approval-record-validation.json"
    validation_data = {
        "job_id": job_id,
        "decision": decision,
        "validated_at": datetime.now(timezone.utc).isoformat()
    }
    with open(validation_file, "w") as f:
        json.dump(validation_data, f)
    return validation_file


def _create_proposed_record(jobs_dir, job_id, record_id, finding_id):
    """Helper to create proposed ApprovalRecord."""
    records_dir = jobs_dir / job_id / "approval-records" / "proposed"
    records_dir.mkdir(parents=True, exist_ok=True)

    records_file = records_dir / "proposed-approval-records.json"
    record_data = {
        "approval_record_id": record_id,
        "candidate_id": f"AC-{finding_id}",
        "finding_id": finding_id,
        "device_id": 1890,
        "device_name": "Device",
        "scope": "interface",
        "object_type": "interface",
        "object_name": f"Eth-Trunk0/{finding_id}",
        "rule_id": "RULE-001",
        "severity": "warning",
        "risk_level": "low",
        "proposed_action_type": "documentation_update",
        "proposed_change": {"description": "Safe change"},
        "status": "proposed",
        "approved": False,
        "approved_by": None,
        "approved_at": None,
        "write_allowed": False,
        "execution_allowed": False,
        "apply_plan_created": False,
        "manual_approval_required": True,
        "state_history": [
            {
                "status": "proposed",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": None,
                "reason": "Proposed from candidate"
            }
        ],
        "safety": {
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False
        }
    }

    records_json = {
        "job_id": job_id,
        "status": "PROPOSED_APPROVAL_RECORDS_BUILT",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": "TestOp",
        "records": [record_data]
    }

    with open(records_file, "w") as f:
        json.dump(records_json, f)
    return records_file


def test_applyplan_candidate_requires_gate(tmp_compliance_jobs):
    """Block if gate missing."""
    from webui.services.compliance_applyplan_candidates import build_applyplan_candidate

    job_id = "job-001"
    with pytest.raises(ValueError, match="ApplyPlan candidate gate not found"):
        build_applyplan_candidate(job_id, "Test", tmp_compliance_jobs)


def test_applyplan_candidate_requires_gate_ready(tmp_compliance_jobs):
    """Block if gate not ready."""
    from webui.services.compliance_applyplan_candidates import build_applyplan_candidate

    job_id = "job-002"
    _create_applyplan_candidate_gate(tmp_compliance_jobs, job_id, "APPLYPLAN_CANDIDATE_BLOCKED")

    with pytest.raises(ValueError, match="must be READY"):
        build_applyplan_candidate(job_id, "Test", tmp_compliance_jobs)


def test_applyplan_candidate_requires_records(tmp_compliance_jobs):
    """Block if no records."""
    from webui.services.compliance_applyplan_candidates import build_applyplan_candidate

    job_id = "job-003"
    _create_applyplan_candidate_gate(tmp_compliance_jobs, job_id)
    _create_approval_record_validation(tmp_compliance_jobs, job_id)

    with pytest.raises(ValueError, match="No proposed ApprovalRecords"):
        build_applyplan_candidate(job_id, "Test", tmp_compliance_jobs)


def test_build_applyplan_candidate_succeeds(tmp_compliance_jobs):
    """Build ApplyPlan candidate."""
    from webui.services.compliance_applyplan_candidates import build_applyplan_candidate

    job_id = "job-004"
    _create_applyplan_candidate_gate(tmp_compliance_jobs, job_id)
    _create_approval_record_validation(tmp_compliance_jobs, job_id)
    _create_proposed_record(tmp_compliance_jobs, job_id, "PAR-001", "CMP-001")

    result = build_applyplan_candidate(job_id, "TestOp", tmp_compliance_jobs)

    assert result["status"] == "APPLYPLAN_CANDIDATE_BUILT"
    assert result["mode"] == "candidate"
    assert len(result["items"]) >= 1


def test_applyplan_item_has_write_allowed_false(tmp_compliance_jobs):
    """Item must have write_allowed=false."""
    from webui.services.compliance_applyplan_candidates import build_applyplan_candidate

    job_id = "job-005"
    _create_applyplan_candidate_gate(tmp_compliance_jobs, job_id)
    _create_approval_record_validation(tmp_compliance_jobs, job_id)
    _create_proposed_record(tmp_compliance_jobs, job_id, "PAR-001", "CMP-001")

    result = build_applyplan_candidate(job_id, "TestOp", tmp_compliance_jobs)
    item = result["items"][0]

    assert item["write_allowed"] is False
    assert item["execution_allowed"] is False


def test_applyplan_item_requires_dry_run(tmp_compliance_jobs):
    """Item must require dry-run."""
    from webui.services.compliance_applyplan_candidates import build_applyplan_candidate

    job_id = "job-006"
    _create_applyplan_candidate_gate(tmp_compliance_jobs, job_id)
    _create_approval_record_validation(tmp_compliance_jobs, job_id)
    _create_proposed_record(tmp_compliance_jobs, job_id, "PAR-001", "CMP-001")

    result = build_applyplan_candidate(job_id, "TestOp", tmp_compliance_jobs)
    item = result["items"][0]

    assert item["requires_dry_run"] is True
    assert item["requires_real_write_gate"] is True


def test_validation_blocks_write_allowed_true(tmp_compliance_jobs):
    """Validation blocks write_allowed=true."""
    from webui.services.compliance_applyplan_candidates import build_applyplan_candidate
    from webui.services.compliance_applyplan_validation import validate_applyplan_candidate

    job_id = "job-007"
    _create_applyplan_candidate_gate(tmp_compliance_jobs, job_id)
    _create_approval_record_validation(tmp_compliance_jobs, job_id)
    _create_proposed_record(tmp_compliance_jobs, job_id, "PAR-001", "CMP-001")

    build_applyplan_candidate(job_id, "TestOp", tmp_compliance_jobs)

    # Manually edit candidate
    candidate_file = tmp_compliance_jobs / job_id / "applyplan" / "candidate" / "applyplan-candidate.json"
    with open(candidate_file, "r") as f:
        data = json.load(f)
    data["items"][0]["write_allowed"] = True
    with open(candidate_file, "w") as f:
        json.dump(data, f)

    result = validate_applyplan_candidate(job_id, tmp_compliance_jobs)
    assert result["decision"] == "APPLYPLAN_CANDIDATE_INVALID"


def test_validation_blocks_secret_in_payload(tmp_compliance_jobs):
    """Validation blocks secret keyword in payload."""
    from webui.services.compliance_applyplan_candidates import build_applyplan_candidate
    from webui.services.compliance_applyplan_validation import validate_applyplan_candidate

    job_id = "job-008"
    _create_applyplan_candidate_gate(tmp_compliance_jobs, job_id)
    _create_approval_record_validation(tmp_compliance_jobs, job_id)
    _create_proposed_record(tmp_compliance_jobs, job_id, "PAR-001", "CMP-001")

    build_applyplan_candidate(job_id, "TestOp", tmp_compliance_jobs)

    # Manually edit candidate
    candidate_file = tmp_compliance_jobs / job_id / "applyplan" / "candidate" / "applyplan-candidate.json"
    with open(candidate_file, "r") as f:
        data = json.load(f)
    data["items"][0]["payload"] = {"password": "secret123"}
    with open(candidate_file, "w") as f:
        json.dump(data, f)

    result = validate_applyplan_candidate(job_id, tmp_compliance_jobs)
    assert result["decision"] == "APPLYPLAN_CANDIDATE_INVALID"


def test_validation_passes_safe_candidate(tmp_compliance_jobs):
    """Validation passes for safe candidate."""
    from webui.services.compliance_applyplan_candidates import build_applyplan_candidate
    from webui.services.compliance_applyplan_validation import validate_applyplan_candidate

    job_id = "job-009"
    _create_applyplan_candidate_gate(tmp_compliance_jobs, job_id)
    _create_approval_record_validation(tmp_compliance_jobs, job_id)
    _create_proposed_record(tmp_compliance_jobs, job_id, "PAR-001", "CMP-001")

    build_applyplan_candidate(job_id, "TestOp", tmp_compliance_jobs)
    result = validate_applyplan_candidate(job_id, tmp_compliance_jobs)

    assert result["decision"] == "APPLYPLAN_CANDIDATE_VALID"
    assert result["issue_count"] == 0


def test_applyplan_candidate_written_to_file(tmp_compliance_jobs):
    """ApplyPlan candidate written to file."""
    from webui.services.compliance_applyplan_candidates import build_applyplan_candidate

    job_id = "job-010"
    _create_applyplan_candidate_gate(tmp_compliance_jobs, job_id)
    _create_approval_record_validation(tmp_compliance_jobs, job_id)
    _create_proposed_record(tmp_compliance_jobs, job_id, "PAR-001", "CMP-001")

    build_applyplan_candidate(job_id, "TestOp", tmp_compliance_jobs)

    candidate_file = tmp_compliance_jobs / job_id / "applyplan" / "candidate" / "applyplan-candidate.json"
    assert candidate_file.exists()

    md_file = tmp_compliance_jobs / job_id / "applyplan" / "candidate" / "APPLYPLAN-CANDIDATE.md"
    assert md_file.exists()


def test_load_applyplan_candidate(tmp_compliance_jobs):
    """Load ApplyPlan candidate."""
    from webui.services.compliance_applyplan_candidates import build_applyplan_candidate, load_applyplan_candidate

    job_id = "job-011"
    _create_applyplan_candidate_gate(tmp_compliance_jobs, job_id)
    _create_approval_record_validation(tmp_compliance_jobs, job_id)
    _create_proposed_record(tmp_compliance_jobs, job_id, "PAR-001", "CMP-001")

    build_applyplan_candidate(job_id, "TestOp", tmp_compliance_jobs)
    loaded = load_applyplan_candidate(job_id, tmp_compliance_jobs)

    assert loaded["status"] == "APPLYPLAN_CANDIDATE_BUILT"
    assert len(loaded["items"]) >= 1
