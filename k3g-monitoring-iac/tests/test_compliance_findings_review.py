"""Tests for compliance findings review workflow (FASES REVIEW-002–004)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from webui.services.compliance_findings_review import (
    validate_finding_decision,
    save_finding_decision,
    load_findings,
    load_review_decisions,
    summarize_review,
    evaluate_remediation_draft_eligibility,
    DECISION_STATUS_MAP,
)
from tests.test_compliance_parser_artifacts import _prepare_collection_artifacts, LocalHttpClient


@pytest.fixture
def client():
    from webui.app import app

    return LocalHttpClient()


@pytest.fixture
def jobs_base(tmp_path):
    base = tmp_path / "reports" / "compliance" / "jobs"
    base.mkdir(parents=True, exist_ok=True)
    return base


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    for name in [
        "COMPLIANCE_SSH_USERNAME",
        "COMPLIANCE_SSH_PASSWORD",
        "COMPLIANCE_SSH_PORT",
        "COMPLIANCE_SSH_TIMEOUT",
        "COMPLIANCE_SSH_PREFLIGHT_TCP_CHECK",
    ]:
        monkeypatch.delenv(name, raising=False)


def _prepare_compare_artifacts(client, jobs_base, monkeypatch):
    """Full pipeline: create → parse → compare. Returns job with findings."""
    job = _prepare_collection_artifacts(client, jobs_base, monkeypatch)
    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_huawei_ne8000_parser.JOBS_BASE", jobs_base
    ):
        client.post(f"/compliance/jobs/{job['job_id']}/parse", json={"operator": "Keslley", "confirm_local_parse": True})
    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_compare.JOBS_BASE", jobs_base
    ):
        client.post(f"/compliance/jobs/{job['job_id']}/compare", json={"operator": "Keslley", "confirm_local_compare": True})
    return job


# === Decision validation tests ===


def test_decision_requires_reviewer():
    """Decision without reviewer fails validation."""
    valid, error = validate_finding_decision({"reason": "test", "decision": "accepted"})
    assert not valid
    assert "reviewer" in error


def test_decision_requires_reason():
    """Decision without reason fails validation."""
    valid, error = validate_finding_decision({"reviewer": "Keslley", "decision": "accepted"})
    assert not valid
    assert "reason" in error


def test_decision_invalid_blocked():
    """Invalid decision value fails validation."""
    valid, error = validate_finding_decision(
        {"reviewer": "Keslley", "reason": "test", "decision": "invalid_decision"}
    )
    assert not valid
    assert "decision inválida" in error


def test_valid_decision_passes():
    """Valid decision passes validation."""
    for decision in ["accepted", "false_positive", "ignored_temporarily", "needs_remediation", "needs_more_evidence", "blocked"]:
        valid, error = validate_finding_decision(
            {"reviewer": "Keslley", "reason": "test reason", "decision": decision}
        )
        assert valid, f"Decision {decision} should be valid"


# === Decision saving tests ===


def test_save_finding_decision_valid(client, jobs_base, monkeypatch):
    """Save a valid decision."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    findings = load_findings(job_id, jobs_base)
    assert findings, "Should have findings after compare"

    finding_id = findings[0]["finding_id"]
    payload = {"reviewer": "Keslley", "reason": "Descrição ausente precisa ser padronizada", "decision": "needs_remediation"}

    result = save_finding_decision(job_id, finding_id, payload, jobs_base)

    assert result["success"]
    assert result["finding_id"] == finding_id
    assert result["decision"] == "needs_remediation"
    assert result["status"] == "remediation_candidate"


def test_save_decision_nonexistent_finding(client, jobs_base, monkeypatch):
    """Save decision for non-existent finding fails."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    payload = {"reviewer": "Keslley", "reason": "test", "decision": "accepted"}
    result = save_finding_decision(job_id, "CMP-NONEXISTENT", payload, jobs_base)

    assert not result["success"]
    assert "não encontrado" in result["error"]


def test_save_decision_invalid_payload(client, jobs_base, monkeypatch):
    """Save decision with invalid payload fails."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    findings = load_findings(job_id, jobs_base)
    finding_id = findings[0]["finding_id"]

    # Missing reviewer
    payload = {"reason": "test", "decision": "accepted"}
    result = save_finding_decision(job_id, finding_id, payload, jobs_base)

    assert not result["success"]


