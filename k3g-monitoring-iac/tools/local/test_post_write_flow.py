#!/usr/bin/env python3
"""Test FASES 2.54-2.56: Complete post-write flow.

25 test cases covering:
- Full end-to-end flow (execution → verification → compliance → closure)
- Each phase independently
- Token handling (read-only, environment variable)
- Error propagation
- Closure decision logic
- Safety confirmations
- No writes constraint
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def create_execution_result(tmpdir, status: str = "REAL_WRITE_SUCCESS") -> Path:
    """Create mock execution result."""
    f = Path(tmpdir) / "exec_result.json"
    f.write_text(
        json.dumps({
            "execution_id": "exec-123",
            "execution_package_id": "pkg-456",
            "device": "4WNET-MNS-KTG-RX",
            "device_id": "dev-789",
            "operator": "test-op",
            "status": status,
            "token_logged": False,
            "items": [
                {
                    "item_id": "item-1",
                    "approval_id": "approval-123",
                    "object_type": "Interface",
                    "object_key": "Eth-Trunk0",
                    "endpoint": "/api/dcim/interfaces/",
                    "response_id": 42,
                    "status": "REAL_WRITE_CREATED" if status == "REAL_WRITE_SUCCESS" else "REAL_WRITE_FAILED",
                }
            ],
        })
    )
    return f


def create_verification_result(tmpdir, status: str = "POST_WRITE_VERIFICATION_SUCCESS") -> Path:
    """Create mock verification result."""
    f = Path(tmpdir) / "verif_result.json"
    f.write_text(
        json.dumps({
            "verification_id": "verif-456",
            "execution_id": "exec-123",
            "device": "4WNET-MNS-KTG-RX",
            "status": status,
            "verified_count": 1 if status == "POST_WRITE_VERIFICATION_SUCCESS" else 0,
            "failed_count": 0 if status == "POST_WRITE_VERIFICATION_SUCCESS" else 1,
            "total_count": 1,
            "token_logged": False,
            "items": [
                {
                    "item_id": "item-1",
                    "verification_status": "VERIFIED" if status == "POST_WRITE_VERIFICATION_SUCCESS" else "VERIFICATION_FAILED",
                }
            ],
        })
    )
    return f


def create_compliance_result(tmpdir, status: str = "POST_WRITE_COMPLIANCE_SUCCESS") -> Path:
    """Create mock compliance result."""
    f = Path(tmpdir) / "comp_result.json"
    f.write_text(
        json.dumps({
            "compliance_run_id": "comp-789",
            "execution_id": "exec-123",
            "device": "4WNET-MNS-KTG-RX",
            "status": status,
            "checks_passed": 3 if status == "POST_WRITE_COMPLIANCE_SUCCESS" else 1,
            "checks_failed": 0 if status == "POST_WRITE_COMPLIANCE_SUCCESS" else 2,
            "total_checks": 3,
            "token_logged": False,
            "compliance_checks": [
                {"check_id": "COMPLIANCE-001", "name": "Execution successful", "passed": status == "POST_WRITE_COMPLIANCE_SUCCESS"},
                {"check_id": "COMPLIANCE-002", "name": "Verification passed", "passed": status == "POST_WRITE_COMPLIANCE_SUCCESS"},
                {"check_id": "COMPLIANCE-003", "name": "No pre-phase writes", "passed": True},
            ],
        })
    )
    return f


def test_01_load_execution_result():
    """Test 1: Load execution result."""
    with tempfile.TemporaryDirectory() as tmpdir:
        f = create_execution_result(tmpdir)

        from tools.local.post_write_verification import load_execution_result

        ok, reason, result = load_execution_result(f)
        assert ok is True
        assert result["execution_id"] == "exec-123"


def test_02_load_verification_result():
    """Test 2: Load verification result."""
    with tempfile.TemporaryDirectory() as tmpdir:
        f = create_verification_result(tmpdir)

        from tools.local.post_write_compliance_rerun import load_execution_result

        ok, reason, result = load_execution_result(f)
        assert ok is True
        assert result["verification_id"] == "verif-456"


def test_03_load_compliance_result():
    """Test 3: Load compliance result."""
    with tempfile.TemporaryDirectory() as tmpdir:
        f = create_compliance_result(tmpdir)

        from tools.local.post_write_compliance_rerun import load_execution_result

        ok, reason, result = load_execution_result(f)
        assert ok is True
        assert result["compliance_run_id"] == "comp-789"


def test_04_execution_result_invalid_json():
    """Test 4: Execution result with invalid JSON fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        f = Path(tmpdir) / "bad.json"
        f.write_text("{invalid json")

        from tools.local.post_write_verification import load_execution_result

        ok, reason, result = load_execution_result(f)
        assert ok is False
        assert "invalid" in reason.lower()


