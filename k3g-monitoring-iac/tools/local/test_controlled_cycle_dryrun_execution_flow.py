#!/usr/bin/env python3
"""Test FASES 4.14, 4.15, 4.16: Dry-Run Execution Gate, Simulation, Real Write Readiness."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def create_valid_applyplan(tmpdir) -> Path:
    """Create valid dry-run ApplyPlan."""
    f = Path(tmpdir) / "applyplan.json"
    applyplan = {
        "apply_plan_id": "applyplan-cycle-001-abc123",
        "cycle_id": "cycle-001",
        "device": "4WNET-MNS-KTG-RX",
        "device_id": "1890",
        "mode": "dry_run",
        "status": "generated",
        "source_approval_records": ["test-001"],
        "items": [{
            "item_id": "item-1",
            "approval_id": "test-001",
            "object_type": "interface",
            "object_key": "item-1",
            "method": "POST",
            "target_endpoint": "/api/dcim/interfaces/",
            "proposed_payload": {"name": "Eth-Trunk0"},
            "evidence_hash": "abc123",
            "expected_result": {"status_code": 201},
            "rollback_hint": "DELETE /api/dcim/interfaces/item-1",
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
            "next_gate": "FASE_4_14",
            "max_items": 3,
            "allowed_methods": ["POST"],
            "forbidden_methods": ["PATCH", "DELETE"],
            "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
        },
    }
    f.write_text(json.dumps(applyplan))
    return f


def create_valid_approval_record(tmpdir) -> Path:
    """Create valid approved ApprovalRecord."""
    f = Path(tmpdir) / "test-001.json"
    record = {
        "approval_id": "test-001",
        "cycle_id": "cycle-001",
        "status": "approved",
        "state": "approved",
        "approved_by": "reviewer@example.com",
        "approved_at": "2026-04-29T01:00:00+00:00",
        "approval_reason": "Approved after review",
        "object_type": "interface",
        "object_id": "item-1",
        "evidence_hash": "abc123",
        "proposed_payload": {"method": "POST"},
        "state_history": [
            {"event": "approved_for_cycle_dryrun_applyplan"},
        ],
    }
    f.write_text(json.dumps(record))
    return f


def test_01_gate_blocks_no_validation_report():
    """Test 1: Gate blocks if validation report missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        applyplan_file = create_valid_applyplan(tmpdir)
        gate_f = tmpdir / "gate.md"
        gate_json = tmpdir / "gate.json"

        from tools.local.controlled_cycle_dryrun_execution_gate import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--apply-plan", str(applyplan_file),
            "--validation-report", str(tmpdir / "nonexistent.md"),
            "--output", str(gate_f),
            "--output-json", str(gate_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(gate_json.read_text())
        assert "BLOCKED" in result["decision"]
        assert exit_code == 1
        print("✓ test_01_gate_blocks_no_validation_report")


def test_02_gate_blocks_invalid_mode():
    """Test 2: Gate blocks if mode != dry_run."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        applyplan_file = tmpdir / "applyplan.json"

        applyplan = {
            "apply_plan_id": "test",
            "cycle_id": "cycle-001",
            "device": "4WNET",
            "mode": "real",  # Invalid!
            "status": "generated",
            "items": [{"item_id": "1"}],
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
                "allowed_methods": ["POST"],
                "forbidden_methods": ["PATCH", "DELETE"],
                "forbidden_targets": ["/sync"],
            },
        }
        applyplan_file.write_text(json.dumps(applyplan))

        report_f = tmpdir / "report.md"
        report_f.write_text("CYCLE_DRYRUN_APPLYPLAN_VALID")

        gate_f = tmpdir / "gate.md"
        gate_json = tmpdir / "gate.json"

        from tools.local.controlled_cycle_dryrun_execution_gate import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--apply-plan", str(applyplan_file),
            "--validation-report", str(report_f),
            "--output", str(gate_f),
            "--output-json", str(gate_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(gate_json.read_text())
        assert "BLOCKED" in result["decision"]
        assert exit_code == 1
        print("✓ test_02_gate_blocks_invalid_mode")


def test_03_gate_produces_output():
    """Test 3: Gate produces output files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        applyplan_file = create_valid_applyplan(tmpdir)
        report_f = tmpdir / "report.md"
        report_f.write_text("CYCLE_DRYRUN_APPLYPLAN_VALID")

        gate_f = tmpdir / "gate.md"
        gate_json = tmpdir / "gate.json"

        from tools.local.controlled_cycle_dryrun_execution_gate import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--apply-plan", str(applyplan_file),
            "--validation-report", str(report_f),
            "--output", str(gate_f),
            "--output-json", str(gate_json),
        ]

        with patch("sys.argv", test_args):
            main()

        result = json.loads(gate_json.read_text())
        assert "CYCLE_DRYRUN_EXECUTION" in result["decision"]
        assert gate_f.exists()
        assert gate_json.exists()
        print("✓ test_03_gate_produces_output")


