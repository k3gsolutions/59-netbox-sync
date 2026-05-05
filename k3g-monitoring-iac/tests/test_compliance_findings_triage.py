"""Tests for compliance findings triage."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from webui.app import app
from webui.services.compliance_findings_triage import classify_finding_noise_or_action
from tests.test_compliance_parser_artifacts import _prepare_collection_artifacts


class SimpleResponse:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text

    def json(self):
        return json.loads(self.text)


class LocalHttpClient:
    async def _request(self, method: str, path: str, json_body: dict | None = None):
        query_string = b""
        raw_path = path.encode("utf-8")
        if "?" in path:
            raw_path, query = path.split("?", 1)
            query_string = query.encode("utf-8")
            raw_path = raw_path.encode("utf-8")

        body = b""
        headers = []
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            headers = [(b"content-type", b"application/json"), (b"accept", b"application/json")]

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path.split("?", 1)[0],
            "raw_path": raw_path,
            "query_string": query_string,
            "headers": headers,
            "client": ("testclient", 123),
            "server": ("testserver", 80),
        }
        status_code = 500
        chunks: list[bytes] = []
        request_seen = False

        async def receive():
            nonlocal request_seen
            if not request_seen:
                request_seen = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            elif message["type"] == "http.response.body":
                chunks.append(message.get("body", b""))

        await app(scope, receive, send)
        return SimpleResponse(status_code, b"".join(chunks).decode("utf-8", errors="ignore"))

    def get(self, path: str):
        return asyncio.run(self._request("GET", path))

    def post(self, path: str, json: dict | None = None):
        return asyncio.run(self._request("POST", path, json_body=json))


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


def _prepare_compare_artifacts(client: LocalHttpClient, jobs_base: Path, monkeypatch):
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


def test_classify_bgp_non_established_needs_human_review():
    finding = {
        "finding_id": "CMP-1",
        "severity": "warning",
        "rule_id": "bgp.peer.state.not_established",
        "scope": "bgp",
        "object_name": "10.0.0.1",
        "evidence": {"value": "Idle"},
        "recommendation": "Validate session",
    }
    classified = classify_finding_noise_or_action(finding)
    assert classified["triage_bucket"] == "needs_human_review"
    assert classified["remediation_allowed"] is False


def test_classify_bgp_missing_policy_needs_human_review():
    finding = {
        "finding_id": "CMP-2",
        "severity": "warning",
        "rule_id": "bgp.peer.policy.missing",
        "scope": "bgp",
        "object_name": "10.0.0.2",
        "evidence": {"value": None},
        "recommendation": "Confirm import/export policies",
    }
    classified = classify_finding_noise_or_action(finding)
    assert classified["triage_bucket"] == "needs_human_review"


def test_classify_bgp_missing_description_needs_human_review():
    finding = {
        "finding_id": "CMP-3",
        "severity": "warning",
        "rule_id": "bgp.peer.description.required",
        "scope": "bgp",
        "object_name": "10.0.0.3",
        "evidence": {"value": None},
        "recommendation": "Add description",
    }
    classified = classify_finding_noise_or_action(finding)
    assert classified["triage_bucket"] == "needs_human_review"


def test_virtual_ethernet_naming_invalid_is_policy_or_noise():
    finding = {
        "finding_id": "CMP-4",
        "severity": "error",
        "rule_id": "interface.naming.invalid",
        "scope": "interface",
        "object_name": "Virtual-Ethernet0/2/100.100",
        "evidence": {"value": "Virtual-Ethernet0/2/100.100"},
        "recommendation": "Review naming policy",
    }
    classified = classify_finding_noise_or_action(finding)
    assert classified["triage_bucket"] in {"likely_policy_too_strict", "likely_parser_noise"}


def test_interface_without_description_needs_human_review():
    finding = {
        "finding_id": "CMP-5",
        "severity": "warning",
        "rule_id": "interface.description.required",
        "scope": "interface",
        "object_name": "GigabitEthernet0/0/0",
        "evidence": {"value": None},
        "recommendation": "Add description",
    }
    classified = classify_finding_noise_or_action(finding)
    assert classified["triage_bucket"] == "needs_human_review"


def test_route_policy_missing_needs_human_review():
    finding = {
        "finding_id": "CMP-6",
        "severity": "info",
        "rule_id": "route_policy.missing",
        "scope": "route_policy",
        "object_name": "*",
        "evidence": {"value": None},
        "recommendation": "Verify collection",
    }
    classified = classify_finding_noise_or_action(finding)
    assert classified["triage_bucket"] == "needs_human_review"


def test_prefix_list_missing_needs_human_review():
    finding = {
        "finding_id": "CMP-7",
        "severity": "info",
        "rule_id": "prefix_list.missing",
        "scope": "prefix_list",
        "object_name": "*",
        "evidence": {"value": None},
        "recommendation": "Verify collection",
    }
    classified = classify_finding_noise_or_action(finding)
    assert classified["triage_bucket"] == "needs_human_review"


def test_generate_triage_artifact_and_top10_excludes_virtual_ethernet(client):
    job_id = "compliance-job-e961838f0ae1"
    response = client.post(
        f"/compliance/jobs/{job_id}/triage",
        json={"operator": "Keslley"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "TRIAGE_COMPLETED"
    assert data["triage"]["findings_total"] >= 100
    assert data["triage"]["safety"]["netbox_write"] is False
    assert data["triage"]["safety"]["device_connection"] is False
    assert data["triage"]["safety"]["sync_called"] is False
    assert data["triage"]["safety"]["approval_record_created"] is False
    assert data["triage"]["safety"]["apply_plan_created"] is False

    triage_path = Path("reports/compliance/jobs") / job_id / "triage" / "findings-triage.json"
    assert triage_path.exists()
    top10 = data["triage"]["top_review_items"]
    assert len(top10) == 10
    assert not any(str(item["object_name"]).startswith("Virtual-Ethernet") for item in top10)
    assert all(item["remediation_allowed"] is False for item in data["triage"]["findings"])


def test_triage_ui_has_section_and_no_apply_button(client):
    job_id = "compliance-job-e961838f0ae1"
    response = client.post(f"/compliance/jobs/{job_id}/triage", json={"operator": "Keslley"})
    assert response.status_code == 200
    response = client.get(f"/compliance/jobs/{job_id}")

    assert response.status_code == 200
    body = response.text
    assert "Triagem dos Achados" in body
    assert "id=\"triage-btn\"" in body
    assert "id=\"triage-apply-btn\"" not in body
