#!/usr/bin/env python3
"""Test FASES 4.17-4.21: Real Write Authorization and Freeze Checks."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def create_valid_execution_package(tmpdir) -> Path:
    """Create valid execution package."""
    f = Path(tmpdir) / "execution_package.json"
    pkg = {
        "execution_id": "exec-cycle-001-abc123",
        "cycle_id": "cycle-001",
        "apply_plan_id": "applyplan-cycle-001-abc123",
        "device": "4WNET-MNS-KTG-RX",
        "device_id": "1890",
        "execution_allowed": False,
        "execution_phrase": "EXECUTAR_ESCRITA_REAL_CYCLE-001_4WNET-MNS-KTG-RX_applyplan-cycle-001-abc123",
        "items": [
            {
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
            }
        ],
        "item_count": 1,
        "safety_flags": {
            "execution_allowed": True,
            "no_automatic_retry": True,
            "no_rollback_automatic": True,
            "requires_execution_confirmation": True,
            "requires_final_no_write_freeze": True,
            "generated_from_approved_records": True,
        },
        "execution_policy": {
            "execution_allowed": False,
            "requires_next_gate": True,
            "next_gate": "FASE_4_21_FINAL_NO_WRITE_FREEZE",
            "max_items": 3,
            "allowed_methods": ["POST"],
            "forbidden_methods": ["PATCH", "DELETE"],
            "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
        },
        "source_applyplan": {
            "apply_plan_id": "applyplan-cycle-001-abc123",
            "mode": "dry_run",
            "status": "validated",
            "item_count": 1,
        },
    }
    f.write_text(json.dumps(pkg))
    return f


def create_valid_authorization_package(tmpdir) -> Path:
    """Create valid authorization package."""
    f = Path(tmpdir) / "authz_package.json"
    pkg = {
        "cycle_id": "cycle-001",
        "apply_plan_id": "applyplan-cycle-001-abc123",
        "device": "4WNET-MNS-KTG-RX",
        "authorization_id": "authz-cycle-001-abc123",
        "authorization_phrase": "AUTORIZO_PRE_FLIGHT_ESCRITA_REAL_CYCLE-001_4WNET-MNS-KTG-RX_applyplan-cycle-001-abc123",
        "generated_at": "2026-04-29T01:00:00+00:00",
        "readiness_gate_decision": "CYCLE_READY_FOR_REAL_WRITE_REVIEW",
        "item_count": 1,
        "validation_passed": True,
        "issues": [],
        "evidence_chain": {
            "applyplan_validated": True,
            "simulation_passed": True,
            "readiness_gate_ready": True,
            "safety_flags_enforced": True,
        },
    }
    f.write_text(json.dumps(pkg))
    return f


def create_valid_preflight_result(tmpdir) -> Path:
    """Create valid preflight gate result."""
    f = Path(tmpdir) / "preflight_result.json"
    result = {
        "cycle_id": "cycle-001",
        "apply_plan_id": "applyplan-cycle-001-abc123",
        "device": "4WNET-MNS-KTG-RX",
        "authorization_id": "authz-cycle-001-abc123",
        "decision": "CYCLE_PREFLIGHT_CLEARED_FOR_EXECUTION",
        "validated_at": "2026-04-29T01:00:00+00:00",
        "preflight_checks": {
            "phrase_validated": True,
            "evidence_chain_complete": True,
            "safety_enforced": True,
        },
        "issues": [],
    }
    f.write_text(json.dumps(result))
    return f


def create_valid_applyplan(tmpdir) -> Path:
    """Create valid dry-run ApplyPlan."""
    f = Path(tmpdir) / "applyplan.json"
    applyplan = {
        "apply_plan_id": "applyplan-cycle-001-abc123",
        "cycle_id": "cycle-001",
        "device": "4WNET-MNS-KTG-RX",
        "device_id": "1890",
        "mode": "dry_run",
        "status": "validated",
        "items": [
            {
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
            }
        ],
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
            "next_gate": "FASE_4_17_BUILD_AUTHZ_PACKAGE",
            "max_items": 3,
            "allowed_methods": ["POST"],
            "forbidden_methods": ["PATCH", "DELETE"],
            "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
        },
    }
    f.write_text(json.dumps(applyplan))
    return f


def create_valid_readiness_gate(tmpdir) -> Path:
    """Create valid readiness gate result."""
    f = Path(tmpdir) / "readiness_gate.json"
    gate = {
        "cycle_id": "cycle-001",
        "apply_plan_id": "applyplan-cycle-001-abc123",
        "decision": "CYCLE_READY_FOR_REAL_WRITE_REVIEW",
        "validated_at": "2026-04-29T01:00:00+00:00",
        "summary": {
            "item_count": 1,
            "simulated_items": 1,
            "issues_found": 0,
            "ready_for_authorization": True,
        },
        "issues": [],
        "governance_chain": {
            "approval_records_validated": True,
            "simulation_passed": True,
            "execution_gate_ready": True,
            "applyplan_safe": True,
        },
    }
    f.write_text(json.dumps(gate))
    return f


def create_valid_simulation_result(tmpdir) -> Path:
    """Create valid simulation result."""
    f = Path(tmpdir) / "sim_result.json"
    result = {
        "simulation_id": "sim-cycle-001-abc123",
        "cycle_id": "cycle-001",
        "apply_plan_id": "applyplan-cycle-001-abc123",
        "device": "4WNET-MNS-KTG-RX",
        "status": "CYCLE_DRYRUN_SIMULATION_PASSED",
        "generated_at": "2026-04-29T01:00:00+00:00",
        "items": [
            {
                "item_id": "item-1",
                "dry_run_status": "simulated_ok",
            }
        ],
        "summary": {"total_items": 1, "simulated_ok": 1},
        "safety_confirmations": {
            "local_only": True,
            "no_network_call": True,
            "no_token_read": True,
            "no_netbox_write": True,
            "no_apply_execution": True,
        },
        "next_gate_required": True,
    }
    f.write_text(json.dumps(result))
    return f


def create_valid_validation_result(tmpdir) -> Path:
    """Create valid execution package validation result."""
    f = Path(tmpdir) / "validation_result.json"
    result = {
        "cycle_id": "cycle-001",
        "execution_id": "exec-cycle-001-abc123",
        "apply_plan_id": "applyplan-cycle-001-abc123",
        "decision": "CYCLE_EXECUTION_PACKAGE_VALID",
        "validated_at": "2026-04-29T01:00:00+00:00",
        "summary": {
            "item_count": 1,
            "issues_found": 0,
            "valid_for_freeze": True,
        },
        "issues": [],
        "safety_checks": {
            "execution_allowed_false": True,
            "safety_flags_enforced": True,
            "no_secrets": True,
            "no_forbidden_methods": True,
        },
    }
    f.write_text(json.dumps(result))
    return f


def test_01_authorization_package_blocks_not_ready():
    """Test 1: Authorization package blocks if readiness gate NOT_READY."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        applyplan_file = create_valid_applyplan(tmpdir)

        # Create readiness gate with NOT_READY decision
        readiness_file = tmpdir / "readiness.json"
        readiness = {
            "cycle_id": "cycle-001",
            "apply_plan_id": "applyplan-cycle-001-abc123",
            "decision": "CYCLE_NOT_READY_FOR_REAL_WRITE",
            "issues": ["test issue"],
            "governance_chain": {
                "applyplan_safe": True,
                "simulation_passed": True,
                "execution_gate_ready": True,
            },
        }
        readiness_file.write_text(json.dumps(readiness))

        sim_result_file = create_valid_simulation_result(tmpdir)

        output_f = tmpdir / "authz.md"
        output_json = tmpdir / "authz.json"

        from tools.local.controlled_cycle_build_real_write_authorization_package import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--apply-plan", str(applyplan_file),
            "--simulation-result", str(sim_result_file),
            "--readiness-gate", str(readiness_file),
            "--approved-dir", str(tmpdir),
            "--output", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        # Should fail because readiness gate is NOT_READY
        assert exit_code == 1
        result = json.loads(output_json.read_text())
        assert "NOT_READY" in result.get("readiness_gate_decision", "")
        print("✓ test_01_authorization_package_blocks_not_ready")


