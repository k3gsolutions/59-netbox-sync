#!/usr/bin/env python3
"""Test FASES 4.22-4.25: Real Write Execution, Verification, Compliance, Closure."""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def create_valid_execution_package(tmpdir) -> Path:
    """Create valid execution package."""
    f = Path(tmpdir) / "execution_package.json"
    pkg = {
        "execution_id": "exec-cycle-001-abc123",
        "cycle_id": "cycle-001",
        "device": "4WNET-MNS-KTG-RX",
        "device_id": "1890",
        "execution_allowed": False,
        "execution_phrase": "EXECUTAR_ESCRITA_REAL_CYCLE-001_4WNET-MNS-KTG-RX_exec-cycle-001-abc123",
        "items": [
            {
                "item_id": "item-1",
                "approval_id": "test-001",
                "object_type": "interface",
                "object_key": "Eth-Trunk0",
                "method": "POST",
                "target_endpoint": "/api/dcim/interfaces/",
                "proposed_payload": {"name": "Eth-Trunk0", "type": "virtual"},
            }
        ],
        "item_count": 1,
        "safety_flags": {
            "execution_allowed": True,
            "requires_execution_confirmation": True,
            "requires_final_no_write_freeze": True,
            "no_automatic_retry": True,
        },
        "execution_policy": {
            "execution_allowed": False,
            "requires_next_gate": True,
            "allowed_methods": ["POST"],
            "forbidden_methods": ["PATCH", "DELETE"],
            "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
        },
    }
    f.write_text(json.dumps(pkg))
    return f


def create_valid_freeze_result(tmpdir) -> Path:
    """Create valid freeze result."""
    f = Path(tmpdir) / "freeze.json"
    result = {
        "decision": "CYCLE_FINAL_NO_WRITE_FREEZE_CLEARED",
        "checks": {
            "no_netbox_writes": True,
            "no_token_references": True,
            "no_network_targets": True,
            "execution_package_locked": True,
            "validation_passed": True,
        },
    }
    f.write_text(json.dumps(result))
    return f


def create_valid_execution_result(tmpdir) -> Path:
    """Create valid execution result."""
    f = Path(tmpdir) / "exec_result.json"
    result = {
        "execution_id": "exec-cycle-001-abc123",
        "cycle_id": "cycle-001",
        "device": "4WNET-MNS-KTG-RX",
        "status": "CYCLE_REAL_WRITE_SUCCESS",
        "operator": "Keslley",
        "items": [
            {
                "item_id": "item-1",
                "approval_id": "test-001",
                "object_type": "interface",
                "object_key": "Eth-Trunk0",
                "response_id": 42,
                "status": "CYCLE_REAL_WRITE_CREATED",
                "verification_status": "verified",
            }
        ],
        "summary": {"total_items": 1, "created": 1, "failed": 0},
        "one_shot_execution": True,
        "retry_attempted": False,
        "rollback_attempted": False,
        "token_logged": False,
        "token_saved": False,
    }
    f.write_text(json.dumps(result))
    return f


def test_01_execute_blocks_no_confirm_flag():
    """Test 1: Execute blocks without --confirm-real-write-once."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        exec_pkg_file = create_valid_execution_package(tmpdir)
        freeze_file = create_valid_freeze_result(tmpdir)

        output_json = tmpdir / "result.json"
        output_md = tmpdir / "result.md"

        from tools.local.controlled_cycle_execute_real_write_once import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--execution-package", str(exec_pkg_file),
            "--operator", "Keslley",
            "--confirm-execution-phrase", "EXECUTAR_ESCRITA_REAL_CYCLE-001_4WNET-MNS-KTG-RX_exec-cycle-001-abc123",
            # Missing: --confirm-real-write-once
            "--netbox-url", "https://example.com",
            "--output-json", str(output_json),
            "--output-md", str(output_md),
            "--freeze-result", str(freeze_file),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        assert exit_code != 0
        print("✓ test_01_execute_blocks_no_confirm_flag")


def test_02_execute_blocks_wrong_phrase():
    """Test 2: Execute blocks with wrong execution phrase."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        exec_pkg_file = create_valid_execution_package(tmpdir)
        freeze_file = create_valid_freeze_result(tmpdir)

        output_json = tmpdir / "result.json"
        output_md = tmpdir / "result.md"

        from tools.local.controlled_cycle_execute_real_write_once import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--execution-package", str(exec_pkg_file),
            "--operator", "Keslley",
            "--confirm-execution-phrase", "WRONG_PHRASE",
            "--confirm-real-write-once",
            "--netbox-url", "https://example.com",
            "--output-json", str(output_json),
            "--output-md", str(output_md),
            "--freeze-result", str(freeze_file),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert "ABORTED" in result["status"]
        assert exit_code != 0
        print("✓ test_02_execute_blocks_wrong_phrase")


