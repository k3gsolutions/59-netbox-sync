#!/usr/bin/env python3
"""Cycle-002 manual approval + dry-run ApplyPlan tests."""

from __future__ import annotations

import json
import subprocess
import tempfile
import asyncio
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from webui.app import app

MANUAL = ROOT / "tools/local/controlled_cycle_manual_approval_review_v2.py"
GENERATE = ROOT / "tools/local/controlled_cycle_generate_dryrun_applyplan_v2.py"
VALIDATE = ROOT / "tools/local/controlled_cycle_validate_dryrun_applyplan_v2.py"


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


def make_cycle(tmp: Path) -> tuple[Path, Path, Path, Path]:
    cycle_dir = tmp / "reports/controlled-operation/cycle-002"
    pending = cycle_dir / "approvals/pending"
    approved = cycle_dir / "approvals/approved"
    dryrun = cycle_dir / "apply-plans/dry-run"
    pending.mkdir(parents=True, exist_ok=True)
    approved.mkdir(parents=True, exist_ok=True)
    dryrun.mkdir(parents=True, exist_ok=True)
    (cycle_dir / "CYCLE-002-STATUS.md").write_text("# CYCLE-002\n\nStatus: READY_FOR_MANUAL_APPROVAL_REVIEW\n", encoding="utf-8")
    (cycle_dir / "approvals" / "CYCLE-002-APPROVAL-READINESS-GATE.md").write_text("# gate\n", encoding="utf-8")
    (cycle_dir / "approvals" / "cycle-002-approval-readiness-gate.json").write_text(json.dumps({"decision": "READY_FOR_MANUAL_APPROVAL_REVIEW"}), encoding="utf-8")
    record = {
        "approval_id": "cycle-002-test-1",
        "approval_record_id": "cycle-002-test-1",
        "cycle_id": "cycle-002",
        "device": "4WNET-MNS-KTG-RX",
        "device_id": "1890",
        "object_type": "bgp_peer",
        "object_key": "203.0.113.1",
        "object_id": "203-0-113-1",
        "status": "proposed",
        "state": "proposed",
        "created_at": "2026-04-30T00:00:00+00:00",
        "source_week2_review": "cycle-002-week2-human-review.json",
        "source_draft": "approval-draft-203-0-113-1",
        "source_decision_csv": "CYCLE-002-WEEK2-DECISIONS.csv",
        "proposal": {"object_key": "203.0.113.1", "object_type": "bgp_peer", "category": "bgp", "preferred_next_step": "Revisar manualmente"},
        "proposed_payload": {"cycle_id": "cycle-002", "device": "4WNET-MNS-KTG-RX", "device_id": "1890", "team": "bgp", "object_type": "bgp_peer", "object_key": "203.0.113.1", "action": "safe_create_staged", "category": "bgp"},
        "evidence_hash": "sha256:test",
        "review": {"status": "proposed", "reviewed_by": "Keslley", "reviewed_at": "2026-04-30T00:00:00+00:00", "decision": "approve_for_approval_record", "comment": "ok", "changes_requested": []},
        "safety_confirmations": {"no_netbox_write": True, "no_apply_plan_created": True, "manual_review_required": True, "human_decision_required": True, "proposed_only": True},
        "state_history": [{"status": "draft_review", "timestamp": "2026-04-30T00:00:00+00:00", "event": "cycle_week2_reviewed"}],
    }
    pending_record = pending / "approval-203-0-113-1.json"
    pending_record.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return cycle_dir, pending, approved, dryrun


def test_manual_approval_blocks_without_reviewer() -> None:
    with tempfile.TemporaryDirectory() as td:
        cycle_dir, pending, approved, _ = make_cycle(Path(td))
        proc = run(
            [
                "python3", str(MANUAL),
                "--cycle-id", "cycle-002",
                "--approval-record", str(pending / "approval-203-0-113-1.json"),
                "--decision", "approve",
                "--reviewer", "",
                "--reason", "ok",
                "--output-dir", str(approved),
                "--report", str(cycle_dir / "approvals/report.md"),
                "--output-json", str(cycle_dir / "approvals/report.json"),
            ],
            expect=1,
        )
        assert "reviewer required" in proc.stdout.lower() or "reviewer required" in proc.stderr.lower()


def test_manual_approval_blocks_without_reason() -> None:
    with tempfile.TemporaryDirectory() as td:
        cycle_dir, pending, approved, _ = make_cycle(Path(td))
        run(
            [
                "python3", str(MANUAL),
                "--cycle-id", "cycle-002",
                "--approval-record", str(pending / "approval-203-0-113-1.json"),
                "--decision", "approve",
                "--reviewer", "Keslley",
                "--reason", "",
                "--output-dir", str(approved),
                "--report", str(cycle_dir / "approvals/report.md"),
                "--output-json", str(cycle_dir / "approvals/report.json"),
            ],
            expect=1,
        )


