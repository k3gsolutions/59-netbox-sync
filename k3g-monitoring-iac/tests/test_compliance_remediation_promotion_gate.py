"""Tests for remediation promotion gate and UI visibility."""

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


def _prepare_generated_drafts(client: LocalHttpClient, jobs_base: Path, monkeypatch) -> dict:
    job = _prepare_compare_artifacts(client, jobs_base, monkeypatch)
    findings = load_findings(job["job_id"], jobs_base)
    assert findings
    save_finding_decision(
        job["job_id"],
        findings[0]["finding_id"],
        {"reviewer": "Keslley", "reason": "review", "decision": "needs_remediation"},
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


def test_promotion_gate_blocks_without_validation(client, jobs_base, monkeypatch):
    job = _prepare_generated_drafts(client, jobs_base, monkeypatch)

    with _patch_job_bases(jobs_base):
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/remediation/promotion-gate",
            json={"operator": "Keslley", "confirm_human_reviewed_drafts": True},
        )

    assert response.status_code == 409
    assert response.json()["decision"] == "REMEDIATION_PROMOTION_BLOCKED"


def test_promotion_gate_blocks_unsafe_validation(client, jobs_base, monkeypatch):
    job = _prepare_generated_drafts(client, jobs_base, monkeypatch)
    payload = json.loads(_draft_file(jobs_base, job["job_id"]).read_text(encoding="utf-8"))
    payload["drafts"][0]["write_allowed"] = True
    _draft_file(jobs_base, job["job_id"]).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    with _patch_job_bases(jobs_base):
        validation = client.get(f"/compliance/jobs/{job['job_id']}/remediation/drafts/validation")
        assert validation.status_code == 409
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/remediation/promotion-gate",
            json={"operator": "Keslley", "confirm_human_reviewed_drafts": True},
        )

    assert response.status_code == 409
    assert response.json()["decision"] == "REMEDIATION_PROMOTION_BLOCKED"


def test_promotion_gate_ready_with_safe_validation_and_confirmation(client, jobs_base, monkeypatch):
    job = _prepare_generated_drafts(client, jobs_base, monkeypatch)

    with _patch_job_bases(jobs_base):
        validation = client.get(f"/compliance/jobs/{job['job_id']}/remediation/drafts/validation")
        assert validation.status_code == 200
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/remediation/promotion-gate",
            json={"operator": "Keslley", "confirm_human_reviewed_drafts": True},
        )

    assert response.status_code == 200
    assert response.json()["decision"] in {
        "REMEDIATION_PROMOTION_CANDIDATE_READY",
        "REMEDIATION_PROMOTION_CANDIDATE_READY_WITH_WARNINGS",
    }


def test_job_ui_shows_drafts_section_without_apply_write_sync_buttons(client, jobs_base, monkeypatch):
    job = _prepare_generated_drafts(client, jobs_base, monkeypatch)
    with _patch_job_bases(jobs_base):
        response = client.get(f"/compliance/jobs/{job['job_id']}")

    assert response.status_code == 200
    body = response.text
    assert "Rascunhos de Remediação" in body
    assert "Gerar rascunhos locais" in body
    assert ">Aplicar<" not in body
    assert ">Write<" not in body
    assert ">Sync<" not in body


def test_promotion_gate_service_reports_local_safety(client, jobs_base, monkeypatch):
    job = _prepare_generated_drafts(client, jobs_base, monkeypatch)
    validate_remediation_drafts(job["job_id"], jobs_base)
    with _patch_job_bases(jobs_base):
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/remediation/promotion-gate",
            json={"operator": "Keslley", "confirm_human_reviewed_drafts": True},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["safety"]["netbox_write"] is False
    assert payload["safety"]["approval_record_created"] is False
    assert payload["safety"]["apply_plan_created"] is False