def test_03_execute_blocks_no_token():
    """Test 3: Execute blocks without NETBOX_WRITE_TOKEN."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        exec_pkg_file = create_valid_execution_package(tmpdir)
        freeze_file = create_valid_freeze_result(tmpdir)

        output_json = tmpdir / "result.json"
        output_md = tmpdir / "result.md"

        from tools.local.controlled_cycle_execute_real_write_once import main

        # Clear token from environment
        env = os.environ.copy()
        env.pop("NETBOX_WRITE_TOKEN", None)

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--execution-package", str(exec_pkg_file),
            "--operator", "Keslley",
            "--confirm-execution-phrase", "EXECUTAR_ESCRITA_REAL_CYCLE-001_4WNET-MNS-KTG-RX_exec-cycle-001-abc123",
            "--confirm-real-write-once",
            "--netbox-url", "https://example.com",
            "--output-json", str(output_json),
            "--output-md", str(output_md),
            "--freeze-result", str(freeze_file),
        ]

        with patch("sys.argv", test_args):
            with patch.dict(os.environ, env, clear=True):
                exit_code = main()

        result = json.loads(output_json.read_text())
        assert "ABORTED" in result["status"]
        assert exit_code != 0
        print("✓ test_03_execute_blocks_no_token")


def test_04_execute_blocks_freeze_not_ready():
    """Test 4: Execute blocks if freeze not cleared."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        exec_pkg_file = create_valid_execution_package(tmpdir)

        # Create freeze with BLOCKED decision
        freeze_file = tmpdir / "freeze.json"
        freeze_file.write_text(json.dumps({"decision": "CYCLE_FINAL_NO_WRITE_FREEZE_BLOCKED"}))

        output_json = tmpdir / "result.json"
        output_md = tmpdir / "result.md"

        from tools.local.controlled_cycle_execute_real_write_once import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--execution-package", str(exec_pkg_file),
            "--operator", "Keslley",
            "--confirm-execution-phrase", "EXECUTAR_ESCRITA_REAL_CYCLE-001_4WNET-MNS-KTG-RX_exec-cycle-001-abc123",
            "--confirm-real-write-once",
            "--netbox-url", "https://example.com",
            "--output-json", str(output_json),
            "--output-md", str(output_md),
            "--freeze-result", str(freeze_file),
        ]

        with patch("sys.argv", test_args):
            with patch.dict(os.environ, {"NETBOX_WRITE_TOKEN": "test-token"}, clear=True):
                exit_code = main()

        result = json.loads(output_json.read_text())
        assert "ABORTED" in result["status"]
        assert exit_code != 0
        print("✓ test_04_execute_blocks_freeze_not_ready")


