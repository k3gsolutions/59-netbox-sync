#!/usr/bin/env python3
"""Test FASE 4.58.8 — Target Endpoint and Payload Fix."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_01():
    """Test: Fixes target_endpoint '/' to /api/ipam/ip-addresses/."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        pkg = {
            "items": [{
                "object_key": "203.0.113.1",
                "object_type": "ip_address",
                "method": "POST",
                "endpoint": "/api/ipam/ip-addresses/",
                "target_endpoint": "/",
                "proposed_payload": {"address": "203.0.113.1/32"},
                "execution_allowed": False,
                "required_execution_phrase": "EXEC_PHRASE"
            }]
        }

        pkg_file = tmpdir / "exec_pkg.json"
        pkg_file.write_text(json.dumps(pkg, indent=2))

        from tools.local.fix_cycle002_target_endpoint_and_payload import main

        with patch("sys.argv", [
            "prog",
            "--cycle-id", "cycle-002",
            "--execution-package", str(pkg_file),
            "--output-report", str(tmpdir / "fix.md"),
            "--output-json", str(tmpdir / "fix.json"),
        ]):
            exit_code = main()

        assert exit_code == 0
        fixed_pkg = json.loads(pkg_file.read_text())
        assert fixed_pkg["items"][0]["target_endpoint"] == "/api/ipam/ip-addresses/"
        print("✓ test_01_fixes_target_endpoint")


def test_02():
    """Test: Converts internal payload to NetBox IPAM payload."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        pkg = {
            "items": [{
                "object_key": "203.0.113.1",
                "object_type": "ip_address",
                "method": "POST",
                "endpoint": "/api/ipam/ip-addresses/",
                "target_endpoint": "/api/ipam/ip-addresses/",
                "proposed_payload": {
                    "cycle_id": "cycle-002",
                    "device": "4WNET-MNS-KTG-RX",
                    "device_id": "1890",
                    "team": "bgp",
                    "object_type": "bgp_peer",
                    "object_key": "203.0.113.1",
                    "action": "safe_create_staged",
                    "category": "bgp"
                },
                "execution_allowed": False
            }]
        }

        pkg_file = tmpdir / "exec_pkg.json"
        pkg_file.write_text(json.dumps(pkg, indent=2))

        from tools.local.fix_cycle002_target_endpoint_and_payload import main

        with patch("sys.argv", [
            "prog",
            "--cycle-id", "cycle-002",
            "--execution-package", str(pkg_file),
            "--output-report", str(tmpdir / "fix.md"),
            "--output-json", str(tmpdir / "fix.json"),
        ]):
            exit_code = main()

        assert exit_code == 0
        fixed_pkg = json.loads(pkg_file.read_text())
        payload = fixed_pkg["items"][0]["proposed_payload"]
        assert "address" in payload
        assert payload["address"] == "203.0.113.1/32"
        assert payload["status"] == "active"
        assert "cycle_id" not in payload
        assert "device" not in payload
        print("✓ test_02_converts_payload")


def test_03():
    """Test: Preserves execution_allowed=false."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        pkg = {
            "items": [{
                "object_key": "203.0.113.1",
                "object_type": "ip_address",
                "method": "POST",
                "endpoint": "/api/ipam/ip-addresses/",
                "target_endpoint": "/",
                "proposed_payload": {"device": "test"},
                "execution_allowed": False
            }]
        }

        pkg_file = tmpdir / "exec_pkg.json"
        pkg_file.write_text(json.dumps(pkg, indent=2))

        from tools.local.fix_cycle002_target_endpoint_and_payload import main

        with patch("sys.argv", [
            "prog",
            "--cycle-id", "cycle-002",
            "--execution-package", str(pkg_file),
            "--output-report", str(tmpdir / "fix.md"),
            "--output-json", str(tmpdir / "fix.json"),
        ]):
            main()

        fixed_pkg = json.loads(pkg_file.read_text())
        assert fixed_pkg["items"][0]["execution_allowed"] is False
        print("✓ test_03_preserves_execution_allowed")


