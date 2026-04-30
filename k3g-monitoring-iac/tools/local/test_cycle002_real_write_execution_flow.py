#!/usr/bin/env python3
"""Cycle-002 real-write execution flow tests."""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from webui.app import app  # noqa: E402
from tools.local.controlled_cycle_execute_real_write_once_v2 import execute_real_write_once  # noqa: E402
from tools.local.controlled_cycle_post_write_verification_v2 import verify_post_write  # noqa: E402
from tools.local.controlled_cycle_post_write_compliance_rerun_v2 import rerun_compliance  # noqa: E402
from tools.local.controlled_cycle_build_closure_package_v2 import build_closure_package  # noqa: E402


class FakeResponse:
    def __init__(self, status: int, payload: dict[str, object], headers: dict[str, str] | None = None):
        self.status = status
        self._body = json.dumps(payload).encode("utf-8")
        self._headers = headers or {}

    def read(self) -> bytes:
        return self._body

    def getheader(self, name: str, default: str | None = None) -> str | None:
        return self._headers.get(name, default)


class FakeConn:
    def __init__(self, responses: list[FakeResponse]):
        self.responses = responses
        self.calls: list[tuple[str, str, bytes | None]] = []

    def request(self, method: str, path: str, body: bytes | None = None, headers: dict[str, str] | None = None):
        self.calls.append((method, path, body))

    def getresponse(self):
        if not self.responses:
            raise AssertionError("no fake response left")
        return self.responses.pop(0)


def fake_factory(responses: list[FakeResponse]):
    conn = FakeConn(responses)

    def factory(_host: str):
        return conn

    factory.conn = conn  # type: ignore[attr-defined]
    return factory


async def call_asgi(path: str) -> tuple[int, str]:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 8000),
        "root_path": "",
    }
    messages = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    await app(scope, receive, send)
    status = 0
    body = b""
    for msg in messages:
        if msg["type"] == "http.response.start":
            status = msg["status"]
        elif msg["type"] == "http.response.body":
            body += msg.get("body", b"")
    return status, body.decode("utf-8", errors="ignore")


def make_chain(tmp: Path, *, endpoint: str = "/api/dcim/interfaces/1/") -> tuple[Path, Path, Path]:
    cycle_dir = tmp / "reports/controlled-operation/cycle-002"
    exec_dir = cycle_dir / "real-write-execution"
    auth_dir = cycle_dir / "real-write-authorization"
    exec_dir.mkdir(parents=True, exist_ok=True)
    auth_dir.mkdir(parents=True, exist_ok=True)
    package = {
        "execution_package_id": "exec-cycle-002-test",
        "cycle_id": "cycle-002",
        "device": "4WNET-MNS-KTG-RX",
        "device_id": "1890",
        "apply_plan_id": "apply-plan-cycle-002-test",
        "authorization_id": "auth-cycle-002-test",
        "generated_at": "2026-04-30T00:00:00+00:00",
        "status": "prepared",
        "mode": "real_write_prepared",
        "execution_allowed": False,
        "token_required_in_next_phase": True,
        "explicit_confirm_required": True,
        "one_shot_execution": True,
        "max_items": 3,
        "items": [
            {
                "approval_id": "approval-1",
                "object_type": "interface",
                "object_key": "eth0",
                "method": "POST",
                "target_endpoint": endpoint,
                "proposed_payload": {"id": 1, "name": "eth0"},
                "expected_result": "created",
                "rollback_hint": "manual only",
                "pre_write_checks": ["local_validation"],
                "post_write_checks": ["GET verify"],
            }
        ],
        "safety_confirmations": {
            "no_write_executed": True,
            "no_token_read": True,
            "no_network_call": True,
            "package_only": True,
            "real_write_not_executed": True,
        },
        "required_next_phase": "FASE_4_59_CYCLE002_EXECUTE_REAL_WRITE_ONCE",
        "required_execution_phrase": "EXECUTAR_ESCRITA_REAL_CYCLE-002_4WNET-MNS-KTG-RX_exec-cycle-002-test",
    }
    freeze = {
        "cycle_id": "cycle-002",
        "decision": "CYCLE_READY_FOR_REAL_WRITE_PHASE",
        "issues": [],
        "no_write_executed": True,
        "no_token_read": True,
        "no_network_call": True,
        "no_netbox_write": True,
        "no_apply_plan_created": True,
    }
    (exec_dir / "execution_package.json").write_text(json.dumps(package, indent=2), encoding="utf-8")
    (exec_dir / "CYCLE-002-FINAL-NO-WRITE-FREEZE-CHECK.json").write_text(json.dumps(freeze, indent=2), encoding="utf-8")
    return cycle_dir, exec_dir / "execution_package.json", exec_dir / "CYCLE-002-FINAL-NO-WRITE-FREEZE-CHECK.json"


