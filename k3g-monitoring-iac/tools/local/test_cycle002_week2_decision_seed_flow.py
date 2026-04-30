#!/usr/bin/env python3
"""Tests for Cycle-002 Week 2 decision seed / re-review / promotion / readiness gate."""

from __future__ import annotations

import csv
import json
import os
import sys
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "tools/local/controlled_cycle_week2_seed_decision_v2.py"
REVIEW = ROOT / "tools/local/controlled_cycle_week2_review_v2.py"
PROMOTE = ROOT / "tools/local/controlled_cycle_promote_to_approval_records_v2.py"
GATE = ROOT / "tools/local/controlled_cycle_approval_readiness_gate_v2.py"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run(cmd: list[str], cwd: Path | None = None, expect: int = 0) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=cwd or ROOT, text=True, capture_output=True)
    if proc.returncode != expect:
        raise AssertionError(f"cmd failed: {cmd}\nstdout={proc.stdout}\nstderr={proc.stderr}")
    return proc


def make_cycle(tmp: Path) -> Path:
    cycle_dir = tmp / "reports/controlled-operation/cycle-002"
    week2 = cycle_dir / "week2"
    drafts = week2 / "approval-drafts"
    (week2 / "audit").mkdir(parents=True, exist_ok=True)
    write_text(
        cycle_dir / "CYCLE-002-SCOPE.json",
        json.dumps({"cycle_id": "cycle-002", "max_items": 3, "allowed_methods": ["POST"], "forbidden_methods": ["PATCH", "DELETE"], "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"]}),
    )
    write_text(cycle_dir / "CYCLE-002-STATUS.md", "# cycle-002\n\nStatus: PLANNED_NOT_STARTED\n")
    write_text(
        week2 / "CYCLE-002-WEEK2-REVIEW-BOARD.md",
        "# board\n",
    )
    write_text(
        week2 / "CYCLE-002-WEEK2-DECISIONS.csv",
        "item_id,device,device_id,object_type,object_key,responsible_team,decision,reviewer,reviewed_at,approval_record_allowed,reason,notes,restriction\n"
        "a1,4WNET-MNS-KTG-RX,1890,bgp_peer,203.0.113.1,bgp,pending,,,false,,,none\n"
        "a2,4WNET-MNS-KTG-RX,1890,ip_address,192.0.2.1/30,network_ops,pending,,,false,,,none\n"
        "a3,4WNET-MNS-KTG-RX,1890,subinterface,Eth-Trunk0.10,service,pending,,,false,,,none\n",
    )
    for name in ["a1", "a2", "a3"]:
        write_text(drafts / f"approval-draft-{name}.json", json.dumps({"status": "draft_review", "draft_id": name, "created_at": "2026-04-29T00:00:00+00:00"}))
    return cycle_dir


def test_01_seed_blocks_without_reviewer() -> None:
    with tempfile.TemporaryDirectory() as td:
        cycle_dir = make_cycle(Path(td))
        week2 = cycle_dir / "week2"
        out = week2 / "seed.md"
        outj = week2 / "seed.json"
        run(
            [sys.executable, str(SEED), "--cycle-id", "cycle-002", "--device", "4WNET-MNS-KTG-RX", "--device-id", "1890", "--week2-dir", str(week2), "--decision", "approve_for_approval_record", "--reviewer", "", "--reason", "x", "--approval-record-allowed", "true", "--output", str(out), "--output-json", str(outj)],
            expect=1,
        )


def test_02_seed_blocks_without_reason() -> None:
    with tempfile.TemporaryDirectory() as td:
        cycle_dir = make_cycle(Path(td))
        week2 = cycle_dir / "week2"
        run(
            [sys.executable, str(SEED), "--cycle-id", "cycle-002", "--device", "4WNET-MNS-KTG-RX", "--device-id", "1890", "--week2-dir", str(week2), "--decision", "approve_for_approval_record", "--reviewer", "Keslley", "--reason", "", "--approval-record-allowed", "true", "--output", str(week2 / "seed.md"), "--output-json", str(week2 / "seed.json")],
            expect=1,
        )


