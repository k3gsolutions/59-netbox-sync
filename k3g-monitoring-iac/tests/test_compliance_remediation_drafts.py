"""Tests for local remediation draft generation."""

from __future__ import annotations

import asyncio
import json
import sys
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_compliance_findings_review import _prepare_compare_artifacts, LocalHttpClient
from webui.services.compliance_findings_review import (
    evaluate_remediation_draft_eligibility,
    load_findings,
    save_finding_decision,
)
from webui.services.compliance_remediation_drafts import (
    generate_remediation_drafts,
    load_remediation_drafts,
    load_remediation_eligible_findings,
    summarize_remediation_drafts,
)


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


@contextmanager
def _patch_job_bases(jobs_base: Path):
    with ExitStack() as stack:
        stack.enter_context(patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base))
        stack.enter_context(patch("webui.services.compliance_findings_review.JOBS_BASE", jobs_base))
        stack.enter_context(patch("webui.services.compliance_remediation_drafts.JOBS_BASE", jobs_base))
        yield


def _prepare_eligible_job(client: LocalHttpClient, jobs_base: Path, monkeypatch) -> dict:
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    findings = load_findings(job["job_id"], jobs_base)
    assert findings

    first = findings[0]
    save_finding_decision(
        job["job_id"],
        first["finding_id"],
        {"reviewer": "Keslley", "reason": "Needs local remediation", "decision": "needs_remediation"},
        jobs_base,
    )
    if len(findings) > 1:
        save_finding_decision(
            job["job_id"],
            findings[1]["finding_id"],
            {"reviewer": "Keslley", "reason": "False positive", "decision": "false_positive"},
            jobs_base,
        )
    evaluate_remediation_draft_eligibility(job["job_id"], jobs_base)
    return job


def test_generate_drafts_blocks_without_eligibility(client, jobs_base, monkeypatch):
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)

    with _patch_job_bases(jobs_base):
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/remediation/drafts",
            json={"operator": "Keslley", "confirm_generate_drafts": True},
        )

    assert response.status_code == 409
    assert "eligibility" in response.json()["error"]


def test_generate_drafts_for_needs_remediation(client, jobs_base, monkeypatch):
    job = _prepare_eligible_job(client, jobs_base, monkeypatch)

    with _patch_job_bases(jobs_base):
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/remediation/drafts",
            json={"operator": "Keslley", "confirm_generate_drafts": True},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "REMEDIATION_DRAFTS_GENERATED"
    assert data["draft_count"] >= 1
    assert data["safety"]["netbox_write"] is False
    assert data["safety"]["device_write"] is False

    drafts_file = jobs_base / job["job_id"] / "remediation" / "drafts" / "remediation-drafts.json"
    md_file = jobs_base / job["job_id"] / "remediation" / "drafts" / "REMEDIATION-DRAFTS.md"
    assert drafts_file.exists()
    assert md_file.exists()

    loaded = load_remediation_drafts(job["job_id"], jobs_base)
    assert loaded["status"] == "REMEDIATION_DRAFTS_GENERATED"
    assert len(loaded["drafts"]) == data["draft_count"]


def test_false_positive_not_generated(client, jobs_base, monkeypatch):
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    findings = load_findings(job["job_id"], jobs_base)
    assert len(findings) >= 2

    save_finding_decision(
        job["job_id"],
        findings[0]["finding_id"],
        {"reviewer": "Keslley", "reason": "false positive", "decision": "false_positive"},
        jobs_base,
    )
    save_finding_decision(
        job["job_id"],
        findings[1]["finding_id"],
        {"reviewer": "Keslley", "reason": "needs remediation", "decision": "needs_remediation"},
        jobs_base,
    )
    evaluate_remediation_draft_eligibility(job["job_id"], jobs_base)

    with _patch_job_bases(jobs_base):
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/remediation/drafts",
            json={"operator": "Keslley", "confirm_generate_drafts": True},
        )

    assert response.status_code == 200
    drafts = response.json()["drafts"]
    draft_finding_ids = {draft["finding_id"] for draft in drafts}
    assert findings[0]["finding_id"] not in draft_finding_ids
    assert findings[1]["finding_id"] in draft_finding_ids


def test_draft_write_and_execution_flags_false(client, jobs_base, monkeypatch):
    job = _prepare_eligible_job(client, jobs_base, monkeypatch)

    with _patch_job_bases(jobs_base):
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/remediation/drafts",
            json={"operator": "Keslley", "confirm_generate_drafts": True},
        )

    draft = response.json()["drafts"][0]
    assert draft["write_allowed"] is False
    assert draft["execution_allowed"] is False
    assert draft["requires_approval"] is True
    assert draft["requires_apply_plan"] is False
    assert draft["safety"]["netbox_write"] is False
    assert draft["safety"]["device_write"] is False


def test_drafts_do_not_create_approval_or_apply_plan(client, jobs_base, monkeypatch):
    job = _prepare_eligible_job(client, jobs_base, monkeypatch)

    with _patch_job_bases(jobs_base):
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/remediation/drafts",
            json={"operator": "Keslley", "confirm_generate_drafts": True},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["safety"]["approval_record_created"] is False
    assert payload["safety"]["apply_plan_created"] is False

    body = json.dumps(payload).lower()
    assert "approvalrecord" not in body
    assert "applyplan" not in body


def test_drafts_do_not_write_or_execute(client, jobs_base, monkeypatch):
    job = _prepare_eligible_job(client, jobs_base, monkeypatch)

    with _patch_job_bases(jobs_base):
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/remediation/drafts",
            json={"operator": "Keslley", "confirm_generate_drafts": True},
        )

    payload = response.json()
    assert payload["safety"]["netbox_write"] is False
    assert payload["safety"]["device_write"] is False
    assert payload["safety"]["sync_called"] is False
    assert "ssh" not in json.dumps(payload).lower()
    assert "snmp" not in json.dumps(payload).lower()
    assert "netconf" not in json.dumps(payload).lower()


def test_load_eligible_findings_only_needs_remediation(client, jobs_base, monkeypatch):
    job = _prepare_eligible_job(client, jobs_base, monkeypatch)
    eligible = load_remediation_eligible_findings(job["job_id"], jobs_base)
    assert eligible
    assert all(item["review_decision"]["decision"] == "needs_remediation" for item in eligible)


def test_summarize_remediation_drafts_empty_when_missing(client, jobs_base, monkeypatch):
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    summary = summarize_remediation_drafts(job["job_id"], jobs_base)
    assert summary["total_drafts"] == 0
    assert summary["safety"]["netbox_write"] is False