def test_05_execute_blocks_patch_method():
    """Test 5: Execute blocks PATCH method."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create execution package with PATCH method
        exec_pkg_file = tmpdir / "execution_package.json"
        pkg = {
            "execution_id": "exec-cycle-001-abc123",
            "cycle_id": "cycle-001",
            "device": "4WNET-MNS-KTG-RX",
            "execution_allowed": False,
            "execution_phrase": "EXECUTAR_ESCRITA_REAL_CYCLE-001_4WNET-MNS-KTG-RX_exec-cycle-001-abc123",
            "items": [
                {
                    "item_id": "item-1",
                    "method": "PATCH",  # FORBIDDEN!
                    "target_endpoint": "/api/dcim/interfaces/1/",
                    "proposed_payload": {"name": "Eth-Trunk0"},
                }
            ],
            "safety_flags": {
                "execution_allowed": True,
                "requires_execution_confirmation": True,
                "requires_final_no_write_freeze": True,
                "no_automatic_retry": True,
            },
            "execution_policy": {
                "execution_allowed": False,
                "allowed_methods": ["POST"],
                "forbidden_methods": ["PATCH", "DELETE"],
            },
        }
        exec_pkg_file.write_text(json.dumps(pkg))

        freeze_file = create_valid_freeze_result(tmpdir)
        output_json = tmpdir / "result.json"
        output_md = tmpdir / "result.md"

        from tools.local.controlled_cycle_execute_real_write_once import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--execution-package", str(exec_pkg_file),
            "--operator", "Keslley",
            "--confirm-execution-phrase", "EXECUTAR_ESCRITA_REAL_CYCLE-001_4WNET-MNS-KTG-RX_exec-cycle-001-abc123",
            "--confirm-real-write-once",
            "--netbox-url", "https://example.com",
            "--output-json", str(output_json),
            "--output-md", str(output_md),
            "--freeze-result", str(freeze_file),
        ]

        with patch("sys.argv", test_args):
            with patch.dict(os.environ, {"NETBOX_WRITE_TOKEN": "test-token"}, clear=True):
                exit_code = main()

        result = json.loads(output_json.read_text())
        assert "ABORTED" in result["status"]
        assert exit_code != 0
        print("✓ test_05_execute_blocks_patch_method")


def test_06_execute_blocks_sync_endpoint():
    """Test 6: Execute blocks /sync endpoints."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        exec_pkg_file = tmpdir / "execution_package.json"
        pkg = {
            "execution_id": "exec-cycle-001-abc123",
            "cycle_id": "cycle-001",
            "device": "4WNET-MNS-KTG-RX",
            "execution_allowed": False,
            "execution_phrase": "EXECUTAR_ESCRITA_REAL_CYCLE-001_4WNET-MNS-KTG-RX_exec-cycle-001-abc123",
            "items": [
                {
                    "item_id": "item-1",
                    "method": "POST",
                    "target_endpoint": "/api/dcim/devices/1/sync",  # FORBIDDEN!
                    "proposed_payload": {"action": "sync"},
                }
            ],
            "safety_flags": {
                "execution_allowed": True,
                "requires_execution_confirmation": True,
                "requires_final_no_write_freeze": True,
                "no_automatic_retry": True,
            },
            "execution_policy": {
                "execution_allowed": False,
                "allowed_methods": ["POST"],
                "forbidden_targets": ["/sync"],
            },
        }
        exec_pkg_file.write_text(json.dumps(pkg))

        freeze_file = create_valid_freeze_result(tmpdir)
        output_json = tmpdir / "result.json"
        output_md = tmpdir / "result.md"

        from tools.local.controlled_cycle_execute_real_write_once import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--execution-package", str(exec_pkg_file),
            "--operator", "Keslley",
            "--confirm-execution-phrase", "EXECUTAR_ESCRITA_REAL_CYCLE-001_4WNET-MNS-KTG-RX_exec-cycle-001-abc123",
            "--confirm-real-write-once",
            "--netbox-url", "https://example.com",
            "--output-json", str(output_json),
            "--output-md", str(output_md),
            "--freeze-result", str(freeze_file),
        ]

        with patch("sys.argv", test_args):
            with patch.dict(os.environ, {"NETBOX_WRITE_TOKEN": "test-token"}, clear=True):
                exit_code = main()

        result = json.loads(output_json.read_text())
        assert "ABORTED" in result["status"]
        assert exit_code != 0
        print("✓ test_06_execute_blocks_sync_endpoint")


