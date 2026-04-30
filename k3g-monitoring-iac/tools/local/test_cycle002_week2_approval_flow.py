#!/usr/bin/env python3
"""Cycle-002 Week 2 approval flow tests."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.local.test_multi_cycle_operations import ASGIClient


ROOT = Path(__file__).parent.parent.parent


def run_script(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, script, *args], capture_output=True, text=True)


def make_cycle(tmpdir: Path, *, max_items: int = 3) -> Path:
    cycle_dir = tmpdir / "reports" / "controlled-operation" / "cycle-002"
    cycle_dir.mkdir(parents=True, exist_ok=True)
    scope = {
        "cycle_id": "cycle-002",
        "device": "4WNET-MNS-KTG-RX",
        "device_id": 1890,
        "status": "WEEK2_PREPARATION_READY",
        "max_items": max_items,
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
    (cycle_dir / "CYCLE-002-SCOPE.json").write_text(json.dumps(scope), encoding="utf-8")
    (cycle_dir / "CYCLE-002-STATUS.md").write_text("# cycle-002\n\nStatus: WEEK2_PREPARATION_READY\n", encoding="utf-8")
    week2 = cycle_dir / "week2"
    week2.mkdir(exist_ok=True)
    (week2 / "CYCLE-002-WEEK2-REVIEW-BOARD.md").write_text("# board\n", encoding="utf-8")
    (week2 / "CYCLE-002-WEEK2-DECISIONS.csv").write_text(
        "item_id,device,device_id,object_type,object_key,responsible_team,decision,reviewer,reviewed_at,approval_record_allowed,reason,notes,restriction\n",
        encoding="utf-8",
    )
    (week2 / "CYCLE-002-WEEK2-STATUS.md").write_text("# status\n\nStatus: WEEK2_PREPARATION_READY\n", encoding="utf-8")
    return cycle_dir


def write_draft(drafts_dir: Path, item_id: str, object_type: str = "subinterface", object_key: str = "Eth-Trunk0.147") -> Path:
    drafts_dir.mkdir(parents=True, exist_ok=True)
    draft = {
        "draft_id": f"approval-draft-{item_id}",
        "status": "draft_review",
        "device": "4WNET-MNS-KTG-RX",
        "device_id": 1890,
        "object_type": object_type,
        "object_key": object_key,
        "action": "safe_create_staged",
        "category": "service",
        "created_at": "2026-04-29T00:00:00+00:00",
        "allowed_to_promote": False,
        "restriction": "none",
        "evidence": "UAT evidence",
        "owner": "uat",
        "notes": "UAT response",
        "safety": {"no_netbox_write": True, "no_apply_plan_created": True, "manual_review_required": True},
    }
    path = drafts_dir / f"approval-draft-{item_id}.json"
    path.write_text(json.dumps(draft, indent=2), encoding="utf-8")
    return path


def run_week2_review(tmpdir: Path, csv_text: str, *, max_items: int = 3) -> tuple[int, dict]:
    cycle_dir = make_cycle(tmpdir, max_items=max_items)
    week2_dir = cycle_dir / "week2"
    (week2_dir / "CYCLE-002-WEEK2-DECISIONS.csv").write_text(csv_text, encoding="utf-8")
    out_md = week2_dir / "CYCLE-002-WEEK2-HUMAN-REVIEW.md"
    out_json = week2_dir / "cycle-002-week2-human-review.json"
    proc = run_script(
        "tools/local/controlled_cycle_week2_review_v2.py",
        "--cycle-id",
        "cycle-002",
        "--device",
        "4WNET-MNS-KTG-RX",
        "--device-id",
        "1890",
        "--cycle-dir",
        str(cycle_dir),
        "--week2-dir",
        str(week2_dir),
        "--output",
        str(out_md),
        "--output-json",
        str(out_json),
    )
    return proc.returncode, json.loads(out_json.read_text(encoding="utf-8"))


def test_01_week2_review_blocks_invalid_decision() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cycle_dir = make_cycle(root)
        write_draft(cycle_dir / "week2" / "approval-drafts", "Eth-Trunk0-147")
        code, data = run_week2_review(
            root,
            "item_id,device,device_id,object_type,object_key,responsible_team,decision,reviewer,reviewed_at,approval_record_allowed,reason,notes,restriction\n"
            "Eth-Trunk0-147,4WNET-MNS-KTG-RX,1890,subinterface,Eth-Trunk0.147,service,maybe,qa,2026-04-29T00:00:00Z,false,reason,notes,none\n",
        )
        assert code != 0
        assert data["decision"] == "WEEK2_REVIEW_BLOCKED"


def test_02_week2_review_blocks_approve_without_reviewer() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cycle_dir = make_cycle(root)
        write_draft(cycle_dir / "week2" / "approval-drafts", "Eth-Trunk0-147")
        code, data = run_week2_review(
            root,
            "item_id,device,device_id,object_type,object_key,responsible_team,decision,reviewer,reviewed_at,approval_record_allowed,reason,notes,restriction\n"
            "Eth-Trunk0-147,4WNET-MNS-KTG-RX,1890,subinterface,Eth-Trunk0.147,service,approve_for_approval_record,,2026-04-29T00:00:00Z,true,reason,notes,none\n",
        )
        assert code != 0
        assert data["decision"] == "WEEK2_REVIEW_BLOCKED"


def test_03_week2_review_blocks_without_allowance() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cycle_dir = make_cycle(root)
        write_draft(cycle_dir / "week2" / "approval-drafts", "Eth-Trunk0-147")
        code, data = run_week2_review(
            root,
            "item_id,device,device_id,object_type,object_key,responsible_team,decision,reviewer,reviewed_at,approval_record_allowed,reason,notes,restriction\n"
            "Eth-Trunk0-147,4WNET-MNS-KTG-RX,1890,subinterface,Eth-Trunk0.147,service,approve_for_approval_record,qa,2026-04-29T00:00:00Z,false,reason,notes,none\n",
        )
        assert code != 0
        assert data["decision"] == "WEEK2_REVIEW_BLOCKED"


def test_04_week2_review_passes_valid() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cycle_dir = make_cycle(root)
        write_draft(cycle_dir / "week2" / "approval-drafts", "Eth-Trunk0-147")
        code, data = run_week2_review(
            root,
            "item_id,device,device_id,object_type,object_key,responsible_team,decision,reviewer,reviewed_at,approval_record_allowed,reason,notes,restriction\n"
            "Eth-Trunk0-147,4WNET-MNS-KTG-RX,1890,subinterface,Eth-Trunk0.147,service,approve_for_approval_record,qa,2026-04-29T00:00:00Z,true,OK,notes,none\n",
        )
        assert code == 0
        assert data["decision"] == "WEEK2_REVIEW_PASSED"


def test_05_promote_creates_proposed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cycle_dir = make_cycle(root)
        drafts_dir = cycle_dir / "week2" / "approval-drafts"
        write_draft(drafts_dir, "Eth-Trunk0-147")
        review_json = cycle_dir / "week2" / "cycle-002-week2-human-review.json"
        review_json.write_text(
            json.dumps(
                {
                    "cycle_id": "cycle-002",
                    "device": "4WNET-MNS-KTG-RX",
                    "device_id": "1890",
                    "decision": "WEEK2_REVIEW_PASSED",
                    "source_decisions_csv": "CYCLE-002-WEEK2-DECISIONS.csv",
                    "items": [
                        {
                            "item_id": "Eth-Trunk0-147",
                            "object_key": "Eth-Trunk0.147",
                            "object_type": "subinterface",
                            "responsible_team": "service",
                            "decision": "approve_for_approval_record",
                            "reviewer": "qa",
                            "reviewed_at": "2026-04-29T00:00:00Z",
                            "approval_record_allowed": True,
                            "notes": "ok",
                            "reason": "ok",
                            "restriction": "none",
                            "classification": "approved_for_approval_record",
                        }
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        out_dir = cycle_dir / "approvals" / "pending"
        report = cycle_dir / "approvals" / "CYCLE-002-PROPOSED-APPROVALS.md"
        output_json = cycle_dir / "approvals" / "cycle-002-proposed-approvals.json"
        proc = run_script(
            "tools/local/controlled_cycle_promote_to_approval_records_v2.py",
            "--cycle-id",
            "cycle-002",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--week2-review",
            str(review_json),
            "--drafts-dir",
            str(drafts_dir),
            "--output-dir",
            str(out_dir),
            "--report",
            str(report),
            "--output-json",
            str(output_json),
        )
        assert proc.returncode == 0
        promoted = list(out_dir.glob("*.json"))
        assert len(promoted) == 1
        record = json.loads(promoted[0].read_text(encoding="utf-8"))
        assert record["status"] == "proposed"
        assert record["state"] == "proposed"


def test_06_promote_does_not_create_approved() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cycle_dir = make_cycle(root)
        drafts_dir = cycle_dir / "week2" / "approval-drafts"
        write_draft(drafts_dir, "Eth-Trunk0-147")
        review_json = cycle_dir / "week2" / "cycle-002-week2-human-review.json"
        review_json.write_text(
            json.dumps(
                {
                    "cycle_id": "cycle-002",
                    "device": "4WNET-MNS-KTG-RX",
                    "device_id": "1890",
                    "decision": "WEEK2_REVIEW_PASSED",
                    "source_decisions_csv": "CYCLE-002-WEEK2-DECISIONS.csv",
                    "items": [
                        {
                            "item_id": "Eth-Trunk0-147",
                            "object_key": "Eth-Trunk0.147",
                            "object_type": "subinterface",
                            "responsible_team": "service",
                            "decision": "approve_for_approval_record",
                            "reviewer": "qa",
                            "reviewed_at": "2026-04-29T00:00:00Z",
                            "approval_record_allowed": True,
                            "notes": "ok",
                            "reason": "ok",
                            "restriction": "none",
                            "classification": "approved_for_approval_record",
                        }
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        out_dir = cycle_dir / "approvals" / "pending"
        proc = run_script(
            "tools/local/controlled_cycle_promote_to_approval_records_v2.py",
            "--cycle-id",
            "cycle-002",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--week2-review",
            str(review_json),
            "--drafts-dir",
            str(drafts_dir),
            "--output-dir",
            str(out_dir),
            "--report",
            str(cycle_dir / "approvals" / "report.md"),
            "--output-json",
            str(cycle_dir / "approvals" / "out.json"),
        )
        assert proc.returncode == 0
        record = json.loads(next(out_dir.glob("*.json")).read_text(encoding="utf-8"))
        assert record["status"] == "proposed"
        assert "approved" not in json.dumps(record).lower()


def test_07_promote_does_not_create_applyplan() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cycle_dir = make_cycle(root)
        drafts_dir = cycle_dir / "week2" / "approval-drafts"
        write_draft(drafts_dir, "Eth-Trunk0-147")
        review_json = cycle_dir / "week2" / "cycle-002-week2-human-review.json"
        review_json.write_text(
            json.dumps(
                {
                    "cycle_id": "cycle-002",
                    "device": "4WNET-MNS-KTG-RX",
                    "device_id": "1890",
                    "decision": "WEEK2_REVIEW_PASSED",
                    "source_decisions_csv": "CYCLE-002-WEEK2-DECISIONS.csv",
                    "items": [
                        {
                            "item_id": "Eth-Trunk0-147",
                            "object_key": "Eth-Trunk0.147",
                            "object_type": "subinterface",
                            "responsible_team": "service",
                            "decision": "approve_for_approval_record",
                            "reviewer": "qa",
                            "reviewed_at": "2026-04-29T00:00:00Z",
                            "approval_record_allowed": True,
                            "notes": "ok",
                            "reason": "ok",
                            "restriction": "none",
                            "classification": "approved_for_approval_record",
                        }
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        out_dir = cycle_dir / "approvals" / "pending"
        run_script(
            "tools/local/controlled_cycle_promote_to_approval_records_v2.py",
            "--cycle-id",
            "cycle-002",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--week2-review",
            str(review_json),
            "--drafts-dir",
            str(drafts_dir),
            "--output-dir",
            str(out_dir),
            "--report",
            str(cycle_dir / "approvals" / "report.md"),
            "--output-json",
            str(cycle_dir / "approvals" / "out.json"),
        )
        text = "\n".join(path.read_text(encoding="utf-8") for path in out_dir.glob("*.json"))
        assert "ApplyPlan" not in text


def test_08_promote_blocks_missing_draft() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cycle_dir = make_cycle(root)
        review_json = cycle_dir / "week2" / "cycle-002-week2-human-review.json"
        review_json.write_text(
            json.dumps(
                {
                    "cycle_id": "cycle-002",
                    "device": "4WNET-MNS-KTG-RX",
                    "device_id": "1890",
                    "decision": "WEEK2_REVIEW_PASSED",
                    "source_decisions_csv": "CYCLE-002-WEEK2-DECISIONS.csv",
                    "items": [
                        {
                            "item_id": "Eth-Trunk0-147",
                            "object_key": "Eth-Trunk0.147",
                            "object_type": "subinterface",
                            "responsible_team": "service",
                            "decision": "approve_for_approval_record",
                            "reviewer": "qa",
                            "reviewed_at": "2026-04-29T00:00:00Z",
                            "approval_record_allowed": True,
                            "notes": "ok",
                            "reason": "ok",
                            "restriction": "none",
                            "classification": "approved_for_approval_record",
                        }
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        out_dir = cycle_dir / "approvals" / "pending"
        proc = run_script(
            "tools/local/controlled_cycle_promote_to_approval_records_v2.py",
            "--cycle-id",
            "cycle-002",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--week2-review",
            str(review_json),
            "--drafts-dir",
            str(cycle_dir / "week2" / "approval-drafts"),
            "--output-dir",
            str(out_dir),
            "--report",
            str(cycle_dir / "approvals" / "report.md"),
            "--output-json",
            str(cycle_dir / "approvals" / "out.json"),
        )
        assert proc.returncode != 0
        assert not list(out_dir.glob("*.json"))


def test_09_gate_ready_with_valid_proposed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cycle_dir = make_cycle(root)
        approvals_dir = cycle_dir / "approvals" / "pending"
        approvals_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "approval_id": "cycle-002-Eth-Trunk0-147",
            "cycle_id": "cycle-002",
            "status": "proposed",
            "state": "proposed",
            "object_type": "subinterface",
            "object_key": "Eth-Trunk0.147",
            "proposed_payload": {"method": "POST"},
            "review": {"reviewed_by": "qa", "reviewed_at": "2026-04-29T00:00:00Z"},
            "evidence_hash": "sha256:abc",
            "safety_confirmations": {
                "no_netbox_write": True,
                "no_apply_plan_created": True,
                "manual_review_required": True,
                "human_decision_required": True,
                "proposed_only": True,
            },
            "state_history": [{"event": "promoted_to_proposed"}],
        }
        (approvals_dir / "approval-Eth-Trunk0-147.json").write_text(json.dumps(record), encoding="utf-8")
        review_json = cycle_dir / "week2" / "cycle-002-week2-human-review.json"
        review_json.write_text(json.dumps({"items": [{"item_id": "Eth-Trunk0-147"}]}), encoding="utf-8")
        out_md = cycle_dir / "approvals" / "gate.md"
        out_json = cycle_dir / "approvals" / "gate.json"
        proc = run_script(
            "tools/local/controlled_cycle_approval_readiness_gate_v2.py",
            "--cycle-id",
            "cycle-002",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--approvals-dir",
            str(approvals_dir),
            "--week2-review",
            str(review_json),
            "--output",
            str(out_md),
            "--output-json",
            str(out_json),
        )
        assert proc.returncode == 0
        data = json.loads(out_json.read_text(encoding="utf-8"))
        assert data["decision"].startswith("READY")


def test_10_gate_not_ready_with_empty_dir() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cycle_dir = make_cycle(root)
        approvals_dir = cycle_dir / "approvals" / "pending"
        approvals_dir.mkdir(parents=True, exist_ok=True)
        review_json = cycle_dir / "week2" / "cycle-002-week2-human-review.json"
        review_json.write_text(json.dumps({"items": [{"item_id": "Eth-Trunk0-147"}]}), encoding="utf-8")
        out_json = cycle_dir / "approvals" / "gate.json"
        proc = run_script(
            "tools/local/controlled_cycle_approval_readiness_gate_v2.py",
            "--cycle-id",
            "cycle-002",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--approvals-dir",
            str(approvals_dir),
            "--week2-review",
            str(review_json),
            "--output",
            str(cycle_dir / "approvals" / "gate.md"),
            "--output-json",
            str(out_json),
        )
        assert proc.returncode != 0
        assert json.loads(out_json.read_text(encoding="utf-8"))["decision"] == "NOT_READY_FOR_MANUAL_APPROVAL_REVIEW"


def test_11_gate_blocks_secret() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cycle_dir = make_cycle(root)
        approvals_dir = cycle_dir / "approvals" / "pending"
        approvals_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "approval_id": "cycle-002-bad",
            "cycle_id": "cycle-002",
            "status": "proposed",
            "state": "proposed",
            "object_type": "subinterface",
            "object_key": "Eth-Trunk0.147",
            "proposed_payload": {"token": "secret"},
            "review": {"reviewed_by": "qa", "reviewed_at": "2026-04-29T00:00:00Z"},
            "evidence_hash": "sha256:abc",
            "safety_confirmations": {
                "no_netbox_write": True,
                "no_apply_plan_created": True,
                "manual_review_required": True,
                "human_decision_required": True,
                "proposed_only": True,
            },
            "state_history": [{"event": "promoted_to_proposed"}],
        }
        (approvals_dir / "approval-bad.json").write_text(json.dumps(record), encoding="utf-8")
        review_json = cycle_dir / "week2" / "cycle-002-week2-human-review.json"
        review_json.write_text(json.dumps({"items": [{"item_id": "Eth-Trunk0-147"}]}), encoding="utf-8")
        out_json = cycle_dir / "approvals" / "gate.json"
        proc = run_script(
            "tools/local/controlled_cycle_approval_readiness_gate_v2.py",
            "--cycle-id",
            "cycle-002",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--approvals-dir",
            str(approvals_dir),
            "--week2-review",
            str(review_json),
            "--output",
            str(cycle_dir / "approvals" / "gate.md"),
            "--output-json",
            str(out_json),
        )
        assert proc.returncode != 0
        assert json.loads(out_json.read_text(encoding="utf-8"))["decision"] == "NOT_READY_FOR_MANUAL_APPROVAL_REVIEW"


def test_12_gate_blocks_approved_status() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cycle_dir = make_cycle(root)
        approvals_dir = cycle_dir / "approvals" / "pending"
        approvals_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "approval_id": "cycle-002-bad",
            "cycle_id": "cycle-002",
            "status": "approved",
            "state": "approved",
            "object_type": "subinterface",
            "object_key": "Eth-Trunk0.147",
            "proposed_payload": {"method": "POST"},
            "review": {"reviewed_by": "qa", "reviewed_at": "2026-04-29T00:00:00Z"},
            "evidence_hash": "sha256:abc",
            "safety_confirmations": {
                "no_netbox_write": True,
                "no_apply_plan_created": True,
                "manual_review_required": True,
                "human_decision_required": True,
                "proposed_only": True,
            },
            "state_history": [{"event": "promoted_to_proposed"}],
        }
        (approvals_dir / "approval-bad.json").write_text(json.dumps(record), encoding="utf-8")
        review_json = cycle_dir / "week2" / "cycle-002-week2-human-review.json"
        review_json.write_text(json.dumps({"items": [{"item_id": "Eth-Trunk0-147"}]}), encoding="utf-8")
        out_json = cycle_dir / "approvals" / "gate.json"
        proc = run_script(
            "tools/local/controlled_cycle_approval_readiness_gate_v2.py",
            "--cycle-id",
            "cycle-002",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--approvals-dir",
            str(approvals_dir),
            "--week2-review",
            str(review_json),
            "--output",
            str(cycle_dir / "approvals" / "gate.md"),
            "--output-json",
            str(out_json),
        )
        assert proc.returncode != 0
        assert json.loads(out_json.read_text(encoding="utf-8"))["decision"] == "NOT_READY_FOR_MANUAL_APPROVAL_REVIEW"


def test_13_gate_respects_max_items() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cycle_dir = make_cycle(root, max_items=4)
        approvals_dir = cycle_dir / "approvals" / "pending"
        approvals_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "approval_id": "cycle-002-ok",
            "cycle_id": "cycle-002",
            "status": "proposed",
            "state": "proposed",
            "object_type": "subinterface",
            "object_key": "Eth-Trunk0.147",
            "proposed_payload": {"method": "POST"},
            "review": {"reviewed_by": "qa", "reviewed_at": "2026-04-29T00:00:00Z"},
            "evidence_hash": "sha256:abc",
            "safety_confirmations": {
                "no_netbox_write": True,
                "no_apply_plan_created": True,
                "manual_review_required": True,
                "human_decision_required": True,
                "proposed_only": True,
            },
            "state_history": [{"event": "promoted_to_proposed"}],
        }
        (approvals_dir / "approval-ok.json").write_text(json.dumps(record), encoding="utf-8")
        review_json = cycle_dir / "week2" / "cycle-002-week2-human-review.json"
        review_json.write_text(json.dumps({"items": [{"item_id": "Eth-Trunk0-147"}]}), encoding="utf-8")
        out_json = cycle_dir / "approvals" / "gate.json"
        proc = run_script(
            "tools/local/controlled_cycle_approval_readiness_gate_v2.py",
            "--cycle-id",
            "cycle-002",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--approvals-dir",
            str(approvals_dir),
            "--week2-review",
            str(review_json),
            "--output",
            str(cycle_dir / "approvals" / "gate.md"),
            "--output-json",
            str(out_json),
        )
        assert proc.returncode != 0
        assert json.loads(out_json.read_text(encoding="utf-8"))["summary"]["max_items"] == 4


def test_14_webui_week2_review_200() -> None:
    with ASGIClient() as client:
        response = client.get("/controlled-operation/cycle-002/week2/review")
        assert response.status_code == 200


def test_15_webui_approvals_200() -> None:
    with ASGIClient() as client:
        response = client.get("/controlled-operation/cycle-002/approvals")
        assert response.status_code == 200


def test_16_webui_no_apply_sync_token() -> None:
    with ASGIClient() as client:
        text = client.get("/controlled-operation/cycle-002/week2/review").text + client.get("/controlled-operation/cycle-002/approvals").text
        lowered = text.lower()
        assert "apply" not in lowered
        assert "sync" not in lowered
        assert "token" not in lowered


def test_17_no_netbox_write_source() -> None:
    for path in [
        ROOT / "tools" / "local" / "controlled_cycle_week2_review_v2.py",
        ROOT / "tools" / "local" / "controlled_cycle_promote_to_approval_records_v2.py",
        ROOT / "tools" / "local" / "controlled_cycle_approval_readiness_gate_v2.py",
    ]:
        text = path.read_text(encoding="utf-8")
        assert "NETBOX_WRITE_TOKEN" not in text
        assert "Authorization: Token" not in text


def test_18_no_token_reading() -> None:
    for path in [
        ROOT / "tools" / "local" / "controlled_cycle_week2_review_v2.py",
        ROOT / "tools" / "local" / "controlled_cycle_promote_to_approval_records_v2.py",
        ROOT / "tools" / "local" / "controlled_cycle_approval_readiness_gate_v2.py",
    ]:
        text = path.read_text(encoding="utf-8")
        assert "os.environ" not in text or "NETBOX_WRITE_TOKEN" not in text


def main() -> int:
    tests = [obj for name, obj in globals().items() if name.startswith("test_") and callable(obj)]
    passed = 0
    for test in sorted(tests, key=lambda func: func.__name__):
        test()
        passed += 1
        print(f"✓ {test.__name__}")
    print(f"\n{passed}/{len(tests)} week2 approval tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