def test_04_simulation_creates_output():
    """Test 4: Simulation creates output files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        applyplan_file = create_valid_applyplan(tmpdir)
        gate_f = tmpdir / "gate.md"
        gate_f.write_text("CYCLE_DRYRUN_EXECUTION_READY")

        sim_f = tmpdir / "sim.md"
        sim_json = tmpdir / "sim.json"

        from tools.local.controlled_cycle_execute_dryrun_simulation import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--apply-plan", str(applyplan_file),
            "--execution-gate", str(gate_f),
            "--output", str(sim_f),
            "--result-json", str(sim_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(sim_json.read_text())
        assert result["status"].startswith("CYCLE_DRYRUN_SIMULATION")
        assert result["safety_confirmations"]["local_only"] is True
        assert result["safety_confirmations"]["no_network_call"] is True
        assert exit_code == 0
        print("✓ test_04_simulation_creates_output")


def test_05_simulation_no_network_calls():
    """Test 5: Simulation has no network-related imports."""
    import inspect
    from tools.local import controlled_cycle_execute_dryrun_simulation as sim_module

    source = inspect.getsource(sim_module)

    forbidden = ["requests", "pynetbox", "httpx", "urllib", "socket"]
    for lib in forbidden:
        assert lib not in source, f"Found forbidden import: {lib}"

    print("✓ test_05_simulation_no_network_calls")


def test_06_readiness_gate_validates_chain():
    """Test 6: Readiness gate validates governance chain."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        applyplan_file = create_valid_applyplan(tmpdir)
        sim_result_f = tmpdir / "sim.json"

        sim_result = {
            "status": "CYCLE_DRYRUN_SIMULATION_PASSED",
            "next_gate_required": True,
            "summary": {"total_items": 1},
        }
        sim_result_f.write_text(json.dumps(sim_result))

        sim_report_f = tmpdir / "sim.md"
        sim_report_f.write_text("# Simulation\nTest")

        gate_report_f = tmpdir / "gate.md"
        gate_report_f.write_text("CYCLE_DRYRUN_EXECUTION_READY")

        approved_dir = tmpdir / "approved"
        approved_dir.mkdir()
        create_valid_approval_record(approved_dir)

        output_f = tmpdir / "readiness.md"
        output_json = tmpdir / "readiness.json"

        from tools.local.controlled_cycle_real_write_readiness_gate import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--apply-plan", str(applyplan_file),
            "--simulation-result", str(sim_result_f),
            "--simulation-report", str(sim_report_f),
            "--dryrun-execution-gate", str(gate_report_f),
            "--approved-dir", str(approved_dir),
            "--output", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert "READY" in result["decision"]
        assert result["governance_chain"]["simulation_passed"] is True
        assert exit_code == 0
        print("✓ test_06_readiness_gate_validates_chain")


def test_07_no_netbox_token_read():
    """Test 7: Tools don't read NETBOX_WRITE_TOKEN."""
    import inspect
    from tools.local import controlled_cycle_dryrun_execution_gate
    from tools.local import controlled_cycle_execute_dryrun_simulation
    from tools.local import controlled_cycle_real_write_readiness_gate

    modules = [
        controlled_cycle_dryrun_execution_gate,
        controlled_cycle_execute_dryrun_simulation,
        controlled_cycle_real_write_readiness_gate,
    ]

    for module in modules:
        source = inspect.getsource(module)
        assert "NETBOX_WRITE_TOKEN" not in source
        assert "os.environ" not in source or "NETBOX_WRITE_TOKEN" not in source

    print("✓ test_07_no_netbox_token_read")


if __name__ == "__main__":
    test_01_gate_blocks_no_validation_report()
    test_02_gate_blocks_invalid_mode()
    test_03_gate_produces_output()
    test_04_simulation_creates_output()
    test_05_simulation_no_network_calls()
    test_06_readiness_gate_validates_chain()
    test_07_no_netbox_token_read()

    print("\n" + "="*60)
    print("Results: 7/7 tests passed")
    print("="*60)