def test_04():
    """Test: Blocks payload with secrets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        pkg = {
            "items": [{
                "object_key": "203.0.113.1",
                "object_type": "ip_address",
                "method": "POST",
                "endpoint": "/api/ipam/ip-addresses/",
                "target_endpoint": "/",
                "proposed_payload": {"token": "secret"},
                "execution_allowed": False
            }]
        }

        pkg_file = tmpdir / "exec_pkg.json"
        pkg_file.write_text(json.dumps(pkg, indent=2))

        from tools.local.fix_cycle002_target_endpoint_and_payload import main

        with patch("sys.argv", [
            "prog",
            "--cycle-id", "cycle-002",
            "--execution-package", str(pkg_file),
            "--output-report", str(tmpdir / "fix.md"),
            "--output-json", str(tmpdir / "fix.json"),
        ]):
            exit_code = main()

        result = json.loads((tmpdir / "fix.json").read_text())
        assert result["status"] == "TARGET_ENDPOINT_PAYLOAD_FIX_BLOCKED"
        print("✓ test_04_blocks_secrets")


def test_05():
    """Test: Adds change_history."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        pkg = {
            "items": [{
                "object_key": "203.0.113.1",
                "object_type": "ip_address",
                "method": "POST",
                "endpoint": "/api/ipam/ip-addresses/",
                "target_endpoint": "/",
                "proposed_payload": {"device": "test"},
                "execution_allowed": False
            }]
        }

        pkg_file = tmpdir / "exec_pkg.json"
        pkg_file.write_text(json.dumps(pkg, indent=2))

        from tools.local.fix_cycle002_target_endpoint_and_payload import main

        with patch("sys.argv", [
            "prog",
            "--cycle-id", "cycle-002",
            "--execution-package", str(pkg_file),
            "--output-report", str(tmpdir / "fix.md"),
            "--output-json", str(tmpdir / "fix.json"),
        ]):
            main()

        fixed_pkg = json.loads(pkg_file.read_text())
        assert "change_history" in fixed_pkg["items"][0]
        print("✓ test_05_adds_change_history")


def test_06():
    """Test: No token access."""
    import inspect
    from tools.local import fix_cycle002_target_endpoint_and_payload

    source = inspect.getsource(fix_cycle002_target_endpoint_and_payload)
    assert "import requests" not in source
    assert "import socket" not in source
    print("✓ test_06_no_token_access")


def test_07():
    """Test: No network imports."""
    import inspect
    from tools.local import fix_cycle002_target_endpoint_and_payload

    source = inspect.getsource(fix_cycle002_target_endpoint_and_payload)
    assert "import urllib" not in source
    assert "import pynetbox" not in source
    print("✓ test_07_no_network_imports")


def test_08():
    """Test: No NetBox writes."""
    import inspect
    from tools.local import fix_cycle002_target_endpoint_and_payload

    source = inspect.getsource(fix_cycle002_target_endpoint_and_payload)
    assert ".post(" not in source
    assert ".patch(" not in source
    assert ".delete(" not in source
    print("✓ test_08_no_netbox_writes")


def test_09():
    """Test: Adds /32 to IPv4 without CIDR."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        pkg = {
            "items": [{
                "object_key": "203.0.113.1",
                "object_type": "ip_address",
                "method": "POST",
                "endpoint": "/api/ipam/ip-addresses/",
                "target_endpoint": "/",
                "proposed_payload": {"temp": "data"},
                "execution_allowed": False
            }]
        }

        pkg_file = tmpdir / "exec_pkg.json"
        pkg_file.write_text(json.dumps(pkg, indent=2))

        from tools.local.fix_cycle002_target_endpoint_and_payload import main

        with patch("sys.argv", [
            "prog",
            "--cycle-id", "cycle-002",
            "--execution-package", str(pkg_file),
            "--output-report", str(tmpdir / "fix.md"),
            "--output-json", str(tmpdir / "fix.json"),
        ]):
            main()

        fixed_pkg = json.loads(pkg_file.read_text())
        assert fixed_pkg["items"][0]["proposed_payload"]["address"] == "203.0.113.1/32"
        print("✓ test_09_adds_cidr")


def test_10():
    """Test: Final payload clean of internal fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        pkg = {
            "items": [{
                "object_key": "203.0.113.1",
                "object_type": "ip_address",
                "method": "POST",
                "endpoint": "/api/ipam/ip-addresses/",
                "target_endpoint": "/",
                "proposed_payload": {
                    "cycle_id": "cycle-002",
                    "device": "4WNET-MNS-KTG-RX",
                    "device_id": "1890",
                    "team": "bgp"
                },
                "execution_allowed": False
            }]
        }

        pkg_file = tmpdir / "exec_pkg.json"
        pkg_file.write_text(json.dumps(pkg, indent=2))

        from tools.local.fix_cycle002_target_endpoint_and_payload import main

        with patch("sys.argv", [
            "prog",
            "--cycle-id", "cycle-002",
            "--execution-package", str(pkg_file),
            "--output-report", str(tmpdir / "fix.md"),
            "--output-json", str(tmpdir / "fix.json"),
        ]):
            main()

        fixed_pkg = json.loads(pkg_file.read_text())
        payload = fixed_pkg["items"][0]["proposed_payload"]
        assert "cycle_id" not in payload
        assert "device" not in payload
        assert "device_id" not in payload
        assert "team" not in payload
        assert "address" in payload
        assert "status" in payload
        print("✓ test_10_final_payload_clean")


if __name__ == "__main__":
    test_01()
    test_02()
    test_03()
    test_04()
    test_05()
    test_06()
    test_07()
    test_08()
    test_09()
    test_10()

    print("\n" + "=" * 60)
    print("Results: 10/10 tests passed")
    print("=" * 60)