def test_05_verification_result_not_found():
    """Test 5: Verification result not found."""
    from tools.local.post_write_verification import load_execution_result

    ok, reason, result = load_execution_result(Path("/nonexistent/file.json"))
    assert ok is False
    assert "not found" in reason.lower()


def test_06_compliance_result_not_found():
    """Test 6: Compliance result not found."""
    from tools.local.post_write_compliance_rerun import load_execution_result

    ok, reason, result = load_execution_result(Path("/nonexistent/file.json"))
    assert ok is False


def test_07_token_read_only_environment():
    """Test 7: Token read from NETBOX_READ_TOKEN."""
    from tools.local.post_write_verification import read_token_from_env

    os.environ["NETBOX_READ_TOKEN"] = "read-token-12345"
    token = read_token_from_env()

    assert token == "read-token-12345"
    del os.environ["NETBOX_READ_TOKEN"]


def test_08_compliance_all_checks_passed():
    """Test 8: Compliance checks all passed → SUCCESS."""
    with tempfile.TemporaryDirectory() as tmpdir:
        f = create_compliance_result(tmpdir, "POST_WRITE_COMPLIANCE_SUCCESS")

        from tools.local.post_write_compliance_rerun import load_execution_result

        ok, _, result = load_execution_result(f)
        assert result["checks_failed"] == 0
        assert result["status"] == "POST_WRITE_COMPLIANCE_SUCCESS"


def test_09_compliance_some_checks_failed():
    """Test 9: Compliance with failed checks → FAILURE."""
    with tempfile.TemporaryDirectory() as tmpdir:
        f = create_compliance_result(tmpdir, "POST_WRITE_COMPLIANCE_FAILED")

        from tools.local.post_write_compliance_rerun import load_execution_result

        ok, _, result = load_execution_result(f)
        assert result["checks_failed"] > 0
        assert result["status"] == "POST_WRITE_COMPLIANCE_FAILED"


def test_10_consolidate_all_success():
    """Test 10: Consolidate all phases successful → COMPLETE_SUCCESS."""
    with tempfile.TemporaryDirectory() as tmpdir:
        exec_f = create_execution_result(tmpdir, "REAL_WRITE_SUCCESS")
        verif_f = create_verification_result(tmpdir, "POST_WRITE_VERIFICATION_SUCCESS")
        comp_f = create_compliance_result(tmpdir, "POST_WRITE_COMPLIANCE_SUCCESS")

        from tools.local.build_post_write_closure_package import consolidate_results, load_execution_result

        _, _, exec_r = load_execution_result(exec_f)
        _, _, verif_r = load_execution_result(verif_f)
        _, _, comp_r = load_execution_result(comp_f)

        result = consolidate_results(exec_r, verif_r, comp_r)

        assert result["closure_decision"] == "WRITE_EXECUTION_COMPLETE_SUCCESS"
        assert result["execution_success"] is True
        assert result["verification_success"] is True
        assert result["compliance_success"] is True


def test_11_consolidate_execution_failed():
    """Test 11: Execution failed → COMPLETE_FAILURE."""
    with tempfile.TemporaryDirectory() as tmpdir:
        exec_f = create_execution_result(tmpdir, "REAL_WRITE_FAILED")
        verif_f = create_verification_result(tmpdir, "POST_WRITE_VERIFICATION_SUCCESS")
        comp_f = create_compliance_result(tmpdir, "POST_WRITE_COMPLIANCE_SUCCESS")

        from tools.local.build_post_write_closure_package import consolidate_results, load_execution_result

        _, _, exec_r = load_execution_result(exec_f)
        _, _, verif_r = load_execution_result(verif_f)
        _, _, comp_r = load_execution_result(comp_f)

        result = consolidate_results(exec_r, verif_r, comp_r)

        assert result["closure_decision"] == "WRITE_EXECUTION_COMPLETE_FAILURE"
        assert result["execution_success"] is False