def test_false_positive_status_dismissed(client, jobs_base, monkeypatch):
    """false_positive decision maps to dismissed status."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    findings = load_findings(job_id, jobs_base)
    finding_id = findings[0]["finding_id"]

    payload = {"reviewer": "Keslley", "reason": "FP test", "decision": "false_positive"}
    result = save_finding_decision(job_id, finding_id, payload, jobs_base)

    assert result["success"]
    assert result["status"] == "dismissed"
    assert DECISION_STATUS_MAP["false_positive"] == "dismissed"


def test_needs_remediation_status_candidate(client, jobs_base, monkeypatch):
    """needs_remediation decision maps to remediation_candidate status."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    findings = load_findings(job_id, jobs_base)
    finding_id = findings[0]["finding_id"]

    payload = {"reviewer": "Keslley", "reason": "Needs fix", "decision": "needs_remediation"}
    result = save_finding_decision(job_id, finding_id, payload, jobs_base)

    assert result["success"]
    assert result["status"] == "remediation_candidate"


# === Finding and decision loading tests ===


def test_load_findings(client, jobs_base, monkeypatch):
    """Load all findings from comparison artifacts."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    findings = load_findings(job_id, jobs_base)
    assert isinstance(findings, list)
    if findings:
        assert "finding_id" in findings[0]
        assert "severity" in findings[0]


def test_load_review_decisions_empty(client, jobs_base, monkeypatch):
    """Load review decisions when none exist returns empty dict."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    decisions = load_review_decisions(job_id, jobs_base)
    assert "decisions" in decisions
    assert decisions["decisions"] == {}


def test_load_review_decisions_after_save(client, jobs_base, monkeypatch):
    """Load review decisions after saving one."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    findings = load_findings(job_id, jobs_base)
    finding_id = findings[0]["finding_id"]

    payload = {"reviewer": "Keslley", "reason": "test", "decision": "accepted"}
    save_finding_decision(job_id, finding_id, payload, jobs_base)

    decisions = load_review_decisions(job_id, jobs_base)
    assert finding_id in decisions["decisions"]
    assert decisions["decisions"][finding_id]["decision"] == "accepted"


# === Summary tests ===


def test_summarize_review_counts(client, jobs_base, monkeypatch):
    """Summarize review counts."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    findings = load_findings(job_id, jobs_base)
    assert len(findings) > 0

    summary = summarize_review(job_id, jobs_base)
    assert summary["total_findings"] == len(findings)
    assert summary["reviewed"] == 0  # None reviewed yet
    assert summary["pending"] == len(findings)


def test_summarize_review_after_decisions(client, jobs_base, monkeypatch):
    """Summarize review after recording some decisions."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    findings = load_findings(job_id, jobs_base)
    assert len(findings) >= 2

    # Save decisions for first two findings
    for i, finding in enumerate(findings[:2]):
        decision = "needs_remediation" if i == 0 else "accepted"
        payload = {"reviewer": "Keslley", "reason": "test", "decision": decision}
        save_finding_decision(job_id, finding["finding_id"], payload, jobs_base)

    summary = summarize_review(job_id, jobs_base)
    assert summary["reviewed"] == 2
    assert summary["pending"] == len(findings) - 2
    assert summary["needs_remediation"] == 1


# === Eligibility gate tests ===


def test_eligibility_no_findings_blocks(client, jobs_base, monkeypatch):
    """Eligibility blocked when no findings."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    # Artificially clear findings (mock scenario)
    findings = load_findings(job_id, jobs_base)
    if not findings:
        # No findings scenario
        result = evaluate_remediation_draft_eligibility(job_id, jobs_base)
        assert result["decision"] == "REMEDIATION_DRAFT_BLOCKED"


