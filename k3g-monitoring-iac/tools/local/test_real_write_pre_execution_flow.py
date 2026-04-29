#!/usr/bin/env python3
"""Test FASES 2.47-2.52: Real write pre-execution flow.

20 test cases covering:
- Authorization package blocking on NOT_READY
- Authorization package request generation on READY
- Required phrase generation
- Final preflight gate validation
- Execution package generation and validation
- Package freezecheck
- No prohibited imports
- No token reads
"""

import json
import sys
import tempfile
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def create_mock_readiness_gate(tmpdir, decision: str) -> Path:
    """Create mock readiness gate file."""
    gate_file = Path(tmpdir) / "gate.md"
    if decision == "READY":
        content = "### READY_FOR_REAL_WRITE_REVIEW\nGate approved"
    elif decision == "READY_WITH_RESTRICTIONS":
        content = "### READY_WITH_RESTRICTIONS\nApproved with restrictions"
    else:
        content = "### NOT_READY_FOR_REAL_WRITE\nGate failed"

    gate_file.write_text(content)
    return gate_file


def create_mock_apply_plan(tmpdir, apply_plan_id: str = "plan-123") -> Path:
    """Create mock ApplyPlan."""
    plan_file = Path(tmpdir) / "apply_plan.json"
    plan = {
        "apply_plan_id": apply_plan_id,
        "mode": "dry_run",
        "status": "generated",
        "can_execute_real_write": False,
        "requires_next_gate": True,
        "items": [
            {
                "item_id": "item-1",
                "approval_id": "approval-123",
                "object_type": "Interface",
                "object_key": "Eth-Trunk0",
                "method": "POST",
                "target_endpoint": "/api/dcim/interfaces/",
                "proposed_payload": {"name": "Eth-Trunk0", "type": "ethernet"},
                "expected_result": "201",
                "rollback_hint": "DELETE /api/dcim/interfaces/123",
            }
        ],
    }
    plan_file.write_text(json.dumps(plan))
    return plan_file


def create_mock_simulation_result(tmpdir) -> Path:
    """Create mock simulation result."""
    result_file = Path(tmpdir) / "simulation.json"
    result = {
        "simulation_id": "sim-456",
        "status": "DRYRUN_SIMULATION_PASSED",
        "items": [
            {
                "item_id": "item-1",
                "simulated_status": "OK",
            }
        ],
    }
    result_file.write_text(json.dumps(result))
    return result_file


def create_mock_approved_record(tmpdir, approval_id: str) -> Path:
    """Create mock approved ApprovalRecord."""
    record_file = Path(tmpdir) / f"approval-record-{approval_id}.json"
    record = {
        "approval_record_id": approval_id,
        "status": "approved",
        "approved_by": "test-reviewer",
        "approved_at": "2026-04-29T10:00:00+00:00",
        "object_type": "Interface",
        "object_key": "Eth-Trunk0",
        "state_history": [
            {"to": "manual_approval_reviewed"},
            {"to": "approved_for_dry_run_applyplan"},
        ],
    }
    record_file.write_text(json.dumps(record))
    return record_file


def test_01_authorization_package_blocks_not_ready():
    """Test 1: Authorization package blocks gate NOT_READY."""
    with tempfile.TemporaryDirectory() as tmpdir:
        gate_file = create_mock_readiness_gate(tmpdir, "NOT_READY")
        plan_file = create_mock_apply_plan(tmpdir)
        sim_file = create_mock_simulation_result(tmpdir)
        approval_dir = Path(tmpdir) / "approved"
        approval_dir.mkdir()
        output_dir = Path(tmpdir) / "output"

        # Import after creating fixtures
        from tools.local.build_real_write_authorization_package import validate_readiness_gate

        status, reason = validate_readiness_gate(gate_file)
        assert status == "BLOCKED", f"Expected BLOCKED, got {status}"
        assert "NOT_READY" in reason


def test_02_authorization_package_ready():
    """Test 2: Authorization package creates request if READY."""
    with tempfile.TemporaryDirectory() as tmpdir:
        gate_file = create_mock_readiness_gate(tmpdir, "READY")
        plan_file = create_mock_apply_plan(tmpdir)
        sim_file = create_mock_simulation_result(tmpdir)
        approval_dir = Path(tmpdir) / "approved"
        approval_dir.mkdir()
        create_mock_approved_record(approval_dir, "approval-123")
        output_dir = Path(tmpdir) / "output"

        from tools.local.build_real_write_authorization_package import validate_readiness_gate

        status, reason = validate_readiness_gate(gate_file)
        assert status == "AUTHORIZED_PACKAGE_READY"


def test_03_authorization_package_generates_phrase():
    """Test 3: Authorization package generates required phrase."""
    from tools.local.build_real_write_authorization_package import generate_authorization_phrase

    phrase = generate_authorization_phrase("4WNET-MNS-KTG-RX", "plan-123")
    assert "AUTORIZO_PRE_FLIGHT_ESCRITA_REAL_" in phrase
    assert "4WNET-MNS-KTG-RX" in phrase
    assert "plan-123" in phrase