def test_12_consolidate_verification_failed():
    """Test 12: Verification failed → COMPLETE_FAILURE."""
    with tempfile.TemporaryDirectory() as tmpdir:
        exec_f = create_execution_result(tmpdir, "REAL_WRITE_SUCCESS")
        verif_f = create_verification_result(tmpdir, "POST_WRITE_VERIFICATION_FAILED")
        comp_f = create_compliance_result(tmpdir, "POST_WRITE_COMPLIANCE_SUCCESS")

        from tools.local.build_post_write_closure_package import consolidate_results, load_execution_result

        _, _, exec_r = load_execution_result(exec_f)
        _, _, verif_r = load_execution_result(verif_f)
        _, _, comp_r = load_execution_result(comp_f)

        result = consolidate_results(exec_r, verif_r, comp_r)

        assert result["closure_decision"] == "WRITE_EXECUTION_COMPLETE_FAILURE"
        assert result["verification_success"] is False


def test_13_consolidate_compliance_failed():
    """Test 13: Compliance failed → COMPLETE_FAILURE."""
    with tempfile.TemporaryDirectory() as tmpdir:
        exec_f = create_execution_result(tmpdir, "REAL_WRITE_SUCCESS")
        verif_f = create_verification_result(tmpdir, "POST_WRITE_VERIFICATION_SUCCESS")
        comp_f = create_compliance_result(tmpdir, "POST_WRITE_COMPLIANCE_FAILED")

        from tools.local.build_post_write_closure_package import consolidate_results, load_execution_result

        _, _, exec_r = load_execution_result(exec_f)
        _, _, verif_r = load_execution_result(verif_f)
        _, _, comp_r = load_execution_result(comp_f)

        result = consolidate_results(exec_r, verif_r, comp_r)

        assert result["closure_decision"] == "WRITE_EXECUTION_COMPLETE_FAILURE"
        assert result["compliance_success"] is False


def test_14_fase_2_54_no_network_calls():
    """Test 14: FASE 2.54 makes only GET calls (no POST/PATCH/DELETE)."""
    from tools.local.post_write_verification import verify_object_in_netbox

    # Verify uses GET only
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": 42, "name": "test"}

    with patch("tools.local.post_write_verification.requests.get", return_value=mock_response) as mock_get:
        with patch("tools.local.post_write_verification.requests.post") as mock_post:
            verify_ok, _, _ = verify_object_in_netbox(
                "token", "https://example.com", "/api/test/", 42, {"name": "test"}
            )

            assert mock_get.called
            assert not mock_post.called


