"""Tests for parser staging area."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from webui.app import app
from webui.services.compliance_parser_staging import create_parser_staging
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


def _prepare_job(jobs_base: Path) -> dict:
    job = create_compliance_job([1890], _sample_candidates(), "Keslley", "read_only", jobs_base)
    create_collection_start_gate(job["job_id"], "Keslley", True, jobs_base)
    create_collection_plan(job["job_id"], jobs_base)

    results_dir = jobs_base / job["job_id"] / "collection-results"
    raw_dir = results_dir / "devices" / "1890" / "raw"
    redacted_dir = results_dir / "devices" / "1890" / "redacted"
    parsed_dir = results_dir / "devices" / "1890" / "parsed"
    raw_dir.mkdir(parents=True, exist_ok=True)
    redacted_dir.mkdir(parents=True, exist_ok=True)
    parsed_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "display-version.txt").write_text("password secret\n", encoding="utf-8")
    (redacted_dir / "display-version.txt").write_text("password ****\n", encoding="utf-8")
    (parsed_dir / ".gitkeep").touch(exist_ok=True)
    (results_dir / "ssh-collection-result.json").write_text(
        json.dumps(
            {
                "job_id": job["job_id"],
                "status": "SSH_COLLECTION_COMPLETED",
                "operator": "Keslley",
                "simulation_only": False,
                "device_connection_started": True,
                "netbox_write": False,
                "sync_called": False,
                "approval_record_created": False,
                "apply_plan_created": False,
                "commands_executed_count": 1,
                "forbidden_commands_executed": False,
                "config_mode_entered": False,
                "password_logged": False,
                "password_saved": False,
                "devices": [
                    {
                        "device_id": "1890",
                        "name": "4WNET-MNS-KTG-RX",
                        "host": "192.0.2.1",
                        "status": "completed",
                        "commands_executed_count": 1,
                        "errors": [],
                    }
                ],
                "checked_at": "2026-04-30T00:00:00Z",
                "issues": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return job


def test_parser_manifest_lists_raw_redacted_parsed(jobs_base):
    job = _prepare_job(jobs_base)

    manifest = create_parser_staging(job["job_id"], jobs_base)["parser_manifest"]
    device = manifest["devices"][0]
    assert device["raw_files"]
    assert device["redacted_files"]
    assert device["parsed_files"] == []
    assert device["ready_for_parsing"] is True


def test_parser_staging_route_shows_redacted_not_raw(client, jobs_base):
    job = _prepare_job(jobs_base)
    create_parser_staging(job["job_id"], jobs_base)

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("COMPLIANCE_SSH_USERNAME", "readonly")
        mp.setenv("COMPLIANCE_SSH_PASSWORD", "secret")
        mp.setenv("COMPLIANCE_SSH_PORT", "22")
        mp.setenv("COMPLIANCE_SSH_TIMEOUT", "10")
        from unittest.mock import patch

        with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
            "webui.services.compliance_parser_staging.JOBS_BASE", jobs_base
        ):
            response = client.get(f"/compliance/jobs/{job['job_id']}")

    assert response.status_code == 200
    body = response.text
    assert "PARSER-STAGING" in body
    assert "redacted" in body
    assert "parsed" in body
    assert "password secret" not in body