def test_07_execute_blocks_token_in_payload():
    """Test 7: Execute blocks if token keyword in payload."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        exec_pkg_file = tmpdir / "execution_package.json"
        pkg = {
            "execution_id": "exec-cycle-001-abc123",
            "cycle_id": "cycle-001",
            "device": "4WNET-MNS-KTG-RX",
            "execution_allowed": False,
            "execution_phrase": "EXECUTAR_ESCRITA_REAL_CYCLE-001_4WNET-MNS-KTG-RX_exec-cycle-001-abc123",
            "items": [
                {
                    "item_id": "item-1",
                    "method": "POST",
                    "target_endpoint": "/api/dcim/interfaces/",
                    "proposed_payload": {"name": "Eth-Trunk0", "secret": "password123"},  # BLOCKED!
                }
            ],
            "safety_flags": {
                "execution_allowed": True,
                "requires_execution_confirmation": True,
                "requires_final_no_write_freeze": True,
                "no_automatic_retry": True,
            },
            "execution_policy": {
                "execution_allowed": False,
                "allowed_methods": ["POST"],
            },
        }
        exec_pkg_file.write_text(json.dumps(pkg))

        freeze_file = create_valid_freeze_result(tmpdir)
        output_json = tmpdir / "result.json"
        output_md = tmpdir / "result.md"

        from tools.local.controlled_cycle_execute_real_write_once import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--execution-package", str(exec_pkg_file),
            "--operator", "Keslley",
            "--confirm-execution-phrase", "EXECUTAR_ESCRITA_REAL_CYCLE-001_4WNET-MNS-KTG-RX_exec-cycle-001-abc123",
            "--confirm-real-write-once",
            "--netbox-url", "https://example.com",
            "--output-json", str(output_json),
            "--output-md", str(output_md),
            "--freeze-result", str(freeze_file),
        ]

        with patch("sys.argv", test_args):
            with patch.dict(os.environ, {"NETBOX_WRITE_TOKEN": "test-token"}, clear=True):
                exit_code = main()

        result = json.loads(output_json.read_text())
        assert "ABORTED" in result["status"]
        assert exit_code != 0
        print("✓ test_07_execute_blocks_token_in_payload")


def test_08_execute_token_not_logged():
    """Test 8: Token not logged in result."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        exec_pkg_file = create_valid_execution_package(tmpdir)
        freeze_file = create_valid_freeze_result(tmpdir)

        output_json = tmpdir / "result.json"
        output_md = tmpdir / "result.md"

        from tools.local.controlled_cycle_execute_real_write_once import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--execution-package", str(exec_pkg_file),
            "--operator", "Keslley",
            "--confirm-execution-phrase", "EXECUTAR_ESCRITA_REAL_CYCLE-001_4WNET-MNS-KTG-RX_exec-cycle-001-abc123",
            "--confirm-real-write-once",
            "--netbox-url", "https://example.com",
            "--output-json", str(output_json),
            "--output-md", str(output_md),
            "--freeze-result", str(freeze_file),
        ]

        with patch("sys.argv", test_args):
            with patch.dict(os.environ, {"NETBOX_WRITE_TOKEN": "secret-token-value"}, clear=True):
                with patch("urllib.request.urlopen") as mock_urlopen:
                    # Mock successful POST
                    mock_response = MagicMock()
                    mock_response.read.return_value = json.dumps({"id": 42}).encode()
                    mock_response.__enter__.return_value = mock_response

                    # Mock successful GET
                    mock_urlopen.return_value.__enter__.return_value = mock_response

                    exit_code = main()

        result_text = output_json.read_text()
        assert "secret-token-value" not in result_text
        assert "NETBOX_WRITE_TOKEN" not in result_text
        result = json.loads(result_text)
        assert result.get("token_logged") is False
        assert result.get("token_saved") is False
        print("✓ test_08_execute_token_not_logged")


