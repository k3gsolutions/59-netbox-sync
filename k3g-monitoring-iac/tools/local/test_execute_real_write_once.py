#!/usr/bin/env python3
"""Test FASE 2.53: Execute Real Write Once.

18 tests covering security, preflight validation, execution, and result generation.
Uses mock HTTP to avoid real network calls.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def create_mock_execution_package(tmpdir) -> Path:
    """Create mock execution_package.json."""
    pkg_file = Path(tmpdir) / "package.json"
    pkg = {
        "execution_package_id": "pkg-123",
        "device": "test-device",
        "device_id": 1,
        "status": "prepared",
        "mode": "real_write_prepared",
        "execution_allowed": False,
        "required_execution_phrase": "EXECUTO_ESCRITA_REAL_test-device_pkg-123",
        "items": [
            {
                "item_id": "item-1",
                "approval_id": "approval-1",
                "object_type": "Interface",
                "object_key": "Eth-Trunk0",
                "method": "POST",
                "endpoint": "/api/dcim/interfaces/",
                "payload": {"name": "Eth-Trunk0", "type": "ethernet"},
            }
        ],
    }
    pkg_file.write_text(json.dumps(pkg))
    return pkg_file


def create_mock_freeze_check(tmpdir) -> Path:
    """Create mock freeze check file."""
    file = Path(tmpdir) / "freeze.md"
    content = """# Freeze Check
