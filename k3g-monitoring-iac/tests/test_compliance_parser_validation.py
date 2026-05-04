"""Tests for parser safety validation."""

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


def _parse_job(client: LocalHttpClient, jobs_base: Path, job_id: str):
    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_huawei_ne8000_parser.JOBS_BASE", jobs_base
    ):
        response = client.post(
            f"/compliance/jobs/{job_id}/parse",
            json={"operator": "Keslley", "confirm_local_parse": True},
        )
    assert response.status_code == 200
    return response.json()


def _inject_term(jobs_base: Path, job_id: str, term: str) -> None:
    parsed_file = jobs_base / job_id / "collection-results" / "devices" / "1890" / "parsed" / "parsed-inventory.json"
    data = json.loads(parsed_file.read_text(encoding="utf-8"))
    data["system"]["leak"] = f"{term} value"
    parsed_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def test_validation_valid(client, jobs_base, monkeypatch):
    job = _prepare_collection_artifacts(client, jobs_base, monkeypatch)
    _parse_job(client, jobs_base, job["job_id"])

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_parser_validation.JOBS_BASE", jobs_base
    ):
        response = client.get(f"/compliance/jobs/{job['job_id']}/parse/validation")

    assert response.status_code == 200
    data = response.json()
    assert data["decision"] in {"PARSER_SAFETY_VALID", "PARSER_SAFETY_VALID_WITH_WARNINGS"}
    assert data["parser_safety_validation"]["raw_not_displayed_in_ui"] is True


@pytest.mark.parametrize("term", ["password", "token", "cipher"])
def test_validation_blocks_sensitive_terms(client, jobs_base, monkeypatch, term):
    job = _prepare_collection_artifacts(client, jobs_base, monkeypatch)
    _parse_job(client, jobs_base, job["job_id"])
    _inject_term(jobs_base, job["job_id"], term)

    with patch("webui.services.compliance_jobs.JOBS_BASE", jobs_base), patch(
        "webui.services.compliance_parser_validation.JOBS_BASE", jobs_base
    ):
        response = client.get(f"/compliance/jobs/{job['job_id']}/parse/validation")

    assert response.status_code == 409
    assert response.json()["decision"] == "PARSER_SAFETY_INVALID"