def test_02_authorization_package_generates_phrase():
    """Test 2: Authorization package generates correct phrase."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        applyplan_file = create_valid_applyplan(tmpdir)
        readiness_file = create_valid_readiness_gate(tmpdir)
        sim_result_file = create_valid_simulation_result(tmpdir)

        output_f = tmpdir / "authz.md"
        output_json = tmpdir / "authz.json"

        from tools.local.controlled_cycle_build_real_write_authorization_package import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--apply-plan", str(applyplan_file),
            "--simulation-result", str(sim_result_file),
            "--readiness-gate", str(readiness_file),
            "--approved-dir", str(tmpdir),
            "--output", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        phrase = result.get("authorization_phrase", "")
        assert "AUTORIZO_PRE_FLIGHT_ESCRITA_REAL_CYCLE-001" in phrase
        assert "4WNET-MNS-KTG-RX" in phrase
        print("✓ test_02_authorization_package_generates_phrase")


def test_03_preflight_gate_accepts_correct_phrase():
    """Test 3: Preflight gate accepts correct authorization phrase."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        authz_pkg_file = create_valid_authorization_package(tmpdir)
        phrase = "AUTORIZO_PRE_FLIGHT_ESCRITA_REAL_CYCLE-001_4WNET-MNS-KTG-RX_applyplan-cycle-001-abc123"

        output_f = tmpdir / "preflight.md"
        output_json = tmpdir / "preflight.json"

        from tools.local.controlled_cycle_real_write_final_preflight_gate import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--authorization-package", str(authz_pkg_file),
            "--authorization-phrase", phrase,
            "--output", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert "CLEARED_FOR_EXECUTION" in result["decision"]
        assert exit_code == 0
        print("✓ test_03_preflight_gate_accepts_correct_phrase")