### READY_FOR_REAL_WRITE_PHASE
System ready."""
    file.write_text(content)
    return file


def test_01_blocks_without_confirm_flag():
    """Test 1: Blocks execution without --confirm-real-write-once."""
    from tools.local.execute_real_write_once import main

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = create_mock_execution_package(tmpdir)
        freeze_file = create_mock_freeze_check(tmpdir)
        os.environ["NETBOX_WRITE_TOKEN"] = "fake-token"

        sys.argv = [
            "execute_real_write_once.py",
            "--execution-package", str(pkg_file),
            "--operator", "test",
            "--confirm-execution-phrase", "EXECUTO_ESCRITA_REAL_test-device_pkg-123",
            # Missing: --confirm-real-write-once
            "--netbox-url", "https://netbox.test.com",
            "--freeze-check", str(freeze_file),
            "--output-json", str(Path(tmpdir) / "result.json"),
            "--output-md", str(Path(tmpdir) / "result.md"),
        ]

        result = main()
        assert result == 1, "Should block without confirm flag"


def test_02_blocks_wrong_phrase():
    """Test 2: Blocks execution with wrong phrase."""
    from tools.local.execute_real_write_once import main

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = create_mock_execution_package(tmpdir)
        freeze_file = create_mock_freeze_check(tmpdir)
        os.environ["NETBOX_WRITE_TOKEN"] = "fake-token"

        sys.argv = [
            "execute_real_write_once.py",
            "--execution-package", str(pkg_file),
            "--operator", "test",
            "--confirm-execution-phrase", "WRONG_PHRASE",
            "--confirm-real-write-once",
            "--netbox-url", "https://netbox.test.com",
            "--freeze-check", str(freeze_file),
            "--output-json", str(Path(tmpdir) / "result.json"),
            "--output-md", str(Path(tmpdir) / "result.md"),
        ]

        result = main()
        assert result == 1, "Should block with wrong phrase"


def test_03_blocks_without_token():
    """Test 3: Blocks execution without NETBOX_WRITE_TOKEN."""
    from tools.local.execute_real_write_once import main

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = create_mock_execution_package(tmpdir)
        freeze_file = create_mock_freeze_check(tmpdir)

        # Remove token from environment
        if "NETBOX_WRITE_TOKEN" in os.environ:
            del os.environ["NETBOX_WRITE_TOKEN"]

        sys.argv = [
            "execute_real_write_once.py",
            "--execution-package", str(pkg_file),
            "--operator", "test",
            "--confirm-execution-phrase", "EXECUTO_ESCRITA_REAL_test-device_pkg-123",
            "--confirm-real-write-once",
            "--netbox-url", "https://netbox.test.com",
            "--freeze-check", str(freeze_file),
            "--output-json", str(Path(tmpdir) / "result.json"),
            "--output-md", str(Path(tmpdir) / "result.md"),
        ]

        result = main()
        assert result == 1, "Should block without token"


def test_04_blocks_without_freeze_ready():
    """Test 4: Blocks execution if freeze check not READY."""
    from tools.local.execute_real_write_once import main

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = create_mock_execution_package(tmpdir)

        # Create freeze check that's NOT READY
        freeze_file = Path(tmpdir) / "freeze.md"
        freeze_file.write_text("### NOT_READY\nSystem not ready")

        os.environ["NETBOX_WRITE_TOKEN"] = "fake-token"

        sys.argv = [
            "execute_real_write_once.py",
            "--execution-package", str(pkg_file),
            "--operator", "test",
            "--confirm-execution-phrase", "EXECUTO_ESCRITA_REAL_test-device_pkg-123",
            "--confirm-real-write-once",
            "--netbox-url", "https://netbox.test.com",
            "--freeze-check", str(freeze_file),
            "--output-json", str(Path(tmpdir) / "result.json"),
            "--output-md", str(Path(tmpdir) / "result.md"),
        ]

        result = main()
        assert result == 1, "Should block if freeze not READY"


def test_05_blocks_patch_method():
    """Test 5: Blocks execution if item has PATCH method."""
    from tools.local.execute_real_write_once import validate_items

    items = [
        {
            "item_id": "item-1",
            "method": "PATCH",  # FORBIDDEN
            "endpoint": "/api/test/",
            "payload": {},
        }
    ]

    valid, reason = validate_items(items)
    assert valid is False, "Should block PATCH method"


def test_06_blocks_delete_method():
    """Test 6: Blocks execution if item has DELETE method."""
    from tools.local.execute_real_write_once import validate_items

    items = [
        {
            "item_id": "item-1",
            "method": "DELETE",  # FORBIDDEN
            "endpoint": "/api/test/",
            "payload": {},
        }
    ]

    valid, reason = validate_items(items)
    assert valid is False, "Should block DELETE method"


def test_07_blocks_sync_endpoint():
    """Test 7: Blocks execution if endpoint is /sync."""
    from tools.local.execute_real_write_once import validate_items

    items = [
        {
            "item_id": "item-1",
            "method": "POST",
            "endpoint": "/api/dcim/sync/",  # FORBIDDEN
            "payload": {},
        }
    ]

    valid, reason = validate_items(items)
    assert valid is False, "Should block /sync endpoint"


def test_08_blocks_secret_in_payload():
    """Test 8: Blocks execution if payload contains secret keyword."""
    from tools.local.execute_real_write_once import validate_items

    items = [
        {
            "item_id": "item-1",
            "method": "POST",
            "endpoint": "/api/test/",
            "payload": {
                "name": "test",
                "api_key": "secret123",  # FORBIDDEN
            },
        }
    ]

    valid, reason = validate_items(items)
    assert valid is False, "Should block payload with secret"


def test_09_no_token_in_output():
    """Test 9: Result JSON does not contain actual token."""
    from tools.local.execute_real_write_once import main

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = create_mock_execution_package(tmpdir)
        freeze_file = create_mock_freeze_check(tmpdir)
        token_value = "test-token-12345"
        os.environ["NETBOX_WRITE_TOKEN"] = token_value

        output_json = Path(tmpdir) / "result.json"
        output_md = Path(tmpdir) / "result.md"

        # Mock requests to avoid network calls
        with patch("tools.local.execute_real_write_once.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"id": 1, "name": "Eth-Trunk0"}
            mock_post.return_value = mock_response

            with patch("tools.local.execute_real_write_once.requests.get") as mock_get:
                mock_response_get = MagicMock()
                mock_response_get.status_code = 200
                mock_response_get.json.return_value = {"id": 1}
                mock_get.return_value = mock_response_get

                sys.argv = [
                    "execute_real_write_once.py",
                    "--execution-package", str(pkg_file),
                    "--operator", "test",
                    "--confirm-execution-phrase", "EXECUTO_ESCRITA_REAL_test-device_pkg-123",
                    "--confirm-real-write-once",
                    "--netbox-url", "https://netbox.test.com",
                    "--freeze-check", str(freeze_file),
                    "--output-json", str(output_json),
                    "--output-md", str(output_md),
                ]

                result = main()

                # Check result JSON doesn't contain token
                with open(output_json) as f:
                    result_json = json.load(f)

                result_str = json.dumps(result_json)
                assert token_value not in result_str, "Token found in result JSON"
                assert result_json["token_logged"] is False


def test_10_no_token_in_markdown():
    """Test 10: Result markdown does not contain token."""
    from tools.local.execute_real_write_once import main

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = create_mock_execution_package(tmpdir)
        freeze_file = create_mock_freeze_check(tmpdir)
        token_value = "test-token-67890"
        os.environ["NETBOX_WRITE_TOKEN"] = token_value

        output_json = Path(tmpdir) / "result.json"
        output_md = Path(tmpdir) / "result.md"

        with patch("tools.local.execute_real_write_once.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"id": 1, "name": "Eth-Trunk0"}
            mock_post.return_value = mock_response

            with patch("tools.local.execute_real_write_once.requests.get") as mock_get:
                mock_response_get = MagicMock()
                mock_response_get.status_code = 200
                mock_response_get.json.return_value = {"id": 1}
                mock_get.return_value = mock_response_get

                sys.argv = [
                    "execute_real_write_once.py",
                    "--execution-package", str(pkg_file),
                    "--operator", "test",
                    "--confirm-execution-phrase", "EXECUTO_ESCRITA_REAL_test-device_pkg-123",
                    "--confirm-real-write-once",
                    "--netbox-url", "https://netbox.test.com",
                    "--freeze-check", str(freeze_file),
                    "--output-json", str(output_json),
                    "--output-md", str(output_md),
                ]

                result = main()

                # Check result MD doesn't contain token
                with open(output_md) as f:
                    result_md = f.read()

                assert token_value not in result_md, "Token found in result markdown"


def test_11_success_with_post_201():
    """Test 11: Successful execution with POST 201."""
    from tools.local.execute_real_write_once import main

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = create_mock_execution_package(tmpdir)
        freeze_file = create_mock_freeze_check(tmpdir)
        os.environ["NETBOX_WRITE_TOKEN"] = "fake-token"

        output_json = Path(tmpdir) / "result.json"
        output_md = Path(tmpdir) / "result.md"

        with patch("tools.local.execute_real_write_once.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"id": 123, "name": "Eth-Trunk0"}
            mock_post.return_value = mock_response

            with patch("tools.local.execute_real_write_once.requests.get") as mock_get:
                mock_response_get = MagicMock()
                mock_response_get.status_code = 200
                mock_response_get.json.return_value = {"id": 123}
                mock_get.return_value = mock_response_get

                sys.argv = [
                    "execute_real_write_once.py",
                    "--execution-package", str(pkg_file),
                    "--operator", "test",
                    "--confirm-execution-phrase", "EXECUTO_ESCRITA_REAL_test-device_pkg-123",
                    "--confirm-real-write-once",
                    "--netbox-url", "https://netbox.test.com",
                    "--freeze-check", str(freeze_file),
                    "--output-json", str(output_json),
                    "--output-md", str(output_md),
                ]

                result = main()
                assert result == 0, "Should succeed with POST 201"

                with open(output_json) as f:
                    result_json = json.load(f)

                assert result_json["status"] == "REAL_WRITE_SUCCESS"


def test_12_success_with_get_verification():
    """Test 12: Successful execution with GET verification."""
    from tools.local.execute_real_write_once import main

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = create_mock_execution_package(tmpdir)
        freeze_file = create_mock_freeze_check(tmpdir)
        os.environ["NETBOX_WRITE_TOKEN"] = "fake-token"

        output_json = Path(tmpdir) / "result.json"
        output_md = Path(tmpdir) / "result.md"

        with patch("tools.local.execute_real_write_once.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"id": 456}
            mock_post.return_value = mock_response

            with patch("tools.local.execute_real_write_once.requests.get") as mock_get:
                mock_response_get = MagicMock()
                mock_response_get.status_code = 200
                mock_response_get.json.return_value = {"id": 456}
                mock_get.return_value = mock_response_get

                sys.argv = [
                    "execute_real_write_once.py",
                    "--execution-package", str(pkg_file),
                    "--operator", "test",
                    "--confirm-execution-phrase", "EXECUTO_ESCRITA_REAL_test-device_pkg-123",
                    "--confirm-real-write-once",
                    "--netbox-url", "https://netbox.test.com",
                    "--freeze-check", str(freeze_file),
                    "--output-json", str(output_json),
                    "--output-md", str(output_md),
                ]

                result = main()

                with open(output_json) as f:
                    result_json = json.load(f)

                item = result_json["items"][0]
                assert item["verification_status"] == "verified"


def test_13_fails_on_second_item_no_retry():
    """Test 13: Fails on second item and stops (no retry)."""
    from tools.local.execute_real_write_once import main

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create package with 3 items
        pkg_file = Path(tmpdir) / "package.json"
        pkg = {
            "execution_package_id": "pkg-456",
            "device": "test-device",
            "device_id": 1,
            "status": "prepared",
            "mode": "real_write_prepared",
            "execution_allowed": False,
            "required_execution_phrase": "EXECUTO_ESCRITA_REAL_test-device_pkg-456",
            "items": [
                {
                    "item_id": "item-1",
                    "approval_id": "approval-1",
                    "object_type": "Interface",
                    "object_key": "Eth-Trunk0",
                    "method": "POST",
                    "endpoint": "/api/dcim/interfaces/",
                    "payload": {"name": "Eth-Trunk0"},
                },
                {
                    "item_id": "item-2",
                    "approval_id": "approval-2",
                    "object_type": "Interface",
                    "object_key": "Eth-Trunk1",
                    "method": "POST",
                    "endpoint": "/api/dcim/interfaces/",
                    "payload": {"name": "Eth-Trunk1"},
                },
                {
                    "item_id": "item-3",
                    "approval_id": "approval-3",
                    "object_type": "Interface",
                    "object_key": "Eth-Trunk2",
                    "method": "POST",
                    "endpoint": "/api/dcim/interfaces/",
                    "payload": {"name": "Eth-Trunk2"},
                },
            ],
        }
        pkg_file.write_text(json.dumps(pkg))

        freeze_file = create_mock_freeze_check(tmpdir)
        os.environ["NETBOX_WRITE_TOKEN"] = "fake-token"

        output_json = Path(tmpdir) / "result.json"
        output_md = Path(tmpdir) / "result.md"

        with patch("tools.local.execute_real_write_once.requests.post") as mock_post:
            # First succeeds, second fails
            mock_post.side_effect = [
                MagicMock(status_code=201, json=lambda: {"id": 1}),
                MagicMock(status_code=500, text="Server error"),
                MagicMock(),  # Should not be called
            ]

            with patch("tools.local.execute_real_write_once.requests.get") as mock_get:
                mock_response_get = MagicMock()
                mock_response_get.status_code = 200
                mock_response_get.json.return_value = {"id": 1}
                mock_get.return_value = mock_response_get

                sys.argv = [
                    "execute_real_write_once.py",
                    "--execution-package", str(pkg_file),
                    "--operator", "test",
                    "--confirm-execution-phrase", "EXECUTO_ESCRITA_REAL_test-device_pkg-456",
                    "--confirm-real-write-once",
                    "--netbox-url", "https://netbox.test.com",
                    "--freeze-check", str(freeze_file),
                    "--output-json", str(output_json),
                    "--output-md", str(output_md),
                ]

                result = main()

                with open(output_json) as f:
                    result_json = json.load(f)

                # Should have only 2 items (first success, second failure, third not executed)
                assert len(result_json["items"]) == 2, "Should stop after failure"
                assert result_json["items"][0]["status"] == "REAL_WRITE_CREATED"
                assert result_json["items"][1]["status"] == "REAL_WRITE_FAILED"


def test_14_no_retry_attempted():
    """Test 14: Result confirms retry_attempted=false."""
    from tools.local.execute_real_write_once import main

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = create_mock_execution_package(tmpdir)
        freeze_file = create_mock_freeze_check(tmpdir)
        os.environ["NETBOX_WRITE_TOKEN"] = "fake-token"

        output_json = Path(tmpdir) / "result.json"
        output_md = Path(tmpdir) / "result.md"

        with patch("tools.local.execute_real_write_once.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=201, json=lambda: {"id": 1})

            with patch("tools.local.execute_real_write_once.requests.get"):
                sys.argv = [
                    "execute_real_write_once.py",
                    "--execution-package", str(pkg_file),
                    "--operator", "test",
                    "--confirm-execution-phrase", "EXECUTO_ESCRITA_REAL_test-device_pkg-123",
                    "--confirm-real-write-once",
                    "--netbox-url", "https://netbox.test.com",
                    "--freeze-check", str(freeze_file),
                    "--output-json", str(output_json),
                    "--output-md", str(output_md),
                ]

                main()

                with open(output_json) as f:
                    result_json = json.load(f)

                assert result_json["retry_attempted"] is False


def test_15_no_rollback_attempted():
    """Test 15: Result confirms rollback_attempted=false."""
    from tools.local.execute_real_write_once import main

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = create_mock_execution_package(tmpdir)
        freeze_file = create_mock_freeze_check(tmpdir)
        os.environ["NETBOX_WRITE_TOKEN"] = "fake-token"

        output_json = Path(tmpdir) / "result.json"
        output_md = Path(tmpdir) / "result.md"

        with patch("tools.local.execute_real_write_once.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=201, json=lambda: {"id": 1})

            with patch("tools.local.execute_real_write_once.requests.get"):
                sys.argv = [
                    "execute_real_write_once.py",
                    "--execution-package", str(pkg_file),
                    "--operator", "test",
                    "--confirm-execution-phrase", "EXECUTO_ESCRITA_REAL_test-device_pkg-123",
                    "--confirm-real-write-once",
                    "--netbox-url", "https://netbox.test.com",
                    "--freeze-check", str(freeze_file),
                    "--output-json", str(output_json),
                    "--output-md", str(output_md),
                ]

                main()

                with open(output_json) as f:
                    result_json = json.load(f)

                assert result_json["rollback_attempted"] is False


def test_16_safety_confirmations():
    """Test 16: Result includes safety confirmations."""
    from tools.local.execute_real_write_once import main

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = create_mock_execution_package(tmpdir)
        freeze_file = create_mock_freeze_check(tmpdir)
        os.environ["NETBOX_WRITE_TOKEN"] = "fake-token"

        output_json = Path(tmpdir) / "result.json"
        output_md = Path(tmpdir) / "result.md"

        with patch("tools.local.execute_real_write_once.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=201, json=lambda: {"id": 1})

            with patch("tools.local.execute_real_write_once.requests.get"):
                sys.argv = [
                    "execute_real_write_once.py",
                    "--execution-package", str(pkg_file),
                    "--operator", "test",
                    "--confirm-execution-phrase", "EXECUTO_ESCRITA_REAL_test-device_pkg-123",
                    "--confirm-real-write-once",
                    "--netbox-url", "https://netbox.test.com",
                    "--freeze-check", str(freeze_file),
                    "--output-json", str(output_json),
                    "--output-md", str(output_md),
                ]

                main()

                with open(output_json) as f:
                    result_json = json.load(f)

                safety = result_json["safety_confirmations"]
                assert safety["token_not_logged"] is True
                assert safety["token_not_saved"] is True
                assert safety["no_sync_called"] is True
                assert safety["no_patch_delete"] is True
                assert safety["one_shot_only"] is True


def test_17_result_md_no_token():
    """Test 17: Markdown result does not log any token."""
    from tools.local.execute_real_write_once import main

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = create_mock_execution_package(tmpdir)
        freeze_file = create_mock_freeze_check(tmpdir)
        os.environ["NETBOX_WRITE_TOKEN"] = "secret-token-xyz"

        output_json = Path(tmpdir) / "result.json"
        output_md = Path(tmpdir) / "result.md"

        with patch("tools.local.execute_real_write_once.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=201, json=lambda: {"id": 1})

            with patch("tools.local.execute_real_write_once.requests.get"):
                sys.argv = [
                    "execute_real_write_once.py",
                    "--execution-package", str(pkg_file),
                    "--operator", "test",
                    "--confirm-execution-phrase", "EXECUTO_ESCRITA_REAL_test-device_pkg-123",
                    "--confirm-real-write-once",
                    "--netbox-url", "https://netbox.test.com",
                    "--freeze-check", str(freeze_file),
                    "--output-json", str(output_json),
                    "--output-md", str(output_md),
                ]

                main()

                with open(output_md) as f:
                    md = f.read()

                assert "secret-token-xyz" not in md
                assert "token" not in md.lower() or "NETBOX_WRITE_TOKEN" not in md


def test_18_one_shot_only():
    """Test 18: Result confirms one_shot_execution=true."""
    from tools.local.execute_real_write_once import main

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = create_mock_execution_package(tmpdir)
        freeze_file = create_mock_freeze_check(tmpdir)
        os.environ["NETBOX_WRITE_TOKEN"] = "fake-token"

        output_json = Path(tmpdir) / "result.json"
        output_md = Path(tmpdir) / "result.md"

        with patch("tools.local.execute_real_write_once.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=201, json=lambda: {"id": 1})

            with patch("tools.local.execute_real_write_once.requests.get"):
                sys.argv = [
                    "execute_real_write_once.py",
                    "--execution-package", str(pkg_file),
                    "--operator", "test",
                    "--confirm-execution-phrase", "EXECUTO_ESCRITA_REAL_test-device_pkg-123",
                    "--confirm-real-write-once",
                    "--netbox-url", "https://netbox.test.com",
                    "--freeze-check", str(freeze_file),
                    "--output-json", str(output_json),
                    "--output-md", str(output_md),
                ]

                main()

                with open(output_json) as f:
                    result_json = json.load(f)

                assert result_json["one_shot_execution"] is True


def main_tests():
    """Run all tests."""
    test_functions = [
        test_01_blocks_without_confirm_flag,
        test_02_blocks_wrong_phrase,
        test_03_blocks_without_token,
        test_04_blocks_without_freeze_ready,
        test_05_blocks_patch_method,
        test_06_blocks_delete_method,
        test_07_blocks_sync_endpoint,
        test_08_blocks_secret_in_payload,
        test_09_no_token_in_output,
        test_10_no_token_in_markdown,
        test_11_success_with_post_201,
        test_12_success_with_get_verification,
        test_13_fails_on_second_item_no_retry,
        test_14_no_retry_attempted,
        test_15_no_rollback_attempted,
        test_16_safety_confirmations,
        test_17_result_md_no_token,
        test_18_one_shot_only,
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
    raise SystemExit(main_tests())