def test_03_seed_blocks_without_allowance() -> None:
    with tempfile.TemporaryDirectory() as td:
        cycle_dir = make_cycle(Path(td))
        week2 = cycle_dir / "week2"
        run(
            [sys.executable, str(SEED), "--cycle-id", "cycle-002", "--device", "4WNET-MNS-KTG-RX", "--device-id", "1890", "--week2-dir", str(week2), "--decision", "approve_for_approval_record", "--reviewer", "Keslley", "--reason", "ok", "--approval-record-allowed", "false", "--output", str(week2 / "seed.md"), "--output-json", str(week2 / "seed.json")],
            expect=1,
        )


def test_04_seed_blocks_without_pending_review() -> None:
    with tempfile.TemporaryDirectory() as td:
        cycle_dir = make_cycle(Path(td))
        week2 = cycle_dir / "week2"
        csv_path = week2 / "CYCLE-002-WEEK2-DECISIONS.csv"
        rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
        for row in rows:
            row["decision"] = "approve_for_approval_record"
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        run(
            [sys.executable, str(SEED), "--cycle-id", "cycle-002", "--device", "4WNET-MNS-KTG-RX", "--device-id", "1890", "--week2-dir", str(week2), "--decision", "approve_for_approval_record", "--reviewer", "Keslley", "--reason", "ok", "--approval-record-allowed", "true", "--output", str(week2 / "seed.md"), "--output-json", str(week2 / "seed.json")],
            expect=1,
        )


def test_05_seed_blocks_missing_draft() -> None:
    with tempfile.TemporaryDirectory() as td:
        cycle_dir = make_cycle(Path(td))
        week2 = cycle_dir / "week2"
        (week2 / "approval-drafts" / "approval-draft-a1.json").unlink()
        run(
            [sys.executable, str(SEED), "--cycle-id", "cycle-002", "--device", "4WNET-MNS-KTG-RX", "--device-id", "1890", "--week2-dir", str(week2), "--decision", "approve_for_approval_record", "--reviewer", "Keslley", "--reason", "ok", "--approval-record-allowed", "true", "--output", str(week2 / "seed.md"), "--output-json", str(week2 / "seed.json")],
            expect=1,
        )


def test_06_seed_creates_backup_and_audit() -> None:
    with tempfile.TemporaryDirectory() as td:
        cycle_dir = make_cycle(Path(td))
        week2 = cycle_dir / "week2"
        run(
            [sys.executable, str(SEED), "--cycle-id", "cycle-002", "--device", "4WNET-MNS-KTG-RX", "--device-id", "1890", "--week2-dir", str(week2), "--decision", "approve_for_approval_record", "--reviewer", "Keslley", "--reason", "ok", "--approval-record-allowed", "true", "--output", str(week2 / "seed.md"), "--output-json", str(week2 / "seed.json")],
            expect=0,
        )
        assert list(week2.glob("CYCLE-002-WEEK2-DECISIONS.csv.bak.*"))
        assert list((week2 / "audit").glob("decision-seed-*.json"))


def test_07_seed_updates_one_item_only() -> None:
    with tempfile.TemporaryDirectory() as td:
        cycle_dir = make_cycle(Path(td))
        week2 = cycle_dir / "week2"
        run(
            [sys.executable, str(SEED), "--cycle-id", "cycle-002", "--device", "4WNET-MNS-KTG-RX", "--device-id", "1890", "--week2-dir", str(week2), "--decision", "approve_for_approval_record", "--reviewer", "Keslley", "--reason", "ok", "--approval-record-allowed", "true", "--output", str(week2 / "seed.md"), "--output-json", str(week2 / "seed.json")],
            expect=0,
        )
        rows = list(csv.DictReader((week2 / "CYCLE-002-WEEK2-DECISIONS.csv").open(encoding="utf-8")))
        assert sum(1 for row in rows if row["decision"] == "approve_for_approval_record") == 1


