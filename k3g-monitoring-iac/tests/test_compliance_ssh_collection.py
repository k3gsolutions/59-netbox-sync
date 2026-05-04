"""Tests for controlled SSH read-only collection."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from webui.app import app
from webui.services.compliance_collection import build_read_only_commands
from webui.services.compliance_collection import execute_collection_job
from webui.services.compliance_jobs import create_collection_plan, create_collection_start_gate, create_compliance_job
from webui.services.compliance_ssh_policy import sanitize_command_filename


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


def _make_exec_result(output: str):
    stdin = MagicMock()
    stdout = MagicMock()
    stderr = MagicMock()
    stdout.read.return_value = output.encode("utf-8")
    stderr.read.return_value = b""
    return stdin, stdout, stderr


def _run_preflight(client: LocalHttpClient, jobs_base: Path, job_id: str):
    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_ssh_preflight.JOBS_BASE", jobs_base
    ):
        return client.post(
            f"/compliance/jobs/{job_id}/collection/ssh-preflight",
            json={"operator": "Keslley", "confirm_read_only": True},
        )


def test_execute_blocks_without_preflight(client, jobs_base, monkeypatch):
    job = _prepare_ready_job(jobs_base)
    monkeypatch.setenv("COMPLIANCE_SSH_USERNAME", "readonly")
    monkeypatch.setenv("COMPLIANCE_SSH_PASSWORD", "VerySecret123!")

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_ssh_collection.JOBS_BASE", jobs_base
    ), patch("webui.services.compliance_ssh_collection.paramiko.SSHClient") as ssh_client_class:
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/collection/ssh-execute",
            json={"operator": "Keslley", "confirm_execute_read_only": True},
        )

    assert response.status_code == 409
    assert response.json()["decision"] == "SSH_COLLECTION_BLOCKED"
    ssh_client_class.assert_not_called()


def test_execute_blocks_forbidden_command_before_connect(client, jobs_base, monkeypatch):
    job = _prepare_ready_job(jobs_base)
    monkeypatch.setenv("COMPLIANCE_SSH_USERNAME", "readonly")
    monkeypatch.setenv("COMPLIANCE_SSH_PASSWORD", "VerySecret123!")
    _run_preflight(client, jobs_base, job["job_id"])

    plan_path = jobs_base / job["job_id"] / "collection-plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["devices"][0]["planned_commands"] = ["system-view"]
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_ssh_collection.JOBS_BASE", jobs_base
    ), patch("webui.services.compliance_ssh_collection.paramiko.SSHClient") as ssh_client_class:
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/collection/ssh-execute",
            json={"operator": "Keslley", "confirm_execute_read_only": True},
        )

    assert response.status_code == 409
    assert response.json()["decision"] == "SSH_COLLECTION_BLOCKED"
    ssh_client_class.assert_not_called()


def test_execute_uses_primary_ip_without_mask(client, jobs_base, monkeypatch):
    job = _prepare_ready_job(jobs_base)
    monkeypatch.setenv("COMPLIANCE_SSH_USERNAME", "readonly")
    monkeypatch.setenv("COMPLIANCE_SSH_PASSWORD", "VerySecret123!")
    monkeypatch.setenv("COMPLIANCE_SSH_PORT", "2222")
    monkeypatch.setenv("COMPLIANCE_SSH_TIMEOUT", "12")
    _run_preflight(client, jobs_base, job["job_id"])

    plan = json.loads((jobs_base / job["job_id"] / "collection-plan.json").read_text(encoding="utf-8"))
    planned_commands = build_read_only_commands(plan["devices"][0])
    exec_results = [_make_exec_result(f"output {index}") for index, _ in enumerate(planned_commands)]

    ssh_client = MagicMock()
    ssh_client.exec_command.side_effect = exec_results
    ssh_client_class = MagicMock(return_value=ssh_client)

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_ssh_collection.JOBS_BASE", jobs_base
    ), patch("webui.services.compliance_raw_validation.JOBS_BASE", jobs_base
    ), patch("webui.services.compliance_parser_staging.JOBS_BASE", jobs_base
    ), patch("webui.services.compliance_ssh_collection.paramiko.SSHClient", ssh_client_class), patch(
        "webui.services.compliance_ssh_collection.paramiko.AutoAddPolicy", MagicMock(return_value=object())
    ):
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/collection/ssh-execute",
            json={"operator": "Keslley", "confirm_execute_read_only": True},
        )

    assert response.status_code == 200
    ssh_client.connect.assert_called_once_with(
        hostname="192.0.2.1",
        port=2222,
        username="readonly",
        password="VerySecret123!",
        timeout=12,
        look_for_keys=False,
        allow_agent=False,
    )
    result = response.json()["ssh_collection_result"]
    assert result["device_connection_started"] is True
    assert result["status"] in {"SSH_COLLECTION_COMPLETED", "SSH_COLLECTION_COMPLETED_WITH_ERRORS"}


def test_execute_saves_raw_and_meta(client, jobs_base, monkeypatch):
    job = _prepare_ready_job(jobs_base)
    monkeypatch.setenv("COMPLIANCE_SSH_USERNAME", "readonly")
    monkeypatch.setenv("COMPLIANCE_SSH_PASSWORD", "VerySecret123!")
    _run_preflight(client, jobs_base, job["job_id"])

    plan = json.loads((jobs_base / job["job_id"] / "collection-plan.json").read_text(encoding="utf-8"))
    planned_commands = build_read_only_commands(plan["devices"][0])
    ssh_client = MagicMock()
    ssh_client.exec_command.side_effect = [_make_exec_result("ok") for _ in planned_commands]
    ssh_client_class = MagicMock(return_value=ssh_client)

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_ssh_collection.JOBS_BASE", jobs_base
    ), patch("webui.services.compliance_raw_validation.JOBS_BASE", jobs_base
    ), patch("webui.services.compliance_ssh_collection.paramiko.SSHClient", ssh_client_class), patch(
        "webui.services.compliance_ssh_collection.paramiko.AutoAddPolicy", MagicMock(return_value=object())
    ):
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/collection/ssh-execute",
            json={"operator": "Keslley", "confirm_execute_read_only": True},
        )

    assert response.status_code == 200
    raw_dir = jobs_base / job["job_id"] / "collection-results" / "devices" / "1890" / "raw"
    redacted_dir = jobs_base / job["job_id"] / "collection-results" / "devices" / "1890" / "redacted"
    assert any(path.suffix == ".txt" for path in raw_dir.iterdir())
    assert any(path.suffix == ".json" for path in raw_dir.iterdir())
    assert redacted_dir.exists()
    expected_name = sanitize_command_filename(planned_commands[0])
    assert (raw_dir / f"{expected_name}.txt").exists()
    assert (raw_dir / f"{expected_name}.meta.json").exists()
    assert (redacted_dir / f"{expected_name}.txt").exists()
    assert (redacted_dir / f"{expected_name}.meta.json").exists()
    assert (jobs_base / job["job_id"] / "collection-results" / "parser-manifest.json").exists()


def test_execute_does_not_retry_automatically(client, jobs_base, monkeypatch):
    job = _prepare_ready_job(jobs_base)
    monkeypatch.setenv("COMPLIANCE_SSH_USERNAME", "readonly")
    monkeypatch.setenv("COMPLIANCE_SSH_PASSWORD", "VerySecret123!")
    _run_preflight(client, jobs_base, job["job_id"])

    ssh_client = MagicMock()
    ssh_client.connect.side_effect = RuntimeError("boom")
    ssh_client_class = MagicMock(return_value=ssh_client)

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_ssh_collection.JOBS_BASE", jobs_base
    ), patch("webui.services.compliance_raw_validation.JOBS_BASE", jobs_base
    ), patch("webui.services.compliance_ssh_collection.paramiko.SSHClient", ssh_client_class), patch(
        "webui.services.compliance_ssh_collection.paramiko.AutoAddPolicy", MagicMock(return_value=object())
    ):
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/collection/ssh-execute",
            json={"operator": "Keslley", "confirm_execute_read_only": True},
        )

    assert ssh_client.connect.call_count == 1
    assert response.status_code == 409
    assert response.json()["decision"] == "SSH_COLLECTION_FAILED"
