#!/usr/bin/env python3
"""Tests for Cycle-002 Week 1 intake, preparation, and validation."""

from __future__ import annotations

import asyncio
import csv
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from webui.app import app
from tools.local.controlled_cycle_activate_intake import main as activate_main
from tools.local.controlled_cycle_week1_prepare_v2 import main as prepare_main
from tools.local.controlled_cycle_week1_response_intake_v2 import main as intake_main
from tools.local.controlled_cycle_week1_validate_v2 import main as validate_main

try:  # pragma: no cover - fallback only
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover - fallback only
    TestClient = None


ROOT = Path(__file__).parent.parent.parent


class SimpleResponse:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text


class ASGIClient:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    async def _aget(self, path: str) -> SimpleResponse:
        raw_path = path.split("?", 1)[0].encode("utf-8")
        query_string = path.split("?", 1)[1].encode("utf-8") if "?" in path else b""
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": path.split("?", 1)[0],
            "raw_path": raw_path,
            "query_string": query_string,
            "headers": [],
            "client": ("testclient", 123),
            "server": ("testserver", 80),
        }
        status_code = 500
        body_parts: list[bytes] = []
        seen = False

        async def receive():
            nonlocal seen
            if not seen:
                seen = True
                return {"type": "http.request", "body": b"", "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            elif message["type"] == "http.response.body":
                body_parts.append(message.get("body", b""))

        await app(scope, receive, send)
        return SimpleResponse(status_code, b"".join(body_parts).decode("utf-8", errors="ignore"))

    def get(self, path: str):
        return asyncio.run(self._aget(path))


def run_main(main_func, argv: list[str]) -> int:
    with patch("sys.argv", argv):
        return main_func()


def make_cycle(root: Path, *, start_gate: str = "CYCLE_START_READY_WITH_RESTRICTIONS") -> Path:
    cycle_dir = root / "cycle-002"
    cycle_dir.mkdir(parents=True, exist_ok=True)
    index = {
        "measured_at": "2026-04-29T00:00:00+00:00",
        "total_cycles": 1,
        "overall_status": "IN_PROGRESS",
        "cycles": [
            {
                "cycle_id": "cycle-001",
                "current_status": "closed_with_restrictions",
            }
        ],
    }
    (root / "controlled-operation-index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    scope = {
        "cycle_id": "cycle-002",
        "device": "4WNET-MNS-KTG-RX",
        "device_id": "1890",
        "status": "PLANNED_NOT_STARTED",
        "created_at": "2026-04-29T00:00:00+00:00",
        "max_items": 3,
        "allowed_methods": ["POST"],
        "forbidden_methods": ["PATCH", "DELETE"],
        "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
        "requires_week1": True,
        "requires_week2": True,
        "requires_approval_records": True,
        "requires_applyplan_dryrun": True,
        "requires_real_write_authorization": True,
        "requires_post_write_verification": True,
    }
    (cycle_dir / "CYCLE-002-SCOPE.json").write_text(json.dumps(scope, indent=2), encoding="utf-8")
    (cycle_dir / "CYCLE-002-STATUS.md").write_text("# CYCLE-002\n\n## Status Atual\nSTART_READY\n", encoding="utf-8")
    (cycle_dir / "cycle-002-start-gate.json").write_text(
        json.dumps(
            {
                "cycle_id": "cycle-002",
                "previous_cycle": "cycle-001",
                "decision": start_gate,
                "reason": "test",
                "decided_at": "2026-04-29T00:00:00+00:00",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return cycle_dir


def make_responses(responses_dir: Path, valid: bool = True) -> None:
    responses_dir.mkdir(parents=True, exist_ok=True)
    service = {
        "team": "service",
        "object_type": "subinterface",
        "object_key": "svc-001",
        "status": "answered",
        "tenant": "Cliente UAT",
        "service_type": "customer-internet",
        "criticality": "gold",
        "owner": "UAT Service Owner",
        "evidence": "UAT contract",
        "notes": "UAT service response",
        "updated_by": "uat",
    }
    network = {
        "team": "network_ops",
        "object_type": "ip_address",
        "object_key": "ip-001",
        "status": "answered",
        "interface": "GigabitEthernet0/5/0",
        "vrf": "_public_",
        "relation_type": "infrastructure",
        "service_relation": "",
        "owner": "UAT Network Ops",
        "evidence": "UAT evidence",
        "notes": "UAT network response",
        "updated_by": "uat",
    }
    bgp = {
        "team": "bgp",
        "object_type": "bgp_peer",
        "object_key": "bgp-001",
        "status": "answered",
        "remote_asn": "65000",
        "remote_bgp_group": "UAT-GROUP",
        "policy_intent": "UAT policy intent",
        "owner": "UAT BGP Owner",
        "criticality": "silver",
        "evidence": "UAT evidence",
        "notes": "UAT bgp response",
        "updated_by": "uat",
    }
    if not valid:
        bgp["remote_asn"] = "999999999999"
    for name, data in {
        "service-team-response.json": service,
        "network-ops-response.json": network,
        "bgp-team-response.json": bgp,
    }.items():
        (responses_dir / name).write_text(json.dumps(data, indent=2), encoding="utf-8")


def test_01_activate_allows_ready_with_restrictions() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        root = tmpdir / "reports" / "controlled-operation"
        cycle_dir = make_cycle(root, start_gate="CYCLE_START_READY_WITH_RESTRICTIONS")
        output = cycle_dir / "CYCLE-002-INTAKE-ACTIVATION.md"
        output_json = cycle_dir / "cycle-002-intake-activation.json"
        code = run_main(
            activate_main,
            [
                "prog",
                "--cycle-id",
                "cycle-002",
                "--device",
                "4WNET-MNS-KTG-RX",
                "--device-id",
                "1890",
                "--cycle-dir",
                str(cycle_dir),
                "--start-gate",
                str(cycle_dir / "cycle-002-start-gate.json"),
                "--operation-index",
                str(root / "controlled-operation-index.json"),
                "--output",
                str(output),
                "--output-json",
                str(output_json),
            ],
        )
        assert code == 0
        payload = json.loads(output_json.read_text(encoding="utf-8"))
        assert payload["decision"] == "CYCLE_INTAKE_ACTIVATED_WITH_RESTRICTIONS"


def test_02_prepare_week1_creates_structure() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        root = tmpdir / "reports" / "controlled-operation"
        cycle_dir = make_cycle(root)
        (cycle_dir / "CYCLE-002-STATUS.md").write_text("# CYCLE-002\n\n## Status Atual\nINTAKE_ACTIVATED\n", encoding="utf-8")
        week1_dir = cycle_dir / "week1"
        code = run_main(
            prepare_main,
            [
                "prog",
                "--cycle-id",
                "cycle-002",
                "--device",
                "4WNET-MNS-KTG-RX",
                "--device-id",
                "1890",
                "--cycle-dir",
                str(cycle_dir),
                "--output-dir",
                str(week1_dir),
            ],
        )
        assert code == 0
        assert (week1_dir / "responses").exists()
        assert (week1_dir / "audit").exists()


def test_03_week1_intake_counts_responses() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        root = tmpdir / "reports" / "controlled-operation"
        cycle_dir = make_cycle(root)
        week1_dir = cycle_dir / "week1"
        responses_dir = week1_dir / "responses"
        make_responses(responses_dir, valid=True)
        (week1_dir / "CYCLE-002-WEEK1-STATUS.md").write_text("# CYCLE-002\n\n## Status Atual\nWEEK1_READY_FOR_RESPONSES\n", encoding="utf-8")
        output = week1_dir / "CYCLE-002-WEEK1-INTAKE.md"
        output_json = week1_dir / "cycle-002-week1-intake.json"
        code = run_main(
            intake_main,
            [
                "prog",
                "--cycle-id",
                "cycle-002",
                "--device",
                "4WNET-MNS-KTG-RX",
                "--device-id",
                "1890",
                "--cycle-dir",
                str(cycle_dir),
                "--responses-dir",
                str(responses_dir),
                "--output",
                str(output),
                "--output-json",
                str(output_json),
            ],
        )
        assert code == 0
        payload = json.loads(output_json.read_text(encoding="utf-8"))
        assert payload["summary"]["responded"] == 3


def test_04_week1_validation_accepts_valid_responses() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        root = tmpdir / "reports" / "controlled-operation"
        cycle_dir = make_cycle(root)
        week1_dir = cycle_dir / "week1"
        responses_dir = week1_dir / "responses"
        make_responses(responses_dir, valid=True)
        (week1_dir / "CYCLE-002-WEEK1-STATUS.md").write_text("# CYCLE-002\n\n## Status Atual\nWEEK1_READY_FOR_RESPONSES\n", encoding="utf-8")
        output = week1_dir / "CYCLE-002-WEEK1-VALIDATION.md"
        output_json = week1_dir / "cycle-002-week1-validation.json"
        code = run_main(
            validate_main,
            [
                "prog",
                "--cycle-id",
                "cycle-002",
                "--device",
                "4WNET-MNS-KTG-RX",
                "--device-id",
                "1890",
                "--cycle-dir",
                str(cycle_dir),
                "--responses-dir",
                str(responses_dir),
                "--policy-registry",
                str(ROOT / "policies" / "compliance"),
                "--output",
                str(output),
                "--output-json",
                str(output_json),
            ],
        )
        assert code == 0
        payload = json.loads(output_json.read_text(encoding="utf-8"))
        assert payload["summary"]["ready_for_week2_review"] >= 1


def test_05_week1_validation_blocks_bad_asn() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        root = tmpdir / "reports" / "controlled-operation"
        cycle_dir = make_cycle(root)
        week1_dir = cycle_dir / "week1"
        responses_dir = week1_dir / "responses"
        make_responses(responses_dir, valid=False)
        output = week1_dir / "CYCLE-002-WEEK1-VALIDATION.md"
        output_json = week1_dir / "cycle-002-week1-validation.json"
        code = run_main(
            validate_main,
            [
                "prog",
                "--cycle-id",
                "cycle-002",
                "--device",
                "4WNET-MNS-KTG-RX",
                "--device-id",
                "1890",
                "--cycle-dir",
                str(cycle_dir),
                "--responses-dir",
                str(responses_dir),
                "--policy-registry",
                str(ROOT / "policies" / "compliance"),
                "--output",
                str(output),
                "--output-json",
                str(output_json),
            ],
        )
        assert code == 1
        payload = json.loads(output_json.read_text(encoding="utf-8"))
        assert payload["summary"]["blocked"] >= 1


def test_06_ui_cycle_002_routes() -> None:
    with (TestClient(app) if TestClient is not None else ASGIClient()) as client:
        assert client.get("/controlled-operation/cycle-002").status_code == 200
        assert client.get("/controlled-operation/cycle-002/start-gate").status_code == 200
        assert client.get("/controlled-operation/cycle-002/week1").status_code == 200
        assert client.get("/controlled-operation/cycle-002/week1/intake").status_code == 200
        assert client.get("/controlled-operation/cycle-002/week1/validation").status_code == 200


def test_07_no_token_strings() -> None:
    sources = [
        ROOT / "tools/local/controlled_cycle_activate_intake.py",
        ROOT / "tools/local/controlled_cycle_week1_prepare_v2.py",
        ROOT / "tools/local/controlled_cycle_week1_response_intake_v2.py",
        ROOT / "tools/local/controlled_cycle_week1_validate_v2.py",
    ]
    for source in sources:
        text = source.read_text(encoding="utf-8").lower()
        assert "authorization: token" not in text
        assert "bearer " not in text
        assert "netbox_write_token=" not in text


def main() -> int:
    tests = [
        test_01_activate_allows_ready_with_restrictions,
        test_02_prepare_week1_creates_structure,
        test_03_week1_intake_counts_responses,
        test_04_week1_validation_accepts_valid_responses,
        test_05_week1_validation_blocks_bad_asn,
        test_06_ui_cycle_002_routes,
        test_07_no_token_strings,
    ]
    for idx, test in enumerate(tests, start=1):
        test()
        print(f"✓ Test {idx}: {test.__name__}")
    print(f"\n{len(tests)}/{len(tests)} cycle-002 week1 tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