def test_01_execute_blocks_without_confirm() -> None:
    with tempfile.TemporaryDirectory() as td:
        _, pkg, _ = make_chain(Path(td))
        out_json = Path(td) / "out.json"
        out_md = Path(td) / "out.md"
        result = execute_real_write_once(
            cycle_id="cycle-002",
            execution_package_path=pkg,
            operator="Keslley",
            confirm_execution_phrase="EXECUTAR_ESCRITA_REAL_CYCLE-002_4WNET-MNS-KTG-RX_exec-cycle-002-test",
            confirm_real_write_once=False,
            netbox_url="https://docs.k3gsolutions.com.br",
            output_json=out_json,
            output_md=out_md,
            token="fake",
        )
        assert result["status"] == "CYCLE_REAL_WRITE_ABORTED_PREFLIGHT_FAILED"


def test_02_execute_blocks_wrong_phrase() -> None:
    with tempfile.TemporaryDirectory() as td:
        _, pkg, _ = make_chain(Path(td))
        out_json = Path(td) / "out.json"
        out_md = Path(td) / "out.md"
        result = execute_real_write_once(
            cycle_id="cycle-002",
            execution_package_path=pkg,
            operator="Keslley",
            confirm_execution_phrase="WRONG",
            confirm_real_write_once=True,
            netbox_url="https://docs.k3gsolutions.com.br",
            output_json=out_json,
            output_md=out_md,
            token="fake",
        )
        assert result["status"] == "CYCLE_REAL_WRITE_ABORTED_PREFLIGHT_FAILED"


def test_03_execute_blocks_without_token() -> None:
    with tempfile.TemporaryDirectory() as td:
        _, pkg, _ = make_chain(Path(td))
        out_json = Path(td) / "out.json"
        out_md = Path(td) / "out.md"
        result = execute_real_write_once(
            cycle_id="cycle-002",
            execution_package_path=pkg,
            operator="Keslley",
            confirm_execution_phrase="EXECUTAR_ESCRITA_REAL_CYCLE-002_4WNET-MNS-KTG-RX_exec-cycle-002-test",
            confirm_real_write_once=True,
            netbox_url="https://docs.k3gsolutions.com.br",
            output_json=out_json,
            output_md=out_md,
            token=None,
        )
        assert "NETBOX_WRITE_TOKEN missing" in result["issues"]


def test_04_execute_blocks_freeze_not_ready() -> None:
    with tempfile.TemporaryDirectory() as td:
        cycle_dir, pkg, freeze = make_chain(Path(td))
        freeze_path = Path(freeze)
        freeze_path.write_text(json.dumps({"decision": "CYCLE_NOT_READY_FOR_REAL_WRITE_PHASE"}), encoding="utf-8")
        out_json = Path(td) / "out.json"
        out_md = Path(td) / "out.md"
        result = execute_real_write_once(
            cycle_id="cycle-002",
            execution_package_path=pkg,
            operator="Keslley",
            confirm_execution_phrase="EXECUTAR_ESCRITA_REAL_CYCLE-002_4WNET-MNS-KTG-RX_exec-cycle-002-test",
            confirm_real_write_once=True,
            netbox_url="https://docs.k3gsolutions.com.br",
            output_json=out_json,
            output_md=out_md,
            token="fake",
        )
        assert result["status"] == "CYCLE_REAL_WRITE_ABORTED_PREFLIGHT_FAILED"


