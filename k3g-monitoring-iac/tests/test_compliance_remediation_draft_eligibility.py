"""Tests for remediation draft eligibility gate (FASES REVIEW-004)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_compliance_parser_artifacts import _prepare_collection_artifacts, LocalHttpClient


@pytest.fixture
def client():
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


def test_eligibility_blocked_without_confirm(client, jobs_base, monkeypatch):
    """POST eligibility without confirm_review_complete=true returns 400."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_findings_review.JOBS_BASE", jobs_base
    ):
        response = client.post(f"/compliance/jobs/{job_id}/remediation/draft-eligibility", json={"confirm_review_complete": False})

    assert response.status_code == 400


def test_eligibility_creates_artifacts(client, jobs_base, monkeypatch):
    """POST eligibility creates JSON and MD artifacts."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_findings_review.JOBS_BASE", jobs_base
    ):
        response = client.post(f"/compliance/jobs/{job_id}/remediation/draft-eligibility", json={"confirm_review_complete": True})

    assert response.status_code in [200, 409]  # OK if eligible, 409 if blocked
    job_dir = jobs_base / job_id
    review_dir = job_dir / "review"
    assert (review_dir / "remediation-draft-eligibility.json").exists()
    assert (review_dir / "REMEDIATION-DRAFT-ELIGIBILITY.md").exists()


def test_eligibility_no_needs_remediation_blocks(client, jobs_base, monkeypatch):
    """POST eligibility returns 409 when no needs_remediation findings."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    from webui.services.compliance_findings_review import load_findings, save_finding_decision

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base):
        findings = load_findings(job_id, jobs_base)

    # Accept all findings (no needs_remediation)
    for finding in findings:
        if finding.get("severity") in {"blocker", "error"}:
            with patch("webui.services.compliance_findings_review.JOBS_BASE", jobs_base):
                save_finding_decision(
                    job_id, finding["finding_id"], {"reviewer": "K", "reason": "R", "decision": "accepted"}, jobs_base
                )

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_findings_review.JOBS_BASE", jobs_base
    ):
        response = client.post(f"/compliance/jobs/{job_id}/remediation/draft-eligibility", json={"confirm_review_complete": True})

    # Should be blocked because no needs_remediation
    assert response.status_code == 409 or response.json()["decision"] == "REMEDIATION_DRAFT_BLOCKED"


def test_eligibility_blocked_finding_prevents(client, jobs_base, monkeypatch):
    """POST eligibility returns 409 when any finding is blocked."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    from webui.services.compliance_findings_review import load_findings, save_finding_decision

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base):
        findings = load_findings(job_id, jobs_base)

    if not findings:
        pytest.skip("No findings")

    # Block first finding
    with patch("webui.services.compliance_findings_review.JOBS_BASE", jobs_base):
        save_finding_decision(
            job_id, findings[0]["finding_id"], {"reviewer": "K", "reason": "R", "decision": "blocked"}, jobs_base
        )

    # Review critical findings (at least one needs_remediation)
    remediation_recorded = False
    for finding in findings[1:]:
        if finding.get("severity") in {"blocker", "error"}:
            decision = "needs_remediation" if not remediation_recorded else "accepted"
            with patch("webui.services.compliance_findings_review.JOBS_BASE", jobs_base):
                save_finding_decision(
                    job_id, finding["finding_id"], {"reviewer": "K", "reason": "R", "decision": decision}, jobs_base
                )
            remediation_recorded = remediation_recorded or decision == "needs_remediation"

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_findings_review.JOBS_BASE", jobs_base
    ):
        response = client.post(f"/compliance/jobs/{job_id}/remediation/draft-eligibility", json={"confirm_review_complete": True})

    # Should be blocked because of blocked finding
    assert response.status_code == 409
    data = response.json()
    assert data["decision"] == "REMEDIATION_DRAFT_BLOCKED"
    assert data["gates"]["no_blocked_findings"] is False


def test_eligibility_eligible_when_conditions_met(client, jobs_base, monkeypatch):
    """POST eligibility returns 200 ELIGIBLE when conditions are met."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    from webui.services.compliance_findings_review import load_findings, save_finding_decision

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base):
        findings = load_findings(job_id, jobs_base)

    if not findings:
        pytest.skip("No findings")

    # Review critical findings, at least one as needs_remediation
    remediation_recorded = False
    for finding in findings:
        if finding.get("severity") in {"blocker", "error"}:
            decision = "needs_remediation" if not remediation_recorded else "accepted"
            with patch("webui.services.compliance_findings_review.JOBS_BASE", jobs_base):
                save_finding_decision(
                    job_id, finding["finding_id"], {"reviewer": "K", "reason": "R", "decision": decision}, jobs_base
                )
            remediation_recorded = remediation_recorded or decision == "needs_remediation"

    # If no error/blocker findings, mark first as remediation
    if not remediation_recorded and findings:
        with patch("webui.services.compliance_findings_review.JOBS_BASE", jobs_base):
            save_finding_decision(
                job_id, findings[0]["finding_id"], {"reviewer": "K", "reason": "R", "decision": "needs_remediation"}, jobs_base
            )

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_findings_review.JOBS_BASE", jobs_base
    ):
        response = client.post(f"/compliance/jobs/{job_id}/remediation/draft-eligibility", json={"confirm_review_complete": True})

    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "REMEDIATION_DRAFT_ELIGIBLE"


def test_eligibility_response_includes_safety(client, jobs_base, monkeypatch):
    """POST eligibility response includes safety block."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_findings_review.JOBS_BASE", jobs_base
    ):
        response = client.post(f"/compliance/jobs/{job_id}/remediation/draft-eligibility", json={"confirm_review_complete": True})

    data = response.json()
    assert "safety" in data
    assert data["safety"]["netbox_write"] is False
    assert data["safety"]["approval_record_created"] is False
    assert data["safety"]["apply_plan_created"] is False