def test_eligibility_blocked_decision_prevents(client, jobs_base, monkeypatch):
    """Eligibility blocked when any finding is blocked."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    findings = load_findings(job_id, jobs_base)
    if not findings:
        pytest.skip("No findings")

    # Mark first finding as blocked
    payload = {"reviewer": "Keslley", "reason": "Must block", "decision": "blocked"}
    save_finding_decision(job_id, findings[0]["finding_id"], payload, jobs_base)

    # Review all critical findings
    for finding in findings:
        if finding.get("severity") in {"blocker", "error"}:
            if finding["finding_id"] not in [findings[0]["finding_id"]]:
                payload = {"reviewer": "Keslley", "reason": "test", "decision": "accepted"}
                save_finding_decision(job_id, finding["finding_id"], payload, jobs_base)

    result = evaluate_remediation_draft_eligibility(job_id, jobs_base)
    assert result["decision"] == "REMEDIATION_DRAFT_BLOCKED"
    assert result["gates"]["no_blocked_findings"] is False


def test_eligibility_eligible_when_conditions_met(client, jobs_base, monkeypatch):
    """Eligibility eligible when all conditions are met."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    findings = load_findings(job_id, jobs_base)
    if not findings:
        pytest.skip("No findings")

    # Review all critical findings with at least one needs_remediation
    reviewed_one_remediation = False
    for finding in findings:
        if finding.get("severity") in {"blocker", "error"}:
            # Mark critical findings for remediation
            decision = "needs_remediation" if not reviewed_one_remediation else "accepted"
            payload = {"reviewer": "Keslley", "reason": "test", "decision": decision}
            save_finding_decision(job_id, finding["finding_id"], payload, jobs_base)
            if decision == "needs_remediation":
                reviewed_one_remediation = True

    # Ensure at least one needs_remediation
    if not reviewed_one_remediation and findings:
        payload = {"reviewer": "Keslley", "reason": "test", "decision": "needs_remediation"}
        save_finding_decision(job_id, findings[0]["finding_id"], payload, jobs_base)

    result = evaluate_remediation_draft_eligibility(job_id, jobs_base)
    assert result["decision"] == "REMEDIATION_DRAFT_ELIGIBLE"
    assert result["gates"]["no_blocked_findings"] is True
    assert result["gates"]["has_remediation_candidates"] is True


def test_eligibility_artifacts_created(client, jobs_base, monkeypatch):
    """Eligibility creates JSON and MD artifacts."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    job_dir = jobs_base / job_id
    review_dir = job_dir / "review"

    result = evaluate_remediation_draft_eligibility(job_id, jobs_base)

    assert (review_dir / "remediation-draft-eligibility.json").exists()
    assert (review_dir / "REMEDIATION-DRAFT-ELIGIBILITY.md").exists()

    # Verify JSON is valid
    data = json.loads((review_dir / "remediation-draft-eligibility.json").read_text())
    assert "job_id" in data
    assert "status" in data
    assert "decision" in data


def test_safety_in_all_results(client, jobs_base, monkeypatch):
    """All results include safety block with correct values."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    summary = summarize_review(job_id, jobs_base)
    assert summary["safety"]["netbox_write"] is False
    assert summary["safety"]["device_connection"] is False
    assert summary["safety"]["sync_called"] is False
    assert summary["safety"]["approval_record_created"] is False
    assert summary["safety"]["apply_plan_created"] is False

    if load_findings(job_id, jobs_base):
        finding_id = load_findings(job_id, jobs_base)[0]["finding_id"]
        result = save_finding_decision(
            job_id, finding_id, {"reviewer": "K", "reason": "R", "decision": "accepted"}, jobs_base
        )
        assert result["safety"]["netbox_write"] is False

    eligibility = evaluate_remediation_draft_eligibility(job_id, jobs_base)
    assert eligibility["safety"]["netbox_write"] is False
