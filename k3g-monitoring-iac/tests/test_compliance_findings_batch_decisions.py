"""Tests for batch finding decision workflow."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from webui.services.compliance_findings_review import (
    batch_save_decisions,
    generate_next_verification_input,
    load_findings,
    save_finding_decision,
)


@pytest.fixture
def tmp_job_with_findings():
    """Create temp job directory with mock findings."""
    with TemporaryDirectory() as tmp:
        job_id = "test-batch-job-001"
        job_dir = Path(tmp) / job_id
        job_dir.mkdir()

        # Create comparison findings
        comparison_dir = job_dir / "comparison" / "devices" / "1234"
        comparison_dir.mkdir(parents=True)

        findings_data = {
            "findings": [
                {
                    "finding_id": "CMP-001",
                    "rule_id": "bgp.peer.state.not_established",
                    "severity": "error",
                    "scope": "bgp",
                    "object_name": "172.28.1.74",
                    "title": "BGP peer state not ESTABLISHED",
                    "recommendation": "Verify peer connectivity",
                    "triage_bucket": "needs_human_review",
                },
                {
                    "finding_id": "CMP-002",
                    "rule_id": "bgp.peer.description.required",
                    "severity": "error",
                    "scope": "bgp",
                    "object_name": "172.28.1.75",
                    "title": "BGP peer missing description",
                    "recommendation": "Add peer description",
                    "triage_bucket": "remediation_candidate",
                },
                {
                    "finding_id": "CMP-003",
                    "rule_id": "interface.naming.invalid",
                    "severity": "warning",
                    "scope": "interface",
                    "object_name": "Eth-Trunk0",
                    "title": "Interface naming invalid",
                    "recommendation": "Update naming",
                    "triage_bucket": "likely_policy_too_strict",
                },
            ]
        }
        findings_file = comparison_dir / "compliance-findings.json"
        findings_file.write_text(json.dumps(findings_data, indent=2))

        yield Path(tmp), job_id, job_dir


def test_batch_requires_reviewer(tmp_job_with_findings):
    """batch_save_decisions with empty reviewer returns error."""
    tmp_path, job_id, _ = tmp_job_with_findings

    result = batch_save_decisions(
        job_id,
        "",  # empty reviewer
        [{"finding_id": "CMP-001", "decision": "needs_remediation", "reason": "test"}],
        jobs_base=tmp_path,
    )

    assert result["success"] is False
    assert "reviewer" in result["error"]


def test_batch_requires_reason(tmp_job_with_findings):
    """batch_save_decisions skips items without reason."""
    tmp_path, job_id, _ = tmp_job_with_findings

    result = batch_save_decisions(
        job_id,
        "Keslley",
        [
            {"finding_id": "CMP-001", "decision": "needs_remediation", "reason": ""},  # empty reason
        ],
        jobs_base=tmp_path,
    )

    assert result["success"] is True
    assert result["saved_count"] == 0
    assert result["failed_count"] == 1


def test_batch_saves_finding_decisions_json(tmp_job_with_findings):
    """batch_save_decisions creates finding-decisions.json."""
    tmp_path, job_id, job_dir = tmp_job_with_findings

    result = batch_save_decisions(
        job_id,
        "Keslley",
        [
            {
                "finding_id": "CMP-001",
                "decision": "needs_remediation",
                "reason": "Peer down, needs investigation",
            },
            {
                "finding_id": "CMP-002",
                "decision": "needs_remediation",
                "reason": "Missing description",
            },
        ],
        jobs_base=tmp_path,
    )

    assert result["success"] is True
    assert result["saved_count"] == 2

    # Check finding-decisions.json exists
    decisions_file = job_dir / "review" / "finding-decisions.json"
    assert decisions_file.exists()

    decisions_data = json.loads(decisions_file.read_text())
    assert "decisions" in decisions_data
    assert "CMP-001" in decisions_data["decisions"]
    assert "CMP-002" in decisions_data["decisions"]
    assert decisions_data["decisions"]["CMP-001"]["decision"] == "needs_remediation"


def test_batch_creates_audit_files(tmp_job_with_findings):
    """batch_save_decisions creates audit files."""
    tmp_path, job_id, job_dir = tmp_job_with_findings

    result = batch_save_decisions(
        job_id,
        "Keslley",
        [{"finding_id": "CMP-001", "decision": "false_positive", "reason": "Parser noise"}],
        jobs_base=tmp_path,
    )

    assert result["success"] is True

    # Check audit directory exists and has file
    audit_dir = job_dir / "review" / "audit"
    assert audit_dir.exists()
    audit_files = list(audit_dir.glob("*.json"))
    assert len(audit_files) > 0


def test_batch_creates_next_verification_input(tmp_job_with_findings):
    """batch_save_decisions creates next-verification-input.json."""
    tmp_path, job_id, job_dir = tmp_job_with_findings

    result = batch_save_decisions(
        job_id,
        "Keslley",
        [
            {
                "finding_id": "CMP-001",
                "decision": "needs_remediation",
                "reason": "Needs fixing",
            },
            {
                "finding_id": "CMP-002",
                "decision": "false_positive",
                "reason": "Not a real issue",
            },
        ],
        jobs_base=tmp_path,
    )

    assert result["success"] is True

    # Check next-verification-input.json exists
    next_input_file = job_dir / "review" / "next-verification-input.json"
    assert next_input_file.exists()

    next_input = json.loads(next_input_file.read_text())
    assert next_input["job_id"] == job_id
    assert next_input["status"] == "USER_VALIDATION_APPLIED"


def test_batch_response_humanized_summary(tmp_job_with_findings):
    """batch_save_decisions response contains humanized summary."""
    tmp_path, job_id, _ = tmp_job_with_findings

    result = batch_save_decisions(
        job_id,
        "Keslley",
        [
            {
                "finding_id": "CMP-001",
                "decision": "needs_remediation",
                "reason": "Fix needed",
            },
            {
                "finding_id": "CMP-002",
                "decision": "needs_more_evidence",
                "reason": "Investigate more",
            },
            {
                "finding_id": "CMP-003",
                "decision": "false_positive",
                "reason": "False alarm",
            },
        ],
        jobs_base=tmp_path,
    )

    assert result["success"] is True
    assert "summary" in result
    assert result["summary"]["precisa_corrigir"] == 1
    assert result["summary"]["precisa_investigar"] == 1
    assert result["summary"]["falsos_positivos"] == 1


def test_batch_safety_block(tmp_job_with_findings):
    """batch_save_decisions response safety block has all false."""
    tmp_path, job_id, _ = tmp_job_with_findings

    result = batch_save_decisions(
        job_id,
        "Keslley",
        [
            {
                "finding_id": "CMP-001",
                "decision": "needs_remediation",
                "reason": "Fix it",
            },
        ],
        jobs_base=tmp_path,
    )

    assert result["success"] is True
    assert result["safety"]["netbox_write"] is False
    assert result["safety"]["device_connection"] is False
    assert result["safety"]["sync_called"] is False
    assert result["safety"]["approval_record_created"] is False
    assert result["safety"]["apply_plan_created"] is False


def test_generate_next_verification_input_checks_gates(tmp_job_with_findings):
    """generate_next_verification_input checks next_phase_allowed gates."""
    tmp_path, job_id, job_dir = tmp_job_with_findings

    # Create review/finding-decisions.json with blocked item
    review_dir = job_dir / "review"
    review_dir.mkdir()

    decisions = {
        "decisions": {
            "CMP-001": {
                "finding_id": "CMP-001",
                "decision": "blocked",
                "reason": "Waiting for upstream",
                "status": "blocked",
            },
            "CMP-002": {
                "finding_id": "CMP-002",
                "decision": "needs_remediation",
                "reason": "Fix needed",
                "status": "remediation_candidate",
            },
        }
    }
    (review_dir / "finding-decisions.json").write_text(json.dumps(decisions))

    result = generate_next_verification_input(job_id, jobs_base=tmp_path)

    # Blocked items should prevent next phase
    assert result["next_phase_allowed"] is False
    assert "CMP-001" in result["blocked_items"]


def test_next_phase_allowed_when_conditions_met(tmp_job_with_findings):
    """generate_next_verification_input allows next phase when gates pass."""
    tmp_path, job_id, job_dir = tmp_job_with_findings

    review_dir = job_dir / "review"
    review_dir.mkdir()

    # All errors reviewed, no blocked, at least one needs_remediation
    decisions = {
        "decisions": {
            "CMP-001": {
                "finding_id": "CMP-001",
                "decision": "needs_remediation",
                "reason": "Fix needed",
                "status": "remediation_candidate",
            },
            "CMP-002": {
                "finding_id": "CMP-002",
                "decision": "false_positive",
                "reason": "Not real",
                "status": "dismissed",
            },
            "CMP-003": {
                "finding_id": "CMP-003",
                "decision": "ignored_temporarily",
                "reason": "Later",
                "status": "deferred",
            },
        }
    }
    (review_dir / "finding-decisions.json").write_text(json.dumps(decisions))

    result = generate_next_verification_input(job_id, jobs_base=tmp_path)

    # No blocked, has remediation candidates, all errors reviewed
    assert result["next_phase_allowed"] is True
    assert result["next_phase"] == "remediation_draft_eligibility"


def test_next_verification_input_safety(tmp_job_with_findings):
    """next-verification-input.json has safety block with all false."""
    tmp_path, job_id, job_dir = tmp_job_with_findings

    result = generate_next_verification_input(job_id, jobs_base=tmp_path)

    assert result["safety"]["netbox_write"] is False
    assert result["safety"]["device_write"] is False
    assert result["safety"]["sync_called"] is False
    assert result["safety"]["approval_record_created"] is False
    assert result["safety"]["apply_plan_created"] is False

    # Also check the written JSON
    next_input_file = job_dir / "review" / "next-verification-input.json"
    next_input = json.loads(next_input_file.read_text())
    assert next_input["safety"]["netbox_write"] is False
