"""
Tests for FASES COMPLIANCE-APPROVALRECORD-001–003
Proposed ApprovalRecords + Validation + ApplyPlan Gate
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


def _create_proposal_gate(jobs_dir, job_id, decision="APPROVALRECORD_PROPOSAL_READY"):
    """Helper to create approval proposal gate."""
    gate_dir = jobs_dir / job_id / "approval-candidates"
    gate_dir.mkdir(parents=True, exist_ok=True)
    gate_file = gate_dir / "approvalrecord-proposal-gate.json"
    gate_data = {
        "job_id": job_id,
        "decision": decision,
        "evaluated_at": datetime.now(timezone.utc).isoformat()
    }
    with open(gate_file, "w") as f:
        json.dump(gate_data, f)
    return gate_file


def _create_approval_validation(jobs_dir, job_id, decision="APPROVAL_CANDIDATES_SAFE"):
    """Helper to create approval validation."""
    validation_dir = jobs_dir / job_id / "approval-candidates"
    validation_dir.mkdir(parents=True, exist_ok=True)
    validation_file = validation_dir / "approval-candidate-validation.json"
    validation_data = {
        "job_id": job_id,
        "decision": decision,
        "validated_at": datetime.now(timezone.utc).isoformat()
    }
    with open(validation_file, "w") as f:
        json.dump(validation_data, f)
    return validation_file


def _create_approval_candidate(jobs_dir, job_id, candidate_id, finding_id):
    """Helper to create approval candidate."""
    candidates_dir = jobs_dir / job_id / "approval-candidates"
    candidates_dir.mkdir(parents=True, exist_ok=True)

    candidates_file = candidates_dir / "approval-candidates.json"
    candidate_data = {
        "candidate_id": candidate_id,
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
        "approval_intent": {
            "approval_type": "manual_review_required",
            "approval_required": True,
            "reason": "Requires approval"
        },
        "status": "candidate",
        "write_allowed": False,
        "execution_allowed": False,
        "approval_record_created": False,
        "apply_plan_created": False,
        "safety": {
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False
        }
    }

    candidates_json = {
        "job_id": job_id,
        "status": "APPROVAL_CANDIDATES_BUILT",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": "TestOp",
        "candidates": [candidate_data]
    }

    with open(candidates_file, "w") as f:
        json.dump(candidates_json, f)
    return candidates_file


def test_proposed_records_requires_proposal_gate(tmp_compliance_jobs):
    """Block if proposal gate missing."""
    from webui.services.compliance_approval_records import build_proposed_approval_records

    job_id = "job-001"
    with pytest.raises(ValueError, match="Proposal gate not found"):
        build_proposed_approval_records(job_id, "Test", tmp_compliance_jobs)


def test_proposed_records_requires_gate_ready(tmp_compliance_jobs):
    """Block if gate not ready."""
    from webui.services.compliance_approval_records import build_proposed_approval_records

    job_id = "job-002"
    _create_proposal_gate(tmp_compliance_jobs, job_id, "APPROVALRECORD_PROPOSAL_BLOCKED")

    with pytest.raises(ValueError, match="must be READY"):
        build_proposed_approval_records(job_id, "Test", tmp_compliance_jobs)


def test_proposed_records_requires_candidates(tmp_compliance_jobs):
    """Block if no candidates."""
    from webui.services.compliance_approval_records import build_proposed_approval_records

    job_id = "job-003"
    _create_proposal_gate(tmp_compliance_jobs, job_id, "APPROVALRECORD_PROPOSAL_READY")
    _create_approval_validation(tmp_compliance_jobs, job_id, "APPROVAL_CANDIDATES_SAFE")

    with pytest.raises(ValueError, match="No approval candidates"):
        build_proposed_approval_records(job_id, "Test", tmp_compliance_jobs)


def test_build_proposed_records_succeeds(tmp_compliance_jobs):
    """Build proposed records."""
    from webui.services.compliance_approval_records import build_proposed_approval_records

    job_id = "job-004"
    _create_proposal_gate(tmp_compliance_jobs, job_id, "APPROVALRECORD_PROPOSAL_READY")
    _create_approval_validation(tmp_compliance_jobs, job_id, "APPROVAL_CANDIDATES_SAFE")
    _create_approval_candidate(tmp_compliance_jobs, job_id, "AC-001", "CMP-001")

    result = build_proposed_approval_records(job_id, "TestOp", tmp_compliance_jobs)

    assert result["status"] == "PROPOSED_APPROVAL_RECORDS_BUILT"
    assert result["created_by"] == "TestOp"
    assert len(result["records"]) == 1
    assert result["records"][0]["status"] == "proposed"


def test_proposed_record_has_approved_false(tmp_compliance_jobs):
    """Proposed record must have approved=false."""
    from webui.services.compliance_approval_records import build_proposed_approval_records

    job_id = "job-005"
    _create_proposal_gate(tmp_compliance_jobs, job_id)
    _create_approval_validation(tmp_compliance_jobs, job_id)
    _create_approval_candidate(tmp_compliance_jobs, job_id, "AC-001", "CMP-001")

    result = build_proposed_approval_records(job_id, "TestOp", tmp_compliance_jobs)
    record = result["records"][0]

    assert record["approved"] is False
    assert record["approved_by"] is None
    assert record["approved_at"] is None


def test_proposed_record_status_is_proposed(tmp_compliance_jobs):
    """Proposed record status must be 'proposed'."""
    from webui.services.compliance_approval_records import build_proposed_approval_records

    job_id = "job-006"
    _create_proposal_gate(tmp_compliance_jobs, job_id)
    _create_approval_validation(tmp_compliance_jobs, job_id)
    _create_approval_candidate(tmp_compliance_jobs, job_id, "AC-001", "CMP-001")

    result = build_proposed_approval_records(job_id, "TestOp", tmp_compliance_jobs)
    record = result["records"][0]

    assert record["status"] == "proposed"
    assert record["manual_approval_required"] is True


def test_proposed_record_has_write_allowed_false(tmp_compliance_jobs):
    """Proposed record must have write_allowed=false."""
    from webui.services.compliance_approval_records import build_proposed_approval_records

    job_id = "job-007"
    _create_proposal_gate(tmp_compliance_jobs, job_id)
    _create_approval_validation(tmp_compliance_jobs, job_id)
    _create_approval_candidate(tmp_compliance_jobs, job_id, "AC-001", "CMP-001")

    result = build_proposed_approval_records(job_id, "TestOp", tmp_compliance_jobs)
    record = result["records"][0]

    assert record["write_allowed"] is False
    assert record["execution_allowed"] is False
    assert record["apply_plan_created"] is False


def test_validation_blocks_approved_true(tmp_compliance_jobs):
    """Validation blocks if approved=true."""
    from webui.services.compliance_approval_records import build_proposed_approval_records
    from webui.services.compliance_approval_record_validation import validate_proposed_approval_records

    job_id = "job-008"
    _create_proposal_gate(tmp_compliance_jobs, job_id)
    _create_approval_validation(tmp_compliance_jobs, job_id)
    _create_approval_candidate(tmp_compliance_jobs, job_id, "AC-001", "CMP-001")

    build_proposed_approval_records(job_id, "TestOp", tmp_compliance_jobs)

    # Manually edit record to have approved=true
    records_file = tmp_compliance_jobs / job_id / "approval-records" / "proposed" / "proposed-approval-records.json"
    with open(records_file, "r") as f:
        data = json.load(f)
    data["records"][0]["approved"] = True
    with open(records_file, "w") as f:
        json.dump(data, f)

    result = validate_proposed_approval_records(job_id, tmp_compliance_jobs)
    assert result["decision"] == "PROPOSED_APPROVAL_RECORDS_UNSAFE"


def test_validation_blocks_secret_keyword(tmp_compliance_jobs):
    """Validation blocks secret keyword."""
    from webui.services.compliance_approval_records import build_proposed_approval_records
    from webui.services.compliance_approval_record_validation import validate_proposed_approval_records

    job_id = "job-009"
    _create_proposal_gate(tmp_compliance_jobs, job_id)
    _create_approval_validation(tmp_compliance_jobs, job_id)
    _create_approval_candidate(tmp_compliance_jobs, job_id, "AC-001", "CMP-001")

    build_proposed_approval_records(job_id, "TestOp", tmp_compliance_jobs)

    # Manually edit record to have secret
    records_file = tmp_compliance_jobs / job_id / "approval-records" / "proposed" / "proposed-approval-records.json"
    with open(records_file, "r") as f:
        data = json.load(f)
    data["records"][0]["proposed_change"] = {"password": "secret123"}
    with open(records_file, "w") as f:
        json.dump(data, f)

    result = validate_proposed_approval_records(job_id, tmp_compliance_jobs)
    assert result["decision"] == "PROPOSED_APPROVAL_RECORDS_UNSAFE"


def test_validation_passes_safe_record(tmp_compliance_jobs):
    """Validation passes for safe record."""
    from webui.services.compliance_approval_records import build_proposed_approval_records
    from webui.services.compliance_approval_record_validation import validate_proposed_approval_records

    job_id = "job-010"
    _create_proposal_gate(tmp_compliance_jobs, job_id)
    _create_approval_validation(tmp_compliance_jobs, job_id)
    _create_approval_candidate(tmp_compliance_jobs, job_id, "AC-001", "CMP-001")

    build_proposed_approval_records(job_id, "TestOp", tmp_compliance_jobs)
    result = validate_proposed_approval_records(job_id, tmp_compliance_jobs)

    assert result["decision"] == "PROPOSED_APPROVAL_RECORDS_SAFE"
    assert result["issue_count"] == 0


def test_proposed_records_written_to_file(tmp_compliance_jobs):
    """Proposed records written to file."""
    from webui.services.compliance_approval_records import build_proposed_approval_records

    job_id = "job-011"
    _create_proposal_gate(tmp_compliance_jobs, job_id)
    _create_approval_validation(tmp_compliance_jobs, job_id)
    _create_approval_candidate(tmp_compliance_jobs, job_id, "AC-001", "CMP-001")

    build_proposed_approval_records(job_id, "TestOp", tmp_compliance_jobs)

    records_file = tmp_compliance_jobs / job_id / "approval-records" / "proposed" / "proposed-approval-records.json"
    assert records_file.exists()

    md_file = tmp_compliance_jobs / job_id / "approval-records" / "proposed" / "PROPOSED-APPROVAL-RECORDS.md"
    assert md_file.exists()


def test_load_proposed_records(tmp_compliance_jobs):
    """Load proposed records."""
    from webui.services.compliance_approval_records import build_proposed_approval_records, load_proposed_approval_records

    job_id = "job-012"
    _create_proposal_gate(tmp_compliance_jobs, job_id)
    _create_approval_validation(tmp_compliance_jobs, job_id)
    _create_approval_candidate(tmp_compliance_jobs, job_id, "AC-001", "CMP-001")

    build_proposed_approval_records(job_id, "TestOp", tmp_compliance_jobs)
    loaded = load_proposed_approval_records(job_id, tmp_compliance_jobs)

    assert loaded["status"] == "PROPOSED_APPROVAL_RECORDS_BUILT"
    assert len(loaded["records"]) == 1


def test_summarize_proposed_records(tmp_compliance_jobs):
    """Summarize proposed records."""
    from webui.services.compliance_approval_records import build_proposed_approval_records, summarize_proposed_approval_records

    job_id = "job-013"
    _create_proposal_gate(tmp_compliance_jobs, job_id)
    _create_approval_validation(tmp_compliance_jobs, job_id)
    _create_approval_candidate(tmp_compliance_jobs, job_id, "AC-001", "CMP-001")

    build_proposed_approval_records(job_id, "TestOp", tmp_compliance_jobs)
    summary = summarize_proposed_approval_records(job_id, tmp_compliance_jobs)

    assert summary["record_count"] == 1
    assert summary["approved_count"] == 0
    assert summary["pending_count"] == 1