def test_05_execute_blocks_patch_delete() -> None:
    with tempfile.TemporaryDirectory() as td:
        _, pkg, freeze = make_chain(Path(td))
        data = json.loads(pkg.read_text(encoding="utf-8"))
        data["items"][0]["method"] = "PATCH"
        pkg.write_text(json.dumps(data), encoding="utf-8")
        result = execute_real_write_once(
            cycle_id="cycle-002",
            execution_package_path=pkg,
            operator="Keslley",
            confirm_execution_phrase="EXECUTAR_ESCRITA_REAL_CYCLE-002_4WNET-MNS-KTG-RX_exec-cycle-002-test",
            confirm_real_write_once=True,
            netbox_url="https://docs.k3gsolutions.com.br",
            output_json=Path(td) / "out.json",
            output_md=Path(td) / "out.md",
            token="fake",
        )
        assert "method must be POST" in " ".join(result["issues"])


def test_06_execute_blocks_sync_target() -> None:
    with tempfile.TemporaryDirectory() as td:
        _, pkg, _ = make_chain(Path(td), endpoint="/sync")
        result = execute_real_write_once(
            cycle_id="cycle-002",
            execution_package_path=pkg,
            operator="Keslley",
            confirm_execution_phrase="EXECUTAR_ESCRITA_REAL_CYCLE-002_4WNET-MNS-KTG-RX_exec-cycle-002-test",
            confirm_real_write_once=True,
            netbox_url="https://docs.k3gsolutions.com.br",
            output_json=Path(td) / "out.json",
            output_md=Path(td) / "out.md",
            token="fake",
        )
        assert any("endpoint blocked" in issue for issue in result["issues"])


def test_07_execute_blocks_secret_payload() -> None:
    with tempfile.TemporaryDirectory() as td:
        _, pkg, _ = make_chain(Path(td))
        data = json.loads(pkg.read_text(encoding="utf-8"))
        data["items"][0]["proposed_payload"]["token"] = "x"
        pkg.write_text(json.dumps(data), encoding="utf-8")
        result = execute_real_write_once(
            cycle_id="cycle-002",
            execution_package_path=pkg,
            operator="Keslley",
            confirm_execution_phrase="EXECUTAR_ESCRITA_REAL_CYCLE-002_4WNET-MNS-KTG-RX_exec-cycle-002-test",
            confirm_real_write_once=True,
            netbox_url="https://docs.k3gsolutions.com.br",
            output_json=Path(td) / "out.json",
            output_md=Path(td) / "out.md",
            token="fake",
        )
        assert any("secret terms" in issue for issue in result["issues"])


def test_08_execute_does_not_save_token() -> None:
    with tempfile.TemporaryDirectory() as td:
        _, pkg, _ = make_chain(Path(td))
        out_json = Path(td) / "out.json"
        out_md = Path(td) / "out.md"
        result = execute_real_write_once(
            cycle_id="cycle-002",
            execution_package_path=pkg,
            operator="Keslley",
            confirm_execution_phrase="EXECUTAR_ESCRITA_REAL_CYCLE-002_4WNET-MNS-KTG-RX_exec-cycle-002-test",
            confirm_real_write_once=True,
            netbox_url="https://docs.k3gsolutions.com.br",
            output_json=out_json,
            output_md=out_md,
            token=None,
        )
        assert result["token_logged"] is False
        assert result["token_saved"] is False


def test_09_execute_success_with_fake_post_201() -> None:
    with tempfile.TemporaryDirectory() as td:
        _, pkg, _ = make_chain(Path(td))
        factory = fake_factory([
            FakeResponse(201, {"id": 101, "url": "/api/dcim/interfaces/101/", "name": "eth0", "object_key": "eth0"}),
            FakeResponse(200, {"id": 101, "url": "/api/dcim/interfaces/101/", "name": "eth0", "object_key": "eth0"}),
        ])
        result = execute_real_write_once(
            cycle_id="cycle-002",
            execution_package_path=pkg,
            operator="Keslley",
            confirm_execution_phrase="EXECUTAR_ESCRITA_REAL_CYCLE-002_4WNET-MNS-KTG-RX_exec-cycle-002-test",
            confirm_real_write_once=True,
            netbox_url="https://docs.k3gsolutions.com.br",
            output_json=Path(td) / "out.json",
            output_md=Path(td) / "out.md",
            token="tok",
            conn_factory=factory,
        )
        assert result["status"] == "CYCLE_REAL_WRITE_SUCCESS"
        assert result["items"][0]["verification_status"] == "verified"