def test_04_preflight_gate_rejects_wrong_phrase():
    """Test 4: Preflight gate rejects incorrect phrase."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        authz_pkg_file = create_valid_authorization_package(tmpdir)
        wrong_phrase = "WRONG_PHRASE_CYCLE-001"

        output_f = tmpdir / "preflight.md"
        output_json = tmpdir / "preflight.json"

        from tools.local.controlled_cycle_real_write_final_preflight_gate import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--authorization-package", str(authz_pkg_file),
            "--authorization-phrase", wrong_phrase,
            "--output", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert "BLOCKED" in result["decision"]
        assert exit_code == 1
        print("✓ test_04_preflight_gate_rejects_wrong_phrase")


def test_05_execution_package_creation():
    """Test 5: Execution package created with execution_allowed=false."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        applyplan_file = create_valid_applyplan(tmpdir)
        preflight_file = create_valid_preflight_result(tmpdir)

        output_f = tmpdir / "exec_pkg.md"
        output_json = tmpdir / "exec_pkg.json"

        from tools.local.controlled_cycle_build_real_write_execution_package import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--apply-plan", str(applyplan_file),
            "--preflight-gate", str(preflight_file),
            "--output", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert result["execution_allowed"] is False
        assert "EXECUTAR_ESCRITA_REAL_CYCLE-001" in result["execution_phrase"]
        assert exit_code == 0
        print("✓ test_05_execution_package_creation")


def test_06_execution_package_validation_passes():
    """Test 6: Execution package validation passes for valid package."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        exec_pkg_file = create_valid_execution_package(tmpdir)

        output_f = tmpdir / "validation.md"
        output_json = tmpdir / "validation.json"

        from tools.local.controlled_cycle_validate_real_write_execution_package import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--execution-package", str(exec_pkg_file),
            "--output", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert "VALID" in result["decision"]
        assert exit_code == 0
        print("✓ test_06_execution_package_validation_passes")


def test_07_freeze_check_clears_valid_package():
    """Test 7: Freeze check clears valid execution package."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        exec_pkg_file = create_valid_execution_package(tmpdir)
        validation_file = create_valid_validation_result(tmpdir)

        output_f = tmpdir / "freeze.md"
        output_json = tmpdir / "freeze.json"

        from tools.local.controlled_cycle_final_no_write_freeze_check import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--execution-package", str(exec_pkg_file),
            "--validation-result", str(validation_file),
            "--output", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert "CLEARED" in result["decision"]
        assert result["all_frozen"] is True
        assert exit_code == 0
        print("✓ test_07_freeze_check_clears_valid_package")