def test_08_rereview_passes_after_seed() -> None:
    with tempfile.TemporaryDirectory() as td:
        cycle_dir = make_cycle(Path(td))
        week2 = cycle_dir / "week2"
        run([sys.executable, str(SEED), "--cycle-id", "cycle-002", "--device", "4WNET-MNS-KTG-RX", "--device-id", "1890", "--week2-dir", str(week2), "--decision", "approve_for_approval_record", "--reviewer", "Keslley", "--reason", "ok", "--approval-record-allowed", "true", "--output", str(week2 / "seed.md"), "--output-json", str(week2 / "seed.json")], expect=0)
        run([sys.executable, str(REVIEW), "--cycle-id", "cycle-002", "--device", "4WNET-MNS-KTG-RX", "--device-id", "1890", "--cycle-dir", str(cycle_dir), "--week2-dir", str(week2), "--output", str(week2 / "review.md"), "--output-json", str(week2 / "review.json")], expect=0)
        data = json.loads((week2 / "review.json").read_text(encoding="utf-8"))
        assert data["decision"].startswith("WEEK2_REVIEW_PASSED")


def test_09_promotion_creates_proposed() -> None:
    with tempfile.TemporaryDirectory() as td:
        cycle_dir = make_cycle(Path(td))
        week2 = cycle_dir / "week2"
        run([sys.executable, str(SEED), "--cycle-id", "cycle-002", "--device", "4WNET-MNS-KTG-RX", "--device-id", "1890", "--week2-dir", str(week2), "--decision", "approve_for_approval_record", "--reviewer", "Keslley", "--reason", "ok", "--approval-record-allowed", "true", "--output", str(week2 / "seed.md"), "--output-json", str(week2 / "seed.json")], expect=0)
        run([sys.executable, str(REVIEW), "--cycle-id", "cycle-002", "--device", "4WNET-MNS-KTG-RX", "--device-id", "1890", "--cycle-dir", str(cycle_dir), "--week2-dir", str(week2), "--output", str(week2 / "review.md"), "--output-json", str(week2 / "review.json")], expect=0)
        outdir = cycle_dir / "approvals/pending"
        run([sys.executable, str(PROMOTE), "--cycle-id", "cycle-002", "--device", "4WNET-MNS-KTG-RX", "--device-id", "1890", "--week2-review", str(week2 / "review.json"), "--drafts-dir", str(week2 / "approval-drafts"), "--output-dir", str(outdir), "--report", str(cycle_dir / "approvals/report.md"), "--output-json", str(cycle_dir / "approvals/proposed.json")], expect=0)
        assert list(outdir.glob("*.json"))


def test_10_gate_ready_with_proposed() -> None:
    with tempfile.TemporaryDirectory() as td:
        cycle_dir = make_cycle(Path(td))
        week2 = cycle_dir / "week2"
        run([sys.executable, str(SEED), "--cycle-id", "cycle-002", "--device", "4WNET-MNS-KTG-RX", "--device-id", "1890", "--week2-dir", str(week2), "--decision", "approve_for_approval_record", "--reviewer", "Keslley", "--reason", "ok", "--approval-record-allowed", "true", "--output", str(week2 / "seed.md"), "--output-json", str(week2 / "seed.json")], expect=0)
        run([sys.executable, str(REVIEW), "--cycle-id", "cycle-002", "--device", "4WNET-MNS-KTG-RX", "--device-id", "1890", "--cycle-dir", str(cycle_dir), "--week2-dir", str(week2), "--output", str(week2 / "review.md"), "--output-json", str(week2 / "review.json")], expect=0)
        outdir = cycle_dir / "approvals/pending"
        run([sys.executable, str(PROMOTE), "--cycle-id", "cycle-002", "--device", "4WNET-MNS-KTG-RX", "--device-id", "1890", "--week2-review", str(week2 / "review.json"), "--drafts-dir", str(week2 / "approval-drafts"), "--output-dir", str(outdir), "--report", str(cycle_dir / "approvals/report.md"), "--output-json", str(cycle_dir / "approvals/proposed.json")], expect=0)
        run([sys.executable, str(GATE), "--cycle-id", "cycle-002", "--device", "4WNET-MNS-KTG-RX", "--device-id", "1890", "--approvals-dir", str(outdir), "--week2-review", str(week2 / "review.json"), "--output", str(cycle_dir / "approvals/gate.md"), "--output-json", str(cycle_dir / "approvals/gate.json")], expect=0)
        data = json.loads((cycle_dir / "approvals/gate.json").read_text(encoding="utf-8"))
        assert data["decision"].startswith("READY")


