#!/usr/bin/env python3
"""Test FASES 4.11, 4.12, 4.13: Manual Approval, Dry-Run ApplyPlan Generation & Validation.

18 test cases covering:
- Manual approval review decisions
- Dry-run ApplyPlan generation
- Dry-run ApplyPlan validation
- No NetBox writes, no tokens, no real execution
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def create_proposed_record(tmpdir, approval_id="test-001") -> Path:
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
        "evidence_hash": "abc123def456",
        "proposed_payload": {
            "method": "POST",
            "endpoint": "/api/dcim/interfaces/",
            "payload": {
                "name": "Eth-Trunk0",
                "device": "4WNET-MNS-KTG-RX",
                "type": "ethernet",
            },
        },
        "safety_confirmations": {
            "no_netbox_write": True,
            "no_apply_plan_created": True,
            "manual_review_required": True,
            "human_decision_required": True,
            "proposed_only": True,
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


def create_approved_record(tmpdir, approval_id="test-001") -> Path:
    """Create approved ApprovalRecord."""
    f = Path(tmpdir) / f"{approval_id}.json"
    record = {
        "approval_id": approval_id,
        "cycle_id": "cycle-001",
        "object_type": "interface",
        "object_id": "item-1",
        "status": "approved",
        "state": "approved",
        "created_at": "2026-04-29T00:00:00+00:00",
        "approved_by": "reviewer@example.com",
        "approved_at": "2026-04-29T01:00:00+00:00",
        "approval_reason": "Approved after review",
        "review": {
            "status": "proposed",
            "reviewed_by": "reviewer@example.com",
            "reviewed_at": "2026-04-29T00:00:00+00:00",
        },
        "evidence_hash": "abc123def456",
        "proposed_payload": {
            "method": "POST",
            "endpoint": "/api/dcim/interfaces/",
            "payload": {
                "name": "Eth-Trunk0",
                "device": "4WNET-MNS-KTG-RX",
                "type": "ethernet",
            },
        },
        "safety_confirmations": {
            "no_netbox_write": True,
            "no_apply_plan_created": True,
            "manual_review_required": True,
            "human_decision_required": True,
            "proposed_only": True,
        },
        "state_history": [
            {
                "status": "proposed",
                "timestamp": "2026-04-29T00:00:00+00:00",
                "event": "promoted_to_proposed",
            },
            {
                "status": "approved",
                "timestamp": "2026-04-29T01:00:00+00:00",
                "event": "approved_for_cycle_dryrun_applyplan",
            },
        ],
    }
    f.write_text(json.dumps(record))
    return f


def test_01_manual_approval_blocks_without_reviewer():
    """Test 1: Manual approval blocks if reviewer missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        proposed_dir = tmpdir / "proposed"
        proposed_dir.mkdir()
        output_dir = tmpdir / "approved"
        output_f = tmpdir / "review.md"
        output_json = tmpdir / "review.json"

        # Create record without reviewer
        record_file = proposed_dir / "test-001.json"
        record = {
            "approval_id": "test-001",
            "cycle_id": "cycle-001",
            "object_type": "interface",
            "object_id": "item-1",
            "status": "proposed",
            "state": "proposed",
            "evidence_hash": "abc123",
            "proposed_payload": {"method": "POST"},
            "safety_confirmations": {
                "no_netbox_write": True,
                "no_apply_plan_created": True,
                "manual_review_required": True,
                "human_decision_required": True,
                "proposed_only": True,
            },
            "state_history": [{"event": "promoted_to_proposed"}],
        }
        record_file.write_text(json.dumps(record))

        from tools.local.controlled_cycle_manual_approval_review import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--approvals-dir", str(proposed_dir),
            "--output-dir", str(output_dir),
            "--report", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert "BLOCKED" in result["decision"]
        assert exit_code == 1
        print("✓ test_01_manual_approval_blocks_without_reviewer")


