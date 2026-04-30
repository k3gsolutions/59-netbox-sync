#!/usr/bin/env python3
"""Cycle-002 dry-run to freeze flow tests."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from webui.app import app  # noqa: E402


SCRIPTS = {
    "normalize": ROOT / "tools/local/controlled_cycle_normalize_approved_dir_v2.py",
    "dryrun_gate": ROOT / "tools/local/controlled_cycle_dryrun_execution_gate_v2.py",
    "simulate": ROOT / "tools/local/controlled_cycle_execute_dryrun_simulation_v2.py",
    "readiness": ROOT / "tools/local/controlled_cycle_real_write_readiness_gate_v2.py",
    "authorize": ROOT / "tools/local/controlled_cycle_build_real_write_authorization_package_v2.py",
    "preflight": ROOT / "tools/local/controlled_cycle_real_write_final_preflight_gate_v2.py",
    "execution": ROOT / "tools/local/controlled_cycle_build_real_write_execution_package_v2.py",
    "validate": ROOT / "tools/local/controlled_cycle_validate_real_write_execution_package_v2.py",
    "freeze": ROOT / "tools/local/controlled_cycle_final_no_write_freeze_check_v2.py",
}


def run(cmd: list[str], expect: int = 0, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=cwd or ROOT, text=True, capture_output=True)
    if proc.returncode != expect:
        raise AssertionError(f"command failed: {cmd}\nstdout={proc.stdout}\nstderr={proc.stderr}")
    return proc


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


def make_approved_record(path: Path) -> Path:
    approved_dir = path / "reports/controlled-operation/cycle-002/approvals/approved"
    compat = approved_dir / "approved"
    approved_dir.mkdir(parents=True, exist_ok=True)
    compat.mkdir(parents=True, exist_ok=True)
    record = {
        "approval_id": "approval-203-0-113-1",
        "cycle_id": "cycle-002",
        "device": "4WNET-MNS-KTG-RX",
        "device_id": "1890",
        "object_type": "bgp_peer",
        "object_key": "203.0.113.1",
        "status": "approved",
        "state": "approved",
        "approved_by": "Keslley",
        "approved_at": "2026-04-30T00:00:00+00:00",
        "approval_reason": "ok",
        "evidence_hash": "sha256:test",
        "proposed_payload": {
            "cycle_id": "cycle-002",
            "device": "4WNET-MNS-KTG-RX",
            "device_id": "1890",
            "team": "bgp",
            "object_type": "bgp_peer",
            "object_key": "203.0.113.1",
            "action": "safe_create_staged",
        },
        "review": {
            "status": "proposed",
            "reviewed_by": "Keslley",
            "reviewed_at": "2026-04-30T00:00:00+00:00",
        },
        "state_history": [
            {"event": "draft_review_created", "timestamp": "2026-04-30T00:00:00+00:00"},
            {"event": "approved_for_cycle_dryrun_applyplan", "timestamp": "2026-04-30T00:00:01+00:00"},
        ],
        "safety_confirmations": {
            "no_netbox_write": True,
            "no_apply_plan_created": True,
            "manual_review_required": True,
            "human_decision_required": True,
            "proposed_only": True,
        },
    }
    (compat / "approval-203-0-113-1.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return approved_dir


def make_apply_plan(path: Path) -> Path:
    dryrun = path / "reports/controlled-operation/cycle-002/apply-plans/dry-run"
    dryrun.mkdir(parents=True, exist_ok=True)
    plan = {
        "apply_plan_id": "apply-plan-cycle-002-test",
        "cycle_id": "cycle-002",
        "device": "4WNET-MNS-KTG-RX",
        "device_id": "1890",
        "mode": "dry_run",
        "status": "generated",
        "generated_at": "2026-04-30T00:00:00+00:00",
        "source_approval_records": ["approval-203-0-113-1.json"],
        "items": [
            {
                "item_id": "203.0.113.1",
                "approval_id": "approval-203-0-113-1",
                "object_type": "bgp_peer",
                "object_key": "203.0.113.1",
                "action": "safe_create_staged",
                "method": "POST",
                "target_endpoint": "/",
                "proposed_payload": {"object_key": "203.0.113.1"},
                "expected_result": "dry-run only",
                "rollback_hint": "manual only",
                "evidence_hash": "sha256:test",
            }
        ],
        "safety_flags": {
            "dry_run_only": True,
            "no_netbox_write": True,
            "no_token_required": True,
            "no_apply_execution": True,
            "manual_execution_gate_required": True,
            "generated_from_approved_records": True,
        },
        "execution_policy": {
            "can_execute_real_write": False,
            "requires_next_gate": True,
            "next_gate": "FASE_4_51_CYCLE002_DRYRUN_EXECUTION_GATE",
            "max_items": 3,
            "allowed_methods": ["POST"],
            "forbidden_methods": ["PATCH", "DELETE"],
            "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
        },
    }
    plan_file = dryrun / "apply-plan-cycle-002-test.json"
    plan_file.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return plan_file


def make_validation_report(path: Path, decision: str = "CYCLE_DRYRUN_APPLYPLAN_VALID") -> Path:
    report = path / "reports/controlled-operation/cycle-002/apply-plans/CYCLE-002-DRYRUN-APPLYPLAN-VALIDATION.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(f"# report\n\n{decision}\n", encoding="utf-8")
    return report


def positive_chain(tmp: Path):
    approved_dir = make_approved_record(tmp)
    plan_file = make_apply_plan(tmp)
    validation_report = make_validation_report(tmp)
    return approved_dir, plan_file, validation_report


def test_01_dryrun_gate_ready() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _, plan_file, validation_report = positive_chain(tmp)
        out = tmp / "out.md"
        out_json = tmp / "out.json"
        run([
            "python3", str(SCRIPTS["dryrun_gate"]),
            "--cycle-id", "cycle-002",
            "--apply-plan", str(plan_file),
            "--validation-report", str(validation_report),
            "--output", str(out),
            "--output-json", str(out_json),
        ])
        payload = json.loads(out_json.read_text(encoding="utf-8"))
        assert payload["decision"].startswith("CYCLE_DRYRUN_EXECUTION_READY")


def test_02_dryrun_gate_blocks_real_write_true() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _, plan_file, validation_report = positive_chain(tmp)
        data = json.loads(plan_file.read_text(encoding="utf-8"))
        data["execution_policy"]["can_execute_real_write"] = True
        plan_file.write_text(json.dumps(data), encoding="utf-8")
        out = tmp / "out.md"
        out_json = tmp / "out.json"
        run([
            "python3", str(SCRIPTS["dryrun_gate"]),
            "--cycle-id", "cycle-002",
            "--apply-plan", str(plan_file),
            "--validation-report", str(validation_report),
            "--output", str(out),
            "--output-json", str(out_json),
        ], expect=1)


def test_03_simulation_generates_result() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _, plan_file, validation_report = positive_chain(tmp)
        gate_out = tmp / "gate.md"
        gate_json = tmp / "gate.json"
        run([
            "python3", str(SCRIPTS["dryrun_gate"]),
            "--cycle-id", "cycle-002",
            "--apply-plan", str(plan_file),
            "--validation-report", str(validation_report),
            "--output", str(gate_out),
            "--output-json", str(gate_json),
        ])
        sim_out = tmp / "sim.md"
        sim_json = tmp / "sim.json"
        run([
            "python3", str(SCRIPTS["simulate"]),
            "--cycle-id", "cycle-002",
            "--apply-plan", str(plan_file),
            "--execution-gate", str(gate_out),
            "--output", str(sim_out),
            "--result-json", str(sim_json),
        ])
        payload = json.loads(sim_json.read_text(encoding="utf-8"))
        assert payload["safety_confirmations"]["local_only"] is True


def test_04_simulation_no_prohibited_imports() -> None:
    source = SCRIPTS["simulate"].read_text(encoding="utf-8")
    for term in ["requests", "pynetbox", "httpx", "urllib.request", "socket", "subprocess"]:
        assert term not in source


def test_05_simulation_no_token_read() -> None:
    source = SCRIPTS["simulate"].read_text(encoding="utf-8")
    assert "NETBOX_WRITE_TOKEN" not in source


def test_06_real_write_readiness_ready() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        approved_dir, plan_file, validation_report = positive_chain(tmp)
        gate_out = tmp / "gate.md"
        gate_json = tmp / "gate.json"
        run([
            "python3", str(SCRIPTS["dryrun_gate"]),
            "--cycle-id", "cycle-002",
            "--apply-plan", str(plan_file),
            "--validation-report", str(validation_report),
            "--output", str(gate_out),
            "--output-json", str(gate_json),
        ])
        sim_out = tmp / "sim.md"
        sim_json = tmp / "sim.json"
        run([
            "python3", str(SCRIPTS["simulate"]),
            "--cycle-id", "cycle-002",
            "--apply-plan", str(plan_file),
            "--execution-gate", str(gate_out),
            "--output", str(sim_out),
            "--result-json", str(sim_json),
        ])
        readiness_out = tmp / "readiness.md"
        readiness_json = tmp / "readiness.json"
        run([
            "python3", str(SCRIPTS["readiness"]),
            "--cycle-id", "cycle-002",
            "--apply-plan", str(plan_file),
            "--simulation-result", str(sim_json),
            "--simulation-report", str(sim_out),
            "--dryrun-execution-gate", str(gate_out),
            "--approved-dir", str(approved_dir),
            "--output", str(readiness_out),
            "--output-json", str(readiness_json),
        ])
        payload = json.loads(readiness_json.read_text(encoding="utf-8"))
        assert payload["decision"].startswith("CYCLE_READY")


def test_07_real_write_readiness_accepts_compat_approved_dir() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        approved_dir = make_approved_record(tmp)
        assert (approved_dir / "approved" / "approval-203-0-113-1.json").exists()
        plan_file = make_apply_plan(tmp)
        validation_report = make_validation_report(tmp)
        gate_out = tmp / "gate.md"
        gate_json = tmp / "gate.json"
        run([
            "python3", str(SCRIPTS["dryrun_gate"]),
            "--cycle-id", "cycle-002",
            "--apply-plan", str(plan_file),
            "--validation-report", str(validation_report),
            "--output", str(gate_out),
            "--output-json", str(gate_json),
        ])
        sim_out = tmp / "sim.md"
        sim_json = tmp / "sim.json"
        run([
            "python3", str(SCRIPTS["simulate"]),
            "--cycle-id", "cycle-002",
            "--apply-plan", str(plan_file),
            "--execution-gate", str(gate_out),
            "--output", str(sim_out),
            "--result-json", str(sim_json),
        ])
        readiness_out = tmp / "readiness.md"
        readiness_json = tmp / "readiness.json"
        run([
            "python3", str(SCRIPTS["readiness"]),
            "--cycle-id", "cycle-002",
            "--apply-plan", str(plan_file),
            "--simulation-result", str(sim_json),
            "--simulation-report", str(sim_out),
            "--dryrun-execution-gate", str(gate_out),
            "--approved-dir", str(approved_dir),
            "--output", str(readiness_out),
            "--output-json", str(readiness_json),
        ])
        assert "approval-203-0-113-1.json" in readiness_json.read_text(encoding="utf-8")


def test_08_authorization_phrase_generated() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        approved_dir, plan_file, validation_report = positive_chain(tmp)
        gate_out = tmp / "gate.md"
        gate_json = tmp / "gate.json"
        run(["python3", str(SCRIPTS["dryrun_gate"]), "--cycle-id", "cycle-002", "--apply-plan", str(plan_file), "--validation-report", str(validation_report), "--output", str(gate_out), "--output-json", str(gate_json)])
        sim_out = tmp / "sim.md"
        sim_json = tmp / "sim.json"
        run(["python3", str(SCRIPTS["simulate"]), "--cycle-id", "cycle-002", "--apply-plan", str(plan_file), "--execution-gate", str(gate_out), "--output", str(sim_out), "--result-json", str(sim_json)])
        readiness_out = tmp / "readiness.md"
        readiness_json = tmp / "readiness.json"
        run(["python3", str(SCRIPTS["readiness"]), "--cycle-id", "cycle-002", "--apply-plan", str(plan_file), "--simulation-result", str(sim_json), "--simulation-report", str(sim_out), "--dryrun-execution-gate", str(gate_out), "--approved-dir", str(approved_dir), "--output", str(readiness_out), "--output-json", str(readiness_json)])
        report = tmp / "auth" / "report.md"
        run([
            "python3", str(SCRIPTS["authorize"]),
            "--cycle-id", "cycle-002",
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--apply-plan", str(plan_file),
            "--simulation-result", str(sim_json),
            "--real-write-readiness-gate", str(readiness_json),
            "--approved-dir", str(approved_dir),
            "--output-dir", str(tmp / "auth"),
            "--report", str(report),
        ])
        auth = json.loads((tmp / "auth" / "authorization_request.json").read_text(encoding="utf-8"))
        assert auth["required_phrase"].startswith("AUTORIZO_PRE_FLIGHT_ESCRITA_REAL_CYCLE-002_4WNET-MNS-KTG-RX_")


def test_09_final_preflight_blocks_wrong_phrase() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        approved_dir, plan_file, validation_report = positive_chain(tmp)
        gate_out = tmp / "gate.md"
        gate_json = tmp / "gate.json"
        run(["python3", str(SCRIPTS["dryrun_gate"]), "--cycle-id", "cycle-002", "--apply-plan", str(plan_file), "--validation-report", str(validation_report), "--output", str(gate_out), "--output-json", str(gate_json)])
        sim_out = tmp / "sim.md"
        sim_json = tmp / "sim.json"
        run(["python3", str(SCRIPTS["simulate"]), "--cycle-id", "cycle-002", "--apply-plan", str(plan_file), "--execution-gate", str(gate_out), "--output", str(sim_out), "--result-json", str(sim_json)])
        readiness_out = tmp / "readiness.md"
        readiness_json = tmp / "readiness.json"
        run(["python3", str(SCRIPTS["readiness"]), "--cycle-id", "cycle-002", "--apply-plan", str(plan_file), "--simulation-result", str(sim_json), "--simulation-report", str(sim_out), "--dryrun-execution-gate", str(gate_out), "--approved-dir", str(approved_dir), "--output", str(readiness_out), "--output-json", str(readiness_json)])
        report = tmp / "auth" / "report.md"
        run(["python3", str(SCRIPTS["authorize"]), "--cycle-id", "cycle-002", "--device", "4WNET-MNS-KTG-RX", "--device-id", "1890", "--apply-plan", str(plan_file), "--simulation-result", str(sim_json), "--real-write-readiness-gate", str(readiness_json), "--approved-dir", str(approved_dir), "--output-dir", str(tmp / "auth"), "--report", str(report)])
        auth = tmp / "auth" / "authorization_request.json"
        preflight_out = tmp / "preflight.md"
        preflight_json = tmp / "preflight.json"
        run([
            "python3", str(SCRIPTS["preflight"]),
            "--authorization-request", str(auth),
            "--operator", "Keslley",
            "--authorization-phrase", "WRONG",
            "--output", str(preflight_out),
            "--output-json", str(preflight_json),
        ], expect=1)


def test_10_final_preflight_allows_correct_phrase() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        approved_dir, plan_file, validation_report = positive_chain(tmp)
        gate_out = tmp / "gate.md"
        gate_json = tmp / "gate.json"
        run(["python3", str(SCRIPTS["dryrun_gate"]), "--cycle-id", "cycle-002", "--apply-plan", str(plan_file), "--validation-report", str(validation_report), "--output", str(gate_out), "--output-json", str(gate_json)])
        sim_out = tmp / "sim.md"
        sim_json = tmp / "sim.json"
        run(["python3", str(SCRIPTS["simulate"]), "--cycle-id", "cycle-002", "--apply-plan", str(plan_file), "--execution-gate", str(gate_out), "--output", str(sim_out), "--result-json", str(sim_json)])
        readiness_out = tmp / "readiness.md"
        readiness_json = tmp / "readiness.json"
        run(["python3", str(SCRIPTS["readiness"]), "--cycle-id", "cycle-002", "--apply-plan", str(plan_file), "--simulation-result", str(sim_json), "--simulation-report", str(sim_out), "--dryrun-execution-gate", str(gate_out), "--approved-dir", str(approved_dir), "--output", str(readiness_out), "--output-json", str(readiness_json)])
        report = tmp / "auth" / "report.md"
        run(["python3", str(SCRIPTS["authorize"]), "--cycle-id", "cycle-002", "--device", "4WNET-MNS-KTG-RX", "--device-id", "1890", "--apply-plan", str(plan_file), "--simulation-result", str(sim_json), "--real-write-readiness-gate", str(readiness_json), "--approved-dir", str(approved_dir), "--output-dir", str(tmp / "auth"), "--report", str(report)])
        auth = json.loads((tmp / "auth" / "authorization_request.json").read_text(encoding="utf-8"))
        preflight_out = tmp / "preflight.md"
        preflight_json = tmp / "preflight.json"
        run([
            "python3", str(SCRIPTS["preflight"]),
            "--authorization-request", str(tmp / "auth" / "authorization_request.json"),
            "--operator", "Keslley",
            "--authorization-phrase", auth["required_phrase"],
            "--output", str(preflight_out),
            "--output-json", str(preflight_json),
        ])
        payload = json.loads(preflight_json.read_text(encoding="utf-8"))
        assert payload["decision"].startswith("CYCLE_READY")


def test_11_execution_package_created_locked() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        approved_dir, plan_file, validation_report = positive_chain(tmp)
        gate_out = tmp / "gate.md"
        gate_json = tmp / "gate.json"
        run(["python3", str(SCRIPTS["dryrun_gate"]), "--cycle-id", "cycle-002", "--apply-plan", str(plan_file), "--validation-report", str(validation_report), "--output", str(gate_out), "--output-json", str(gate_json)])
        sim_out = tmp / "sim.md"
        sim_json = tmp / "sim.json"
        run(["python3", str(SCRIPTS["simulate"]), "--cycle-id", "cycle-002", "--apply-plan", str(plan_file), "--execution-gate", str(gate_out), "--output", str(sim_out), "--result-json", str(sim_json)])
        readiness_out = tmp / "readiness.md"
        readiness_json = tmp / "readiness.json"
        run(["python3", str(SCRIPTS["readiness"]), "--cycle-id", "cycle-002", "--apply-plan", str(plan_file), "--simulation-result", str(sim_json), "--simulation-report", str(sim_out), "--dryrun-execution-gate", str(gate_out), "--approved-dir", str(approved_dir), "--output", str(readiness_out), "--output-json", str(readiness_json)])
        auth_report = tmp / "auth" / "report.md"
        run(["python3", str(SCRIPTS["authorize"]), "--cycle-id", "cycle-002", "--device", "4WNET-MNS-KTG-RX", "--device-id", "1890", "--apply-plan", str(plan_file), "--simulation-result", str(sim_json), "--real-write-readiness-gate", str(readiness_json), "--approved-dir", str(approved_dir), "--output-dir", str(tmp / "auth"), "--report", str(auth_report)])
        preflight_out = tmp / "preflight.md"
        preflight_json = tmp / "preflight.json"
        auth = json.loads((tmp / "auth" / "authorization_request.json").read_text(encoding="utf-8"))
        run(["python3", str(SCRIPTS["preflight"]), "--authorization-request", str(tmp / "auth" / "authorization_request.json"), "--operator", "Keslley", "--authorization-phrase", auth["required_phrase"], "--output", str(preflight_out), "--output-json", str(preflight_json)])
        exec_report = tmp / "exec" / "report.md"
        run(["python3", str(SCRIPTS["execution"]), "--cycle-id", "cycle-002", "--authorization-request", str(tmp / "auth" / "authorization_request.json"), "--final-preflight-gate", str(preflight_json), "--apply-plan", str(plan_file), "--simulation-result", str(sim_json), "--output-dir", str(tmp / "exec"), "--report", str(exec_report)])
        package = json.loads((tmp / "exec" / "execution_package.json").read_text(encoding="utf-8"))
        assert package["execution_allowed"] is False
        assert package["mode"] == "real_write_prepared"


def test_12_execution_package_phrase_present() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        approved_dir, plan_file, validation_report = positive_chain(tmp)
        gate_out = tmp / "gate.md"
        gate_json = tmp / "gate.json"
        run(["python3", str(SCRIPTS["dryrun_gate"]), "--cycle-id", "cycle-002", "--apply-plan", str(plan_file), "--validation-report", str(validation_report), "--output", str(gate_out), "--output-json", str(gate_json)])
        sim_out = tmp / "sim.md"
        sim_json = tmp / "sim.json"
        run(["python3", str(SCRIPTS["simulate"]), "--cycle-id", "cycle-002", "--apply-plan", str(plan_file), "--execution-gate", str(gate_out), "--output", str(sim_out), "--result-json", str(sim_json)])
        readiness_out = tmp / "readiness.md"
        readiness_json = tmp / "readiness.json"
        run(["python3", str(SCRIPTS["readiness"]), "--cycle-id", "cycle-002", "--apply-plan", str(plan_file), "--simulation-result", str(sim_json), "--simulation-report", str(sim_out), "--dryrun-execution-gate", str(gate_out), "--approved-dir", str(approved_dir), "--output", str(readiness_out), "--output-json", str(readiness_json)])
        auth_report = tmp / "auth" / "report.md"
        run(["python3", str(SCRIPTS["authorize"]), "--cycle-id", "cycle-002", "--device", "4WNET-MNS-KTG-RX", "--device-id", "1890", "--apply-plan", str(plan_file), "--simulation-result", str(sim_json), "--real-write-readiness-gate", str(readiness_json), "--approved-dir", str(approved_dir), "--output-dir", str(tmp / "auth"), "--report", str(auth_report)])
        preflight_out = tmp / "preflight.md"
        preflight_json = tmp / "preflight.json"
        auth = json.loads((tmp / "auth" / "authorization_request.json").read_text(encoding="utf-8"))
        run(["python3", str(SCRIPTS["preflight"]), "--authorization-request", str(tmp / "auth" / "authorization_request.json"), "--operator", "Keslley", "--authorization-phrase", auth["required_phrase"], "--output", str(preflight_out), "--output-json", str(preflight_json)])
        exec_report = tmp / "exec" / "report.md"
        run(["python3", str(SCRIPTS["execution"]), "--cycle-id", "cycle-002", "--authorization-request", str(tmp / "auth" / "authorization_request.json"), "--final-preflight-gate", str(preflight_json), "--apply-plan", str(plan_file), "--simulation-result", str(sim_json), "--output-dir", str(tmp / "exec"), "--report", str(exec_report)])
        package = json.loads((tmp / "exec" / "execution_package.json").read_text(encoding="utf-8"))
        assert package["required_execution_phrase"].startswith("EXECUTAR_ESCRITA_REAL_CYCLE-002_4WNET-MNS-KTG-RX_")


def test_13_validate_blocks_execution_allowed_true() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        approved_dir, plan_file, validation_report = positive_chain(tmp)
        gate_out = tmp / "gate.md"
        gate_json = tmp / "gate.json"
        run(["python3", str(SCRIPTS["dryrun_gate"]), "--cycle-id", "cycle-002", "--apply-plan", str(plan_file), "--validation-report", str(validation_report), "--output", str(gate_out), "--output-json", str(gate_json)])
        sim_out = tmp / "sim.md"
        sim_json = tmp / "sim.json"
        run(["python3", str(SCRIPTS["simulate"]), "--cycle-id", "cycle-002", "--apply-plan", str(plan_file), "--execution-gate", str(gate_out), "--output", str(sim_out), "--result-json", str(sim_json)])
        readiness_out = tmp / "readiness.md"
        readiness_json = tmp / "readiness.json"
        run(["python3", str(SCRIPTS["readiness"]), "--cycle-id", "cycle-002", "--apply-plan", str(plan_file), "--simulation-result", str(sim_json), "--simulation-report", str(sim_out), "--dryrun-execution-gate", str(gate_out), "--approved-dir", str(approved_dir), "--output", str(readiness_out), "--output-json", str(readiness_json)])
        auth_report = tmp / "auth" / "report.md"
        run(["python3", str(SCRIPTS["authorize"]), "--cycle-id", "cycle-002", "--device", "4WNET-MNS-KTG-RX", "--device-id", "1890", "--apply-plan", str(plan_file), "--simulation-result", str(sim_json), "--real-write-readiness-gate", str(readiness_json), "--approved-dir", str(approved_dir), "--output-dir", str(tmp / "auth"), "--report", str(auth_report)])
        preflight_out = tmp / "preflight.md"
        preflight_json = tmp / "preflight.json"
        auth = json.loads((tmp / "auth" / "authorization_request.json").read_text(encoding="utf-8"))
        run(["python3", str(SCRIPTS["preflight"]), "--authorization-request", str(tmp / "auth" / "authorization_request.json"), "--operator", "Keslley", "--authorization-phrase", auth["required_phrase"], "--output", str(preflight_out), "--output-json", str(preflight_json)])
        exec_report = tmp / "exec" / "report.md"
        run(["python3", str(SCRIPTS["execution"]), "--cycle-id", "cycle-002", "--authorization-request", str(tmp / "auth" / "authorization_request.json"), "--final-preflight-gate", str(preflight_json), "--apply-plan", str(plan_file), "--simulation-result", str(sim_json), "--output-dir", str(tmp / "exec"), "--report", str(exec_report)])
        package = json.loads((tmp / "exec" / "execution_package.json").read_text(encoding="utf-8"))
        package["execution_allowed"] = True
        (tmp / "exec" / "execution_package.json").write_text(json.dumps(package), encoding="utf-8")
        out = tmp / "validation.md"
        out_json = tmp / "validation.json"
        run([
            "python3", str(SCRIPTS["validate"]),
            "--cycle-id", "cycle-002",
            "--execution-package", str(tmp / "exec" / "execution_package.json"),
            "--output", str(out),
            "--output-json", str(out_json),
        ], expect=1)


def test_14_freeze_ready_with_valid_package() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        approved_dir, plan_file, validation_report = positive_chain(tmp)
        gate_out = tmp / "gate.md"
        gate_json = tmp / "gate.json"
        run(["python3", str(SCRIPTS["dryrun_gate"]), "--cycle-id", "cycle-002", "--apply-plan", str(plan_file), "--validation-report", str(validation_report), "--output", str(gate_out), "--output-json", str(gate_json)])
        sim_out = tmp / "sim.md"
        sim_json = tmp / "sim.json"
        run(["python3", str(SCRIPTS["simulate"]), "--cycle-id", "cycle-002", "--apply-plan", str(plan_file), "--execution-gate", str(gate_out), "--output", str(sim_out), "--result-json", str(sim_json)])
        readiness_out = tmp / "readiness.md"
        readiness_json = tmp / "readiness.json"
        run(["python3", str(SCRIPTS["readiness"]), "--cycle-id", "cycle-002", "--apply-plan", str(plan_file), "--simulation-result", str(sim_json), "--simulation-report", str(sim_out), "--dryrun-execution-gate", str(gate_out), "--approved-dir", str(approved_dir), "--output", str(readiness_out), "--output-json", str(readiness_json)])
        auth_report = tmp / "auth" / "report.md"
        run(["python3", str(SCRIPTS["authorize"]), "--cycle-id", "cycle-002", "--device", "4WNET-MNS-KTG-RX", "--device-id", "1890", "--apply-plan", str(plan_file), "--simulation-result", str(sim_json), "--real-write-readiness-gate", str(readiness_json), "--approved-dir", str(approved_dir), "--output-dir", str(tmp / "auth"), "--report", str(auth_report)])
        preflight_out = tmp / "preflight.md"
        preflight_json = tmp / "preflight.json"
        auth = json.loads((tmp / "auth" / "authorization_request.json").read_text(encoding="utf-8"))
        run(["python3", str(SCRIPTS["preflight"]), "--authorization-request", str(tmp / "auth" / "authorization_request.json"), "--operator", "Keslley", "--authorization-phrase", auth["required_phrase"], "--output", str(preflight_out), "--output-json", str(preflight_json)])
        exec_report = tmp / "exec" / "report.md"
        run(["python3", str(SCRIPTS["execution"]), "--cycle-id", "cycle-002", "--authorization-request", str(tmp / "auth" / "authorization_request.json"), "--final-preflight-gate", str(preflight_json), "--apply-plan", str(plan_file), "--simulation-result", str(sim_json), "--output-dir", str(tmp / "exec"), "--report", str(exec_report)])
        validation_out = tmp / "validation.md"
        validation_json = tmp / "validation.json"
        run(["python3", str(SCRIPTS["validate"]), "--cycle-id", "cycle-002", "--execution-package", str(tmp / "exec" / "execution_package.json"), "--output", str(validation_out), "--output-json", str(validation_json)])
        freeze_out = tmp / "freeze.md"
        freeze_json = tmp / "freeze.json"
        run(["python3", str(SCRIPTS["freeze"]), "--cycle-id", "cycle-002", "--execution-package", str(tmp / "exec" / "execution_package.json"), "--package-validation", str(validation_json), "--output", str(freeze_out), "--output-json", str(freeze_json)])
        payload = json.loads(freeze_json.read_text(encoding="utf-8"))
        assert payload["decision"].startswith("CYCLE_READY")


def test_15_freeze_blocks_token_in_artifacts() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        package = {
            "execution_allowed": False,
            "required_execution_phrase": "EXECUTAR",
            "safety_confirmations": {"no_write_executed": True, "no_token_read": True, "no_network_call": True},
        }
        pkg = tmp / "pkg.json"
        pkg.write_text(json.dumps(package), encoding="utf-8")
        val = tmp / "val.json"
        val.write_text(json.dumps({"decision": "CYCLE_REAL_WRITE_EXECUTION_PACKAGE_VALID"}), encoding="utf-8")
        package["token"] = "bad"
        pkg.write_text(json.dumps(package), encoding="utf-8")
        run([
            "python3", str(SCRIPTS["freeze"]),
            "--cycle-id", "cycle-002",
            "--execution-package", str(pkg),
            "--package-validation", str(val),
            "--output", str(tmp / "freeze.md"),
            "--output-json", str(tmp / "freeze.json"),
        ], expect=1)


def test_16_webui_routes_200() -> None:
    for path in [
        "/controlled-operation/cycle-002/applyplan/dryrun-gate",
        "/controlled-operation/cycle-002/applyplan/simulation",
        "/controlled-operation/cycle-002/applyplan/real-write-readiness",
        "/controlled-operation/cycle-002/real-write-authorization",
        "/controlled-operation/cycle-002/real-write-preflight",
        "/controlled-operation/cycle-002/real-write-package",
        "/controlled-operation/cycle-002/real-write-freeze",
    ]:
        status, body = asyncio.run(call_asgi(path))
        assert status == 200, body


def test_17_webui_no_apply_sync_token() -> None:
    for path in [
        "/controlled-operation/cycle-002/applyplan/dryrun-gate",
        "/controlled-operation/cycle-002/real-write-package",
    ]:
        status, body = asyncio.run(call_asgi(path))
        assert status == 200
        lowered = body.lower()
        assert "executar escrita" not in lowered
        assert "sync" not in lowered
        assert "token" not in lowered


def test_18_no_netbox_write_sources() -> None:
    for source in SCRIPTS.values():
        text = source.read_text(encoding="utf-8")
        assert "requests" not in text
        assert "pynetbox" not in text


def test_19_no_token_reads() -> None:
    for source in SCRIPTS.values():
        text = source.read_text(encoding="utf-8")
        assert "NETBOX_WRITE_TOKEN" not in text


def test_20_no_network_calls() -> None:
    for source in [SCRIPTS["simulate"], SCRIPTS["preflight"], SCRIPTS["execution"], SCRIPTS["freeze"]]:
        text = source.read_text(encoding="utf-8")
        for term in ["socket", "urllib.request", "httpx", "requests", "pynetbox"]:
            assert term not in text


def main() -> int:
    tests = [
        test_01_dryrun_gate_ready,
        test_02_dryrun_gate_blocks_real_write_true,
        test_03_simulation_generates_result,
        test_04_simulation_no_prohibited_imports,
        test_05_simulation_no_token_read,
        test_06_real_write_readiness_ready,
        test_07_real_write_readiness_accepts_compat_approved_dir,
        test_08_authorization_phrase_generated,
        test_09_final_preflight_blocks_wrong_phrase,
        test_10_final_preflight_allows_correct_phrase,
        test_11_execution_package_created_locked,
        test_12_execution_package_phrase_present,
        test_13_validate_blocks_execution_allowed_true,
        test_14_freeze_ready_with_valid_package,
        test_15_freeze_blocks_token_in_artifacts,
        test_16_webui_routes_200,
        test_17_webui_no_apply_sync_token,
        test_18_no_netbox_write_sources,
        test_19_no_token_reads,
        test_20_no_network_calls,
    ]
    passed = 0
    for test in tests:
        test()
        print(f"✓ {test.__name__}")
        passed += 1
    print(f"\n{passed}/{len(tests)} cycle-002 simulation/freeze tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