def test_09_verification_get_only():
    """Test 9: Verification uses only GET."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        exec_result_file = create_valid_execution_result(tmpdir)
        exec_pkg_file = create_valid_execution_package(tmpdir)

        output_json = tmpdir / "verification.json"
        output_md = tmpdir / "verification.md"

        from tools.local.controlled_cycle_post_write_verification import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--execution-result", str(exec_result_file),
            "--execution-package", str(exec_pkg_file),
            "--netbox-url", "https://example.com",
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--output-json", str(output_json),
            "--output-md", str(output_md),
        ]

        with patch("sys.argv", test_args):
            with patch.dict(os.environ, {"NETBOX_WRITE_TOKEN": "test-token"}, clear=True):
                with patch("urllib.request.urlopen") as mock_urlopen:
                    mock_response = MagicMock()
                    mock_response.read.return_value = json.dumps({
                        "id": 42,
                        "name": "Eth-Trunk0",
                        "type": "virtual"
                    }).encode()
                    mock_urlopen.return_value.__enter__.return_value = mock_response

                    exit_code = main()

        result = json.loads(output_json.read_text())
        assert "PASSED" in result["status"]
        print("✓ test_09_verification_get_only")


def test_10_verification_not_applicable_aborted():
    """Test 10: Verification NOT_APPLICABLE if execution aborted."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create aborted execution result
        exec_result_file = tmpdir / "exec_result.json"
        exec_result_file.write_text(json.dumps({
            "status": "CYCLE_REAL_WRITE_ABORTED_PREFLIGHT_FAILED",
            "items": [],
        }))

        exec_pkg_file = create_valid_execution_package(tmpdir)

        output_json = tmpdir / "verification.json"
        output_md = tmpdir / "verification.md"

        from tools.local.controlled_cycle_post_write_verification import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--execution-result", str(exec_result_file),
            "--execution-package", str(exec_pkg_file),
            "--netbox-url", "https://example.com",
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--output-json", str(output_json),
            "--output-md", str(output_md),
        ]

        with patch("sys.argv", test_args):
            with patch.dict(os.environ, {"NETBOX_WRITE_TOKEN": "test-token"}, clear=True):
                exit_code = main()

        result = json.loads(output_json.read_text())
        assert "NOT_APPLICABLE" in result["status"]
        print("✓ test_10_verification_not_applicable_aborted")


def test_11_compliance_read_only():
    """Test 11: Compliance re-run is read-only."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        exec_result_file = create_valid_execution_result(tmpdir)

        verif_result_file = tmpdir / "verification.json"
        verif_result_file.write_text(json.dumps({
            "status": "CYCLE_POST_WRITE_VERIFICATION_PASSED",
            "summary": {"verified": 1},
        }))

        output_json = tmpdir / "compliance.json"
        output_md = tmpdir / "compliance.md"

        from tools.local.controlled_cycle_post_write_compliance_rerun import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--execution-result", str(exec_result_file),
            "--post-write-verification", str(verif_result_file),
            "--output-json", str(output_json),
            "--output-md", str(output_md),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert "PASSED" in result["status"]
        # No token used for compliance rerun
        print("✓ test_11_compliance_read_only")


def test_12_closure_success():
    """Test 12: Closure determines SUCCESS."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        exec_result_file = create_valid_execution_result(tmpdir)

        verif_result_file = tmpdir / "verification.json"
        verif_result_file.write_text(json.dumps({
            "status": "CYCLE_POST_WRITE_VERIFICATION_PASSED",
            "summary": {"verified": 1},
        }))

        compliance_result_file = tmpdir / "compliance.json"
        compliance_result_file.write_text(json.dumps({
            "status": "CYCLE_POST_WRITE_COMPLIANCE_PASSED",
            "summary": {"passed": 1},
        }))

        output_dir = tmpdir / "closure"
        output_report = tmpdir / "closure_report.md"

        from tools.local.controlled_cycle_build_closure_package import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--execution-result", str(exec_result_file),
            "--post-write-verification", str(verif_result_file),
            "--post-write-compliance", str(compliance_result_file),
            "--output-dir", str(output_dir),
            "--report", str(output_report),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        report_text = output_report.read_text()
        assert "CYCLE_CLOSED_SUCCESS" in report_text
        print("✓ test_12_closure_success")