def test_10_execute_get_verification() -> None:
    with tempfile.TemporaryDirectory() as td:
        _, pkg, _ = make_chain(Path(td))
        factory = fake_factory([
            FakeResponse(201, {"id": 101, "url": "/api/dcim/interfaces/101/", "name": "eth0", "object_key": "eth0"}),
            FakeResponse(200, {"id": 101, "url": "/api/dcim/interfaces/101/", "name": "eth0", "object_key": "eth0"}),
        ])
        result = execute_real_write_once(
            cycle_id="cycle-002",
            execution_package_path=pkg,
            operator="Keslley",
            confirm_execution_phrase="EXECUTAR_ESCRITA_REAL_CYCLE-002_4WNET-MNS-KTG-RX_exec-cycle-002-test",
            confirm_real_write_once=True,
            netbox_url="https://docs.k3gsolutions.com.br",
            output_json=Path(td) / "out.json",
            output_md=Path(td) / "out.md",
            token="tok",
            conn_factory=factory,
        )
        assert factory.conn.calls[1][0] == "GET"  # type: ignore[attr-defined]


def test_11_execute_stops_on_first_failure() -> None:
    with tempfile.TemporaryDirectory() as td:
        _, pkg, _ = make_chain(Path(td))
        data = json.loads(pkg.read_text(encoding="utf-8"))
        data["items"].append({**data["items"][0], "approval_id": "approval-2", "object_key": "eth1"})
        pkg.write_text(json.dumps(data), encoding="utf-8")
        factory = fake_factory([
            FakeResponse(201, {"id": 101, "url": "/api/dcim/interfaces/101/", "name": "eth0", "object_key": "eth0"}),
            FakeResponse(200, {"id": 101, "url": "/api/dcim/interfaces/101/", "name": "eth0", "object_key": "eth0"}),
            FakeResponse(500, {"detail": "boom"}),
        ])
        result = execute_real_write_once(
            cycle_id="cycle-002",
            execution_package_path=pkg,
            operator="Keslley",
            confirm_execution_phrase="EXECUTAR_ESCRITA_REAL_CYCLE-002_4WNET-MNS-KTG-RX_exec-cycle-002-test",
            confirm_real_write_once=True,
            netbox_url="https://docs.k3gsolutions.com.br",
            output_json=Path(td) / "out.json",
            output_md=Path(td) / "out.md",
            token="tok",
            conn_factory=factory,
        )
        assert result["status"] in {"CYCLE_REAL_WRITE_PARTIAL_FAILED", "CYCLE_REAL_WRITE_FAILED"}


def test_12_retry_attempted_false() -> None:
    with tempfile.TemporaryDirectory() as td:
        _, pkg, _ = make_chain(Path(td))
        result = execute_real_write_once(
            cycle_id="cycle-002",
            execution_package_path=pkg,
            operator="Keslley",
            confirm_execution_phrase="EXECUTAR_ESCRITA_REAL_CYCLE-002_4WNET-MNS-KTG-RX_exec-cycle-002-test",
            confirm_real_write_once=True,
            netbox_url="https://docs.k3gsolutions.com.br",
            output_json=Path(td) / "out.json",
            output_md=Path(td) / "out.md",
            token=None,
        )
        assert result["retry_attempted"] is False


def test_13_rollback_attempted_false() -> None:
    with tempfile.TemporaryDirectory() as td:
        _, pkg, _ = make_chain(Path(td))
        result = execute_real_write_once(
            cycle_id="cycle-002",
            execution_package_path=pkg,
            operator="Keslley",
            confirm_execution_phrase="EXECUTAR_ESCRITA_REAL_CYCLE-002_4WNET-MNS-KTG-RX_exec-cycle-002-test",
            confirm_real_write_once=True,
            netbox_url="https://docs.k3gsolutions.com.br",
            output_json=Path(td) / "out.json",
            output_md=Path(td) / "out.md",
            token=None,
        )
        assert result["rollback_attempted"] is False


