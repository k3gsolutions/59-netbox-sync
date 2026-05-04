"""
Tests for FASE COMPLIANCE-APPROVAL-003 — Approval Candidate Safety Validation
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


def _create_approval_candidates(jobs_dir, job_id, candidates_list):
    """Helper to create approval candidates artifact."""
    candidates_dir = jobs_dir / job_id / "approval-candidates"
    candidates_dir.mkdir(parents=True, exist_ok=True)
    candidates_file = candidates_dir / "approval-candidates.json"
    candidates_data = {
        "job_id": job_id,
        "status": "APPROVAL_CANDIDATES_BUILT",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": "TestOp",
        "candidates": candidates_list
    }
    with open(candidates_file, "w") as f:
        json.dump(candidates_data, f)
    return candidates_file


def _make_safe_candidate(candidate_id="AC-001", draft_id="RD-001"):
    """Helper to create a safe candidate."""
    return {
        "candidate_id": candidate_id,
        "draft_id": draft_id,
        "finding_id": "CMP-001",
        "device_id": 1890,
        "device_name": "Device",
        "scope": "interface",
        "object_type": "interface",
        "object_name": "Eth-Trunk0/1",
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


def test_validation_requires_candidates(tmp_compliance_jobs):
    """Block validation if no candidates found."""
    from webui.services.compliance_approval_validation import validate_approval_candidates

    job_id = "job-001"
    with pytest.raises(ValueError, match="No approval candidates found"):
        validate_approval_candidates(job_id, tmp_compliance_jobs)


def test_validation_blocks_write_allowed_true(tmp_compliance_jobs):
    """Block validation if write_allowed=true."""
    from webui.services.compliance_approval_validation import validate_approval_candidates

    job_id = "job-002"
    candidate = _make_safe_candidate()
    candidate["write_allowed"] = True
    _create_approval_candidates(tmp_compliance_jobs, job_id, [candidate])

    result = validate_approval_candidates(job_id, tmp_compliance_jobs)
    assert result["decision"] == "APPROVAL_CANDIDATES_UNSAFE"
    assert any("write_allowed" in issue for issue in result["issues"])


def test_validation_blocks_execution_allowed_true(tmp_compliance_jobs):
    """Block validation if execution_allowed=true."""
    from webui.services.compliance_approval_validation import validate_approval_candidates

    job_id = "job-003"
    candidate = _make_safe_candidate()
    candidate["execution_allowed"] = True
    _create_approval_candidates(tmp_compliance_jobs, job_id, [candidate])

    result = validate_approval_candidates(job_id, tmp_compliance_jobs)
    assert result["decision"] == "APPROVAL_CANDIDATES_UNSAFE"
    assert any("execution_allowed" in issue for issue in result["issues"])


def test_validation_blocks_approval_record_created_true(tmp_compliance_jobs):
    """Block validation if approval_record_created=true."""
    from webui.services.compliance_approval_validation import validate_approval_candidates

    job_id = "job-004"
    candidate = _make_safe_candidate()
    candidate["approval_record_created"] = True
    _create_approval_candidates(tmp_compliance_jobs, job_id, [candidate])

    result = validate_approval_candidates(job_id, tmp_compliance_jobs)
    assert result["decision"] == "APPROVAL_CANDIDATES_UNSAFE"
    assert any("approval_record_created" in issue for issue in result["issues"])


def test_validation_blocks_apply_plan_created_true(tmp_compliance_jobs):
    """Block validation if apply_plan_created=true."""
    from webui.services.compliance_approval_validation import validate_approval_candidates

    job_id = "job-005"
    candidate = _make_safe_candidate()
    candidate["apply_plan_created"] = True
    _create_approval_candidates(tmp_compliance_jobs, job_id, [candidate])

    result = validate_approval_candidates(job_id, tmp_compliance_jobs)
    assert result["decision"] == "APPROVAL_CANDIDATES_UNSAFE"
    assert any("apply_plan_created" in issue for issue in result["issues"])


def test_validation_blocks_forbidden_command(tmp_compliance_jobs):
    """Block validation if proposed_change contains forbidden command."""
    from webui.services.compliance_approval_validation import validate_approval_candidates

    job_id = "job-006"
    candidate = _make_safe_candidate()
    candidate["proposed_change"] = {"command": "system-view"}
    _create_approval_candidates(tmp_compliance_jobs, job_id, [candidate])

    result = validate_approval_candidates(job_id, tmp_compliance_jobs)
    assert result["decision"] == "APPROVAL_CANDIDATES_UNSAFE"
    assert any("forbidden command" in issue for issue in result["issues"])


def test_validation_blocks_secret_keyword(tmp_compliance_jobs):
    """Block validation if proposed_change contains secret keyword."""
    from webui.services.compliance_approval_validation import validate_approval_candidates

    job_id = "job-007"
    candidate = _make_safe_candidate()
    candidate["proposed_change"] = {"password": "secret123"}
    _create_approval_candidates(tmp_compliance_jobs, job_id, [candidate])

    result = validate_approval_candidates(job_id, tmp_compliance_jobs)
    assert result["decision"] == "APPROVAL_CANDIDATES_UNSAFE"
    assert any("secret keyword" in issue for issue in result["issues"])


def test_validation_blocks_approval_required_false(tmp_compliance_jobs):
    """Block validation if approval_required=false."""
    from webui.services.compliance_approval_validation import validate_approval_candidates

    job_id = "job-008"
    candidate = _make_safe_candidate()
    candidate["approval_intent"]["approval_required"] = False
    _create_approval_candidates(tmp_compliance_jobs, job_id, [candidate])

    result = validate_approval_candidates(job_id, tmp_compliance_jobs)
    assert result["decision"] == "APPROVAL_CANDIDATES_UNSAFE"
    assert any("approval_required" in issue for issue in result["issues"])


def test_validation_blocks_safety_flag_true(tmp_compliance_jobs):
    """Block validation if any safety flag is true."""
    from webui.services.compliance_approval_validation import validate_approval_candidates

    job_id = "job-009"
    candidate = _make_safe_candidate()
    candidate["safety"]["netbox_write"] = True
    _create_approval_candidates(tmp_compliance_jobs, job_id, [candidate])

    result = validate_approval_candidates(job_id, tmp_compliance_jobs)
    assert result["decision"] == "APPROVAL_CANDIDATES_UNSAFE"
    assert any("netbox_write" in issue for issue in result["issues"])


def test_validation_passes_safe_candidate(tmp_compliance_jobs):
    """Pass validation for safe candidate."""
    from webui.services.compliance_approval_validation import validate_approval_candidates

    job_id = "job-010"
    candidate = _make_safe_candidate()
    _create_approval_candidates(tmp_compliance_jobs, job_id, [candidate])

    result = validate_approval_candidates(job_id, tmp_compliance_jobs)
    assert result["decision"] == "APPROVAL_CANDIDATES_SAFE"
    assert result["issue_count"] == 0


def test_validation_multiple_candidates_safe(tmp_compliance_jobs):
    """Validate multiple safe candidates."""
    from webui.services.compliance_approval_validation import validate_approval_candidates

    job_id = "job-011"
    candidates = [
        _make_safe_candidate("AC-001", "RD-001"),
        _make_safe_candidate("AC-002", "RD-002"),
        _make_safe_candidate("AC-003", "RD-003")
    ]
    _create_approval_candidates(tmp_compliance_jobs, job_id, candidates)

    result = validate_approval_candidates(job_id, tmp_compliance_jobs)
    assert result["decision"] == "APPROVAL_CANDIDATES_SAFE"
    assert result["candidate_count"] == 3
    assert result["valid_count"] == 3


def test_validation_result_written_to_file(tmp_compliance_jobs):
    """Validation result written to file."""
    from webui.services.compliance_approval_validation import validate_approval_candidates

    job_id = "job-012"
    candidate = _make_safe_candidate()
    _create_approval_candidates(tmp_compliance_jobs, job_id, [candidate])

    validate_approval_candidates(job_id, tmp_compliance_jobs)

    validation_file = tmp_compliance_jobs / job_id / "approval-candidates" / "approval-candidate-validation.json"
    assert validation_file.exists()

    with open(validation_file, "r") as f:
        file_data = json.load(f)

    assert file_data["decision"] == "APPROVAL_CANDIDATES_SAFE"


def test_validation_markdown_written(tmp_compliance_jobs):
    """Validation markdown written."""
    from webui.services.compliance_approval_validation import validate_approval_candidates

    job_id = "job-013"
    candidate = _make_safe_candidate()
    _create_approval_candidates(tmp_compliance_jobs, job_id, [candidate])

    validate_approval_candidates(job_id, tmp_compliance_jobs)

    md_file = tmp_compliance_jobs / job_id / "approval-candidates" / "APPROVAL-CANDIDATE-VALIDATION.md"
    assert md_file.exists()

    with open(md_file, "r") as f:
        md_content = f.read()

    assert "Approval Candidate Validation" in md_content


def test_validation_has_safety_flags(tmp_compliance_jobs):
    """Validation result has safety flags."""
    from webui.services.compliance_approval_validation import validate_approval_candidates

    job_id = "job-014"
    candidate = _make_safe_candidate()
    _create_approval_candidates(tmp_compliance_jobs, job_id, [candidate])

    result = validate_approval_candidates(job_id, tmp_compliance_jobs)
    assert result["safety"]["netbox_write"] is False
    assert result["safety"]["device_write"] is False
    assert result["safety"]["sync_called"] is False