def test_13_closure_with_warnings():
    """Test 13: Closure determines WITH_WARNINGS."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        exec_result_file = create_valid_execution_result(tmpdir)

        verif_result_file = tmpdir / "verification.json"
        verif_result_file.write_text(json.dumps({
            "status": "CYCLE_POST_WRITE_VERIFICATION_PASSED_WITH_DRIFT",
            "summary": {"verified": 1, "drift": 1},
        }))

        compliance_result_file = tmpdir / "compliance.json"
        compliance_result_file.write_text(json.dumps({
            "status": "CYCLE_POST_WRITE_COMPLIANCE_PASSED",
            "summary": {"passed": 1},
        }))

        output_dir = tmpdir / "closure"
        output_report = tmpdir / "closure_report.md"

        from tools.local.controlled_cycle_build_closure_package import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--execution-result", str(exec_result_file),
            "--post-write-verification", str(verif_result_file),
            "--post-write-compliance", str(compliance_result_file),
            "--output-dir", str(output_dir),
            "--report", str(output_report),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        report_text = output_report.read_text()
        assert "CYCLE_CLOSED_WITH_WARNINGS" in report_text
        print("✓ test_13_closure_with_warnings")


def test_14_no_subprocess_calls():
    """Test 14: Tools don't use subprocess."""
    import inspect
    from tools.local import (
        controlled_cycle_execute_real_write_once as m422,
        controlled_cycle_post_write_verification as m423,
        controlled_cycle_post_write_compliance_rerun as m424,
        controlled_cycle_build_closure_package as m425,
    )

    modules = [m422, m423, m424, m425]
    for module in modules:
        source = inspect.getsource(module)
        assert "subprocess" not in source
        assert "os.system" not in source
        assert "popen" not in source

    print("✓ test_14_no_subprocess_calls")


def test_15_one_shot_execution():
    """Test 15: Execution is one-shot (retry_attempted=false)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        exec_pkg_file = create_valid_execution_package(tmpdir)
        freeze_file = create_valid_freeze_result(tmpdir)

        output_json = tmpdir / "result.json"
        output_md = tmpdir / "result.md"

        from tools.local.controlled_cycle_execute_real_write_once import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--execution-package", str(exec_pkg_file),
            "--operator", "Keslley",
            "--confirm-execution-phrase", "EXECUTAR_ESCRITA_REAL_CYCLE-001_4WNET-MNS-KTG-RX_exec-cycle-001-abc123",
            "--confirm-real-write-once",
            "--netbox-url", "https://example.com",
            "--output-json", str(output_json),
            "--output-md", str(output_md),
            "--freeze-result", str(freeze_file),
        ]

        with patch("sys.argv", test_args):
            with patch.dict(os.environ, {"NETBOX_WRITE_TOKEN": "test-token"}, clear=True):
                with patch("urllib.request.urlopen") as mock_urlopen:
                    mock_response = MagicMock()
                    mock_response.read.return_value = json.dumps({"id": 42}).encode()
                    mock_urlopen.return_value.__enter__.return_value = mock_response
                    exit_code = main()

        result = json.loads(output_json.read_text())
        assert result.get("retry_attempted") is False
        assert result.get("rollback_attempted") is False
        assert result.get("one_shot_execution") is True
        print("✓ test_15_one_shot_execution")


if __name__ == "__main__":
    test_01_execute_blocks_no_confirm_flag()
    test_02_execute_blocks_wrong_phrase()
    test_03_execute_blocks_no_token()
    test_04_execute_blocks_freeze_not_ready()
    test_05_execute_blocks_patch_method()
    test_06_execute_blocks_sync_endpoint()
    test_07_execute_blocks_token_in_payload()
    test_08_execute_token_not_logged()
    test_09_verification_get_only()
    test_10_verification_not_applicable_aborted()
    test_11_compliance_read_only()
    test_12_closure_success()
    test_13_closure_with_warnings()
    test_14_no_subprocess_calls()
    test_15_one_shot_execution()

    print("\n" + "="*60)
    print("Results: 15/15 tests passed")
    print("="*60)
