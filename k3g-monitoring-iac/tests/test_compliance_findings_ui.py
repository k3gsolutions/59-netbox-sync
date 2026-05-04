"""Tests for findings section in compliance job UI."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from webui.app import app
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


def test_ui_shows_findings_and_hides_raw(client, jobs_base, monkeypatch):
    job = _prepare_collection_artifacts(client, jobs_base, monkeypatch)
    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_huawei_ne8000_parser.JOBS_BASE", jobs_base
    ):
        client.post(
            f"/compliance/jobs/{job['job_id']}/parse",
            json={"operator": "Keslley", "confirm_local_parse": True},
        )
    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_compare.JOBS_BASE", jobs_base
    ):
        client.post(
            f"/compliance/jobs/{job['job_id']}/compare",
            json={"operator": "Keslley", "confirm_local_compare": True},
        )

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base):
        response = client.get(f"/compliance/jobs/{job['job_id']}")

    assert response.status_code == 200
    body = response.text
    assert "Achados de Compliance" in body
    assert "Comparar com políticas" in body
    assert "COMPLIANCE-FINDINGS.md" in body
    assert "VERY_SECRET_RAW_MARKER" not in body
    assert "Aplicar correção" not in body