def test_manual_approval_blocks_invalid_status() -> None:
    with tempfile.TemporaryDirectory() as td:
        cycle_dir, pending, approved, _ = make_cycle(Path(td))
        data = json.loads((pending / "approval-203-0-113-1.json").read_text(encoding="utf-8"))
        data["status"] = "approved"
        (pending / "approval-203-0-113-1.json").write_text(json.dumps(data), encoding="utf-8")
        run(
            [
                "python3", str(MANUAL),
                "--cycle-id", "cycle-002",
                "--approval-record", str(pending / "approval-203-0-113-1.json"),
                "--decision", "approve",
                "--reviewer", "Keslley",
                "--reason", "ok",
                "--output-dir", str(approved),
                "--report", str(cycle_dir / "approvals/report.md"),
                "--output-json", str(cycle_dir / "approvals/report.json"),
            ],
            expect=1,
        )


def test_manual_approval_approve_creates_approved_copy() -> None:
    with tempfile.TemporaryDirectory() as td:
        cycle_dir, pending, approved, _ = make_cycle(Path(td))
        run(
            [
                "python3", str(MANUAL),
                "--cycle-id", "cycle-002",
                "--approval-record", str(pending / "approval-203-0-113-1.json"),
                "--decision", "approve",
                "--reviewer", "Keslley",
                "--reason", "Aprovado",
                "--output-dir", str(approved),
                "--report", str(cycle_dir / "approvals/report.md"),
                "--output-json", str(cycle_dir / "approvals/report.json"),
            ],
            expect=0,
        )
        out = next((approved / "approved").glob("*.json"))
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["status"] == "approved"
        assert payload["state"] == "approved"
        assert any(item.get("event") == "approved_for_cycle_dryrun_applyplan" for item in payload["state_history"])


def test_manual_approval_reject_creates_rejected_copy() -> None:
    with tempfile.TemporaryDirectory() as td:
        cycle_dir, pending, approved, _ = make_cycle(Path(td))
        run(
            [
                "python3", str(MANUAL),
                "--cycle-id", "cycle-002",
                "--approval-record", str(pending / "approval-203-0-113-1.json"),
                "--decision", "reject",
                "--reviewer", "Keslley",
                "--reason", "Rejeitado",
                "--output-dir", str(approved),
                "--report", str(cycle_dir / "approvals/report.md"),
                "--output-json", str(cycle_dir / "approvals/report.json"),
            ],
            expect=1,
        )
        out = next((approved / "rejected").glob("*.json"))
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["status"] == "rejected"


def test_generate_dryrun_blocks_without_approved() -> None:
    with tempfile.TemporaryDirectory() as td:
        cycle_dir, pending, approved, dryrun = make_cycle(Path(td))
        run(
            [
                "python3", str(GENERATE),
                "--cycle-id", "cycle-002",
                "--device", "4WNET-MNS-KTG-RX",
                "--device-id", "1890",
                "--approved-dir", str(approved / "approved"),
                "--approval-review", str(cycle_dir / "approvals/report.json"),
                "--output-dir", str(dryrun),
                "--report", str(cycle_dir / "apply-plans/report.md"),
                "--output-json", str(cycle_dir / "apply-plans/report.json"),
            ],
            expect=1,
        )


def test_generate_dryrun_creates_dryrun_applyplan() -> None:
    with tempfile.TemporaryDirectory() as td:
        cycle_dir, pending, approved, dryrun = make_cycle(Path(td))
        run(
            [
                "python3", str(MANUAL),
                "--cycle-id", "cycle-002",
                "--approval-record", str(pending / "approval-203-0-113-1.json"),
                "--decision", "approve",
                "--reviewer", "Keslley",
                "--reason", "Aprovado",
                "--output-dir", str(approved),
                "--report", str(cycle_dir / "approvals/report.md"),
                "--output-json", str(cycle_dir / "approvals/report.json"),
            ],
            expect=0,
        )
        run(
            [
                "python3", str(GENERATE),
                "--cycle-id", "cycle-002",
                "--device", "4WNET-MNS-KTG-RX",
                "--device-id", "1890",
                "--approved-dir", str(approved / "approved"),
                "--approval-review", str(cycle_dir / "approvals/report.json"),
                "--output-dir", str(dryrun),
                "--report", str(cycle_dir / "apply-plans/report.md"),
                "--output-json", str(cycle_dir / "apply-plans/report.json"),
            ],
            expect=0,
        )
        plan = json.loads(next(dryrun.glob("*.json")).read_text(encoding="utf-8"))
        assert plan["mode"] == "dry_run"
        assert plan["execution_policy"]["can_execute_real_write"] is False


