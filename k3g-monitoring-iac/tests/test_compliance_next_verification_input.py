"""Tests for next-verification-input.json artifact."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from webui.services.compliance_findings_review import (
    batch_save_decisions,
    generate_next_verification_input,
)


@pytest.fixture
def tmp_job_with_findings():
    """Create temp job directory with mock findings."""
    with TemporaryDirectory() as tmp:
        job_id = "test-next-input-job"
        job_dir = Path(tmp) / job_id
        job_dir.mkdir()

        # Create comparison findings
        comparison_dir = job_dir / "comparison" / "devices" / "5678"
        comparison_dir.mkdir(parents=True)

        findings_data = {
            "findings": [
                {
                    "finding_id": "CMP-A",
                    "severity": "error",
                    "scope": "bgp",
                    "object_name": "peer1",
                },
                {
                    "finding_id": "CMP-B",
                    "severity": "error",
                    "scope": "bgp",
                    "object_name": "peer2",
                },
                {
                    "finding_id": "CMP-C",
                    "severity": "warning",
                    "scope": "interface",
                    "object_name": "eth0",
                },
            ]
        }
        findings_file = comparison_dir / "compliance-findings.json"
        findings_file.write_text(json.dumps(findings_data))

        yield Path(tmp), job_id, job_dir


def test_needs_remediation_in_next_phase(tmp_job_with_findings):
    """needs_remediation decisions go into items_for_next_phase."""
    tmp_path, job_id, job_dir = tmp_job_with_findings

    batch_save_decisions(
        job_id,
        "Keslley",
        [
            {
                "finding_id": "CMP-A",
                "decision": "needs_remediation",
                "reason": "Fix this",
            },
            {
                "finding_id": "CMP-B",
                "decision": "needs_remediation",
                "reason": "Fix that",
            },
        ],
        jobs_base=tmp_path,
    )

    next_input_file = job_dir / "review" / "next-verification-input.json"
    next_input = json.loads(next_input_file.read_text())

    assert "CMP-A" in next_input["items_for_next_phase"]
    assert "CMP-B" in next_input["items_for_next_phase"]
    assert next_input["summary"]["needs_remediation"] == 2


def test_false_positive_not_in_next_phase(tmp_job_with_findings):
    """false_positive decisions do NOT go into items_for_next_phase."""
    tmp_path, job_id, job_dir = tmp_job_with_findings

    batch_save_decisions(
        job_id,
        "Keslley",
        [
            {
                "finding_id": "CMP-A",
                "decision": "false_positive",
                "reason": "Not real",
            },
            {
                "finding_id": "CMP-B",
                "decision": "needs_remediation",
                "reason": "Real issue",
            },
        ],
        jobs_base=tmp_path,
    )

    next_input_file = job_dir / "review" / "next-verification-input.json"
    next_input = json.loads(next_input_file.read_text())

    assert "CMP-A" not in next_input["items_for_next_phase"]
    assert "CMP-B" in next_input["items_for_next_phase"]
    assert next_input["summary"]["false_positive"] == 1


def test_blocked_in_blocked_items(tmp_job_with_findings):
    """blocked decisions go into blocked_items."""
    tmp_path, job_id, job_dir = tmp_job_with_findings

    batch_save_decisions(
        job_id,
        "Keslley",
        [
            {
                "finding_id": "CMP-A",
                "decision": "blocked",
                "reason": "Waiting on upstream",
            },
        ],
        jobs_base=tmp_path,
    )

    next_input_file = job_dir / "review" / "next-verification-input.json"
    next_input = json.loads(next_input_file.read_text())

    assert "CMP-A" in next_input["blocked_items"]
    assert next_input["summary"]["blocked"] == 1


def test_blocked_prevents_next_phase(tmp_job_with_findings):
    """Any blocked item sets next_phase_allowed to false."""
    tmp_path, job_id, job_dir = tmp_job_with_findings

    batch_save_decisions(
        job_id,
        "Keslley",
        [
            {
                "finding_id": "CMP-A",
                "decision": "needs_remediation",
                "reason": "Fix",
            },
            {
                "finding_id": "CMP-B",
                "decision": "blocked",
                "reason": "Blocked",
            },
            {
                "finding_id": "CMP-C",
                "decision": "ignored_temporarily",
                "reason": "Later",
            },
        ],
        jobs_base=tmp_path,
    )

    next_input_file = job_dir / "review" / "next-verification-input.json"
    next_input = json.loads(next_input_file.read_text())

    # Even though we have needs_remediation, blocked prevents progress
    assert next_input["next_phase_allowed"] is False
    assert next_input["next_phase"] is None


def test_next_phase_allowed_conditions(tmp_job_with_findings):
    """next_phase_allowed requires: no blocked + 1+ needs_remediation + all errors reviewed."""
    tmp_path, job_id, job_dir = tmp_job_with_findings

    batch_save_decisions(
        job_id,
        "Keslley",
        [
            {
                "finding_id": "CMP-A",
                "decision": "needs_remediation",
                "reason": "Fix",
            },
            {
                "finding_id": "CMP-B",
                "decision": "false_positive",
                "reason": "Not real",
            },
            {
                "finding_id": "CMP-C",
                "decision": "ignored_temporarily",
                "reason": "Later",
            },
        ],
        jobs_base=tmp_path,
    )

    next_input_file = job_dir / "review" / "next-verification-input.json"
    next_input = json.loads(next_input_file.read_text())

    # All conditions met: no blocked, has needs_remediation, all errors reviewed
    assert next_input["next_phase_allowed"] is True
    assert next_input["next_phase"] == "remediation_draft_eligibility"


def test_needs_more_evidence_in_pending_items(tmp_job_with_findings):
    """needs_more_evidence decisions go into pending_items."""
    tmp_path, job_id, job_dir = tmp_job_with_findings

    batch_save_decisions(
        job_id,
        "Keslley",
        [
            {
                "finding_id": "CMP-A",
                "decision": "needs_more_evidence",
                "reason": "Need more data",
            },
            {
                "finding_id": "CMP-B",
                "decision": "needs_remediation",
                "reason": "Fix",
            },
        ],
        jobs_base=tmp_path,
    )

    next_input_file = job_dir / "review" / "next-verification-input.json"
    next_input = json.loads(next_input_file.read_text())

    assert "CMP-A" in next_input["pending_items"]
    assert "CMP-B" not in next_input["pending_items"]
    assert next_input["summary"]["needs_more_evidence"] == 1


def test_next_verification_input_summary_counts(tmp_job_with_findings):
    """next-verification-input.json summary has correct counts."""
    tmp_path, job_id, job_dir = tmp_job_with_findings

    batch_save_decisions(
        job_id,
        "Keslley",
        [
            {"finding_id": "CMP-A", "decision": "needs_remediation", "reason": "Fix"},
            {"finding_id": "CMP-B", "decision": "needs_more_evidence", "reason": "Investigate"},
            {"finding_id": "CMP-C", "decision": "false_positive", "reason": "Not real"},
        ],
        jobs_base=tmp_path,
    )

    next_input_file = job_dir / "review" / "next-verification-input.json"
    next_input = json.loads(next_input_file.read_text())

    assert next_input["summary"]["total_findings"] == 3
    assert next_input["summary"]["validated"] == 3
    assert next_input["summary"]["pending"] == 0
    assert next_input["summary"]["needs_remediation"] == 1
    assert next_input["summary"]["needs_more_evidence"] == 1
    assert next_input["summary"]["false_positive"] == 1
    assert next_input["summary"]["blocked"] == 0


def test_next_verification_input_markdown_created(tmp_job_with_findings):
    """NEXT-VERIFICATION-INPUT.md file is created."""
    tmp_path, job_id, job_dir = tmp_job_with_findings

    generate_next_verification_input(job_id, jobs_base=tmp_path)

    md_file = job_dir / "review" / "NEXT-VERIFICATION-INPUT.md"
    assert md_file.exists()

    md_content = md_file.read_text()
    assert "NEXT-VERIFICATION-INPUT" in md_content
    assert "Job ID" in md_content
    assert "Status" in md_content


def test_next_verification_input_safety(tmp_job_with_findings):
    """next-verification-input.json safety block is correct."""
    tmp_path, job_id, job_dir = tmp_job_with_findings

    batch_save_decisions(
        job_id,
        "Keslley",
        [
            {
                "finding_id": "CMP-A",
                "decision": "needs_remediation",
                "reason": "Fix",
            },
        ],
        jobs_base=tmp_path,
    )

    next_input_file = job_dir / "review" / "next-verification-input.json"
    next_input = json.loads(next_input_file.read_text())

    assert next_input["safety"]["netbox_write"] is False
    assert next_input["safety"]["device_write"] is False
    assert next_input["safety"]["sync_called"] is False
    assert next_input["safety"]["approval_record_created"] is False
    assert next_input["safety"]["apply_plan_created"] is False