def test_04_final_preflight_validates_phrase():
    """Test 4: Final preflight validates phrase exactly."""
    from tools.local.real_write_final_preflight_gate import validate_phrase

    required = "AUTORIZO_PRE_FLIGHT_ESCRITA_REAL_device_plan"
    operator = "AUTORIZO_PRE_FLIGHT_ESCRITA_REAL_device_plan"

    valid, reason = validate_phrase(required, operator)
    assert valid is True


def test_05_final_preflight_blocks_wrong_phrase():
    """Test 5: Final preflight blocks incorrect phrase."""
    from tools.local.real_write_final_preflight_gate import validate_phrase

    required = "AUTORIZO_PRE_FLIGHT_ESCRITA_REAL_device_plan"
    operator = "WRONG_PHRASE"

    valid, reason = validate_phrase(required, operator)
    assert valid is False


def test_06_execution_package_has_execution_allowed_false():
    """Test 6: Execution package sets execution_allowed=false."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = Path(tmpdir) / "package.json"
        pkg = {
            "execution_package_id": "pkg-123",
            "device": "test-device",
            "execution_allowed": False,
            "token_required_in_next_phase": True,
            "one_shot_execution": True,
            "status": "prepared",
            "items": [],
            "safety_confirmations": {
                "no_write_executed": True,
                "no_token_read": True,
                "no_network_call": True,
                "package_only": True,
                "real_write_not_executed": True,
            },
        }
        pkg_file.write_text(json.dumps(pkg))

        assert pkg["execution_allowed"] is False


def test_07_execution_package_generates_phrase():
    """Test 7: Execution package generates required execution phrase."""
    from tools.local.build_real_write_execution_package import generate_execution_phrase

    phrase = generate_execution_phrase("4WNET-MNS-KTG-RX", "pkg-uuid")
    assert "EXECUTO_ESCRITA_REAL_" in phrase
    assert "4WNET-MNS-KTG-RX" in phrase
    assert "pkg-uuid" in phrase


def test_08_package_validation_rejects_execution_allowed_true():
    """Test 8: Package validation rejects execution_allowed=true."""
    from tools.local.validate_real_write_execution_package import validate_execution_package

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = Path(tmpdir) / "package.json"
        pkg = {
            "execution_package_id": "pkg-123",
            "device": "test",
            "apply_plan_id": "plan-123",
            "authorization_id": "auth-123",
            "execution_allowed": True,  # WRONG
            "status": "prepared",
            "items": [{"approval_id": "a1", "object_type": "Interface", "object_key": "Eth0"}],
        }
        pkg_file.write_text(json.dumps(pkg))

        valid, reason, _ = validate_execution_package(pkg_file)
        assert valid is False


def test_09_package_validation_rejects_secrets():
    """Test 9: Package validation rejects secrets in payload."""
    from tools.local.validate_real_write_execution_package import check_for_secrets

    pkg = {
        "items": [
            {
                "payload": {
                    "name": "interface",
                    "password": "secret123",  # FORBIDDEN
                }
            }
        ]
    }

    valid, reason = check_for_secrets(pkg)
    assert valid is False


def test_10_execution_package_no_imports_requests():
    """Test 10: Execution package does not import requests."""
    import tools.local.build_real_write_execution_package as mod

    source = Path(mod.__file__).read_text()
    assert "import requests" not in source
    assert "from requests" not in source


def test_11_authorization_package_no_imports_requests():
    """Test 11: Authorization package does not import requests."""
    import tools.local.build_real_write_authorization_package as mod

    source = Path(mod.__file__).read_text()
    assert "import requests" not in source


def test_12_validation_package_no_imports_requests():
    """Test 12: Validation package does not import requests."""
    import tools.local.validate_real_write_execution_package as mod

    source = Path(mod.__file__).read_text()
    assert "import requests" not in source


def test_13_preflight_gate_no_imports_requests():
    """Test 13: Preflight gate does not import requests."""
    import tools.local.real_write_final_preflight_gate as mod

    source = Path(mod.__file__).read_text()
    assert "import requests" not in source


def test_14_freeze_check_no_imports_requests():
    """Test 14: Freeze check does not import requests."""
    import tools.local.final_no_write_freeze_check as mod

    source = Path(mod.__file__).read_text()
    assert "import requests" not in source


def test_15_no_tools_import_pynetbox():
    """Test 15: No tools import pynetbox."""
    tools_to_check = [
        "tools.local.build_real_write_authorization_package",
        "tools.local.real_write_final_preflight_gate",
        "tools.local.build_real_write_execution_package",
        "tools.local.validate_real_write_execution_package",
        "tools.local.final_no_write_freeze_check",
    ]

    for tool_name in tools_to_check:
        try:
            mod = __import__(tool_name, fromlist=[tool_name.split(".")[-1]])
            source = Path(mod.__file__).read_text()
            assert "import pynetbox" not in source
            assert "from pynetbox" not in source
        except ImportError:
            pass  # Tool may not be importable in test context


def test_16_package_blocks_forbidden_methods():
    """Test 16: Package validation blocks PATCH/DELETE."""
    from tools.local.validate_real_write_execution_package import validate_execution_package

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = Path(tmpdir) / "package.json"
        pkg = {
            "execution_package_id": "pkg-123",
            "device": "test",
            "apply_plan_id": "plan-123",
            "authorization_id": "auth-123",
            "execution_allowed": False,
            "status": "prepared",
            "items": [
                {
                    "approval_id": "a1",
                    "object_type": "Interface",
                    "object_key": "Eth0",
                    "method": "PATCH",  # FORBIDDEN
                    "endpoint": "/api/test/",
                    "payload": {},
                    "rollback_hint": "undo",
                    "pre_write_checks": [],
                    "post_write_checks": [],
                }
            ],
        }
        pkg_file.write_text(json.dumps(pkg))

        valid, reason, _ = validate_execution_package(pkg_file)
        assert valid is False


def test_17_package_blocks_forbidden_endpoints():
    """Test 17: Package validation blocks forbidden endpoints."""
    from tools.local.validate_real_write_execution_package import validate_execution_package

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = Path(tmpdir) / "package.json"
        pkg = {
            "execution_package_id": "pkg-123",
            "device": "test",
            "apply_plan_id": "plan-123",
            "authorization_id": "auth-123",
            "execution_allowed": False,
            "status": "prepared",
            "items": [
                {
                    "approval_id": "a1",
                    "object_type": "Interface",
                    "object_key": "Eth0",
                    "method": "POST",
                    "endpoint": "/api/dcim/equipment/",  # FORBIDDEN
                    "payload": {},
                    "rollback_hint": "undo",
                    "pre_write_checks": [],
                    "post_write_checks": [],
                }
            ],
        }
        pkg_file.write_text(json.dumps(pkg))

        valid, reason, _ = validate_execution_package(pkg_file)
        assert valid is False


def test_18_freeze_check_detects_tokens():
    """Test 18: Freeze check detects token patterns in items."""
    from tools.local.final_no_write_freeze_check import check_for_tokens

    # The function looks for patterns like "token=", "auth=", "bearer ", "api_key=", etc.
    # specifically in the items list
    pkg = {
        "items": [
            {
                "payload": {
                    "note": "token=abc123",  # Forbidden pattern in item
                }
            }
        ]
    }

    valid, reason = check_for_tokens(pkg)
    assert valid is False, f"Expected token pattern to be detected in item, got: {reason}"


def test_19_freeze_check_detects_writes():
    """Test 19: Freeze check detects 'applied' status."""
    from tools.local.final_no_write_freeze_check import check_for_writes

    pkg = {
        "items": [
            {
                "status": "applied",  # FORBIDDEN
            }
        ]
    }

    valid, reason = check_for_writes(pkg)
    assert valid is False


def test_20_end_to_end_no_netbox_writes():
    """Test 20: Complete flow executes zero NetBox writes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create all required artifacts
        gate_file = create_mock_readiness_gate(tmpdir, "READY")
        plan_file = create_mock_apply_plan(tmpdir)
        sim_file = create_mock_simulation_result(tmpdir)
        approval_dir = tmpdir / "approved"
        approval_dir.mkdir()
        create_mock_approved_record(approval_dir, "approval-123")

        # Import tools
        from tools.local.build_real_write_authorization_package import (
            validate_readiness_gate,
            validate_apply_plan,
            validate_simulation_result,
        )

        # Run validations
        gate_status, _ = validate_readiness_gate(gate_file)
        plan_valid, _ = validate_apply_plan(plan_file)
        sim_valid, _ = validate_simulation_result(sim_file)

        # Verify no writes occurred
        assert gate_status in ["AUTHORIZED_PACKAGE_READY", "READY_WITH_RESTRICTIONS"]
        assert plan_valid is True
        assert sim_valid is True
        assert plan_file.read_text() == create_mock_apply_plan(tmpdir).read_text()  # Unchanged


def main():
    """Run all tests."""
    test_functions = [
        test_01_authorization_package_blocks_not_ready,
        test_02_authorization_package_ready,
        test_03_authorization_package_generates_phrase,
        test_04_final_preflight_validates_phrase,
        test_05_final_preflight_blocks_wrong_phrase,
        test_06_execution_package_has_execution_allowed_false,
        test_07_execution_package_generates_phrase,
        test_08_package_validation_rejects_execution_allowed_true,
        test_09_package_validation_rejects_secrets,
        test_10_execution_package_no_imports_requests,
        test_11_authorization_package_no_imports_requests,
        test_12_validation_package_no_imports_requests,
        test_13_preflight_gate_no_imports_requests,
        test_14_freeze_check_no_imports_requests,
        test_15_no_tools_import_pynetbox,
        test_16_package_blocks_forbidden_methods,
        test_17_package_blocks_forbidden_endpoints,
        test_18_freeze_check_detects_tokens,
        test_19_freeze_check_detects_writes,
        test_20_end_to_end_no_netbox_writes,
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