def test_08_freeze_check_blocks_execution_allowed_true():
    """Test 8: Freeze check blocks if execution_allowed=true."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create package with execution_allowed=true (wrong!)
        exec_pkg_file = tmpdir / "exec_pkg.json"
        pkg = {
            "execution_id": "exec-cycle-001-abc123",
            "execution_allowed": True,  # WRONG!
            "items": [{"method": "POST", "target_endpoint": "/api/dcim/interfaces/"}],
            "safety_flags": {
                "execution_allowed": True,
                "no_automatic_retry": True,
                "no_rollback_automatic": True,
                "requires_execution_confirmation": True,
                "requires_final_no_write_freeze": True,
            },
            "execution_policy": {
                "execution_allowed": False,
                "requires_next_gate": True,
            },
        }
        exec_pkg_file.write_text(json.dumps(pkg))

        validation_file = create_valid_validation_result(tmpdir)

        output_f = tmpdir / "freeze.md"
        output_json = tmpdir / "freeze.json"

        from tools.local.controlled_cycle_final_no_write_freeze_check import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--execution-package", str(exec_pkg_file),
            "--validation-result", str(validation_file),
            "--output", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert "BLOCKED" in result["decision"]
        assert exit_code == 1
        print("✓ test_08_freeze_check_blocks_execution_allowed_true")


def test_09_freeze_check_blocks_token_keyword():
    """Test 9: Freeze check blocks if token keyword found."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create package with token keyword
        exec_pkg_file = tmpdir / "exec_pkg.json"
        pkg = {
            "execution_id": "exec-cycle-001-abc123",
            "execution_allowed": False,
            "items": [
                {
                    "method": "POST",
                    "target_endpoint": "/api/dcim/interfaces/",
                    "proposed_payload": {"note": "token_value_here"},  # SECRET!
                }
            ],
            "safety_flags": {
                "execution_allowed": True,
                "no_automatic_retry": True,
                "no_rollback_automatic": True,
                "requires_execution_confirmation": True,
                "requires_final_no_write_freeze": True,
            },
            "execution_policy": {
                "execution_allowed": False,
                "requires_next_gate": True,
            },
        }
        exec_pkg_file.write_text(json.dumps(pkg))

        validation_file = create_valid_validation_result(tmpdir)

        output_f = tmpdir / "freeze.md"
        output_json = tmpdir / "freeze.json"

        from tools.local.controlled_cycle_final_no_write_freeze_check import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--execution-package", str(exec_pkg_file),
            "--validation-result", str(validation_file),
            "--output", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert "BLOCKED" in result["decision"]
        assert exit_code == 1
        print("✓ test_09_freeze_check_blocks_token_keyword")


def test_10_freeze_check_blocks_forbidden_method():
    """Test 10: Freeze check blocks PATCH or DELETE methods."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create package with PATCH method
        exec_pkg_file = tmpdir / "exec_pkg.json"
        pkg = {
            "execution_id": "exec-cycle-001-abc123",
            "execution_allowed": False,
            "items": [
                {
                    "method": "PATCH",  # FORBIDDEN!
                    "target_endpoint": "/api/dcim/interfaces/1/",
                }
            ],
            "safety_flags": {
                "execution_allowed": True,
                "no_automatic_retry": True,
                "no_rollback_automatic": True,
                "requires_execution_confirmation": True,
                "requires_final_no_write_freeze": True,
            },
            "execution_policy": {
                "execution_allowed": False,
                "requires_next_gate": True,
            },
        }
        exec_pkg_file.write_text(json.dumps(pkg))

        validation_file = create_valid_validation_result(tmpdir)

        output_f = tmpdir / "freeze.md"
        output_json = tmpdir / "freeze.json"

        from tools.local.controlled_cycle_final_no_write_freeze_check import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--execution-package", str(exec_pkg_file),
            "--validation-result", str(validation_file),
            "--output", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert "BLOCKED" in result["decision"]
        assert exit_code == 1
        print("✓ test_10_freeze_check_blocks_forbidden_method")


def test_11_freeze_check_blocks_sync_endpoint():
    """Test 11: Freeze check blocks /sync endpoints."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create package with /sync endpoint
        exec_pkg_file = tmpdir / "exec_pkg.json"
        pkg = {
            "execution_id": "exec-cycle-001-abc123",
            "execution_allowed": False,
            "items": [
                {
                    "method": "POST",
                    "target_endpoint": "/api/dcim/devices/1/sync",  # FORBIDDEN!
                }
            ],
            "safety_flags": {
                "execution_allowed": True,
                "no_automatic_retry": True,
                "no_rollback_automatic": True,
                "requires_execution_confirmation": True,
                "requires_final_no_write_freeze": True,
            },
            "execution_policy": {
                "execution_allowed": False,
                "requires_next_gate": True,
            },
        }
        exec_pkg_file.write_text(json.dumps(pkg))

        validation_file = create_valid_validation_result(tmpdir)

        output_f = tmpdir / "freeze.md"
        output_json = tmpdir / "freeze.json"

        from tools.local.controlled_cycle_final_no_write_freeze_check import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--execution-package", str(exec_pkg_file),
            "--validation-result", str(validation_file),
            "--output", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert "BLOCKED" in result["decision"]
        assert exit_code == 1
        print("✓ test_11_freeze_check_blocks_sync_endpoint")