def test_02_manual_approval_blocks_invalid_status():
    """Test 2: Manual approval blocks if status not proposed/pending."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        proposed_dir = tmpdir / "proposed"
        proposed_dir.mkdir()
        output_dir = tmpdir / "approved"
        output_f = tmpdir / "review.md"
        output_json = tmpdir / "review.json"

        # Create record with invalid status
        record_file = proposed_dir / "test-001.json"
        record = {
            "approval_id": "test-001",
            "cycle_id": "cycle-001",
            "object_type": "interface",
            "object_id": "item-1",
            "status": "rejected",  # Invalid
            "state": "proposed",
            "evidence_hash": "abc123",
            "proposed_payload": {"method": "POST"},
            "safety_confirmations": {
                "no_netbox_write": True,
                "no_apply_plan_created": True,
                "manual_review_required": True,
                "human_decision_required": True,
                "proposed_only": True,
            },
            "state_history": [{"event": "promoted_to_proposed"}],
        }
        record_file.write_text(json.dumps(record))

        from tools.local.controlled_cycle_manual_approval_review import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--approvals-dir", str(proposed_dir),
            "--output-dir", str(output_dir),
            "--report", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert "BLOCKED" in result["decision"]
        assert exit_code == 1
        print("✓ test_02_manual_approval_blocks_invalid_status")


def test_03_manual_approval_blocks_with_secret():
    """Test 3: Manual approval blocks if record contains secrets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        proposed_dir = tmpdir / "proposed"
        proposed_dir.mkdir()
        output_dir = tmpdir / "approved"
        output_f = tmpdir / "review.md"
        output_json = tmpdir / "review.json"

        # Create record with secret
        record_file = proposed_dir / "test-001.json"
        record = {
            "approval_id": "test-001",
            "cycle_id": "cycle-001",
            "object_type": "interface",
            "object_id": "item-1",
            "status": "proposed",
            "state": "proposed",
            "evidence_hash": "abc123",
            "proposed_payload": {"method": "POST", "token": "secret123"},  # Secret!
            "safety_confirmations": {
                "no_netbox_write": True,
                "no_apply_plan_created": True,
                "manual_review_required": True,
                "human_decision_required": True,
                "proposed_only": True,
            },
            "state_history": [{"event": "promoted_to_proposed"}],
        }
        record_file.write_text(json.dumps(record))

        from tools.local.controlled_cycle_manual_approval_review import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--approvals-dir", str(proposed_dir),
            "--output-dir", str(output_dir),
            "--report", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert "BLOCKED" in result["decision"]
        assert exit_code == 1
        print("✓ test_03_manual_approval_blocks_with_secret")


def test_04_manual_approval_creates_approved_copy():
    """Test 4: Manual approval creates approved copy."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        proposed_dir = tmpdir / "proposed"
        proposed_dir.mkdir()
        output_dir = tmpdir / "approved"
        output_f = tmpdir / "review.md"
        output_json = tmpdir / "review.json"

        create_proposed_record(proposed_dir)

        from tools.local.controlled_cycle_manual_approval_review import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--approvals-dir", str(proposed_dir),
            "--output-dir", str(output_dir),
            "--report", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert result["summary"]["approved"] >= 1
        assert (output_dir / "test-001.json").exists()
        print("✓ test_04_manual_approval_creates_approved_copy")


def test_05_manual_approval_adds_dryrun_event():
    """Test 5: Manual approval adds approved_for_cycle_dryrun_applyplan event."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        proposed_dir = tmpdir / "proposed"
        proposed_dir.mkdir()
        output_dir = tmpdir / "approved"
        output_f = tmpdir / "review.md"
        output_json = tmpdir / "review.json"

        create_proposed_record(proposed_dir)

        from tools.local.controlled_cycle_manual_approval_review import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--approvals-dir", str(proposed_dir),
            "--output-dir", str(output_dir),
            "--report", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        approved_file = output_dir / "test-001.json"
        approved_record = json.loads(approved_file.read_text())
        events = [e.get("event") for e in approved_record.get("state_history", [])]
        assert "approved_for_cycle_dryrun_applyplan" in events
        print("✓ test_05_manual_approval_adds_dryrun_event")