def test_11_gate_blocks_secret() -> None:
    with tempfile.TemporaryDirectory() as td:
        cycle_dir = make_cycle(Path(td))
        week2 = cycle_dir / "week2"
        run([sys.executable, str(SEED), "--cycle-id", "cycle-002", "--device", "4WNET-MNS-KTG-RX", "--device-id", "1890", "--week2-dir", str(week2), "--decision", "approve_for_approval_record", "--reviewer", "Keslley", "--reason", "ok", "--approval-record-allowed", "true", "--output", str(week2 / "seed.md"), "--output-json", str(week2 / "seed.json")], expect=0)
        run([sys.executable, str(REVIEW), "--cycle-id", "cycle-002", "--device", "4WNET-MNS-KTG-RX", "--device-id", "1890", "--cycle-dir", str(cycle_dir), "--week2-dir", str(week2), "--output", str(week2 / "review.md"), "--output-json", str(week2 / "review.json")], expect=0)
        outdir = cycle_dir / "approvals/pending"
        run([sys.executable, str(PROMOTE), "--cycle-id", "cycle-002", "--device", "4WNET-MNS-KTG-RX", "--device-id", "1890", "--week2-review", str(week2 / "review.json"), "--drafts-dir", str(week2 / "approval-drafts"), "--output-dir", str(outdir), "--report", str(cycle_dir / "approvals/report.md"), "--output-json", str(cycle_dir / "approvals/proposed.json")], expect=0)
        record = next(outdir.glob("*.json"))
        payload = json.loads(record.read_text(encoding="utf-8"))
        payload["review"]["comment"] = "token=bad"
        record.write_text(json.dumps(payload), encoding="utf-8")
        run([sys.executable, str(GATE), "--cycle-id", "cycle-002", "--device", "4WNET-MNS-KTG-RX", "--device-id", "1890", "--approvals-dir", str(outdir), "--week2-review", str(week2 / "review.json"), "--output", str(cycle_dir / "approvals/gate.md"), "--output-json", str(cycle_dir / "approvals/gate.json")], expect=1)


def test_12_no_netbox_write_source() -> None:
    text = SEED.read_text(encoding="utf-8")
    assert "requests" not in text
    assert "pynetbox" not in text


def test_13_webui_safety_suite_covers_routes() -> None:
    run([sys.executable, str(ROOT / "tools/local/test_webui_safety.py")], expect=0)


def test_14_no_token_reading() -> None:
    text = SEED.read_text(encoding="utf-8")
    assert "NETBOX_WRITE_TOKEN" not in text


def main() -> int:
    tests = [
        test_01_seed_blocks_without_reviewer,
        test_02_seed_blocks_without_reason,
        test_03_seed_blocks_without_allowance,
        test_04_seed_blocks_without_pending_review,
        test_05_seed_blocks_missing_draft,
        test_06_seed_creates_backup_and_audit,
        test_07_seed_updates_one_item_only,
        test_08_rereview_passes_after_seed,
        test_09_promotion_creates_proposed,
        test_10_gate_ready_with_proposed,
        test_11_gate_blocks_secret,
        test_12_no_netbox_write_source,
        test_13_webui_safety_suite_covers_routes,
        test_14_no_token_reading,
    ]
    passed = 0
    for test in tests:
        test()
        print(f"✓ {test.__name__}")
        passed += 1
    print(f"\n{passed}/{len(tests)} cycle-002 decision-seed tests passed")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main())
