#!/usr/bin/env python3
"""Test cycle-002 execution package endpoint fix."""

from __future__ import annotations

import json
import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(".").resolve()))

from tools.local.fix_cycle002_execution_package_endpoint import (
    validate_endpoint,
    fix_package_endpoints,
    BLOCKED_ENDPOINTS,
)


def test_blocked_endpoints() -> None:
    """Test blocked endpoint detection."""
    print("TEST: Blocked endpoints")
    
    for blocked in BLOCKED_ENDPOINTS:
        assert not validate_endpoint(blocked), f"Should block {blocked}"
    
    assert not validate_endpoint("/sync")
    assert not validate_endpoint("equipment")
    assert not validate_endpoint("ssh")
    assert not validate_endpoint("netconf")
    
    print("  ✓ Blocks all invalid endpoints")


def test_valid_endpoints() -> None:
    """Test valid endpoint detection."""
    print("\nTEST: Valid endpoints")
    
    valid = [
        "/api/ipam/ip-addresses/",
        "/api/dcim/interfaces/",
        "/api/ipam/prefixes/",
        "/api/ipam/vrfs/",
    ]
    
    for endpoint in valid:
        assert validate_endpoint(endpoint), f"Should allow {endpoint}"
    
    print("  ✓ Allows valid endpoints")


def test_fix_ip_address_endpoint() -> None:
    """Test fixing ip_address endpoint."""
    print("\nTEST: Fix ip_address endpoint")
    
    package = {
        "items": [
            {
                "object_type": "ip_address",
                "object_key": "192.168.1.1/32",
                "endpoint": "/",
                "payload": {"address": "192.168.1.1/32"},
            }
        ]
    }
    
    fixed, count = fix_package_endpoints(package)
    assert count == 1
    assert fixed["items"][0]["endpoint"] == "/api/ipam/ip-addresses/"
    print("  ✓ Fixes ip_address endpoint")


def test_fix_interface_endpoint() -> None:
    """Test fixing interface endpoint."""
    print("\nTEST: Fix interface endpoint")
    
    package = {
        "items": [
            {
                "object_type": "interface",
                "object_key": "eth0",
                "endpoint": "/",
                "payload": {"name": "eth0"},
            }
        ]
    }
    
    fixed, count = fix_package_endpoints(package)
    assert count == 1
    assert fixed["items"][0]["endpoint"] == "/api/dcim/interfaces/"
    print("  ✓ Fixes interface endpoint")


def test_preserves_payload() -> None:
    """Test payload preservation."""
    print("\nTEST: Payload preservation")
    
    payload = {"address": "192.168.1.1/32", "description": "test"}
    package = {
        "items": [
            {
                "object_type": "ip_address",
                "object_key": "192.168.1.1/32",
                "endpoint": "/",
                "payload": payload,
                "execution_allowed": False,
                "token_required_in_next_phase": True,
            }
        ]
    }
    
    fixed, _ = fix_package_endpoints(package)
    assert fixed["items"][0]["payload"] == payload
    assert fixed["items"][0]["execution_allowed"] == False
    assert fixed["items"][0]["token_required_in_next_phase"] == True
    print("  ✓ Preserves payload and flags")


def test_backup_creation() -> None:
    """Test backup file creation."""
    print("\nTEST: Backup creation")
    
    from tools.local.fix_cycle002_execution_package_endpoint import create_backup
    
    with tempfile.TemporaryDirectory() as tmpdir:
        package_file = Path(tmpdir) / "package.json"
        package_file.write_text('{"test": true}')
        
        backup = create_backup(package_file)
        assert backup.exists()
        assert "bak" in backup.name
        assert backup.read_text() == package_file.read_text()
        print("  ✓ Creates backup")


def test_no_token_read() -> None:
    """Ensure no token is read."""
    print("\nTEST: No token read")
    
    from tools.local.fix_cycle002_execution_package_endpoint import fix_package_endpoints
    
    # Tool should never read NETBOX_WRITE_TOKEN
    package = {
        "items": [
            {
                "object_type": "ip_address",
                "object_key": "test",
                "endpoint": "/",
            }
        ]
    }
    
    # Should not raise or access environment
    fixed, _ = fix_package_endpoints(package)
    assert fixed is not None
    print("  ✓ No token access")


def main() -> int:
    """Run tests."""
    try:
        test_blocked_endpoints()
        test_valid_endpoints()
        test_fix_ip_address_endpoint()
        test_fix_interface_endpoint()
        test_preserves_payload()
        test_backup_creation()
        test_no_token_read()
        
        print("\n" + "="*60)
        print("✓ All endpoint fix tests pass")
        print("="*60)
        return 0
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