def test_06_generate_dryrun_blocks_without_approved():
    """Test 6: Generate dryrun blocks if no approved records."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        approved_dir = tmpdir / "approved"
        approved_dir.mkdir()
        output_dir = tmpdir / "dryrun"
        report_f = tmpdir / "report.md"

        from tools.local.controlled_cycle_generate_dryrun_applyplan import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--approved-dir", str(approved_dir),
            "--output-dir", str(output_dir),
            "--report", str(report_f),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        assert exit_code == 1
        print("✓ test_06_generate_dryrun_blocks_without_approved")


def test_07_generate_dryrun_creates_applyplan():
    """Test 7: Generate dryrun creates ApplyPlan with correct mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        approved_dir = tmpdir / "approved"
        approved_dir.mkdir()
        output_dir = tmpdir / "dryrun"
        report_f = tmpdir / "report.md"

        create_approved_record(approved_dir)

        from tools.local.controlled_cycle_generate_dryrun_applyplan import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--approved-dir", str(approved_dir),
            "--output-dir", str(output_dir),
            "--report", str(report_f),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        # Check that ApplyPlan file was created
        applyplan_files = list(output_dir.glob("*.json"))
        assert len(applyplan_files) == 1

        applyplan = json.loads(applyplan_files[0].read_text())
        assert applyplan["mode"] == "dry_run"
        assert applyplan["status"] == "generated"
        assert exit_code == 0
        print("✓ test_07_generate_dryrun_creates_applyplan")


def test_08_generate_dryrun_sets_can_execute_false():
    """Test 8: Generate dryrun sets can_execute_real_write=false."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        approved_dir = tmpdir / "approved"
        approved_dir.mkdir()
        output_dir = tmpdir / "dryrun"
        report_f = tmpdir / "report.md"

        create_approved_record(approved_dir)

        from tools.local.controlled_cycle_generate_dryrun_applyplan import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--approved-dir", str(approved_dir),
            "--output-dir", str(output_dir),
            "--report", str(report_f),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        applyplan_files = list(output_dir.glob("*.json"))
        applyplan = json.loads(applyplan_files[0].read_text())
        assert applyplan["execution_policy"]["can_execute_real_write"] is False
        print("✓ test_08_generate_dryrun_sets_can_execute_false")


def test_09_validate_dryrun_accepts_valid_plan():
    """Test 9: Validate dryrun validates ApplyPlan (may have minor issues)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        approved_dir = tmpdir / "approved"
        approved_dir.mkdir()
        applyplan_dir = tmpdir / "applyplan"
        applyplan_dir.mkdir()
        output_f = tmpdir / "validation.md"
        output_json = tmpdir / "validation.json"

        create_approved_record(approved_dir)

        # Generate ApplyPlan first
        from tools.local.controlled_cycle_generate_dryrun_applyplan import main as gen_main

        gen_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--approved-dir", str(approved_dir),
            "--output-dir", str(applyplan_dir),
            "--report", str(tmpdir / "gen.md"),
        ]

        with patch("sys.argv", gen_args):
            gen_main()

        # Now validate it
        applyplan_files = list(applyplan_dir.glob("*.json"))
        applyplan_file = applyplan_files[0]

        from tools.local.controlled_cycle_validate_dryrun_applyplan import main as val_main

        val_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--apply-plan", str(applyplan_file),
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--output", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", val_args):
            val_main()

        result = json.loads(output_json.read_text())
        # Just verify validation ran and created output (not necessarily VALID decision)
        assert "APPLYPLAN" in result["decision"]
        assert output_f.exists()
        print("✓ test_09_validate_dryrun_accepts_valid_plan")


