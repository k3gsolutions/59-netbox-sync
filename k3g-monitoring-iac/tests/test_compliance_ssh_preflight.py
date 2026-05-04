"""Tests for SSH connectivity preflight."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from webui.app import app
from webui.services.compliance_collection import execute_collection_job
from webui.services.compliance_jobs import create_collection_plan, create_collection_start_gate, create_compliance_job


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


def _sample_candidates() -> list[dict]:
    return [
        {
            "id": 1890,
            "name": "4WNET-MNS-KTG-RX",
            "status": "active",
            "tenant": "K3G Solutions",
            "site": "MNS",
            "manufacturer": "Huawei",
            "model": "NE8000",
            "primary_ip4": "192.0.2.1/32",
        }
    ]


def _prepare_ready_job(jobs_base: Path) -> dict:
    job = create_compliance_job([1890], _sample_candidates(), "Keslley", "read_only", jobs_base)
    create_collection_start_gate(job["job_id"], "Keslley", True, jobs_base)
    create_collection_plan(job["job_id"], jobs_base)
    execute_collection_job(job["job_id"], "Keslley", simulation_only=True, jobs_base=jobs_base)
    return job


def test_preflight_blocks_without_env(client, jobs_base):
    job = _prepare_ready_job(jobs_base)
    from unittest.mock import patch

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_ssh_preflight.JOBS_BASE", jobs_base
    ):
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/collection/ssh-preflight",
            json={"operator": "Keslley", "confirm_read_only": True},
        )

    assert response.status_code == 409
    data = response.json()
    assert data["decision"] == "SSH_PREFLIGHT_BLOCKED"
    assert any(
        "COMPLIANCE_SSH_USERNAME" in issue or "missing env" in issue.lower()
        for issue in data["ssh_preflight"]["command_issues"]
    )
    assert (jobs_base / job["job_id"] / "collection-results" / "ssh-preflight.json").exists()


def test_preflight_ready_config_only(client, jobs_base, monkeypatch):
    job = _prepare_ready_job(jobs_base)
    monkeypatch.setenv("COMPLIANCE_SSH_USERNAME", "readonly")
    monkeypatch.setenv("COMPLIANCE_SSH_PASSWORD", "VerySecret123!")
    monkeypatch.setenv("COMPLIANCE_SSH_PORT", "22")
    monkeypatch.setenv("COMPLIANCE_SSH_TIMEOUT", "10")
    monkeypatch.setenv("COMPLIANCE_SSH_PREFLIGHT_TCP_CHECK", "false")

    from unittest.mock import patch

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_ssh_preflight.JOBS_BASE", jobs_base
    ):
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/collection/ssh-preflight",
            json={"operator": "Keslley", "confirm_read_only": True},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "SSH_PREFLIGHT_READY_CONFIG_ONLY"
    assert data["ssh_preflight"]["env"]["username_present"] is True
    assert data["ssh_preflight"]["env"]["password_present"] is True
    assert "VerySecret123!" not in response.text

    preflight_file = jobs_base / job["job_id"] / "collection-results" / "ssh-preflight.json"
    markdown_file = jobs_base / job["job_id"] / "collection-results" / "SSH-PREFLIGHT.md"
    assert preflight_file.exists()
    assert markdown_file.exists()
    assert "VerySecret123!" not in preflight_file.read_text(encoding="utf-8")
    assert "VerySecret123!" not in markdown_file.read_text(encoding="utf-8")
