#!/usr/bin/env python3
"""
Integration tests for Compliance Policy Registry with Web UI.
Tests that convention_validator functions work correctly with response_forms.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add webui module to path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from webui.services.convention_validator import (
    validate_interface_name,
    validate_vrf_name,
    validate_comment,
    validate_community,
    validate_bgp_metadata,
    validate_ip_address_relation,
)
from webui.services.response_forms import (
    validate_response_payload,
    _collect_convention_violations,
)
from webui.services.validators import (
    validate_interface_name_registry,
    validate_vrf_name_registry,
    validate_comment_registry,
)


def test_interface_base_valid() -> bool:
    """Test 1: Eth-Trunk0 matches base_inventory pattern."""
    print("\nTest 1: Interface base_inventory pattern")
    result = validate_interface_name("Eth-Trunk0")
    if not result.get("valid"):
        print(f"  ✗ FAILED: expected valid, got {result}")
        return False
    if result.get("details", {}).get("classification") != "base_inventory":
        print(f"  ✗ FAILED: expected base_inventory, got {result.get('details')}")
        return False
    print("  ✓ Eth-Trunk0 → base_inventory valid")
    return True


def test_interface_service_valid() -> bool:
    """Test 2: Eth-Trunk0.1580 matches service_interface pattern."""
    print("\nTest 2: Interface service_interface pattern")
    result = validate_interface_name("Eth-Trunk0.1580")
    if not result.get("valid"):
        print(f"  ✗ FAILED: expected valid, got {result}")
        return False
    if result.get("details", {}).get("classification") != "service_interface":
        print(f"  ✗ FAILED: expected service_interface, got {result.get('details')}")
        return False
    print("  ✓ Eth-Trunk0.1580 → service_interface valid")
    return True


def test_interface_invalid() -> bool:
    """Test 3: Bad.Naming invalid."""
    print("\nTest 3: Interface invalid pattern")
    result = validate_interface_name("Bad.Naming")
    if result.get("valid"):
        print(f"  ✗ FAILED: expected invalid, got {result}")
        return False
    if result.get("rule_id") != "IFACE-001":
        print(f"  ✗ FAILED: expected IFACE-001, got {result.get('rule_id')}")
        return False
    print("  ✓ Bad.Naming → invalid")
    return True


def test_interface_gigabit() -> bool:
    """Test 4: GigabitEthernet0/1/0 matches base_inventory."""
    print("\nTest 4: GigabitEthernet base pattern")
    result = validate_interface_name("GigabitEthernet0/1/0")
    if not result.get("valid"):
        print(f"  ✗ FAILED: expected valid, got {result}")
        return False
    print("  ✓ GigabitEthernet0/1/0 → valid")
    return True


def test_route_policy_valid() -> bool:
    """Test 5: Route-policy name AS263934-INFORR-BVA-InterCDN-IPv4-Export valid."""
    print("\nTest 5: Route-policy naming convention")
    from webui.services.convention_validator import validate_route_policy_name
    result = validate_route_policy_name("AS263934-INFORR-BVA-InterCDN-IPv4-Export")
    if not result.get("valid"):
        print(f"  ✗ FAILED: expected valid, got {result}")
        return False
    print("  ✓ AS263934-INFORR-BVA-InterCDN-IPv4-Export → valid")
    return True


def test_route_policy_invalid() -> bool:
    """Test 6: Route-policy name invalid-policy-name invalid."""
    print("\nTest 6: Route-policy invalid naming")
    from webui.services.convention_validator import validate_route_policy_name
    result = validate_route_policy_name("invalid-policy-name")
    if result.get("valid"):
        print(f"  ✗ FAILED: expected invalid, got {result}")
        return False
    if result.get("rule_id") != "RTPOL-001":
        print(f"  ✗ FAILED: expected RTPOL-001, got {result.get('rule_id')}")
        return False
    print("  ✓ invalid-policy-name → RTPOL-001 error")
    return True


def test_prefix_bogons() -> bool:
    """Test 7: BOGONS-IPv4 prefix valid."""
    print("\nTest 7: Prefix list BOGONS")
    from webui.services.convention_validator import validate_ip_prefix_name
    result = validate_ip_prefix_name("BOGONS-IPv4")
    if not result.get("valid"):
        print(f"  ✗ FAILED: expected valid, got {result}")
        return False
    print("  ✓ BOGONS-IPv4 → valid")
    return True


def test_prefix_customer() -> bool:
    """Test 8: CUSTOMER-CLIENTEABC-IPv4 prefix valid."""
    print("\nTest 8: Prefix list CUSTOMER")
    from webui.services.convention_validator import validate_ip_prefix_name
    result = validate_ip_prefix_name("CUSTOMER-CLIENTEABC-IPv4")
    if not result.get("valid"):
        print(f"  ✗ FAILED: expected valid, got {result}")
        return False
    print("  ✓ CUSTOMER-CLIENTEABC-IPv4 → valid")
    return True


def test_community_valid() -> bool:
    """Test 9: Community 263934:100 valid."""
    print("\nTest 9: BGP community ASN:VALUE")
    result = validate_community("263934:100")
    if not result.get("valid"):
        print(f"  ✗ FAILED: expected valid, got {result}")
        return False
    if result.get("rule_id") != "COMM-001":
        print(f"  ✗ FAILED: expected COMM-001, got {result.get('rule_id')}")
        return False
    print("  ✓ 263934:100 → valid")
    return True


def test_community_invalid() -> bool:
    """Test 10: Community bad_community invalid."""
    print("\nTest 10: Community invalid format")
    result = validate_community("bad_community")
    if result.get("valid"):
        print(f"  ✗ FAILED: expected invalid, got {result}")
        return False
    if result.get("rule_id") != "COMM-001":
        print(f"  ✗ FAILED: expected COMM-001, got {result.get('rule_id')}")
        return False
    print("  ✓ bad_community → COMM-001 error")
    return True


def test_comment_blocked_keyword() -> bool:
    """Test 11: Comment with 'token' blocked."""
    print("\nTest 11: Comment with blocked keyword")
    result = validate_comment("Use token ABC123 here")
    if result.get("valid"):
        print(f"  ✗ FAILED: expected blocker, got {result}")
        return False
    if result.get("severity") != "blocker":
        print(f"  ✗ FAILED: expected severity=blocker, got {result.get('severity')}")
        return False
    if result.get("rule_id") != "COMMENT-001":
        print(f"  ✗ FAILED: expected COMMENT-001, got {result.get('rule_id')}")
        return False
    print("  ✓ Comment with 'token' → COMMENT-001 blocker")
    return True


def test_comment_valid() -> bool:
    """Test 12: Comment 'Configured per ticket 1234' valid."""
    print("\nTest 12: Comment valid")
    result = validate_comment("Configured per ticket 1234")
    if not result.get("valid"):
        print(f"  ✗ FAILED: expected valid, got {result}")
        return False
    print("  ✓ Valid comment accepted")
    return True


def test_bgp_missing_remote_asn() -> bool:
    """Test 13: BGP peer missing remote_asn invalid."""
    print("\nTest 13: BGP metadata missing remote_asn")
    data = {
        "remote_asn": None,
        "owner": "netops",
        "policy_intent": "Peering with upstream",
        "notes": ""
    }
    violations = validate_bgp_metadata(data)
    if not any(v.get("rule_id") == "BGP-001" for v in violations):
        print(f"  ✗ FAILED: expected BGP-001, got {violations}")
        return False
    print("  ✓ Missing remote_asn → BGP-001 error")
    return True


def test_ip_service_missing_relation() -> bool:
    """Test 14: IP relation_type=service without service_relation invalid."""
    print("\nTest 14: IP address relation missing service_relation")
    data = {
        "relation_type": "service",
        "service_relation": None,
        "notes": ""
    }
    violations = validate_ip_address_relation(data)
    if not any(v.get("rule_id") == "IPMAP-001" for v in violations):
        print(f"  ✗ FAILED: expected IPMAP-001, got {violations}")
        return False
    print("  ✓ relation_type=service without service_relation → IPMAP-001 error")
    return True


def test_response_payload_convention_violations() -> bool:
    """Test 15: Response payload collects convention_violations."""
    print("\nTest 15: Response payload with convention_violations")
    item = {
        "device": "router1",
        "object_type": "bgp_peer",
        "object_key": "192.0.2.1",
        "responsible_team": "bgp-team",
    }
    payload = {
        "status": "answered",
        "remote_asn": "65001",
        "remote_bgp_group": "upstream",
        "policy_intent": "Peering agreement",
        "owner": "netops",
        "criticality": "gold",
        "evidence": "Ticket 1234",
        "notes": "This comment contains a token ABC123",
        "updated_by": "testuser",
    }
    valid, errors, violations = validate_response_payload(item, payload)

    # Should have COMMENT-001 blocker violation
    if not any(v.get("rule_id") == "COMMENT-001" and v.get("severity") == "blocker" for v in violations):
        print(f"  ✗ FAILED: expected COMMENT-001 blocker, got violations={violations}, errors={errors}")
        return False

    # Should fail validation due to blocker
    if valid:
        print(f"  ✗ FAILED: expected invalid due to blocker, got valid=True")
        return False

    print("  ✓ Response payload collects convention_violations correctly")
    return True


def test_registry_unavailable_blocks_interface_validation() -> bool:
    """Test 16: Registry unavailable causes REGISTRY-001 blocker (interface validation)."""
    print("\nTest 16: Registry unavailable → REGISTRY-001 blocker")
    from webui.services import validators

    # Simulate registry unavailability by temporarily setting HAS_CONVENTION_VALIDATOR to False
    original_flag = validators.HAS_CONVENTION_VALIDATOR
    validators.HAS_CONVENTION_VALIDATOR = False

    try:
        valid, message = validators.validate_interface_name_registry("Eth-Trunk0")

        # Should NOT be valid, should have REGISTRY-001 in message
        if valid:
            print(f"  ✗ FAILED: expected invalid due to registry unavailable, got valid=True")
            return False

        if "REGISTRY-001" not in str(message):
            print(f"  ✗ FAILED: expected REGISTRY-001 in message, got {message}")
            return False

        print("  ✓ Registry unavailable blocks validation with REGISTRY-001")
        return True
    finally:
        validators.HAS_CONVENTION_VALIDATOR = original_flag


def test_registry_unavailable_blocks_bgp_validation() -> bool:
    """Test 17: Registry unavailable causes REGISTRY-001 blocker (BGP metadata)."""
    print("\nTest 17: Registry unavailable → REGISTRY-001 blocker (BGP)")
    from webui.services import validators

    # Simulate registry unavailability
    original_flag = validators.HAS_CONVENTION_VALIDATOR
    validators.HAS_CONVENTION_VALIDATOR = False

    try:
        data = {"remote_asn": "65001", "owner": "netops", "policy_intent": "Peer"}
        violations = validators.validate_bgp_metadata_registry(data)

        # Should have REGISTRY-001 blocker
        if not any(v.get("rule_id") == "REGISTRY-001" and v.get("severity") == "blocker" for v in violations):
            print(f"  ✗ FAILED: expected REGISTRY-001 blocker, got violations={violations}")
            return False

        print("  ✓ Registry unavailable blocks BGP validation with REGISTRY-001")
        return True
    finally:
        validators.HAS_CONVENTION_VALIDATOR = original_flag


def main() -> int:
    """Run all integration tests."""
    print("=" * 60)
    print("Convention Registry Integration Tests")
    print("=" * 60)

    tests = [
        test_interface_base_valid,
        test_interface_service_valid,
        test_interface_invalid,
        test_interface_gigabit,
        test_route_policy_valid,
        test_route_policy_invalid,
        test_prefix_bogons,
        test_prefix_customer,
        test_community_valid,
        test_community_invalid,
        test_comment_blocked_keyword,
        test_comment_valid,
        test_bgp_missing_remote_asn,
        test_ip_service_missing_relation,
        test_response_payload_convention_violations,
        test_registry_unavailable_blocks_interface_validation,
        test_registry_unavailable_blocks_bgp_validation,
    ]

    results = [test() for test in tests]

    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)

    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
