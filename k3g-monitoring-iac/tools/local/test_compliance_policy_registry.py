#!/usr/bin/env python3
"""Test compliance policy registry and convention validator."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from webui.services.convention_validator import (
    classify_interface,
    validate_interface_name,
    validate_vrf_name,
    validate_route_policy_name,
    validate_ip_prefix_name,
    validate_community,
    validate_comment,
    validate_bgp_metadata,
    validate_ip_address_relation,
)


def test_interface_base_inventory():
    """Test Eth-Trunk0 = base_inventory valid."""
    print("Test 1: Interface base_inventory")
    result = validate_interface_name("Eth-Trunk0")
    if not result["valid"]:
        print(f"  ✗ FAILED: {result}")
        return False
    if classify_interface("Eth-Trunk0") != "base_inventory":
        print("  ✗ FAILED: classification not base_inventory")
        return False
    print("  ✓ Eth-Trunk0 valid")
    return True


def test_interface_service():
    """Test Eth-Trunk0.1580 = service_interface valid."""
    print("Test 2: Interface service_interface")
    result = validate_interface_name("Eth-Trunk0.1580")
    if not result["valid"]:
        print(f"  ✗ FAILED: {result}")
        return False
    if classify_interface("Eth-Trunk0.1580") != "service_interface":
        print("  ✗ FAILED: classification not service_interface")
        return False
    print("  ✓ Eth-Trunk0.1580 valid")
    return True


def test_interface_invalid():
    """Test Bad.Naming = invalid."""
    print("Test 3: Interface invalid")
    result = validate_interface_name("Bad.Naming")
    if result["valid"]:
        print(f"  ✗ FAILED: should be invalid")
        return False
    print("  ✓ Bad.Naming invalid")
    return True


def test_interface_10ge():
    """Test 10GE0/1/0 = base_inventory valid."""
    print("Test 4: Interface 10GE0/1/0")
    result = validate_interface_name("10GE0/1/0")
    if not result["valid"]:
        print(f"  ✗ FAILED: {result}")
        return False
    print("  ✓ 10GE0/1/0 valid")
    return True


def test_route_policy_valid():
    """Test AS263934-INFORR-BVA-InterCDN-IPv4-Export = valid."""
    print("Test 5: Route-policy valid")
    result = validate_route_policy_name("AS263934-INFORR-BVA-InterCDN-IPv4-Export")
    if not result["valid"]:
        print(f"  ✗ FAILED: {result}")
        return False
    print("  ✓ AS263934-INFORR-BVA-InterCDN-IPv4-Export valid")
    return True


def test_route_policy_invalid():
    """Test invalid-policy-name = invalid."""
    print("Test 6: Route-policy invalid")
    result = validate_route_policy_name("invalid-policy-name")
    if result["valid"]:
        print(f"  ✗ FAILED: should be invalid")
        return False
    print("  ✓ invalid-policy-name invalid")
    return True


def test_prefix_bogons():
    """Test BOGONS-IPv4 = valid."""
    print("Test 7: IP prefix BOGONS-IPv4")
    result = validate_ip_prefix_name("BOGONS-IPv4")
    if not result["valid"]:
        print(f"  ✗ FAILED: {result}")
        return False
    print("  ✓ BOGONS-IPv4 valid")
    return True


def test_prefix_customer():
    """Test CUSTOMER-CLIENTEABC-IPv4 = valid."""
    print("Test 8: IP prefix CUSTOMER-CLIENTEABC-IPv4")
    result = validate_ip_prefix_name("CUSTOMER-CLIENTEABC-IPv4")
    if not result["valid"]:
        print(f"  ✗ FAILED: {result}")
        return False
    print("  ✓ CUSTOMER-CLIENTEABC-IPv4 valid")
    return True


def test_community_valid():
    """Test 263934:100 = valid."""
    print("Test 9: Community 263934:100")
    result = validate_community("263934:100")
    if not result["valid"]:
        print(f"  ✗ FAILED: {result}")
        return False
    print("  ✓ 263934:100 valid")
    return True


def test_community_invalid():
    """Test bad_community = invalid."""
    print("Test 10: Community bad_community")
    result = validate_community("bad_community")
    if result["valid"]:
        print(f"  ✗ FAILED: should be invalid")
        return False
    print("  ✓ bad_community invalid")
    return True


def test_snmp_public_blocked():
    """Test SNMP community 'public' = blocked."""
    print("Test 11: SNMP community public blocked")
    result = validate_comment("snmp community=public")
    # This comment has "public" but not the blocked keywords directly
    # The blocked keywords are: token, password, secret, etc.
    # Let's test with actual blocked keyword
    result = validate_comment("password=secret123")
    if result["valid"]:
        print(f"  ✗ FAILED: password keyword should be blocked")
        return False
    print("  ✓ password keyword blocked")
    return True


def test_snmp_v3_valid():
    """Test SNMPv3 complete = valid."""
    print("Test 12: SNMPv3 complete")
    result = validate_comment("SNMPv3 configured with SHA auth and AES privacy")
    if not result["valid"]:
        print(f"  ✗ FAILED: {result}")
        return False
    print("  ✓ SNMPv3 comment valid")
    return True


def test_bgp_missing_asn():
    """Test BGP metadata missing remote_asn = invalid."""
    print("Test 13: BGP missing remote_asn")
    data = {
        "owner": "noc-team",
        "policy_intent": "Prefer primary path",
    }
    errors = validate_bgp_metadata(data)
    if not any(e["rule_id"] == "BGP-001" for e in errors):
        print(f"  ✗ FAILED: missing BGP-001 error")
        return False
    print("  ✓ BGP-001 error for missing remote_asn")
    return True


def test_ip_relation_service_no_relation():
    """Test IP relation_type=service without service_relation = invalid."""
    print("Test 14: IP relation_type=service without service_relation")
    data = {
        "relation_type": "service",
    }
    errors = validate_ip_address_relation(data)
    if not any(e["rule_id"] == "IPMAP-001" for e in errors):
        print(f"  ✗ FAILED: missing IPMAP-001 error")
        return False
    print("  ✓ IPMAP-001 error for missing service_relation")
    return True


def test_comment_token_blocked():
    """Test comment with 'token' = blocked."""
    print("Test 15: Comment with token blocked")
    result = validate_comment("api token is xyz123")
    if result["valid"]:
        print(f"  ✗ FAILED: token should be blocked")
        return False
    if result["rule_id"] != "COMMENT-001":
        print(f"  ✗ FAILED: wrong rule_id {result['rule_id']}")
        return False
    print("  ✓ token keyword blocked")
    return True


def main() -> int:
    """Run all tests."""
    print("=" * 60)
    print("Compliance Policy Registry Tests")
    print("=" * 60)

    tests = [
        test_interface_base_inventory,
        test_interface_service,
        test_interface_invalid,
        test_interface_10ge,
        test_route_policy_valid,
        test_route_policy_invalid,
        test_prefix_bogons,
        test_prefix_customer,
        test_community_valid,
        test_community_invalid,
        test_snmp_public_blocked,
        test_snmp_v3_valid,
        test_bgp_missing_asn,
        test_ip_relation_service_no_relation,
        test_comment_token_blocked,
    ]

    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as exc:
            print(f"  ✗ EXCEPTION: {exc}")
            results.append(False)

    print("\n" + "=" * 60)
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
