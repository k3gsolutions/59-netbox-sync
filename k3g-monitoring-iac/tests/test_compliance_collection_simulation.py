"""Tests for read-only compliance collection simulation."""

from __future__ import annotations

import asyncio
import json
import sys
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from webui.app import app
from webui.services.compliance_collection import (
    SAFETY_INVALID,
    SAFETY_VALID,
    build_read_only_commands,
    validate_collection_plan,
)
from webui.services.compliance_jobs import create_compliance_job


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
    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base):
        from webui.services.compliance_jobs import create_collection_start_gate, create_collection_plan

        create_collection_start_gate(job["job_id"], "Keslley", True, jobs_base)
        create_collection_plan(job["job_id"], jobs_base)
    return job


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_execute_blocks_without_start_gate(client, jobs_base):
    job = create_compliance_job([1890], _sample_candidates(), "Keslley", "read_only", jobs_base)
    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch("webui.services.compliance_collection.JOBS_BASE", jobs_base):
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/collection/execute",
            json={"operator": "Keslley", "confirm_read_only": True},
        )

    assert response.status_code == 409
    assert "start gate" in response.json()["error"].lower()


def test_execute_blocks_without_collection_plan(client, jobs_base):
    job = create_compliance_job([1890], _sample_candidates(), "Keslley", "read_only", jobs_base)
    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch("webui.services.compliance_collection.JOBS_BASE", jobs_base):
        from webui.services.compliance_jobs import create_collection_start_gate

        create_collection_start_gate(job["job_id"], "Keslley", True, jobs_base)
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/collection/execute",
            json={"operator": "Keslley", "confirm_read_only": True},
        )

    assert response.status_code == 409
    assert "plan" in response.json()["error"].lower()


def test_execute_blocks_without_confirm_read_only(client, jobs_base):
    job = _prepare_ready_job(jobs_base)
    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch("webui.services.compliance_collection.JOBS_BASE", jobs_base):
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/collection/execute",
            json={"operator": "Keslley", "confirm_read_only": False},
        )

    assert response.status_code == 400


def test_execute_creates_collection_results(client, jobs_base):
    job = _prepare_ready_job(jobs_base)
    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch("webui.services.compliance_collection.JOBS_BASE", jobs_base):
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/collection/execute",
            json={"operator": "Keslley", "confirm_read_only": True},
        )

    assert response.status_code == 200
    results_dir = jobs_base / job["job_id"] / "collection-results"
    assert results_dir.exists()
    assert (results_dir / "collection-execution.json").exists()
    assert (results_dir / "COLLECTION-EXECUTION.md").exists()
    assert (results_dir / "collection-safety-validation.json").exists()
    assert (results_dir / "COLLECTION-SAFETY-VALIDATION.md").exists()


def test_execute_creates_planned_commands(client, jobs_base):
    job = _prepare_ready_job(jobs_base)
    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch("webui.services.compliance_collection.JOBS_BASE", jobs_base):
        client.post(
            f"/compliance/jobs/{job['job_id']}/collection/execute",
            json={"operator": "Keslley", "confirm_read_only": True},
        )

    planned = _load_json(jobs_base / job["job_id"] / "collection-results" / "devices" / "1890" / "planned-commands.json")
    assert "planned_commands" in planned
    assert planned["planned_commands"]


def test_huawei_commands_are_display_show():
    commands = build_read_only_commands({"manufacturer": "Huawei", "model": "NE8000", "platform": "VRP"})
    assert all(cmd.lower().startswith("display ") or cmd.lower().startswith("show ") for cmd in commands)


@pytest.mark.parametrize("command", ["system-view", "commit", "save", "delete"])
def test_validate_blocks_forbidden_commands(command):
    plan = {
        "decision": "COLLECTION_PLAN_PREPARED",
        "collection_started": False,
        "safety": {
            "netbox_write": False,
            "device_connection_started": False,
            "collection_started": False,
            "approval_record_created": False,
            "apply_plan_created": False,
        },
        "devices": [
            {
                "device_id": 1890,
                "name": "4WNET-MNS-KTG-RX",
                "manufacturer": "Huawei",
                "model": "NE8000",
                "platform": "VRP",
                "primary_ip4": "192.0.2.1/32",
                "planned_commands": [command],
            }
        ],
    }
    valid, issues = validate_collection_plan(plan)
    assert valid is False
    assert any(command in issue for issue in issues)


