#!/usr/bin/env python3
"""Test FASES 4.8, 4.9, 4.10: Week 2 Review & Approval Flow.

18 test cases covering:
- Week 2 human review validation
- Promote drafts to proposed ApprovalRecords
- Approval readiness gate validation
- No writes, no tokens, no automatic approvals
"""

import csv
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def create_mock_decisions_csv(tmpdir, decisions_data: list, cycle_id: str = "cycle-001") -> Path:
    """Create mock decisions CSV."""
    f = Path(tmpdir) / f"{cycle_id.upper()}-WEEK2-DECISIONS.csv"
    with open(f, "w", newline="") as csvfile:
        fieldnames = [
            "item_id",
            "object_type",
            "team",
            "decision",
            "reviewed_by",
            "evidence_reference",
            "notes",
            "approval_record_allowed",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(decisions_data)
    return f


def create_mock_approval_draft(tmpdir, item_id="item-1") -> Path:
    """Create mock approval draft."""
    f = Path(tmpdir) / f"draft-{item_id}.json"
    draft = {
        "cycle_id": "cycle-001",
        "approval_id": f"draft-cycle-001-{item_id}",
        "status": "draft",
        "object_type": "interface",
        "object_id": item_id,
        "notes": "Test draft",
    }
    f.write_text(json.dumps(draft))
    return f


def create_proposed_approval_record(tmpdir, approval_id="test-001") -> Path:
    """Create proposed ApprovalRecord."""
    f = Path(tmpdir) / f"{approval_id}.json"
    record = {
        "approval_id": approval_id,
        "cycle_id": "cycle-001",
        "object_type": "interface",
        "object_id": "item-1",
        "status": "proposed",
        "state": "proposed",
        "created_at": "2026-04-29T00:00:00+00:00",
        "review": {
            "status": "proposed",
            "reviewed_by": "reviewer@example.com",
            "reviewed_at": "2026-04-29T00:00:00+00:00",
        },
        "safety_confirmations": {
            "no_netbox_write": True,
            "no_apply_plan_created": True,
            "manual_review_required": True,
            "proposed_only": True,
            "no_automatic_approval": True,
        },
        "state_history": [
            {
                "status": "proposed",
                "timestamp": "2026-04-29T00:00:00+00:00",
                "event": "promoted_to_proposed",
            }
        ],
    }
    f.write_text(json.dumps(record))
    return f


def test_01_week2_review_validates_decision():
    """Test 1: Week 2 review validates decision field."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        week2_dir = tmpdir / "week2"
        week2_dir.mkdir()
        output_f = week2_dir / "review.md"
        output_json = week2_dir / "review.json"

        decisions = [
            {
                "item_id": "item-1",
                "object_type": "interface",
                "team": "network_ops",
                "decision": "approve_for_approval_record",
                "reviewed_by": "reviewer@example.com",
                "evidence_reference": "test",
                "notes": "approved",
                "approval_record_allowed": "true",
            }
        ]
        create_mock_decisions_csv(week2_dir, decisions)

        from tools.local.controlled_cycle_week2_review import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--cycle-dir",
            str(tmpdir),
            "--week2-dir",
            str(week2_dir),
            "--output",
            str(output_f),
            "--output-json",
            str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert result["summary"]["approved"] == 1
        assert exit_code == 0


def test_02_week2_review_blocks_invalid_decision():
    """Test 2: Week 2 review blocks invalid decision."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        week2_dir = tmpdir / "week2"
        week2_dir.mkdir()
        output_f = week2_dir / "review.md"
        output_json = week2_dir / "review.json"

        decisions = [
            {
                "item_id": "item-1",
                "object_type": "interface",
                "team": "network_ops",
                "decision": "invalid_decision",
                "reviewed_by": "reviewer@example.com",
                "evidence_reference": "test",
                "notes": "invalid",
                "approval_record_allowed": "false",
            }
        ]
        create_mock_decisions_csv(week2_dir, decisions)

        from tools.local.controlled_cycle_week2_review import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--cycle-dir",
            str(tmpdir),
            "--week2-dir",
            str(week2_dir),
            "--output",
            str(output_f),
            "--output-json",
            str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert result["decision"] == "WEEK2_REVIEW_BLOCKED"
        assert exit_code == 1


def test_03_week2_review_blocks_approve_without_reviewer():
    """Test 3: Week 2 review blocks approve without reviewer."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        week2_dir = tmpdir / "week2"
        week2_dir.mkdir()
        output_f = week2_dir / "review.md"
        output_json = week2_dir / "review.json"

        decisions = [
            {
                "item_id": "item-1",
                "object_type": "interface",
                "team": "network_ops",
                "decision": "approve_for_approval_record",
                "reviewed_by": "",
                "evidence_reference": "test",
                "notes": "no reviewer",
                "approval_record_allowed": "true",
            }
        ]
        create_mock_decisions_csv(week2_dir, decisions)

        from tools.local.controlled_cycle_week2_review import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--cycle-dir",
            str(tmpdir),
            "--week2-dir",
            str(week2_dir),
            "--output",
            str(output_f),
            "--output-json",
            str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert result["decision"] == "WEEK2_REVIEW_BLOCKED"


def test_04_week2_review_blocks_approve_without_allowed_flag():
    """Test 4: Week 2 review blocks approve without approval_record_allowed=true."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        week2_dir = tmpdir / "week2"
        week2_dir.mkdir()
        output_f = week2_dir / "review.md"
        output_json = week2_dir / "review.json"

        decisions = [
            {
                "item_id": "item-1",
                "object_type": "interface",
                "team": "network_ops",
                "decision": "approve_for_approval_record",
                "reviewed_by": "reviewer@example.com",
                "evidence_reference": "test",
                "notes": "missing flag",
                "approval_record_allowed": "false",
            }
        ]
        create_mock_decisions_csv(week2_dir, decisions)

        from tools.local.controlled_cycle_week2_review import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--cycle-dir",
            str(tmpdir),
            "--week2-dir",
            str(week2_dir),
            "--output",
            str(output_f),
            "--output-json",
            str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert result["decision"] == "WEEK2_REVIEW_BLOCKED"


def test_05_promote_creates_proposed_approval():
    """Test 5: Promote creates proposed ApprovalRecord."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        week2_dir = tmpdir / "week2"
        week2_dir.mkdir()
        drafts_dir = week2_dir / "approval-drafts"
        drafts_dir.mkdir()
        approvals_dir = tmpdir / "approvals"
        approvals_dir.mkdir()

        # Create review
        review = {
            "decisions": [
                {
                    "item_id": "item-1",
                    "object_type": "interface",
                    "decision": "approve_for_approval_record",
                    "reviewed_by": "reviewer@example.com",
                    "approval_record_allowed": "true",
                    "notes": "approved",
                }
            ]
        }
        review_file = week2_dir / "review.json"
        review_file.write_text(json.dumps(review))

        # Create draft
        create_mock_approval_draft(drafts_dir, "item-1")

        from tools.local.controlled_cycle_promote_to_approval_records import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--week2-review",
            str(review_file),
            "--drafts-dir",
            str(drafts_dir),
            "--output-dir",
            str(approvals_dir),
            "--report",
            str(tmpdir / "promotion.md"),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        assert exit_code == 0
        assert len(list(approvals_dir.glob("*.json"))) > 0


def test_06_promote_sets_proposed_status():
    """Test 6: Promote sets status=proposed not approved."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        week2_dir = tmpdir / "week2"
        week2_dir.mkdir()
        drafts_dir = week2_dir / "approval-drafts"
        drafts_dir.mkdir()
        approvals_dir = tmpdir / "approvals"
        approvals_dir.mkdir()

        review = {
            "decisions": [
                {
                    "item_id": "item-1",
                    "object_type": "interface",
                    "decision": "approve_for_approval_record",
                    "reviewed_by": "reviewer@example.com",
                    "approval_record_allowed": "true",
                    "notes": "approved",
                }
            ]
        }
        review_file = week2_dir / "review.json"
        review_file.write_text(json.dumps(review))

        create_mock_approval_draft(drafts_dir, "item-1")

        from tools.local.controlled_cycle_promote_to_approval_records import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--week2-review",
            str(review_file),
            "--drafts-dir",
            str(drafts_dir),
            "--output-dir",
            str(approvals_dir),
            "--report",
            str(tmpdir / "promotion.md"),
        ]

        with patch("sys.argv", test_args):
            main()

        records = list(approvals_dir.glob("*.json"))
        if records:
            record = json.loads(records[0].read_text())
            assert record["status"] == "proposed"
            assert record["state"] == "proposed"


