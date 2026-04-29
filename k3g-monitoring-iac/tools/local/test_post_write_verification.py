#!/usr/bin/env python3
"""Test FASE 2.54: Post-Write Verification.

15 critical test cases covering:
- GET verification success
- Field comparison (primitives, dicts, lists)
- Mismatch detection
- Token handling (read-only token, environment)
- HTTP error handling
- Connection errors
- Safety confirmations (no writes, read-only)
- Item matching from package
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def create_mock_execution_result(tmpdir, status: str = "REAL_WRITE_SUCCESS") -> Path:
    """Create mock REAL-WRITE-EXECUTION-RESULT.json."""
    result_file = Path(tmpdir) / "execution_result.json"
    result = {
        "execution_id": "exec-123",
        "execution_package_id": "pkg-456",
        "device": "4WNET-MNS-KTG-RX",
        "device_id": "device-789",
        "operator": "test-operator",
        "started_at": "2026-04-29T10:00:00+00:00",
        "finished_at": "2026-04-29T10:05:00+00:00",
        "status": status,
        "items": [
            {
                "item_id": "item-1",
                "approval_id": "approval-123",
                "object_type": "Interface",
                "object_key": "Eth-Trunk0",
                "method": "POST",
                "endpoint": "/api/dcim/interfaces/",
                "http_status": 201,
                "response_id": 42,
                "verification_status": "verified",
            }
        ],
    }
    result_file.write_text(json.dumps(result))
    return result_file


def create_mock_execution_package(tmpdir) -> Path:
    """Create mock execution_package.json."""
    package_file = Path(tmpdir) / "package.json"
    package = {
        "execution_package_id": "pkg-456",
        "device": "4WNET-MNS-KTG-RX",
        "items": [
            {
                "item_id": "item-1",
                "approval_id": "approval-123",
                "object_type": "Interface",
                "object_key": "Eth-Trunk0",
                "endpoint": "/api/dcim/interfaces/",
                "payload": {
                    "name": "Eth-Trunk0",
                    "type": "ethernet",
                    "mtu": 1500,
                },
            }
        ],
    }
    package_file.write_text(json.dumps(package))
    return package_file


def test_01_get_verify_success():
    """Test 1: GET verify succeeds with matching fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result_file = create_mock_execution_result(tmpdir)
        package_file = create_mock_execution_package(tmpdir)

        from tools.local.post_write_verification import verify_object_in_netbox

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 42,
            "name": "Eth-Trunk0",
            "type": "ethernet",
            "mtu": 1500,
        }

        with patch("tools.local.post_write_verification.requests.get", return_value=mock_response):
            verify_ok, msg, response = verify_object_in_netbox(
                "test-token",
                "https://netbox.example.com",
                "/api/dcim/interfaces/",
                42,
                {"name": "Eth-Trunk0", "type": "ethernet", "mtu": 1500},
            )

            assert verify_ok is True, f"Expected success, got: {msg}"
            assert response["id"] == 42


def test_02_get_verify_field_mismatch():
    """Test 2: GET verify detects field mismatch."""
    with tempfile.TemporaryDirectory() as tmpdir:
        from tools.local.post_write_verification import verify_object_in_netbox

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 42,
            "name": "Eth-Trunk0",
            "type": "gigabit-ethernet",  # WRONG
            "mtu": 1500,
        }

        with patch("tools.local.post_write_verification.requests.get", return_value=mock_response):
            verify_ok, msg, response = verify_object_in_netbox(
                "test-token",
                "https://netbox.example.com",
                "/api/dcim/interfaces/",
                42,
                {"name": "Eth-Trunk0", "type": "ethernet", "mtu": 1500},
            )

            assert verify_ok is False, "Expected failure on mismatch"
            assert "type" in msg.lower() or "mismatch" in msg.lower()


