"""Tests for compliance job review dashboard, start gate, and read-only plan."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from webui.app import app
from webui.services import compliance_jobs
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


def _patch_jobs_base(jobs_base: Path):
    return patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base)


def _create_prepared_job(jobs_base: Path) -> dict:
    return create_compliance_job([1890], _sample_candidates(), "Keslley", "read_only", jobs_base)


def _read_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_get_compliance_jobs_lists_jobs(client, jobs_base):
    job = _create_prepared_job(jobs_base)

    with _patch_jobs_base(jobs_base):
        response = client.get("/compliance/jobs")

    assert response.status_code == 200
    body = response.text
    assert job["job_id"] in body
    assert "Compliance Jobs" in body


def test_get_compliance_job_detail_shows_details(client, jobs_base):
    job = _create_prepared_job(jobs_base)

    with _patch_jobs_base(jobs_base):
        response = client.get(f"/compliance/jobs/{job['job_id']}")

    assert response.status_code == 200
    body = response.text
    assert job["job_id"] in body
    assert "Preparar plano de coleta read-only" in body
    assert "manual_review_before_collection" in body
    assert "4WNET-MNS-KTG-RX" in body


def test_start_gate_blocks_missing_job(client, jobs_base):
    with _patch_jobs_base(jobs_base):
        response = client.post(
            "/compliance/jobs/compliance-job-missing/collection/start-gate",
            json={"operator": "Keslley", "confirm": True},
        )

    assert response.status_code == 404
    assert response.json()["success"] is False


def test_start_gate_blocks_non_prepared_job(client, jobs_base):
    job_id = "compliance-job-badstatus"
    job_dir = jobs_base / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "job-request.json").write_text(
        json.dumps(
            {
                "job_id": job_id,
                "status": "blocked",
                "triggered_by": "Keslley",
                "safety": compliance_jobs.get_compliance_job_safety(),
                "device_ids": [1890],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (job_dir / "selected-devices.json").write_text(
        json.dumps({"job_id": job_id, "selected_count": 1, "devices": _sample_candidates()}, indent=2)
        + "\n",
        encoding="utf-8",
    )

    with _patch_jobs_base(jobs_base):
        response = client.post(
            f"/compliance/jobs/{job_id}/collection/start-gate",
            json={"operator": "Keslley", "confirm": True},
        )

    assert response.status_code == 409
    assert response.json()["decision"] == "COLLECTION_START_GATE_BLOCKED"


def test_start_gate_creates_ready_gate(client, jobs_base):
    job = _create_prepared_job(jobs_base)

    with _patch_jobs_base(jobs_base):
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/collection/start-gate",
            json={"operator": "Keslley", "confirm": True},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "COLLECTION_START_GATE_READY"
    gate_file = jobs_base / job["job_id"] / "collection-start-gate.json"
    assert gate_file.exists()
    gate_data = _read_json(str(gate_file))
    assert gate_data["decision"] == "COLLECTION_START_GATE_READY"
    assert gate_data["checks"]["job_status_prepared"] is True
    assert (jobs_base / job["job_id"] / "COLLECTION-START-GATE.md").exists()


def test_collection_plan_blocks_without_gate(client, jobs_base):
    job = _create_prepared_job(jobs_base)

    with _patch_jobs_base(jobs_base):
        response = client.post(f"/compliance/jobs/{job['job_id']}/collection/plan")

    assert response.status_code == 409
    body = response.json()
    assert body["decision"] == "COLLECTION_PLAN_BLOCKED"


def test_collection_plan_creates_read_only_plan(client, jobs_base):
    job = _create_prepared_job(jobs_base)

    with _patch_jobs_base(jobs_base):
        start_gate_response = client.post(
            f"/compliance/jobs/{job['job_id']}/collection/start-gate",
            json={"operator": "Keslley", "confirm": True},
        )
        assert start_gate_response.status_code == 200
        response = client.post(f"/compliance/jobs/{job['job_id']}/collection/plan")

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "COLLECTION_PLAN_PREPARED"
    plan_file = jobs_base / job["job_id"] / "collection-plan.json"
    assert plan_file.exists()
    plan_data = _read_json(str(plan_file))
    assert plan_data["decision"] == "COLLECTION_PLAN_PREPARED"
    assert len(plan_data["devices"]) == 1


def test_collection_plan_does_not_execute_ssh(client, jobs_base):
    job = _create_prepared_job(jobs_base)

    with _patch_jobs_base(jobs_base):
        client.post(
            f"/compliance/jobs/{job['job_id']}/collection/start-gate",
            json={"operator": "Keslley", "confirm": True},
        )
        with patch.object(compliance_jobs, "execute_ssh_collection", create=True) as mock_ssh:
            response = client.post(f"/compliance/jobs/{job['job_id']}/collection/plan")

    assert response.status_code == 200
    mock_ssh.assert_not_called()


def test_collection_plan_does_not_execute_snmp(client, jobs_base):
    job = _create_prepared_job(jobs_base)

    with _patch_jobs_base(jobs_base):
        client.post(
            f"/compliance/jobs/{job['job_id']}/collection/start-gate",
            json={"operator": "Keslley", "confirm": True},
        )
        with patch.object(compliance_jobs, "execute_snmp_collection", create=True) as mock_snmp:
            response = client.post(f"/compliance/jobs/{job['job_id']}/collection/plan")

    assert response.status_code == 200
    mock_snmp.assert_not_called()


def test_collection_plan_does_not_execute_netconf(client, jobs_base):
    job = _create_prepared_job(jobs_base)

    with _patch_jobs_base(jobs_base):
        client.post(
            f"/compliance/jobs/{job['job_id']}/collection/start-gate",
            json={"operator": "Keslley", "confirm": True},
        )
        with patch.object(compliance_jobs, "execute_netconf_collection", create=True) as mock_netconf:
            response = client.post(f"/compliance/jobs/{job['job_id']}/collection/plan")

    assert response.status_code == 200
    mock_netconf.assert_not_called()


def test_collection_plan_does_not_write_netbox(client, jobs_base):
    job = _create_prepared_job(jobs_base)

    with _patch_jobs_base(jobs_base):
        client.post(
            f"/compliance/jobs/{job['job_id']}/collection/start-gate",
            json={"operator": "Keslley", "confirm": True},
        )
        with patch("webui.app.get_netbox_client") as mock_get_netbox:
            response = client.post(f"/compliance/jobs/{job['job_id']}/collection/plan")

    assert response.status_code == 200
    mock_get_netbox.assert_not_called()


def test_collection_plan_contains_forbidden_methods(client, jobs_base):
    job = _create_prepared_job(jobs_base)

    with _patch_jobs_base(jobs_base):
        client.post(
            f"/compliance/jobs/{job['job_id']}/collection/start-gate",
            json={"operator": "Keslley", "confirm": True},
        )
        client.post(f"/compliance/jobs/{job['job_id']}/collection/plan")

    plan_data = _read_json(str(jobs_base / job["job_id"] / "collection-plan.json"))
    device_plan = plan_data["devices"][0]
    assert "forbidden_methods" in device_plan
    assert device_plan["forbidden_methods"] == [
        "netconf_write",
        "cli_config",
        "netbox_write",
        "sync",
    ]


def test_collection_plan_command_policy_blocks_write_commands(client, jobs_base):
    job = _create_prepared_job(jobs_base)

    with _patch_jobs_base(jobs_base):
        client.post(
            f"/compliance/jobs/{job['job_id']}/collection/start-gate",
            json={"operator": "Keslley", "confirm": True},
        )
        client.post(f"/compliance/jobs/{job['job_id']}/collection/plan")

    plan_data = _read_json(str(jobs_base / job["job_id"] / "collection-plan.json"))
    device_plan = plan_data["devices"][0]
    policy = " ".join(device_plan["command_policy"]).lower()
    assert "show/display only" in policy
    assert "no configure/system-view" in policy
    assert "no commit/save" in policy
    assert all(command not in {"configure", "system-view", "commit", "save"} for command in device_plan["command_policy"])
