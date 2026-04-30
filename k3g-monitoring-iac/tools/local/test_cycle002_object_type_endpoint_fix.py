#!/usr/bin/env python3
"""Test FASE 4.58.5 — Object Type/Endpoint Fix."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_01():
    """Test: Fixes bgp_peer + ipam/ip-addresses + IPv4."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create package with inconsistent item
        pkg = {
            "items": [{
                "object_key": "203.0.113.1",
                "object_type": "bgp_peer",
                "method": "POST",
                "endpoint": "/api/ipam/ip-addresses/",
                "payload": {"address": "203.0.113.1"},
                "required_execution_phrase": "EXECUTAR_ESCRITA_REAL_cycle-002_device_planid",
                "execution_allowed": False
            }]
        }

        pkg_file = tmpdir / "exec_pkg.json"
        pkg_file.write_text(json.dumps(pkg, indent=2))

        from tools.local.fix_cycle002_object_type_endpoint_consistency import main

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
        assert fixed_pkg["items"][0]["object_type"] == "ip_address"
        print("✓ test_01_fixes_bgp_peer_ipam_ipv4")


def test_02():
    """Test: Preserves payload."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        pkg = {
            "items": [{
                "object_key": "203.0.113.1",
                "object_type": "bgp_peer",
                "endpoint": "/api/ipam/ip-addresses/",
                "payload": {"address": "203.0.113.1", "description": "test"},
                "execution_allowed": False
            }]
        }

        pkg_file = tmpdir / "exec_pkg.json"
        pkg_file.write_text(json.dumps(pkg, indent=2))

        from tools.local.fix_cycle002_object_type_endpoint_consistency import main

        with patch("sys.argv", [
            "prog",
            "--cycle-id", "cycle-002",
            "--execution-package", str(pkg_file),
            "--output-report", str(tmpdir / "fix.md"),
            "--output-json", str(tmpdir / "fix.json"),
        ]):
            main()

        fixed_pkg = json.loads(pkg_file.read_text())
        assert fixed_pkg["items"][0]["payload"]["description"] == "test"
        print("✓ test_02_preserves_payload")


def test_03():
    """Test: Preserves execution_allowed=false."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        pkg = {
            "items": [{
                "object_key": "203.0.113.1",
                "object_type": "bgp_peer",
                "endpoint": "/api/ipam/ip-addresses/",
                "payload": {"address": "203.0.113.1"},
                "execution_allowed": False
            }]
        }

        pkg_file = tmpdir / "exec_pkg.json"
        pkg_file.write_text(json.dumps(pkg, indent=2))

        from tools.local.fix_cycle002_object_type_endpoint_consistency import main

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
        print("✓ test_03_preserves_execution_allowed_false")


def test_04():
    """Test: Adds change_history."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        pkg = {
            "items": [{
                "object_key": "203.0.113.1",
                "object_type": "bgp_peer",
                "endpoint": "/api/ipam/ip-addresses/",
                "payload": {"address": "203.0.113.1"},
                "execution_allowed": False
            }]
        }

        pkg_file = tmpdir / "exec_pkg.json"
        pkg_file.write_text(json.dumps(pkg, indent=2))

        from tools.local.fix_cycle002_object_type_endpoint_consistency import main

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
        assert fixed_pkg["items"][0]["change_history"][0]["action"] == "fix_object_type_endpoint_consistency"
        print("✓ test_04_adds_change_history")


def test_05():
    """Test: Blocks if payload looks like BGP peer."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        pkg = {
            "items": [{
                "object_key": "203.0.113.1",
                "object_type": "bgp_peer",
                "endpoint": "/api/ipam/ip-addresses/",
                "payload": {"address": "203.0.113.1", "remote_as": 65000},
                "execution_allowed": False
            }]
        }

        pkg_file = tmpdir / "exec_pkg.json"
        pkg_file.write_text(json.dumps(pkg, indent=2))

        from tools.local.fix_cycle002_object_type_endpoint_consistency import main

        with patch("sys.argv", [
            "prog",
            "--cycle-id", "cycle-002",
            "--execution-package", str(pkg_file),
            "--output-report", str(tmpdir / "fix.md"),
            "--output-json", str(tmpdir / "fix.json"),
        ]):
            exit_code = main()

        result = json.loads((tmpdir / "fix.json").read_text())
        assert result["status"] == "OBJECT_TYPE_ENDPOINT_FIX_BLOCKED"
        print("✓ test_05_blocks_bgp_peer_payload")


def test_06():
    """Test: No token access."""
    import inspect
    from tools.local import fix_cycle002_object_type_endpoint_consistency

    source = inspect.getsource(fix_cycle002_object_type_endpoint_consistency)
    assert "import os" not in source or ".environ" not in source
    assert "NETBOX_WRITE_TOKEN" not in source
    assert "import requests" not in source
    print("✓ test_06_no_token_access")


def test_07():
    """Test: No network imports."""
    import inspect
    from tools.local import fix_cycle002_object_type_endpoint_consistency

    source = inspect.getsource(fix_cycle002_object_type_endpoint_consistency)
    assert "import socket" not in source
    assert "import urllib" not in source
    assert "import pynetbox" not in source
    print("✓ test_07_no_network_imports")


def test_08():
    """Test: No NetBox writes."""
    import inspect
    from tools.local import fix_cycle002_object_type_endpoint_consistency

    source = inspect.getsource(fix_cycle002_object_type_endpoint_consistency)
    assert ".post(" not in source
    assert ".patch(" not in source
    assert ".delete(" not in source
    print("✓ test_08_no_netbox_writes")


def test_09():
    """Test: Creates backup."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        pkg = {
            "items": [{
                "object_key": "203.0.113.1",
                "object_type": "bgp_peer",
                "endpoint": "/api/ipam/ip-addresses/",
                "payload": {"address": "203.0.113.1"},
                "execution_allowed": False
            }]
        }

        pkg_file = tmpdir / "exec_pkg.json"
        pkg_file.write_text(json.dumps(pkg, indent=2))

        from tools.local.fix_cycle002_object_type_endpoint_consistency import main

        with patch("sys.argv", [
            "prog",
            "--cycle-id", "cycle-002",
            "--execution-package", str(pkg_file),
            "--output-report", str(tmpdir / "fix.md"),
            "--output-json", str(tmpdir / "fix.json"),
        ]):
            main()

        backups = list(tmpdir.glob("exec_pkg.json.bak.*"))
        assert len(backups) == 1
        print("✓ test_09_creates_backup")


def test_10():
    """Test: No fixes needed returns correct status."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        pkg = {
            "items": [{
                "object_key": "203.0.113.1",
                "object_type": "ip_address",
                "endpoint": "/api/ipam/ip-addresses/",
                "payload": {"address": "203.0.113.1"},
                "execution_allowed": False
            }]
        }

        pkg_file = tmpdir / "exec_pkg.json"
        pkg_file.write_text(json.dumps(pkg, indent=2))

        from tools.local.fix_cycle002_object_type_endpoint_consistency import main

        with patch("sys.argv", [
            "prog",
            "--cycle-id", "cycle-002",
            "--execution-package", str(pkg_file),
            "--output-report", str(tmpdir / "fix.md"),
            "--output-json", str(tmpdir / "fix.json"),
        ]):
            main()

        result = json.loads((tmpdir / "fix.json").read_text())
        assert result["status"] == "OBJECT_TYPE_ENDPOINT_FIX_NOT_NEEDED"
        print("✓ test_10_not_needed_status")


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
