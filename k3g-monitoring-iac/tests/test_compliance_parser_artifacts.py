"""Tests for parser artifacts and parsed inventory route."""

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


def _make_exec_result(output: str):
    stdin = MagicMock()
    stdout = MagicMock()
    stderr = MagicMock()
    stdout.read.return_value = output.encode("utf-8")
    stderr.read.return_value = b""
    return stdin, stdout, stderr


def _command_output(command: str) -> str:
    command = command.lower()
    if command.startswith("display version"):
        return "\n".join(
            [
                "Huawei Versatile Routing Platform Software",
                "VRP (R) software, Version 8.230 (NE8000 V800R013C00SPC300)",
                "System Name: RX01",
            ]
        )
    if command.startswith("display device"):
        return "\n".join(
            [
                "Device type: NE8000",
                "Slot 0  Main board",
            ]
        )
    if command.startswith("display interface brief"):
        return "\n".join(
            [
                "Interface                       Physical   Protocol  Description",
                "GigabitEthernet0/0/0            up         up        uplink",
                "GigabitEthernet0/0/1            down       down      access",
            ]
        )
    if command.startswith("display ip interface brief"):
        return "\n".join(
            [
                "Interface                       IP Address/Mask      Physical  Protocol  Description",
                "GigabitEthernet0/0/0            192.0.2.1/32         up        up        uplink",
            ]
        )
    if command.startswith("display ipv6 interface brief"):
        return "\n".join(
            [
                "Interface                       IPv6 Address                     Physical  Protocol",
                "GigabitEthernet0/0/0            2001:db8::1/64                   up        up",
            ]
        )
    if command.startswith("display bgp peer"):
        return "\n".join(
            [
                "Peer IP          ASN     State",
                "192.0.2.10       65001   Established",
            ]
        )
    if command.startswith("display route-policy"):
        return "\n".join(
            [
                "route-policy RP1 permit node 10",
                " if-match ip-prefix P1",
                " apply community 100:1",
            ]
        )
    if command.startswith("display ip ip-prefix"):
        return "ip ip-prefix P1 index 10 permit 10.0.0.0 24"
    if command.startswith("display ipv6 prefix"):
        return "ipv6 prefix V6P1 index 10 permit 2001:db8::/64"
    if command.startswith("display snmp-agent sys-info"):
        return "\n".join(
            [
                "sysName: RX01",
                "sysContact: noc@example.com",
                "sysLocation: MNS",
                "snmp-agent sys-info version v3",
            ]
        )
    if "display current-configuration | include sysname" in command:
        return "sysname RX01"
    if "display current-configuration | include snmp-agent" in command:
        return "snmp-agent sys-info version v3"
    if "display current-configuration | include ntp-service" in command:
        return "ntp-service unicast-server 192.0.2.5"
    if "display current-configuration | include ssh" in command:
        return "stelnet server enable"
    if "display current-configuration | include stelnet" in command:
        return "stelnet server enable"
    if "display current-configuration | include local-user" in command:
        return ""
    return "VERY_SECRET_RAW_MARKER generic read-only output"


def _prepare_job(jobs_base: Path) -> dict:
    job = create_compliance_job([1890], _sample_candidates(), "Keslley", "read_only", jobs_base)
    create_collection_start_gate(job["job_id"], "Keslley", True, jobs_base)
    create_collection_plan(job["job_id"], jobs_base)
    return job


def _run_preflight(client: LocalHttpClient, jobs_base: Path, job_id: str):
    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_ssh_preflight.JOBS_BASE", jobs_base
    ):
        return client.post(
            f"/compliance/jobs/{job_id}/collection/ssh-preflight",
            json={"operator": "Keslley", "confirm_read_only": True},
        )