def test_execute_sets_simulation_only_true(client, jobs_base):
    job = _prepare_ready_job(jobs_base)
    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch("webui.services.compliance_collection.JOBS_BASE", jobs_base):
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/collection/execute",
            json={"operator": "Keslley", "confirm_read_only": True},
        )

    data = response.json()
    assert data["simulation_only"] is True


def test_execute_sets_device_connection_started_false(client, jobs_base):
    job = _prepare_ready_job(jobs_base)
    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch("webui.services.compliance_collection.JOBS_BASE", jobs_base):
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/collection/execute",
            json={"operator": "Keslley", "confirm_read_only": True},
        )

    data = response.json()
    assert data["collection_execution"]["device_connection_started"] is False


def test_execute_sets_netbox_write_false(client, jobs_base):
    job = _prepare_ready_job(jobs_base)
    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch("webui.services.compliance_collection.JOBS_BASE", jobs_base):
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/collection/execute",
            json={"operator": "Keslley", "confirm_read_only": True},
        )

    data = response.json()
    assert data["collection_execution"]["netbox_write"] is False


def test_execute_sets_sync_called_false(client, jobs_base):
    job = _prepare_ready_job(jobs_base)
    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch("webui.services.compliance_collection.JOBS_BASE", jobs_base):
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/collection/execute",
            json={"operator": "Keslley", "confirm_read_only": True},
        )

    data = response.json()
    assert data["collection_execution"]["sync_called"] is False


def test_safety_validation_returns_valid(client, jobs_base):
    job = _prepare_ready_job(jobs_base)
    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch("webui.services.compliance_collection.JOBS_BASE", jobs_base):
        execute_response = client.post(
            f"/compliance/jobs/{job['job_id']}/collection/execute",
            json={"operator": "Keslley", "confirm_read_only": True},
        )

    assert execute_response.status_code == 200
    validation = _load_json(jobs_base / job["job_id"] / "collection-results" / "collection-safety-validation.json")
    assert validation["decision"] == SAFETY_VALID
    assert validation["status"] == SAFETY_VALID


def test_collection_safety_invalid_for_bad_plan():
    plan = {
        "decision": "COLLECTION_PLAN_PREPARED",
        "collection_started": True,
        "devices": [],
        "safety": {
            "netbox_write": True,
            "device_connection_started": True,
            "collection_started": True,
            "approval_record_created": True,
            "apply_plan_created": True,
        },
    }
    valid, issues = validate_collection_plan(plan)
    assert valid is False
    assert issues
    assert SAFETY_INVALID == "COLLECTION_SAFETY_INVALID"


def test_webui_detail_shows_collection_buttons(client, jobs_base):
    job = _prepare_ready_job(jobs_base)
    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base):
        response = client.get(f"/compliance/jobs/{job['job_id']}")

    assert response.status_code == 200
    body = response.text
    assert "Preparar coleta read-only" in body
    assert "Preparar plano de coleta read-only" in body
    assert "Validar pré-requisitos SSH" in body
    assert "Executar coleta SSH read-only" in body


def test_execute_does_not_trigger_ssh_snmp_netconf(client, jobs_base):
    job = _prepare_ready_job(jobs_base)
    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch("webui.services.compliance_collection.JOBS_BASE", jobs_base), patch("webui.app.get_netbox_client") as mock_netbox:
        with patch("webui.services.compliance_collection.execute_ssh_collection", create=True) as mock_ssh:
            with patch("webui.services.compliance_collection.execute_snmp_collection", create=True) as mock_snmp:
                with patch("webui.services.compliance_collection.execute_netconf_collection", create=True) as mock_netconf:
                    response = client.post(
                        f"/compliance/jobs/{job['job_id']}/collection/execute",
                        json={"operator": "Keslley", "confirm_read_only": True},
                    )

    assert response.status_code == 200
    mock_netbox.assert_not_called()
    mock_ssh.assert_not_called()
    mock_snmp.assert_not_called()
    mock_netconf.assert_not_called()