def test_03_get_verify_http_404():
    """Test 3: GET verify handles HTTP 404."""
    from tools.local.post_write_verification import verify_object_in_netbox

    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.json.return_value = {"detail": "Not found"}

    with patch("tools.local.post_write_verification.requests.get", return_value=mock_response):
        verify_ok, msg, response = verify_object_in_netbox(
            "test-token",
            "https://netbox.example.com",
            "/api/dcim/interfaces/",
            42,
            {"name": "Eth-Trunk0"},
        )

        assert verify_ok is False
        assert "404" in msg or "not found" in msg.lower()


def test_04_get_verify_connection_error():
    """Test 4: GET verify handles connection error."""
    from tools.local.post_write_verification import verify_object_in_netbox
    import requests

    with patch(
        "tools.local.post_write_verification.requests.get",
        side_effect=requests.exceptions.ConnectionError("Connection failed"),
    ):
        verify_ok, msg, response = verify_object_in_netbox(
            "test-token",
            "https://netbox.example.com",
            "/api/dcim/interfaces/",
            42,
            {"name": "Eth-Trunk0"},
        )

        assert verify_ok is False
        assert "connection" in msg.lower()


def test_05_get_verify_timeout():
    """Test 5: GET verify handles timeout."""
    from tools.local.post_write_verification import verify_object_in_netbox
    import requests

    with patch(
        "tools.local.post_write_verification.requests.get",
        side_effect=requests.exceptions.Timeout("Timeout"),
    ):
        verify_ok, msg, response = verify_object_in_netbox(
            "test-token",
            "https://netbox.example.com",
            "/api/dcim/interfaces/",
            42,
            {"name": "Eth-Trunk0"},
        )

        assert verify_ok is False
        assert "timeout" in msg.lower()


def test_06_load_execution_result_success():
    """Test 6: Load execution result succeeds."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result_file = create_mock_execution_result(tmpdir)

        from tools.local.post_write_verification import load_execution_result

        ok, reason, result = load_execution_result(result_file)
        assert ok is True
        assert result["status"] == "REAL_WRITE_SUCCESS"
        assert len(result["items"]) == 1


def test_07_load_execution_result_wrong_status():
    """Test 7: Load execution result fails if status != SUCCESS."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result_file = create_mock_execution_result(tmpdir, status="REAL_WRITE_FAILED")

        from tools.local.post_write_verification import load_execution_result

        ok, reason, result = load_execution_result(result_file)
        assert ok is False
        assert "not SUCCESS" in reason


def test_08_load_execution_package():
    """Test 8: Load execution package succeeds."""
    with tempfile.TemporaryDirectory() as tmpdir:
        package_file = create_mock_execution_package(tmpdir)

        from tools.local.post_write_verification import load_execution_package

        ok, reason, package = load_execution_package(package_file)
        assert ok is True
        assert len(package["items"]) == 1


def test_09_find_item_in_package():
    """Test 9: Find item in package by item_id."""
    with tempfile.TemporaryDirectory() as tmpdir:
        package_file = create_mock_execution_package(tmpdir)

        from tools.local.post_write_verification import load_execution_package, find_item_in_package

        ok, reason, package = load_execution_package(package_file)
        item = find_item_in_package(package["items"], "item-1")

        assert item is not None
        assert item["object_key"] == "Eth-Trunk0"


def test_10_find_item_not_in_package():
    """Test 10: Find item returns None if not found."""
    with tempfile.TemporaryDirectory() as tmpdir:
        package_file = create_mock_execution_package(tmpdir)

        from tools.local.post_write_verification import load_execution_package, find_item_in_package

        ok, reason, package = load_execution_package(package_file)
        item = find_item_in_package(package["items"], "nonexistent")

        assert item is None


def test_11_token_from_environment():
    """Test 11: Token read from NETBOX_READ_TOKEN environment."""
    from tools.local.post_write_verification import read_token_from_env

    os.environ["NETBOX_READ_TOKEN"] = "test-token-12345"
    token = read_token_from_env()

    assert token == "test-token-12345"
    del os.environ["NETBOX_READ_TOKEN"]


