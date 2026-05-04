"""
Tests for FASE COMPLIANCE-APPROVAL-004 — ApprovalRecord Proposal Gate
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


def _create_approval_candidates(jobs_dir, job_id, count=1):
    """Helper to create approval candidates artifact."""
    candidates_dir = jobs_dir / job_id / "approval-candidates"
    candidates_dir.mkdir(parents=True, exist_ok=True)

    candidates = []
    for i in range(count):
        candidates.append({
            "candidate_id": f"AC-{i:03d}",
            "draft_id": f"RD-{i:03d}",
            "finding_id": f"CMP-{i:03d}",
            "device_id": 1890,
            "device_name": "Device",
            "scope": "interface",
            "object_type": "interface",
            "object_name": f"Eth-Trunk0/{i}",
            "rule_id": f"RULE-{i:03d}",
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
        })

    candidates_file = candidates_dir / "approval-candidates.json"
    candidates_data = {
        "job_id": job_id,
        "status": "APPROVAL_CANDIDATES_BUILT",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": "TestOp",
        "candidates": candidates
    }
    with open(candidates_file, "w") as f:
        json.dump(candidates_data, f)
    return candidates_file


def _create_approval_validation(jobs_dir, job_id, decision="APPROVAL_CANDIDATES_SAFE"):
    """Helper to create approval validation artifact."""
    validation_dir = jobs_dir / job_id / "approval-candidates"
    validation_dir.mkdir(parents=True, exist_ok=True)

    validation_file = validation_dir / "approval-candidate-validation.json"
    validation_data = {
        "job_id": job_id,
        "status": "validation_completed",
        "decision": decision,
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "candidate_count": 1,
        "valid_count": 1,
        "issues": [],
        "issue_count": 0,
        "safety": {
            "netbox_write": False,
            "device_write": False,
            "sync_called": False,
            "approval_record_created": False,
            "apply_plan_created": False
        }
    }
    with open(validation_file, "w") as f:
        json.dump(validation_data, f)
    return validation_file


def test_gate_requires_candidates(tmp_compliance_jobs):
    """Block gate if no candidates found."""
    from webui.services.compliance_approvalrecord_proposal_gate import evaluate_approvalrecord_proposal_gate

    job_id = "job-001"
    with pytest.raises(ValueError, match="No approval candidates found"):
        evaluate_approvalrecord_proposal_gate(job_id, "Test", True, tmp_compliance_jobs)


def test_gate_requires_validation(tmp_compliance_jobs):
    """Block gate if no validation found."""
    from webui.services.compliance_approvalrecord_proposal_gate import evaluate_approvalrecord_proposal_gate

    job_id = "job-002"
    _create_approval_candidates(tmp_compliance_jobs, job_id)

    with pytest.raises(ValueError, match="No approval candidate validation found"):
        evaluate_approvalrecord_proposal_gate(job_id, "Test", True, tmp_compliance_jobs)


def test_gate_blocks_unsafe_validation(tmp_compliance_jobs):
    """Block gate if validation unsafe."""
    from webui.services.compliance_approvalrecord_proposal_gate import evaluate_approvalrecord_proposal_gate

    job_id = "job-003"
    _create_approval_candidates(tmp_compliance_jobs, job_id)
    _create_approval_validation(tmp_compliance_jobs, job_id, "APPROVAL_CANDIDATES_UNSAFE")

    with pytest.raises(ValueError, match="validation is UNSAFE"):
        evaluate_approvalrecord_proposal_gate(job_id, "Test", True, tmp_compliance_jobs)


def test_gate_requires_confirmation(tmp_compliance_jobs):
    """Block gate if confirmation not true."""
    from webui.services.compliance_approvalrecord_proposal_gate import evaluate_approvalrecord_proposal_gate

    job_id = "job-004"
    _create_approval_candidates(tmp_compliance_jobs, job_id)
    _create_approval_validation(tmp_compliance_jobs, job_id, "APPROVAL_CANDIDATES_SAFE")

    with pytest.raises(ValueError, match="confirm_human_reviewed must be true"):
        evaluate_approvalrecord_proposal_gate(job_id, "Test", False, tmp_compliance_jobs)


def test_gate_ready_safe_validation(tmp_compliance_jobs):
    """Gate ready when validation safe."""
    from webui.services.compliance_approvalrecord_proposal_gate import evaluate_approvalrecord_proposal_gate

    job_id = "job-005"
    _create_approval_candidates(tmp_compliance_jobs, job_id)
    _create_approval_validation(tmp_compliance_jobs, job_id, "APPROVAL_CANDIDATES_SAFE")

    result = evaluate_approvalrecord_proposal_gate(job_id, "TestOp", True, tmp_compliance_jobs)

    assert result["decision"] == "APPROVALRECORD_PROPOSAL_READY"
    assert result["validation_decision"] == "APPROVAL_CANDIDATES_SAFE"


def test_gate_ready_with_warnings(tmp_compliance_jobs):
    """Gate ready with warnings when validation has warnings."""
    from webui.services.compliance_approvalrecord_proposal_gate import evaluate_approvalrecord_proposal_gate

    job_id = "job-006"
    _create_approval_candidates(tmp_compliance_jobs, job_id)
    _create_approval_validation(tmp_compliance_jobs, job_id, "APPROVAL_CANDIDATES_SAFE_WITH_WARNINGS")

    result = evaluate_approvalrecord_proposal_gate(job_id, "TestOp", True, tmp_compliance_jobs)

    assert result["decision"] == "APPROVALRECORD_PROPOSAL_READY_WITH_WARNINGS"
    assert result["validation_decision"] == "APPROVAL_CANDIDATES_SAFE_WITH_WARNINGS"


def test_gate_has_safety_flags(tmp_compliance_jobs):
    """Gate result has safety flags."""
    from webui.services.compliance_approvalrecord_proposal_gate import evaluate_approvalrecord_proposal_gate

    job_id = "job-007"
    _create_approval_candidates(tmp_compliance_jobs, job_id)
    _create_approval_validation(tmp_compliance_jobs, job_id, "APPROVAL_CANDIDATES_SAFE")

    result = evaluate_approvalrecord_proposal_gate(job_id, "TestOp", True, tmp_compliance_jobs)

    assert result["safety"]["netbox_write"] is False
    assert result["safety"]["device_write"] is False
    assert result["safety"]["sync_called"] is False
    assert result["safety"]["approval_record_created"] is False
    assert result["safety"]["apply_plan_created"] is False


def test_gate_written_to_file(tmp_compliance_jobs):
    """Gate result written to file."""
    from webui.services.compliance_approvalrecord_proposal_gate import evaluate_approvalrecord_proposal_gate

    job_id = "job-008"
    _create_approval_candidates(tmp_compliance_jobs, job_id)
    _create_approval_validation(tmp_compliance_jobs, job_id, "APPROVAL_CANDIDATES_SAFE")

    evaluate_approvalrecord_proposal_gate(job_id, "TestOp", True, tmp_compliance_jobs)

    gate_file = tmp_compliance_jobs / job_id / "approval-candidates" / "approvalrecord-proposal-gate.json"
    assert gate_file.exists()

    with open(gate_file, "r") as f:
        file_data = json.load(f)

    assert file_data["decision"] == "APPROVALRECORD_PROPOSAL_READY"


def test_gate_markdown_written(tmp_compliance_jobs):
    """Gate markdown written."""
    from webui.services.compliance_approvalrecord_proposal_gate import evaluate_approvalrecord_proposal_gate

    job_id = "job-009"
    _create_approval_candidates(tmp_compliance_jobs, job_id)
    _create_approval_validation(tmp_compliance_jobs, job_id, "APPROVAL_CANDIDATES_SAFE")

    evaluate_approvalrecord_proposal_gate(job_id, "TestOp", True, tmp_compliance_jobs)

    md_file = tmp_compliance_jobs / job_id / "approval-candidates" / "APPROVALRECORD-PROPOSAL-GATE.md"
    assert md_file.exists()

    with open(md_file, "r") as f:
        md_content = f.read()

    assert "ApprovalRecord Proposal Gate" in md_content


def test_gate_does_not_create_approval_record(tmp_compliance_jobs):
    """Gate does NOT create ApprovalRecord."""
    from webui.services.compliance_approvalrecord_proposal_gate import evaluate_approvalrecord_proposal_gate

    job_id = "job-010"
    _create_approval_candidates(tmp_compliance_jobs, job_id)
    _create_approval_validation(tmp_compliance_jobs, job_id, "APPROVAL_CANDIDATES_SAFE")

    evaluate_approvalrecord_proposal_gate(job_id, "TestOp", True, tmp_compliance_jobs)

    approval_dir = tmp_compliance_jobs / job_id / "approvals"
    assert not approval_dir.exists()


def test_gate_candidate_count(tmp_compliance_jobs):
    """Gate tracks candidate count."""
    from webui.services.compliance_approvalrecord_proposal_gate import evaluate_approvalrecord_proposal_gate

    job_id = "job-011"
    _create_approval_candidates(tmp_compliance_jobs, job_id, count=3)
    _create_approval_validation(tmp_compliance_jobs, job_id, "APPROVAL_CANDIDATES_SAFE")

    result = evaluate_approvalrecord_proposal_gate(job_id, "TestOp", True, tmp_compliance_jobs)

    assert result["candidate_count"] == 3
