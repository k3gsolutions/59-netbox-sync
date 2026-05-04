"""Tests for review audit trail (FASES REVIEW-003)."""

from __future__ import annotations

import json
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


def test_post_decision_creates_audit_file(client, jobs_base, monkeypatch):
    """POST /findings/{finding_id}/decision creates audit file."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    # Load findings to get a finding_id
    from webui.services.compliance_findings_review import load_findings

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base):
        findings = load_findings(job_id, jobs_base)

    if not findings:
        pytest.skip("No findings")

    finding_id = findings[0]["finding_id"]

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_findings_review.JOBS_BASE", jobs_base
    ):
        response = client.post(
            f"/compliance/jobs/{job_id}/findings/{finding_id}/decision",
            json={"reviewer": "Keslley", "reason": "Test reason", "decision": "accepted"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"]

    # Check audit file exists
    job_dir = jobs_base / job_id
    audit_dir = job_dir / "review" / "audit"
    audit_files = list(audit_dir.glob(f"{finding_id}-*.json")) if audit_dir.exists() else []
    assert len(audit_files) > 0


def test_get_review_summary(client, jobs_base, monkeypatch):
    """GET /findings/review-summary returns correct counts."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_findings_review.JOBS_BASE", jobs_base
    ):
        response = client.get(f"/compliance/jobs/{job_id}/findings/review-summary")

    assert response.status_code == 200
    data = response.json()
    assert data["success"]
    assert "total_findings" in data
    assert "reviewed" in data
    assert "pending" in data


def test_review_summary_after_decisions(client, jobs_base, monkeypatch):
    """Review summary updates after recording decisions."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    from webui.services.compliance_findings_review import load_findings

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base):
        findings = load_findings(job_id, jobs_base)

    if len(findings) < 2:
        pytest.skip("Need at least 2 findings")

    # Post first decision
    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_findings_review.JOBS_BASE", jobs_base
    ):
        client.post(
            f"/compliance/jobs/{job_id}/findings/{findings[0]['finding_id']}/decision",
            json={"reviewer": "K", "reason": "R", "decision": "accepted"},
        )

    # Check summary
    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_findings_review.JOBS_BASE", jobs_base
    ):
        response = client.get(f"/compliance/jobs/{job_id}/findings/review-summary")

    data = response.json()
    assert data["reviewed"] == 1
    assert data["pending"] == len(findings) - 1


def test_decision_invalid_reviewer_returns_400(client, jobs_base, monkeypatch):
    """POST decision with missing reviewer returns 400."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    from webui.services.compliance_findings_review import load_findings

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base):
        findings = load_findings(job_id, jobs_base)

    if not findings:
        pytest.skip("No findings")

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_findings_review.JOBS_BASE", jobs_base
    ):
        response = client.post(
            f"/compliance/jobs/{job_id}/findings/{findings[0]['finding_id']}/decision",
            json={"reason": "R", "decision": "accepted"},  # missing reviewer
        )

    assert response.status_code == 400
    data = response.json()
    assert not data["success"]


def test_decision_nonexistent_finding_returns_404(client, jobs_base, monkeypatch):
    """POST decision for non-existent finding returns 404."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_findings_review.JOBS_BASE", jobs_base
    ):
        response = client.post(
            f"/compliance/jobs/{job_id}/findings/CMP-NONEXISTENT/decision",
            json={"reviewer": "K", "reason": "R", "decision": "accepted"},
        )

    assert response.status_code == 404


def test_decision_response_includes_safety(client, jobs_base, monkeypatch):
    """POST decision response includes safety block."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    from webui.services.compliance_findings_review import load_findings

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base):
        findings = load_findings(job_id, jobs_base)

    if not findings:
        pytest.skip("No findings")

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_findings_review.JOBS_BASE", jobs_base
    ):
        response = client.post(
            f"/compliance/jobs/{job_id}/findings/{findings[0]['finding_id']}/decision",
            json={"reviewer": "K", "reason": "R", "decision": "accepted"},
        )

    data = response.json()
    assert "safety" in data
    assert data["safety"]["netbox_write"] is False
    assert data["safety"]["approval_record_created"] is False


def test_review_summary_safety_block(client, jobs_base, monkeypatch):
    """Review summary response includes safety block."""
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    job_id = job["job_id"]

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_findings_review.JOBS_BASE", jobs_base
    ):
        response = client.get(f"/compliance/jobs/{job_id}/findings/review-summary")

    data = response.json()
    assert "safety" in data
    assert data["safety"]["netbox_write"] is False
    assert data["safety"]["sync_called"] is False