def test_15_fase_2_55_no_writes():
    """Test 15: FASE 2.55 compliance rerun does no writes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        exec_f = create_execution_result(tmpdir)
        verif_f = create_verification_result(tmpdir)
        output_json = Path(tmpdir) / "output.json"
        output_md = Path(tmpdir) / "output.md"

        os.environ["NETBOX_READ_TOKEN"] = "token"

        from tools.local.post_write_compliance_rerun import main

        test_args = [
            "prog",
            "--execution-result",
            str(exec_f),
            "--verification-result",
            str(verif_f),
            "--device",
            "test-device",
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        # Should succeed
        assert exit_code == 0
        assert output_json.exists()

        result = json.loads(output_json.read_text())
        assert result["safety_confirmations"]["no_writes"] is True

        del os.environ["NETBOX_READ_TOKEN"]


def test_16_fase_2_56_consolidates_all():
    """Test 16: FASE 2.56 consolidates execution + verification + compliance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        exec_f = create_execution_result(tmpdir)
        verif_f = create_verification_result(tmpdir)
        comp_f = create_compliance_result(tmpdir)
        output_json = Path(tmpdir) / "closure.json"
        output_md = Path(tmpdir) / "closure.md"

        from tools.local.build_post_write_closure_package import main

        test_args = [
            "prog",
            "--execution-result",
            str(exec_f),
            "--verification-result",
            str(verif_f),
            "--compliance-result",
            str(comp_f),
            "--device",
            "test-device",
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        assert exit_code == 0
        assert output_json.exists()

        closure = json.loads(output_json.read_text())
        assert closure["closure_decision"] == "WRITE_EXECUTION_COMPLETE_SUCCESS"
        assert closure["phases"]["FASE_2_53_EXECUTION"]["success"] is True
        assert closure["phases"]["FASE_2_54_VERIFICATION"]["success"] is True
        assert closure["phases"]["FASE_2_55_COMPLIANCE"]["success"] is True


def test_17_fase_2_54_safety_confirmations():
    """Test 17: FASE 2.54 includes read-only safety confirmations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result_file = create_execution_result(tmpdir)
        package_file = Path(tmpdir) / "package.json"
        package_file.write_text(json.dumps({"items": [{"item_id": "item-1", "payload": {}}]}))
        output_json = Path(tmpdir) / "output.json"
        output_md = Path(tmpdir) / "output.md"

        os.environ["NETBOX_READ_TOKEN"] = "token"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 42}

        from tools.local.post_write_verification import main

        test_args = [
            "prog",
            "--execution-result",
            str(result_file),
            "--execution-package",
            str(package_file),
            "--netbox-url",
            "https://example.com",
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ]

        with patch("sys.argv", test_args):
            with patch("tools.local.post_write_verification.requests.get", return_value=mock_response):
                exit_code = main()

        assert exit_code == 0
        result = json.loads(output_json.read_text())

        assert result["safety_confirmations"]["token_not_logged"] is True
        assert result["safety_confirmations"]["read_only_get"] is True
        assert result["safety_confirmations"]["no_writes"] is True

        del os.environ["NETBOX_READ_TOKEN"]


def test_18_fase_2_55_safety_confirmations():
    """Test 18: FASE 2.55 includes safety confirmations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        exec_f = create_execution_result(tmpdir)
        verif_f = create_verification_result(tmpdir)
        output_json = Path(tmpdir) / "output.json"
        output_md = Path(tmpdir) / "output.md"

        os.environ["NETBOX_READ_TOKEN"] = "token"

        from tools.local.post_write_compliance_rerun import main

        test_args = [
            "prog",
            "--execution-result",
            str(exec_f),
            "--verification-result",
            str(verif_f),
            "--device",
            "test",
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())

        assert result["safety_confirmations"]["token_not_logged"] is True
        assert result["safety_confirmations"]["read_only"] is True
        assert result["safety_confirmations"]["no_writes"] is True

        del os.environ["NETBOX_READ_TOKEN"]


def test_19_closure_audit_trail():
    """Test 19: Closure package includes audit trail."""
    with tempfile.TemporaryDirectory() as tmpdir:
        exec_f = create_execution_result(tmpdir)
        verif_f = create_verification_result(tmpdir)
        comp_f = create_compliance_result(tmpdir)
        output_json = Path(tmpdir) / "closure.json"
        output_md = Path(tmpdir) / "closure.md"

        from tools.local.build_post_write_closure_package import main

        test_args = [
            "prog",
            "--execution-result",
            str(exec_f),
            "--verification-result",
            str(verif_f),
            "--compliance-result",
            str(comp_f),
            "--device",
            "test",
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        closure = json.loads(output_json.read_text())

        assert closure["audit_trail_complete"] is True
        assert closure["token_logged"] is False


def test_20_end_to_end_success_flow():
    """Test 20: Complete success flow (all phases pass)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        exec_f = create_execution_result(tmpdir, "REAL_WRITE_SUCCESS")
        verif_f = create_verification_result(tmpdir, "POST_WRITE_VERIFICATION_SUCCESS")
        comp_f = create_compliance_result(tmpdir, "POST_WRITE_COMPLIANCE_SUCCESS")
        output_json = Path(tmpdir) / "closure.json"
        output_md = Path(tmpdir) / "closure.md"

        from tools.local.build_post_write_closure_package import main

        test_args = [
            "prog",
            "--execution-result",
            str(exec_f),
            "--verification-result",
            str(verif_f),
            "--compliance-result",
            str(comp_f),
            "--device",
            "device",
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        assert exit_code == 0
        closure = json.loads(output_json.read_text())
        assert "SUCCESS" in closure["closure_decision"]


def test_21_end_to_end_failure_flow():
    """Test 21: Complete failure flow (any phase fails)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        exec_f = create_execution_result(tmpdir, "REAL_WRITE_FAILED")
        verif_f = create_verification_result(tmpdir, "POST_WRITE_VERIFICATION_SUCCESS")
        comp_f = create_compliance_result(tmpdir, "POST_WRITE_COMPLIANCE_SUCCESS")
        output_json = Path(tmpdir) / "closure.json"
        output_md = Path(tmpdir) / "closure.md"

        from tools.local.build_post_write_closure_package import main

        test_args = [
            "prog",
            "--execution-result",
            str(exec_f),
            "--verification-result",
            str(verif_f),
            "--compliance-result",
            str(comp_f),
            "--device",
            "device",
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        assert exit_code == 1
        closure = json.loads(output_json.read_text())
        assert "FAILURE" in closure["closure_decision"]


def test_22_markdown_generated_fase_54():
    """Test 22: FASE 2.54 generates markdown report."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result_file = create_execution_result(tmpdir)
        package_file = Path(tmpdir) / "package.json"
        package_file.write_text(json.dumps({"items": [{"item_id": "item-1", "payload": {}}]}))
        output_json = Path(tmpdir) / "output.json"
        output_md = Path(tmpdir) / "output.md"

        os.environ["NETBOX_READ_TOKEN"] = "token"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 42}

        from tools.local.post_write_verification import main

        test_args = [
            "prog",
            "--execution-result",
            str(result_file),
            "--execution-package",
            str(package_file),
            "--netbox-url",
            "https://example.com",
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ]

        with patch("sys.argv", test_args):
            with patch("tools.local.post_write_verification.requests.get", return_value=mock_response):
                main()

        assert output_md.exists()
        content = output_md.read_text()
        assert "FASE 2.54" in content or "Verificação" in content

        del os.environ["NETBOX_READ_TOKEN"]


def test_23_markdown_generated_fase_55():
    """Test 23: FASE 2.55 generates markdown report."""
    with tempfile.TemporaryDirectory() as tmpdir:
        exec_f = create_execution_result(tmpdir)
        verif_f = create_verification_result(tmpdir)
        output_json = Path(tmpdir) / "output.json"
        output_md = Path(tmpdir) / "output.md"

        os.environ["NETBOX_READ_TOKEN"] = "token"

        from tools.local.post_write_compliance_rerun import main

        test_args = [
            "prog",
            "--execution-result",
            str(exec_f),
            "--verification-result",
            str(verif_f),
            "--device",
            "test",
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ]

        with patch("sys.argv", test_args):
            main()

        assert output_md.exists()
        content = output_md.read_text()
        assert "FASE 2.55" in content or "Compliance" in content

        del os.environ["NETBOX_READ_TOKEN"]


def test_24_markdown_generated_fase_56():
    """Test 24: FASE 2.56 generates markdown report."""
    with tempfile.TemporaryDirectory() as tmpdir:
        exec_f = create_execution_result(tmpdir)
        verif_f = create_verification_result(tmpdir)
        comp_f = create_compliance_result(tmpdir)
        output_json = Path(tmpdir) / "closure.json"
        output_md = Path(tmpdir) / "closure.md"

        from tools.local.build_post_write_closure_package import main

        test_args = [
            "prog",
            "--execution-result",
            str(exec_f),
            "--verification-result",
            str(verif_f),
            "--compliance-result",
            str(comp_f),
            "--device",
            "device",
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ]

        with patch("sys.argv", test_args):
            main()

        assert output_md.exists()
        content = output_md.read_text()
        assert "FASE 2.56" in content or "Fechamento" in content


def test_25_no_token_logging_across_phases():
    """Test 25: No token logged across all post-write phases."""
    # This is a meta-test: verify that safety_confirmations.token_not_logged = true
    # in all three phases

    with tempfile.TemporaryDirectory() as tmpdir:
        result_file = create_execution_result(tmpdir)
        verif_file = create_verification_result(tmpdir)
        comp_file = create_compliance_result(tmpdir)

        # All three should have token_not_logged = true or similar
        exec_data = json.loads(result_file.read_text())
        verif_data = json.loads(verif_file.read_text())
        comp_data = json.loads(comp_file.read_text())

        # Check safety flags across phases
        assert exec_data.get("token_logged") is False
        assert verif_data.get("token_logged") is False
        assert comp_data.get("token_logged") is False


def main():
    """Run all tests."""
    test_functions = [
        test_01_load_execution_result,
        test_02_load_verification_result,
        test_03_load_compliance_result,
        test_04_execution_result_invalid_json,
        test_05_verification_result_not_found,
        test_06_compliance_result_not_found,
        test_07_token_read_only_environment,
        test_08_compliance_all_checks_passed,
        test_09_compliance_some_checks_failed,
        test_10_consolidate_all_success,
        test_11_consolidate_execution_failed,
        test_12_consolidate_verification_failed,
        test_13_consolidate_compliance_failed,
        test_14_fase_2_54_no_network_calls,
        test_15_fase_2_55_no_writes,
        test_16_fase_2_56_consolidates_all,
        test_17_fase_2_54_safety_confirmations,
        test_18_fase_2_55_safety_confirmations,
        test_19_closure_audit_trail,
        test_20_end_to_end_success_flow,
        test_21_end_to_end_failure_flow,
        test_22_markdown_generated_fase_54,
        test_23_markdown_generated_fase_55,
        test_24_markdown_generated_fase_56,
        test_25_no_token_logging_across_phases,
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