def test_14_verification_not_applicable_on_abort() -> None:
    with tempfile.TemporaryDirectory() as td:
        cycle_dir, pkg, freeze = make_chain(Path(td))
        result = execute_real_write_once(
            cycle_id="cycle-002",
            execution_package_path=pkg,
            operator="Keslley",
            confirm_execution_phrase="EXECUTAR_ESCRITA_REAL_CYCLE-002_4WNET-MNS-KTG-RX_exec-cycle-002-test",
            confirm_real_write_once=True,
            netbox_url="https://docs.k3gsolutions.com.br",
            output_json=Path(td) / "out.json",
            output_md=Path(td) / "out.md",
            token=None,
        )
        out_json = Path(td) / "verify.json"
        out_md = Path(td) / "verify.md"
        verification = verify_post_write(
            cycle_id="cycle-002",
            execution_result_path=Path(td) / "out.json",
            execution_package_path=pkg,
            netbox_url="https://docs.k3gsolutions.com.br",
            device="4WNET-MNS-KTG-RX",
            device_id="1890",
            output_json=out_json,
            output_md=out_md,
            token=None,
        )
        assert verification["status"] == "NOT_APPLICABLE"


def test_15_verification_uses_only_get() -> None:
    with tempfile.TemporaryDirectory() as td:
        _, pkg, _ = make_chain(Path(td))
        execution_result = {
            "cycle_id": "cycle-002",
            "execution_package_id": "exec-cycle-002-test",
            "status": "CYCLE_REAL_WRITE_SUCCESS",
            "items": [
                {
                    "approval_id": "approval-1",
                    "object_type": "interface",
                    "object_key": "eth0",
                    "response_id": "101",
                    "response_url": "/api/dcim/interfaces/101/",
                    "verification_status": "verified",
                }
            ],
        }
        (Path(td) / "result.json").write_text(json.dumps(execution_result), encoding="utf-8")
        factory = fake_factory([FakeResponse(200, {"id": 101, "name": "eth0", "object_key": "eth0"})])
        verification = verify_post_write(
            cycle_id="cycle-002",
            execution_result_path=Path(td) / "result.json",
            execution_package_path=pkg,
            netbox_url="https://docs.k3gsolutions.com.br",
            device="4WNET-MNS-KTG-RX",
            device_id="1890",
            output_json=Path(td) / "verify.json",
            output_md=Path(td) / "verify.md",
            token="tok",
            conn_factory=factory,
        )
        assert factory.conn.calls[0][0] == "GET"  # type: ignore[attr-defined]


def test_16_compliance_rerun_read_only() -> None:
    with tempfile.TemporaryDirectory() as td:
        execution_result = {
            "cycle_id": "cycle-002",
            "device": "4WNET-MNS-KTG-RX",
            "device_id": "1890",
            "status": "CYCLE_REAL_WRITE_SUCCESS",
            "items": [{"approval_id": "approval-1", "verification_status": "verified"}],
        }
        verification = {"cycle_id": "cycle-002", "decision": "CYCLE_POST_WRITE_VERIFICATION_PASSED", "items": [{"approval_id": "approval-1", "verification_status": "verified"}]}
        (Path(td) / "result.json").write_text(json.dumps(execution_result), encoding="utf-8")
        (Path(td) / "verification.json").write_text(json.dumps(verification), encoding="utf-8")
        (Path(td) / "policies").mkdir()
        (Path(td) / "policies" / "dummy.yaml").write_text("version: 1\n", encoding="utf-8")
        compliance = rerun_compliance(
            cycle_id="cycle-002",
            device="4WNET-MNS-KTG-RX",
            device_id="1890",
            execution_result_path=Path(td) / "result.json",
            post_write_verification_path=Path(td) / "verification.json",
            policy_registry=Path(td) / "policies",
            output_json=Path(td) / "compliance.json",
            output_md=Path(td) / "compliance.md",
        )
        assert compliance["status"].startswith("CYCLE_POST_WRITE_COMPLIANCE")