def test_12_token_not_in_environment():
    """Test 12: Token returns None if not in environment."""
    from tools.local.post_write_verification import read_token_from_env

    # Ensure token not set
    if "NETBOX_READ_TOKEN" in os.environ:
        del os.environ["NETBOX_READ_TOKEN"]

    token = read_token_from_env()
    assert token is None


def test_13_verify_dict_fields():
    """Test 13: GET verify compares dict fields."""
    from tools.local.post_write_verification import verify_object_in_netbox

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": 42,
        "name": "Eth-Trunk0",
        "custom_fields": {"tenant": "ACME", "region": "US"},
    }

    with patch("tools.local.post_write_verification.requests.get", return_value=mock_response):
        verify_ok, msg, response = verify_object_in_netbox(
            "test-token",
            "https://netbox.example.com",
            "/api/dcim/interfaces/",
            42,
            {"name": "Eth-Trunk0", "custom_fields": {"tenant": "ACME", "region": "US"}},
        )

        assert verify_ok is True, f"Dict comparison failed: {msg}"


def test_14_verify_list_fields():
    """Test 14: GET verify compares list fields."""
    from tools.local.post_write_verification import verify_object_in_netbox

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": 42,
        "name": "Eth-Trunk0",
        "tags": ["prod", "monitored"],
    }

    with patch("tools.local.post_write_verification.requests.get", return_value=mock_response):
        verify_ok, msg, response = verify_object_in_netbox(
            "test-token",
            "https://netbox.example.com",
            "/api/dcim/interfaces/",
            42,
            {"name": "Eth-Trunk0", "tags": ["prod", "monitored"]},
        )

        assert verify_ok is True, f"List comparison failed: {msg}"


def test_15_safety_confirmations_in_result():
    """Test 15: Result JSON has safety confirmations for read-only."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result_file = create_mock_execution_result(tmpdir)
        package_file = create_mock_execution_package(tmpdir)
        output_json = Path(tmpdir) / "verification_result.json"
        output_md = Path(tmpdir) / "verification_result.md"

        # Set token
        os.environ["NETBOX_READ_TOKEN"] = "test-token"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 42,
            "name": "Eth-Trunk0",
            "type": "ethernet",
            "mtu": 1500,
        }

        with patch("tools.local.post_write_verification.requests.get", return_value=mock_response):
            from tools.local.post_write_verification import main

            # Mock argparse to inject our test files
            test_args = [
                "post_write_verification.py",
                "--execution-result",
                str(result_file),
                "--execution-package",
                str(package_file),
                "--netbox-url",
                "https://netbox.example.com",
                "--output-json",
                str(output_json),
                "--output-md",
                str(output_md),
            ]

            with patch("sys.argv", test_args):
                exit_code = main()

            assert exit_code == 0
            assert output_json.exists()
            result = json.loads(output_json.read_text())

            assert result["safety_confirmations"]["token_not_logged"] is True
            assert result["safety_confirmations"]["read_only_get"] is True
            assert result["safety_confirmations"]["no_writes"] is True

        del os.environ["NETBOX_READ_TOKEN"]


def main():
    """Run all tests."""
    test_functions = [
        test_01_get_verify_success,
        test_02_get_verify_field_mismatch,
        test_03_get_verify_http_404,
        test_04_get_verify_connection_error,
        test_05_get_verify_timeout,
        test_06_load_execution_result_success,
        test_07_load_execution_result_wrong_status,
        test_08_load_execution_package,
        test_09_find_item_in_package,
        test_10_find_item_not_in_package,
        test_11_token_from_environment,
        test_12_token_not_in_environment,
        test_13_verify_dict_fields,
        test_14_verify_list_fields,
        test_15_safety_confirmations_in_result,
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