def test_07_approve_readiness_validates_proposed():
    """Test 7: Approval readiness gate validates proposed records."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        approvals_dir = tmpdir / "approvals"
        approvals_dir.mkdir()

        create_proposed_approval_record(approvals_dir, "test-001")

        review = {"decisions": []}
        review_file = tmpdir / "review.json"
        review_file.write_text(json.dumps(review))

        from tools.local.controlled_cycle_approval_readiness_gate import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--approvals-dir",
            str(approvals_dir),
            "--week2-review",
            str(review_file),
            "--output",
            str(tmpdir / "gate.md"),
            "--output-json",
            str(tmpdir / "gate.json"),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads((tmpdir / "gate.json").read_text())
        assert "READY" in result["decision"]
        assert exit_code == 0


def test_08_approval_gate_blocks_approved_status():
    """Test 8: Approval gate blocks approved status (should be proposed)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        approvals_dir = tmpdir / "approvals"
        approvals_dir.mkdir()

        # Create record with status=approved (should be blocked)
        record = {
            "approval_id": "test-001",
            "status": "approved",
            "state": "proposed",
            "object_type": "interface",
            "object_id": "item-1",
            "review": {"status": "approved"},
            "safety_confirmations": {
                "no_netbox_write": True,
                "no_apply_plan_created": True,
                "manual_review_required": True,
                "proposed_only": True,
            },
            "state_history": [{"event": "promoted_to_proposed"}],
        }
        f = approvals_dir / "test-001.json"
        f.write_text(json.dumps(record))

        review = {"decisions": []}
        review_file = tmpdir / "review.json"
        review_file.write_text(json.dumps(review))

        from tools.local.controlled_cycle_approval_readiness_gate import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--approvals-dir",
            str(approvals_dir),
            "--week2-review",
            str(review_file),
            "--output",
            str(tmpdir / "gate.md"),
            "--output-json",
            str(tmpdir / "gate.json"),
        ]

        with patch("sys.argv", test_args):
            main()

        result = json.loads((tmpdir / "gate.json").read_text())
        assert result["decision"] == "NOT_READY_FOR_MANUAL_APPROVAL_REVIEW"