def test_17_closure_success_when_all_pass() -> None:
    with tempfile.TemporaryDirectory() as td:
        exec_result = {"cycle_id": "cycle-002", "device": "4WNET-MNS-KTG-RX", "device_id": "1890", "status": "CYCLE_REAL_WRITE_SUCCESS", "items": [{"approval_id": "approval-1", "verification_status": "verified"}]}
        verification = {"cycle_id": "cycle-002", "decision": "CYCLE_POST_WRITE_VERIFICATION_PASSED", "items": [{"approval_id": "approval-1", "verification_status": "verified"}]}
        compliance = {"cycle_id": "cycle-002", "decision": "CYCLE_POST_WRITE_COMPLIANCE_PASSED", "items": [{"approval_id": "approval-1"}]}
        (Path(td) / "execution.json").write_text(json.dumps(exec_result), encoding="utf-8")
        (Path(td) / "verification.json").write_text(json.dumps(verification), encoding="utf-8")
        (Path(td) / "compliance.json").write_text(json.dumps(compliance), encoding="utf-8")
        closure = build_closure_package(
            cycle_id="cycle-002",
            device="4WNET-MNS-KTG-RX",
            device_id="1890",
            execution_result_path=Path(td) / "execution.json",
            post_write_verification_path=Path(td) / "verification.json",
            post_write_compliance_path=Path(td) / "compliance.json",
            output_dir=Path(td) / "closure",
            report=Path(td) / "closure.md",
        )
        assert closure["status"] == "CYCLE_CLOSED_SUCCESS"


def test_18_closure_action_required_on_failure() -> None:
    with tempfile.TemporaryDirectory() as td:
        exec_result = {"cycle_id": "cycle-002", "device": "4WNET-MNS-KTG-RX", "device_id": "1890", "status": "CYCLE_REAL_WRITE_FAILED", "items": []}
        verification = {"cycle_id": "cycle-002", "decision": "CYCLE_POST_WRITE_VERIFICATION_FAILED", "items": []}
        compliance = {"cycle_id": "cycle-002", "decision": "CYCLE_POST_WRITE_COMPLIANCE_FAILED", "items": []}
        (Path(td) / "execution.json").write_text(json.dumps(exec_result), encoding="utf-8")
        (Path(td) / "verification.json").write_text(json.dumps(verification), encoding="utf-8")
        (Path(td) / "compliance.json").write_text(json.dumps(compliance), encoding="utf-8")
        closure = build_closure_package(
            cycle_id="cycle-002",
            device="4WNET-MNS-KTG-RX",
            device_id="1890",
            execution_result_path=Path(td) / "execution.json",
            post_write_verification_path=Path(td) / "verification.json",
            post_write_compliance_path=Path(td) / "compliance.json",
            output_dir=Path(td) / "closure",
            report=Path(td) / "closure.md",
        )
        assert closure["status"] == "CYCLE_CLOSED_ACTION_REQUIRED"


def test_19_webui_real_write_routes_200() -> None:
    paths = [
        "/controlled-operation/cycle-002/real-write/execution",
        "/controlled-operation/cycle-002/real-write/verification",
        "/controlled-operation/cycle-002/real-write/compliance",
        "/controlled-operation/cycle-002/real-write/closure",
    ]
    for path in paths:
        status, body = asyncio.run(call_asgi(path))
        assert status == 200
        assert "apply" not in body.lower()
        assert "sync" not in body.lower()
        assert "token" not in body.lower()


def test_20_no_netbox_write_tools_use_token() -> None:
    for text in [
        Path(ROOT / "tools/local/controlled_cycle_execute_real_write_once_v2.py").read_text(encoding="utf-8"),
        Path(ROOT / "tools/local/controlled_cycle_post_write_verification_v2.py").read_text(encoding="utf-8"),
        Path(ROOT / "tools/local/controlled_cycle_post_write_compliance_rerun_v2.py").read_text(encoding="utf-8"),
        Path(ROOT / "tools/local/controlled_cycle_build_closure_package_v2.py").read_text(encoding="utf-8"),
    ]:
        assert "NETBOX_WRITE_TOKEN" not in text or "os.environ.get" in text


if __name__ == "__main__":
    tests = [name for name in globals() if name.startswith("test_")]
    passed = 0
    for name in tests:
        globals()[name]()
        passed += 1
    print(f"{passed}/{len(tests)}")
