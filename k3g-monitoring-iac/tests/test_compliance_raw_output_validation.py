"""Tests for raw output safety validation."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from webui.app import app
from webui.services.compliance_raw_validation import (
    RAW_OUTPUT_SAFETY_VALID_WITH_WARNINGS,
    RAW_OUTPUT_SAFETY_VALID,
    validate_raw_collection_outputs,
)


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


def _write_clean_results(job_id: str, jobs_base: Path) -> None:
    results_dir = jobs_base / job_id / "collection-results"
    raw_dir = results_dir / "devices" / "1890" / "raw"
    parsed_dir = results_dir / "devices" / "1890" / "parsed"
    raw_dir.mkdir(parents=True, exist_ok=True)
    parsed_dir.mkdir(parents=True, exist_ok=True)
    (parsed_dir / ".gitkeep").touch(exist_ok=True)

    planned = {
        "job_id": job_id,
        "device_id": "1890",
        "planned_commands": ["display version"],
    }
    (results_dir / "devices" / "1890" / "planned-commands.json").write_text(
        json.dumps(planned, indent=2) + "\n",
        encoding="utf-8",
    )
    (raw_dir / "display-version.txt").write_text("Huawei VRP version info\n", encoding="utf-8")
    (raw_dir / "display-version.meta.json").write_text(
        json.dumps(
            {
                "command": "display version",
                "device_id": "1890",
                "host": "192.0.2.1",
                "executed_at": "2026-04-30T00:00:00Z",
                "stdout_bytes": 24,
                "stderr_bytes": 0,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (results_dir / "ssh-collection-result.json").write_text(
        json.dumps(
            {
                "job_id": job_id,
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


def test_raw_validation_passes_with_clean_outputs(jobs_base):
    job_id = "compliance-job-raw-clean"
    _write_clean_results(job_id, jobs_base)

    result = validate_raw_collection_outputs(job_id, jobs_base)
    assert result["decision"] == RAW_OUTPUT_SAFETY_VALID
    assert result["raw_output_safety_validation"]["issues"] == []
    assert result["raw_output_safety_validation"]["executed_commands"][0]["command"] == "display version"
    assert result["raw_output_safety_validation"]["status"] == RAW_OUTPUT_SAFETY_VALID


@pytest.mark.parametrize(
    "marker,content,expected",
    [
        ("token", "NETBOX_WRITE_TOKEN=abc123", "token"),
        ("password", "password=secret", "password"),
        ("config-mode", "system-view\n", "system-view"),
    ],
)
def test_raw_validation_detects_sensitive_markers(jobs_base, marker, content, expected):
    job_id = f"compliance-job-raw-{marker}"
    _write_clean_results(job_id, jobs_base)
    raw_dir = jobs_base / job_id / "collection-results" / "devices" / "1890" / "raw"
    (raw_dir / "display-version.txt").write_text(content, encoding="utf-8")
    redacted_dir = jobs_base / job_id / "collection-results" / "devices" / "1890" / "redacted"
    redacted_dir.mkdir(parents=True, exist_ok=True)
    (redacted_dir / "display-version.txt").write_text("redacted ****\n", encoding="utf-8")

    result = validate_raw_collection_outputs(job_id, jobs_base)
    assert result["decision"] == RAW_OUTPUT_SAFETY_VALID_WITH_WARNINGS
    assert result["raw_output_safety_validation"]["warnings"]
    assert result["raw_output_safety_validation"]["sensitive_findings_count"] >= 1


def test_raw_validation_route_returns_validation(client, jobs_base):
    job_id = "compliance-job-raw-route"
    _write_clean_results(job_id, jobs_base)

    from unittest.mock import patch

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_raw_validation.JOBS_BASE", jobs_base
    ):
        response = client.get(f"/compliance/jobs/{job_id}/collection/raw-validation")

    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == RAW_OUTPUT_SAFETY_VALID
    assert data["raw_output_safety_validation"]["issues"] == []
