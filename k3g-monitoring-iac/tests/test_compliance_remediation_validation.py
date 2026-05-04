"""Tests for remediation draft safety validation."""

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
from webui.services.compliance_remediation_drafts import load_remediation_drafts
from webui.services.compliance_remediation_validation import validate_remediation_drafts


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
        stack.enter_context(patch("webui.services.compliance_remediation_validation.JOBS_BASE", jobs_base))
        yield


def _prepare_and_generate(client: LocalHttpClient, jobs_base: Path, monkeypatch, first_decision: str = "needs_remediation") -> dict:
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    findings = load_findings(job["job_id"], jobs_base)
    assert findings

    save_finding_decision(
        job["job_id"],
        findings[0]["finding_id"],
        {"reviewer": "Keslley", "reason": "review", "decision": first_decision},
        jobs_base,
    )
    if len(findings) > 1:
        save_finding_decision(
            job["job_id"],
            findings[1]["finding_id"],
            {"reviewer": "Keslley", "reason": "skip", "decision": "false_positive"},
            jobs_base,
        )
    evaluate_remediation_draft_eligibility(job["job_id"], jobs_base)

    with _patch_job_bases(jobs_base):
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/remediation/drafts",
            json={"operator": "Keslley", "confirm_generate_drafts": True},
        )
    assert response.status_code == 200
    return job


def _draft_file(jobs_base: Path, job_id: str) -> Path:
    return jobs_base / job_id / "remediation" / "drafts" / "remediation-drafts.json"


def _load_payload(jobs_base: Path, job_id: str) -> dict:
    return json.loads(_draft_file(jobs_base, job_id).read_text(encoding="utf-8"))


def _write_payload(jobs_base: Path, job_id: str, payload: dict) -> None:
    _draft_file(jobs_base, job_id).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def test_validation_blocks_missing_drafts_file(client, jobs_base, monkeypatch):
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)

    with _patch_job_bases(jobs_base):
        response = client.get(f"/compliance/jobs/{job['job_id']}/remediation/drafts/validation")

    assert response.status_code == 409
    assert response.json()["decision"] == "REMEDIATION_DRAFTS_UNSAFE"


@pytest.mark.parametrize(
    "mutation,expected_issue",
    [
        (lambda draft: draft.__setitem__("write_allowed", True), "write_allowed=true"),
        (lambda draft: draft.__setitem__("execution_allowed", True), "execution_allowed=true"),
        (lambda draft: draft.__setitem__("requires_apply_plan", True), "requires_apply_plan=true"),
    ],
)
def test_validation_blocks_write_execution_and_apply_plan_flags(client, jobs_base, monkeypatch, mutation, expected_issue):
    job = _prepare_and_generate(client, jobs_base, monkeypatch)
    payload = _load_payload(jobs_base, job["job_id"])
    mutation(payload["drafts"][0])
    _write_payload(jobs_base, job["job_id"], payload)

    with _patch_job_bases(jobs_base):
        response = client.get(f"/compliance/jobs/{job['job_id']}/remediation/drafts/validation")

    assert response.status_code == 409
    body = response.json()
    assert body["decision"] == "REMEDIATION_DRAFTS_UNSAFE"
    assert any(
        expected_issue in issue for issue in body["remediation_draft_validation"]["issues"]
    )


def test_validation_blocks_forbidden_system_view_command(client, jobs_base, monkeypatch):
    job = _prepare_and_generate(client, jobs_base, monkeypatch)
    payload = _load_payload(jobs_base, job["job_id"])
    payload["drafts"][0]["proposed_change"]["command_preview"] = "system-view"
    _write_payload(jobs_base, job["job_id"], payload)

    with _patch_job_bases(jobs_base):
        response = client.get(f"/compliance/jobs/{job['job_id']}/remediation/drafts/validation")

    assert response.status_code == 409
    assert any(
        "system-view" in issue
        for issue in response.json()["remediation_draft_validation"]["issues"]
    )


def test_validation_blocks_secret_tokens_in_proposed_change(client, jobs_base, monkeypatch):
    job = _prepare_and_generate(client, jobs_base, monkeypatch)
    payload = _load_payload(jobs_base, job["job_id"])
    payload["drafts"][0]["proposed_change"]["current_value"] = "token=password=secret=cipher"
    _write_payload(jobs_base, job["job_id"], payload)

    with _patch_job_bases(jobs_base):
        response = client.get(f"/compliance/jobs/{job['job_id']}/remediation/drafts/validation")

    assert response.status_code == 409
    issues = response.json()["remediation_draft_validation"]["issues"]
    assert any("secret marker" in issue for issue in issues)


def test_validation_safe_when_drafts_are_clean(client, jobs_base, monkeypatch):
    job = _prepare_and_generate(client, jobs_base, monkeypatch)

    with _patch_job_bases(jobs_base):
        response = client.get(f"/compliance/jobs/{job['job_id']}/remediation/drafts/validation")

    assert response.status_code == 200
    assert response.json()["decision"] in {"REMEDIATION_DRAFTS_SAFE", "REMEDIATION_DRAFTS_SAFE_WITH_WARNINGS"}


def test_validation_service_reports_safety_block(client, jobs_base, monkeypatch):
    job = _prepare_and_generate(client, jobs_base, monkeypatch)
    payload = validate_remediation_drafts(job["job_id"], jobs_base)
    assert payload["decision"] == "REMEDIATION_DRAFTS_SAFE"
    assert payload["remediation_draft_validation"]["safety"]["netbox_write"] is False
    assert payload["remediation_draft_validation"]["safety"]["apply_plan_created"] is False