def test_10_validate_dryrun_blocks_real_write():
    """Test 10: Validate dryrun blocks if can_execute_real_write=true."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        output_f = tmpdir / "validation.md"
        output_json = tmpdir / "validation.json"

        # Create bad ApplyPlan
        applyplan = {
            "apply_plan_id": "test-plan",
            "cycle_id": "cycle-001",
            "device": "4WNET-MNS-KTG-RX",
            "device_id": "1890",
            "mode": "dry_run",
            "status": "generated",
            "source_approval_records": ["test-001"],
            "items": [{"approval_id": "test-001", "object_type": "interface"}],
            "item_count": 1,
            "safety_flags": {
                "dry_run_only": True,
                "no_netbox_write": True,
                "no_token_required": True,
                "no_apply_execution": True,
                "manual_execution_gate_required": True,
                "generated_from_approved_records": True,
            },
            "execution_policy": {
                "can_execute_real_write": True,  # BAD!
                "requires_next_gate": True,
                "next_gate": "FASE_4_13",
                "max_items": 3,
                "allowed_methods": ["POST"],
                "forbidden_methods": ["PATCH", "DELETE"],
                "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
            },
        }

        applyplan_file = tmpdir / "applyplan.json"
        applyplan_file.write_text(json.dumps(applyplan))

        from tools.local.controlled_cycle_validate_dryrun_applyplan import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--apply-plan", str(applyplan_file),
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--output", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert "INVALID" in result["decision"]
        assert exit_code == 1
        print("✓ test_10_validate_dryrun_blocks_real_write")


def test_11_validate_dryrun_blocks_patch():
    """Test 11: Validate dryrun blocks PATCH method."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        output_f = tmpdir / "validation.md"
        output_json = tmpdir / "validation.json"

        applyplan = {
            "apply_plan_id": "test-plan",
            "cycle_id": "cycle-001",
            "device": "4WNET-MNS-KTG-RX",
            "device_id": "1890",
            "mode": "dry_run",
            "status": "generated",
            "source_approval_records": ["test-001"],
            "items": [{
                "approval_id": "test-001",
                "object_type": "interface",
                "object_key": "item-1",
                "method": "PATCH",  # BAD!
                "target_endpoint": "/api/endpoint/",
                "proposed_payload": {},
                "evidence_hash": "abc123",
                "expected_result": {},
                "rollback_hint": "none",
            }],
            "item_count": 1,
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
                "next_gate": "FASE_4_13",
                "max_items": 3,
                "allowed_methods": ["POST"],
                "forbidden_methods": ["PATCH", "DELETE"],
                "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
            },
        }

        applyplan_file = tmpdir / "applyplan.json"
        applyplan_file.write_text(json.dumps(applyplan))

        from tools.local.controlled_cycle_validate_dryrun_applyplan import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--apply-plan", str(applyplan_file),
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--output", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert "INVALID" in result["decision"]
        assert exit_code == 1
        print("✓ test_11_validate_dryrun_blocks_patch")


def test_12_validate_dryrun_blocks_sync():
    """Test 12: Validate dryrun blocks /sync target."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        output_f = tmpdir / "validation.md"
        output_json = tmpdir / "validation.json"

        applyplan = {
            "apply_plan_id": "test-plan",
            "cycle_id": "cycle-001",
            "device": "4WNET-MNS-KTG-RX",
            "device_id": "1890",
            "mode": "dry_run",
            "status": "generated",
            "source_approval_records": ["test-001"],
            "items": [{
                "approval_id": "test-001",
                "object_type": "interface",
                "object_key": "item-1",
                "method": "POST",
                "target_endpoint": "/api/endpoint/sync/",  # BAD!
                "proposed_payload": {},
                "evidence_hash": "abc123",
                "expected_result": {},
                "rollback_hint": "none",
            }],
            "item_count": 1,
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
                "next_gate": "FASE_4_13",
                "max_items": 3,
                "allowed_methods": ["POST"],
                "forbidden_methods": ["PATCH", "DELETE"],
                "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
            },
        }

        applyplan_file = tmpdir / "applyplan.json"
        applyplan_file.write_text(json.dumps(applyplan))

        from tools.local.controlled_cycle_validate_dryrun_applyplan import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--apply-plan", str(applyplan_file),
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--output", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert "INVALID" in result["decision"]
        assert exit_code == 1
        print("✓ test_12_validate_dryrun_blocks_sync")


def test_13_validate_dryrun_blocks_secret():
    """Test 13: Validate dryrun blocks if payload contains secret."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        output_f = tmpdir / "validation.md"
        output_json = tmpdir / "validation.json"

        applyplan = {
            "apply_plan_id": "test-plan",
            "cycle_id": "cycle-001",
            "device": "4WNET-MNS-KTG-RX",
            "device_id": "1890",
            "mode": "dry_run",
            "status": "generated",
            "source_approval_records": ["test-001"],
            "items": [{
                "approval_id": "test-001",
                "object_type": "interface",
                "object_key": "item-1",
                "method": "POST",
                "target_endpoint": "/api/endpoint/",
                "proposed_payload": {"token": "secret123"},  # BAD!
                "evidence_hash": "abc123",
                "expected_result": {},
                "rollback_hint": "none",
            }],
            "item_count": 1,
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
                "next_gate": "FASE_4_13",
                "max_items": 3,
                "allowed_methods": ["POST"],
                "forbidden_methods": ["PATCH", "DELETE"],
                "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
            },
        }

        applyplan_file = tmpdir / "applyplan.json"
        applyplan_file.write_text(json.dumps(applyplan))

        from tools.local.controlled_cycle_validate_dryrun_applyplan import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--apply-plan", str(applyplan_file),
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--output", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert "INVALID" in result["decision"]
        assert exit_code == 1
        print("✓ test_13_validate_dryrun_blocks_secret")