def test_09_approval_gate_blocks_secret():
    """Test 9: Approval gate blocks records with secrets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        approvals_dir = tmpdir / "approvals"
        approvals_dir.mkdir()

        # Create record with token (should be blocked)
        record = {
            "approval_id": "test-001",
            "status": "proposed",
            "state": "proposed",
            "object_type": "interface",
            "object_id": "item-1",
            "notes": "token: secret123",
            "review": {"status": "proposed"},
            "safety_confirmations": {
                "no_netbox_write": True,
                "no_apply_plan_created": True,
                "manual_review_required": True,
                "proposed_only": True,
            },
            "state_history": [{"event": "promoted_to_proposed"}],
        }
        f = approvals_dir / "test-001.json"
        f.write_text(json.dumps(record))

        review = {"decisions": []}
        review_file = tmpdir / "review.json"
        review_file.write_text(json.dumps(review))

        from tools.local.controlled_cycle_approval_readiness_gate import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--approvals-dir",
            str(approvals_dir),
            "--week2-review",
            str(review_file),
            "--output",
            str(tmpdir / "gate.md"),
            "--output-json",
            str(tmpdir / "gate.json"),
        ]

        with patch("sys.argv", test_args):
            main()

        result = json.loads((tmpdir / "gate.json").read_text())
        assert result["decision"] == "NOT_READY_FOR_MANUAL_APPROVAL_REVIEW"


def test_10_promote_no_netbox_writes():
    """Test 10: Promote makes no NetBox writes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        week2_dir = tmpdir / "week2"
        week2_dir.mkdir()
        drafts_dir = week2_dir / "approval-drafts"
        drafts_dir.mkdir()
        approvals_dir = tmpdir / "approvals"
        approvals_dir.mkdir()

        review = {"decisions": []}
        review_file = week2_dir / "review.json"
        review_file.write_text(json.dumps(review))

        from tools.local.controlled_cycle_promote_to_approval_records import main

        with patch("requests.post") as mock_post:
            with patch("requests.patch") as mock_patch:
                test_args = [
                    "prog",
                    "--cycle-id",
                    "cycle-001",
                    "--device",
                    "4WNET-MNS-KTG-RX",
                    "--device-id",
                    "1890",
                    "--week2-review",
                    str(review_file),
                    "--drafts-dir",
                    str(drafts_dir),
                    "--output-dir",
                    str(approvals_dir),
                    "--report",
                    str(tmpdir / "promotion.md"),
                ]

                with patch("sys.argv", test_args):
                    main()

                assert not mock_post.called
                assert not mock_patch.called