def test_12_no_network_imports_in_fase_417():
    """Test 12: FASE 4.17 has no network imports."""
    import inspect
    from tools.local import controlled_cycle_build_real_write_authorization_package as m417

    source = inspect.getsource(m417)
    forbidden = ["requests", "pynetbox", "httpx", "urllib", "socket"]
    for lib in forbidden:
        assert lib not in source, f"Found forbidden import: {lib}"

    print("✓ test_12_no_network_imports_in_fase_417")


def test_13_no_network_imports_in_fase_418():
    """Test 13: FASE 4.18 has no network imports."""
    import inspect
    from tools.local import controlled_cycle_real_write_final_preflight_gate as m418

    source = inspect.getsource(m418)
    forbidden = ["requests", "pynetbox", "httpx", "urllib", "socket"]
    for lib in forbidden:
        assert lib not in source, f"Found forbidden import: {lib}"

    print("✓ test_13_no_network_imports_in_fase_418")


def test_14_no_network_imports_in_fase_419():
    """Test 14: FASE 4.19 has no network imports."""
    import inspect
    from tools.local import controlled_cycle_build_real_write_execution_package as m419

    source = inspect.getsource(m419)
    forbidden = ["requests", "pynetbox", "httpx", "urllib", "socket"]
    for lib in forbidden:
        assert lib not in source, f"Found forbidden import: {lib}"

    print("✓ test_14_no_network_imports_in_fase_419")


def test_15_no_network_imports_in_fase_420():
    """Test 15: FASE 4.20 has no network imports."""
    import inspect
    from tools.local import controlled_cycle_validate_real_write_execution_package as m420

    source = inspect.getsource(m420)
    forbidden = ["requests", "pynetbox", "httpx", "urllib", "socket"]
    for lib in forbidden:
        assert lib not in source, f"Found forbidden import: {lib}"

    print("✓ test_15_no_network_imports_in_fase_420")


def test_16_no_network_imports_in_fase_421():
    """Test 16: FASE 4.21 has no network imports."""
    import inspect
    from tools.local import controlled_cycle_final_no_write_freeze_check as m421

    source = inspect.getsource(m421)
    forbidden = ["requests", "pynetbox", "httpx", "urllib", "socket"]
    for lib in forbidden:
        assert lib not in source, f"Found forbidden import: {lib}"

    print("✓ test_16_no_network_imports_in_fase_421")


def test_17_no_netbox_token_in_fase_417():
    """Test 17: FASE 4.17 doesn't read NETBOX_WRITE_TOKEN."""
    import inspect
    from tools.local import controlled_cycle_build_real_write_authorization_package as m417

    source = inspect.getsource(m417)
    assert "NETBOX_WRITE_TOKEN" not in source
    print("✓ test_17_no_netbox_token_in_fase_417")


def test_18_all_tools_no_subprocess():
    """Test 18: All tools have no subprocess calls."""
    import inspect
    from tools.local import (
        controlled_cycle_build_real_write_authorization_package as m417,
        controlled_cycle_real_write_final_preflight_gate as m418,
        controlled_cycle_build_real_write_execution_package as m419,
        controlled_cycle_validate_real_write_execution_package as m420,
        controlled_cycle_final_no_write_freeze_check as m421,
    )

    modules = [m417, m418, m419, m420, m421]
    for module in modules:
        source = inspect.getsource(module)
        assert "subprocess" not in source
        assert "os.system" not in source
        assert "os.popen" not in source

    print("✓ test_18_all_tools_no_subprocess")


if __name__ == "__main__":
    test_01_authorization_package_blocks_not_ready()
    test_02_authorization_package_generates_phrase()
    test_03_preflight_gate_accepts_correct_phrase()
    test_04_preflight_gate_rejects_wrong_phrase()
    test_05_execution_package_creation()
    test_06_execution_package_validation_passes()
    test_07_freeze_check_clears_valid_package()
    test_08_freeze_check_blocks_execution_allowed_true()
    test_09_freeze_check_blocks_token_keyword()
    test_10_freeze_check_blocks_forbidden_method()
    test_11_freeze_check_blocks_sync_endpoint()
    test_12_no_network_imports_in_fase_417()
    test_13_no_network_imports_in_fase_418()
    test_14_no_network_imports_in_fase_419()
    test_15_no_network_imports_in_fase_420()
    test_16_no_network_imports_in_fase_421()
    test_17_no_netbox_token_in_fase_417()
    test_18_all_tools_no_subprocess()

    print("\n" + "="*60)
    print("Results: 18/18 tests passed")
    print("="*60)
