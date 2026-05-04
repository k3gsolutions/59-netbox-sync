"""
Tests for FASE COMPLIANCE-APPROVAL-001 — Approval Candidate Builder
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


def _create_promotion_gate(jobs_dir, job_id, decision="REMEDIATION_PROMOTION_CANDIDATE_READY"):
    """Helper to create promotion gate artifact."""
    gate_dir = jobs_dir / job_id / "remediation"
    gate_dir.mkdir(parents=True, exist_ok=True)
    gate_file = gate_dir / "remediation-promotion-gate.json"
    gate_data = {
        "job_id": job_id,
        "decision": decision,
        "evaluated_at": datetime.now(timezone.utc).isoformat()
    }
    with open(gate_file, "w") as f:
        json.dump(gate_data, f)
    return gate_file


def _create_validation(jobs_dir, job_id, decision="REMEDIATION_DRAFT_VALIDATION_SAFE"):
    """Helper to create validation artifact."""
    validation_dir = jobs_dir / job_id / "remediation"
    validation_dir.mkdir(parents=True, exist_ok=True)
    validation_file = validation_dir / "remediation-draft-validation.json"
    validation_data = {
        "job_id": job_id,
        "decision": decision,
        "validated_at": datetime.now(timezone.utc).isoformat()
    }
    with open(validation_file, "w") as f:
        json.dump(validation_data, f)
    return validation_file


def _create_remediation_draft(jobs_dir, job_id, draft_id, finding_id, device_id=1890):
    """Helper to create a remediation draft."""
    drafts_dir = jobs_dir / job_id / "remediation" / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    draft_file = drafts_dir / f"{draft_id}-draft.json"
    draft_data = {
        "draft_id": draft_id,
        "finding_id": finding_id,
        "device_id": device_id,
        "device_name": "4WNET-MNS-KTG-RX",
        "scope": "interface",
        "object_type": "interface",
        "object_name": "Eth-Trunk0/1",
        "rule_id": "RULE-001",
        "severity": "warning",
        "risk_level": "low",
        "proposed_action_type": "documentation_update",
        "proposed_change": {"description": "Update interface description"},
        "write_allowed": False,
        "execution_allowed": False,
        "requires_apply_plan": False,
        "requires_approval": True,
        "safety": {
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False
        }
    }
    with open(draft_file, "w") as f:
        json.dump(draft_data, f)
    return draft_file


def test_build_candidate_requires_promotion_gate(tmp_compliance_jobs):
    """Block build if promotion gate missing."""
    from webui.services.compliance_approval_candidates import build_approval_candidates

    job_id = "job-001"
    with pytest.raises(ValueError, match="Promotion gate not found"):
        build_approval_candidates(job_id, "Test", tmp_compliance_jobs)


def test_build_candidate_requires_gate_ready(tmp_compliance_jobs):
    """Block build if gate not ready."""
    from webui.services.compliance_approval_candidates import build_approval_candidates

    job_id = "job-002"
    _create_promotion_gate(tmp_compliance_jobs, job_id, "REMEDIATION_PROMOTION_BLOCKED")

    with pytest.raises(ValueError, match="must be READY"):
        build_approval_candidates(job_id, "Test", tmp_compliance_jobs)


def test_build_candidate_requires_safe_drafts(tmp_compliance_jobs):
    """Block build if no safe drafts found."""
    from webui.services.compliance_approval_candidates import build_approval_candidates

    job_id = "job-003"
    _create_promotion_gate(tmp_compliance_jobs, job_id, "REMEDIATION_PROMOTION_CANDIDATE_READY")
    _create_validation(tmp_compliance_jobs, job_id, "REMEDIATION_DRAFT_VALIDATION_SAFE")

    with pytest.raises(ValueError, match="No safe remediation drafts"):
        build_approval_candidates(job_id, "Test", tmp_compliance_jobs)


def test_build_candidate_blocks_unsafe_validation(tmp_compliance_jobs):
    """Block build if validation marked unsafe."""
    from webui.services.compliance_approval_candidates import build_approval_candidates

    job_id = "job-004"
    _create_promotion_gate(tmp_compliance_jobs, job_id, "REMEDIATION_PROMOTION_CANDIDATE_READY")
    _create_validation(tmp_compliance_jobs, job_id, "REMEDIATION_DRAFT_VALIDATION_UNSAFE")
    _create_remediation_draft(tmp_compliance_jobs, job_id, "RD-001", "CMP-001")

    with pytest.raises(ValueError, match="Draft validation marked unsafe"):
        build_approval_candidates(job_id, "Test", tmp_compliance_jobs)


def test_build_candidate_succeeds(tmp_compliance_jobs):
    """Build candidates from safe drafts."""
    from webui.services.compliance_approval_candidates import build_approval_candidates

    job_id = "job-005"
    _create_promotion_gate(tmp_compliance_jobs, job_id, "REMEDIATION_PROMOTION_CANDIDATE_READY")
    _create_validation(tmp_compliance_jobs, job_id, "REMEDIATION_DRAFT_VALIDATION_SAFE")
    _create_remediation_draft(tmp_compliance_jobs, job_id, "RD-001", "CMP-001")

    result = build_approval_candidates(job_id, "TestOp", tmp_compliance_jobs)

    assert result["status"] == "APPROVAL_CANDIDATES_BUILT"
    assert result["generated_by"] == "TestOp"
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["draft_id"] == "RD-001"


def test_candidate_has_write_allowed_false(tmp_compliance_jobs):
    """Candidate must have write_allowed=false."""
    from webui.services.compliance_approval_candidates import build_approval_candidates

    job_id = "job-006"
    _create_promotion_gate(tmp_compliance_jobs, job_id, "REMEDIATION_PROMOTION_CANDIDATE_READY")
    _create_validation(tmp_compliance_jobs, job_id, "REMEDIATION_DRAFT_VALIDATION_SAFE")
    _create_remediation_draft(tmp_compliance_jobs, job_id, "RD-002", "CMP-002")

    result = build_approval_candidates(job_id, "TestOp", tmp_compliance_jobs)
    candidate = result["candidates"][0]

    assert candidate["write_allowed"] is False


def test_candidate_has_execution_allowed_false(tmp_compliance_jobs):
    """Candidate must have execution_allowed=false."""
    from webui.services.compliance_approval_candidates import build_approval_candidates

    job_id = "job-007"
    _create_promotion_gate(tmp_compliance_jobs, job_id, "REMEDIATION_PROMOTION_CANDIDATE_READY")
    _create_validation(tmp_compliance_jobs, job_id, "REMEDIATION_DRAFT_VALIDATION_SAFE")
    _create_remediation_draft(tmp_compliance_jobs, job_id, "RD-003", "CMP-003")

    result = build_approval_candidates(job_id, "TestOp", tmp_compliance_jobs)
    candidate = result["candidates"][0]

    assert candidate["execution_allowed"] is False


def test_candidate_has_safety_flags(tmp_compliance_jobs):
    """Candidate must have all safety flags set to False."""
    from webui.services.compliance_approval_candidates import build_approval_candidates

    job_id = "job-008"
    _create_promotion_gate(tmp_compliance_jobs, job_id, "REMEDIATION_PROMOTION_CANDIDATE_READY")
    _create_validation(tmp_compliance_jobs, job_id, "REMEDIATION_DRAFT_VALIDATION_SAFE")
    _create_remediation_draft(tmp_compliance_jobs, job_id, "RD-004", "CMP-004")

    result = build_approval_candidates(job_id, "TestOp", tmp_compliance_jobs)
    candidate = result["candidates"][0]

    assert candidate["approval_record_created"] is False
    assert candidate["apply_plan_created"] is False
    assert candidate["safety"]["netbox_write"] is False
    assert candidate["safety"]["device_write"] is False
    assert candidate["safety"]["sync_called"] is False


def test_result_has_safety_flags(tmp_compliance_jobs):
    """Result must have safety flags."""
    from webui.services.compliance_approval_candidates import build_approval_candidates

    job_id = "job-009"
    _create_promotion_gate(tmp_compliance_jobs, job_id, "REMEDIATION_PROMOTION_CANDIDATE_READY")
    _create_validation(tmp_compliance_jobs, job_id, "REMEDIATION_DRAFT_VALIDATION_SAFE")
    _create_remediation_draft(tmp_compliance_jobs, job_id, "RD-005", "CMP-005")

    result = build_approval_candidates(job_id, "TestOp", tmp_compliance_jobs)

    assert result["safety"]["netbox_write"] is False
    assert result["safety"]["device_write"] is False
    assert result["safety"]["sync_called"] is False


def test_candidates_written_to_file(tmp_compliance_jobs):
    """Candidates must be written to approval-candidates.json."""
    from webui.services.compliance_approval_candidates import build_approval_candidates

    job_id = "job-010"
    _create_promotion_gate(tmp_compliance_jobs, job_id, "REMEDIATION_PROMOTION_CANDIDATE_READY")
    _create_validation(tmp_compliance_jobs, job_id, "REMEDIATION_DRAFT_VALIDATION_SAFE")
    _create_remediation_draft(tmp_compliance_jobs, job_id, "RD-006", "CMP-006")

    result = build_approval_candidates(job_id, "TestOp", tmp_compliance_jobs)

    candidates_file = tmp_compliance_jobs / job_id / "approval-candidates" / "approval-candidates.json"
    assert candidates_file.exists()

    with open(candidates_file, "r") as f:
        file_data = json.load(f)

    assert file_data["status"] == "APPROVAL_CANDIDATES_BUILT"
    assert len(file_data["candidates"]) == 1


def test_candidates_markdown_written(tmp_compliance_jobs):
    """Candidates markdown must be written."""
    from webui.services.compliance_approval_candidates import build_approval_candidates

    job_id = "job-011"
    _create_promotion_gate(tmp_compliance_jobs, job_id, "REMEDIATION_PROMOTION_CANDIDATE_READY")
    _create_validation(tmp_compliance_jobs, job_id, "REMEDIATION_DRAFT_VALIDATION_SAFE")
    _create_remediation_draft(tmp_compliance_jobs, job_id, "RD-007", "CMP-007")

    result = build_approval_candidates(job_id, "TestOp", tmp_compliance_jobs)

    md_file = tmp_compliance_jobs / job_id / "approval-candidates" / "APPROVAL-CANDIDATES.md"
    assert md_file.exists()

    with open(md_file, "r") as f:
        md_content = f.read()

    assert "Approval Candidates" in md_content
    assert "APPROVAL_CANDIDATES_BUILT" in md_content


def test_load_approval_candidates(tmp_compliance_jobs):
    """Load existing approval candidates."""
    from webui.services.compliance_approval_candidates import build_approval_candidates, load_approval_candidates

    job_id = "job-012"
    _create_promotion_gate(tmp_compliance_jobs, job_id, "REMEDIATION_PROMOTION_CANDIDATE_READY")
    _create_validation(tmp_compliance_jobs, job_id, "REMEDIATION_DRAFT_VALIDATION_SAFE")
    _create_remediation_draft(tmp_compliance_jobs, job_id, "RD-008", "CMP-008")

    build_approval_candidates(job_id, "TestOp", tmp_compliance_jobs)
    loaded = load_approval_candidates(job_id, tmp_compliance_jobs)

    assert loaded["status"] == "APPROVAL_CANDIDATES_BUILT"
    assert len(loaded["candidates"]) == 1


def test_summarize_approval_candidates(tmp_compliance_jobs):
    """Summarize candidates without loading all details."""
    from webui.services.compliance_approval_candidates import build_approval_candidates, summarize_approval_candidates

    job_id = "job-013"
    _create_promotion_gate(tmp_compliance_jobs, job_id, "REMEDIATION_PROMOTION_CANDIDATE_READY")
    _create_validation(tmp_compliance_jobs, job_id, "REMEDIATION_DRAFT_VALIDATION_SAFE")
    _create_remediation_draft(tmp_compliance_jobs, job_id, "RD-009", "CMP-009")

    build_approval_candidates(job_id, "TestOp", tmp_compliance_jobs)
    summary = summarize_approval_candidates(job_id, tmp_compliance_jobs)

    assert summary["job_id"] == job_id
    assert summary["candidate_count"] == 1
    assert summary["safety"]["netbox_write"] is False