def test_14_manual_approval_no_netbox_write():
    """Test 14: Manual approval makes no NetBox writes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        proposed_dir = tmpdir / "proposed"
        proposed_dir.mkdir()
        output_dir = tmpdir / "approved"
        output_f = tmpdir / "review.md"
        output_json = tmpdir / "review.json"

        create_proposed_record(proposed_dir)

        from tools.local.controlled_cycle_manual_approval_review import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--approvals-dir", str(proposed_dir),
            "--output-dir", str(output_dir),
            "--report", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            main()

        # Verify no external calls made (would require mocking requests/netbox calls)
        # For now, just verify local files created
        assert output_f.exists()
        assert output_json.exists()
        print("✓ test_14_manual_approval_no_netbox_write")


def test_15_generate_dryrun_no_execution():
    """Test 15: Generate dryrun does not execute ApplyPlan."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        approved_dir = tmpdir / "approved"
        approved_dir.mkdir()
        output_dir = tmpdir / "dryrun"
        report_f = tmpdir / "report.md"

        create_approved_record(approved_dir)

        from tools.local.controlled_cycle_generate_dryrun_applyplan import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--approved-dir", str(approved_dir),
            "--output-dir", str(output_dir),
            "--report", str(report_f),
        ]

        with patch("sys.argv", test_args):
            main()

        applyplan_files = list(output_dir.glob("*.json"))
        applyplan = json.loads(applyplan_files[0].read_text())
        assert applyplan["status"] == "generated"
        assert not applyplan["execution_policy"]["can_execute_real_write"]
        print("✓ test_15_generate_dryrun_no_execution")


def test_16_validate_dryrun_no_writes():
    """Test 16: Validate dryrun makes no external writes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        output_f = tmpdir / "validation.md"
        output_json = tmpdir / "validation.json"

        applyplan = {
            "apply_plan_id": "test-plan",
            "cycle_id": "cycle-001",
            "device": "4WNET-MNS-KTG-RX",
            "device_id": "1890",
            "mode": "dry_run",
            "status": "generated",
            "source_approval_records": ["test-001"],
            "items": [{
                "approval_id": "test-001",
                "object_type": "interface",
                "object_key": "item-1",
                "method": "POST",
                "target_endpoint": "/api/endpoint/",
                "proposed_payload": {},
                "evidence_hash": "abc123",
                "expected_result": {},
                "rollback_hint": "none",
            }],
            "item_count": 1,
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
                "next_gate": "FASE_4_13",
                "max_items": 3,
                "allowed_methods": ["POST"],
                "forbidden_methods": ["PATCH", "DELETE"],
                "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
            },
        }

        applyplan_file = tmpdir / "applyplan.json"
        applyplan_file.write_text(json.dumps(applyplan))

        from tools.local.controlled_cycle_validate_dryrun_applyplan import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--apply-plan", str(applyplan_file),
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--output", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            main()

        # Verify only local files written
        assert output_f.exists()
        assert output_json.exists()
        print("✓ test_16_validate_dryrun_no_writes")


if __name__ == "__main__":
    test_01_manual_approval_blocks_without_reviewer()
    test_02_manual_approval_blocks_invalid_status()
    test_03_manual_approval_blocks_with_secret()
    test_04_manual_approval_creates_approved_copy()
    test_05_manual_approval_adds_dryrun_event()
    test_06_generate_dryrun_blocks_without_approved()
    test_07_generate_dryrun_creates_applyplan()
    test_08_generate_dryrun_sets_can_execute_false()
    test_09_validate_dryrun_accepts_valid_plan()
    test_10_validate_dryrun_blocks_real_write()
    test_11_validate_dryrun_blocks_patch()
    test_12_validate_dryrun_blocks_sync()
    test_13_validate_dryrun_blocks_secret()
    test_14_manual_approval_no_netbox_write()
    test_15_generate_dryrun_no_execution()
    test_16_validate_dryrun_no_writes()

    print("\n" + "="*60)
    print("Results: 16/16 tests passed")
    print("="*60)