def _run_collection(client: LocalHttpClient, jobs_base: Path, job_id: str):
    plan = json.loads((jobs_base / job_id / "collection-plan.json").read_text(encoding="utf-8"))
    planned_commands = build_read_only_commands(plan["devices"][0])
    ssh_client = MagicMock()

    def _exec(command, timeout=None):
        return _make_exec_result(_command_output(command))

    ssh_client.exec_command.side_effect = _exec
    ssh_client_class = MagicMock(return_value=ssh_client)
    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_ssh_collection.JOBS_BASE", jobs_base
    ), patch("webui.services.compliance_raw_validation.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_parser_staging.JOBS_BASE", jobs_base
    ), patch("webui.services.compliance_ssh_collection.paramiko.SSHClient", ssh_client_class), patch(
        "webui.services.compliance_ssh_collection.paramiko.AutoAddPolicy", MagicMock(return_value=object())
    ):
        response = client.post(
            f"/compliance/jobs/{job_id}/collection/ssh-execute",
            json={"operator": "Keslley", "confirm_execute_read_only": True},
        )
    assert response.status_code == 200
    assert ssh_client.connect.call_count == 1
    assert ssh_client.exec_command.call_count == len(planned_commands)
    return response.json()


def _run_raw_validation(client: LocalHttpClient, jobs_base: Path, job_id: str):
    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_raw_validation.JOBS_BASE", jobs_base
    ):
        response = client.get(f"/compliance/jobs/{job_id}/collection/raw-validation")
    assert response.status_code == 200
    return response.json()


def _prepare_collection_artifacts(client: LocalHttpClient, jobs_base: Path, monkeypatch):
    job = _prepare_job(jobs_base)
    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_collection.JOBS_BASE", jobs_base
    ):
        execute_collection_job(job["job_id"], "Keslley", simulation_only=True, jobs_base=jobs_base)
    monkeypatch.setenv("COMPLIANCE_SSH_USERNAME", "readonly")
    monkeypatch.setenv("COMPLIANCE_SSH_PASSWORD", "readonly-secret")
    monkeypatch.setenv("COMPLIANCE_SSH_PORT", "22")
    monkeypatch.setenv("COMPLIANCE_SSH_TIMEOUT", "10")
    _run_preflight(client, jobs_base, job["job_id"])
    _run_collection(client, jobs_base, job["job_id"])
    _run_raw_validation(client, jobs_base, job["job_id"])
    return job


def test_parse_job_generates_artifacts(client, jobs_base, monkeypatch):
    job = _prepare_collection_artifacts(client, jobs_base, monkeypatch)

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_huawei_ne8000_parser.JOBS_BASE", jobs_base
    ), patch("webui.app.get_netbox_client") as netbox_client, patch(
        "webui.app.execute_ssh_readonly_collection"
    ) as ssh_exec, patch(
        "webui.app.run_ssh_preflight"
    ) as ssh_preflight:
        response = client.post(
            f"/compliance/jobs/{job['job_id']}/parse",
            json={"operator": "Keslley", "confirm_local_parse": True},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["decision"] in {"PARSER_COMPLETED", "PARSER_COMPLETED_WITH_WARNINGS"}

    results_dir = jobs_base / job["job_id"] / "collection-results"
    assert (results_dir / "parser-result.json").exists()
    assert (results_dir / "PARSER-RESULT.md").exists()
    assert (results_dir / "devices" / "1890" / "parsed" / "parsed-inventory.json").exists()
    assert (results_dir / "devices" / "1890" / "parsed" / "PARSED-INVENTORY.md").exists()
    assert data["parser_result"]["summary"]["interfaces_count"] >= 1
    assert data["parser_result"]["summary"]["warnings_count"] >= 0
    netbox_client.assert_not_called()
    ssh_exec.assert_not_called()
    ssh_preflight.assert_not_called()
    assert not (jobs_base / job["job_id"] / "approval-record.json").exists()
    assert not (jobs_base / job["job_id"] / "apply-plan.json").exists()


def test_parse_ui_shows_summary_and_hides_raw(client, jobs_base, monkeypatch):
    job = _prepare_collection_artifacts(client, jobs_base, monkeypatch)
    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_huawei_ne8000_parser.JOBS_BASE", jobs_base
    ):
        client.post(
            f"/compliance/jobs/{job['job_id']}/parse",
            json={"operator": "Keslley", "confirm_local_parse": True},
        )

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base):
        response = client.get(f"/compliance/jobs/{job['job_id']}")

    assert response.status_code == 200
    body = response.text
    assert "Inventário parseado" in body
    assert "PARSED-INVENTORY.md" in body
    assert "VERY_SECRET_RAW_MARKER" not in body