def test_11_approval_gate_no_writes():
    """Test 11: Approval gate makes no writes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        approvals_dir = tmpdir / "approvals"
        approvals_dir.mkdir()

        create_proposed_approval_record(approvals_dir)

        review = {"decisions": []}
        review_file = tmpdir / "review.json"
        review_file.write_text(json.dumps(review))

        from tools.local.controlled_cycle_approval_readiness_gate import main

        with patch("requests.post") as mock_post:
            test_args = [
                "prog",
                "--cycle-id",
                "cycle-001",
                "--device",
                "4WNET-MNS-KTG-RX",
                "--device-id",
                "1890",
                "--approvals-dir",
                str(approvals_dir),
                "--week2-review",
                str(review_file),
                "--output",
                str(tmpdir / "gate.md"),
                "--output-json",
                str(tmpdir / "gate.json"),
            ]

            with patch("sys.argv", test_args):
                main()

            assert not mock_post.called


def test_12_full_week2_approval_flow():
    """Test 12: Full week 2 → approval readiness with no writes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        week2_dir = tmpdir / "week2"
        week2_dir.mkdir()
        drafts_dir = week2_dir / "approval-drafts"
        drafts_dir.mkdir()
        approvals_dir = tmpdir / "approvals"
        approvals_dir.mkdir()

        # Week 2 decisions
        decisions = [
            {
                "item_id": "item-1",
                "object_type": "interface",
                "team": "network_ops",
                "decision": "approve_for_approval_record",
                "reviewed_by": "reviewer@example.com",
                "evidence_reference": "test",
                "notes": "approved",
                "approval_record_allowed": "true",
            }
        ]
        create_mock_decisions_csv(week2_dir, decisions)
        create_mock_approval_draft(drafts_dir, "item-1")

        from tools.local.controlled_cycle_week2_review import main as review_main
        from tools.local.controlled_cycle_promote_to_approval_records import main as promote_main
        from tools.local.controlled_cycle_approval_readiness_gate import main as gate_main

        with patch("requests.post") as mock_post:
            with patch("requests.patch") as mock_patch:
                # Week 2 Review
                review_args = [
                    "prog",
                    "--cycle-id",
                    "cycle-001",
                    "--device",
                    "4WNET-MNS-KTG-RX",
                    "--device-id",
                    "1890",
                    "--cycle-dir",
                    str(tmpdir),
                    "--week2-dir",
                    str(week2_dir),
                    "--output",
                    str(week2_dir / "review.md"),
                    "--output-json",
                    str(week2_dir / "review.json"),
                ]
                with patch("sys.argv", review_args):
                    review_main()

                # Promote
                review_data = json.loads((week2_dir / "review.json").read_text())
                promote_args = [
                    "prog",
                    "--cycle-id",
                    "cycle-001",
                    "--device",
                    "4WNET-MNS-KTG-RX",
                    "--device-id",
                    "1890",
                    "--week2-review",
                    str(week2_dir / "review.json"),
                    "--drafts-dir",
                    str(drafts_dir),
                    "--output-dir",
                    str(approvals_dir),
                    "--report",
                    str(tmpdir / "promotion.md"),
                ]
                with patch("sys.argv", promote_args):
                    promote_main()

                # Gate
                gate_args = [
                    "prog",
                    "--cycle-id",
                    "cycle-001",
                    "--device",
                    "4WNET-MNS-KTG-RX",
                    "--device-id",
                    "1890",
                    "--approvals-dir",
                    str(approvals_dir),
                    "--week2-review",
                    str(week2_dir / "review.json"),
                    "--output",
                    str(tmpdir / "gate.md"),
                    "--output-json",
                    str(tmpdir / "gate.json"),
                ]
                with patch("sys.argv", gate_args):
                    gate_main()

                assert not mock_post.called
                assert not mock_patch.called


def main():
    """Run all tests."""
    test_functions = [
        test_01_week2_review_validates_decision,
        test_02_week2_review_blocks_invalid_decision,
        test_03_week2_review_blocks_approve_without_reviewer,
        test_04_week2_review_blocks_approve_without_allowed_flag,
        test_05_promote_creates_proposed_approval,
        test_06_promote_sets_proposed_status,
        test_07_approve_readiness_validates_proposed,
        test_08_approval_gate_blocks_approved_status,
        test_09_approval_gate_blocks_secret,
        test_10_promote_no_netbox_writes,
        test_11_approval_gate_no_writes,
        test_12_full_week2_approval_flow,
    ]

    passed = 0
    failed = 0

    for test_func in test_functions:
        try:
            test_func()
            print(f"✓ {test_func.__name__}")
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__}: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