def test_validate_dryrun_accepts_valid_plan() -> None:
    with tempfile.TemporaryDirectory() as td:
        cycle_dir, pending, approved, dryrun = make_cycle(Path(td))
        run(
            [
                "python3", str(MANUAL),
                "--cycle-id", "cycle-002",
                "--approval-record", str(pending / "approval-203-0-113-1.json"),
                "--decision", "approve",
                "--reviewer", "Keslley",
                "--reason", "Aprovado",
                "--output-dir", str(approved),
                "--report", str(cycle_dir / "approvals/report.md"),
                "--output-json", str(cycle_dir / "approvals/report.json"),
            ],
            expect=0,
        )
        run(
            [
                "python3", str(GENERATE),
                "--cycle-id", "cycle-002",
                "--device", "4WNET-MNS-KTG-RX",
                "--device-id", "1890",
                "--approved-dir", str(approved / "approved"),
                "--approval-review", str(cycle_dir / "approvals/report.json"),
                "--output-dir", str(dryrun),
                "--report", str(cycle_dir / "apply-plans/report.md"),
                "--output-json", str(cycle_dir / "apply-plans/report.json"),
            ],
            expect=0,
        )
        plan = next(dryrun.glob("*.json"))
        run(
            [
                "python3", str(VALIDATE),
                "--cycle-id", "cycle-002",
                "--apply-plan", str(plan),
                "--device", "4WNET-MNS-KTG-RX",
                "--device-id", "1890",
                "--output", str(cycle_dir / "apply-plans/validation.md"),
                "--output-json", str(cycle_dir / "apply-plans/validation.json"),
            ],
            expect=0,
        )


def test_validate_blocks_real_write_flag() -> None:
    with tempfile.TemporaryDirectory() as td:
        cycle_dir, _, _, dryrun = make_cycle(Path(td))
        plan = dryrun / "bad.json"
        plan.write_text(json.dumps({"cycle_id": "cycle-002", "mode": "dry_run", "status": "generated", "device": "4WNET-MNS-KTG-RX", "device_id": "1890", "source_approval_records": ["a"], "items": [{"approval_id": "x", "object_type": "bgp_peer", "object_key": "203.0.113.1", "proposed_payload": {}, "evidence_hash": "sha256:x", "expected_result": "ok", "rollback_hint": "manual", "method": "POST"}], "safety_flags": {"dry_run_only": True, "no_netbox_write": True, "no_token_required": True, "no_apply_execution": True, "manual_execution_gate_required": True, "generated_from_approved_records": True}, "execution_policy": {"can_execute_real_write": True, "requires_next_gate": True, "next_gate": "FASE_4_51_CYCLE002_DRYRUN_EXECUTION_GATE", "max_items": 3, "allowed_methods": ["POST"], "forbidden_methods": ["PATCH", "DELETE"], "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"]}}, indent=2), encoding="utf-8")
        run(
            [
                "python3", str(VALIDATE),
                "--cycle-id", "cycle-002",
                "--apply-plan", str(plan),
                "--device", "4WNET-MNS-KTG-RX",
                "--device-id", "1890",
                "--output", str(cycle_dir / "apply-plans/validation.md"),
                "--output-json", str(cycle_dir / "apply-plans/validation.json"),
            ],
            expect=1,
        )


def test_webui_routes_200() -> None:
    for path in [
        "/controlled-operation/cycle-002/approvals/manual-review",
        "/controlled-operation/cycle-002/applyplan",
        "/controlled-operation/cycle-002/applyplan/validation",
    ]:
        status, body = asyncio.run(call_asgi(path))
        assert status == 200, body


def test_no_netbox_write_source() -> None:
    text = MANUAL.read_text(encoding="utf-8") + GENERATE.read_text(encoding="utf-8") + VALIDATE.read_text(encoding="utf-8")
    assert "requests" not in text
    assert "pynetbox" not in text


def main() -> int:
    tests = [
        test_manual_approval_blocks_without_reviewer,
        test_manual_approval_blocks_without_reason,
        test_manual_approval_blocks_invalid_status,
        test_manual_approval_approve_creates_approved_copy,
        test_manual_approval_reject_creates_rejected_copy,
        test_generate_dryrun_blocks_without_approved,
        test_generate_dryrun_creates_dryrun_applyplan,
        test_validate_dryrun_accepts_valid_plan,
        test_validate_blocks_real_write_flag,
        test_webui_routes_200,
        test_no_netbox_write_source,
    ]
    passed = 0
    for test in tests:
        test()
        print(f"✓ {test.__name__}")
        passed += 1
    print(f"\n{passed}/{len(tests)} cycle-002 approval/applyplan tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
