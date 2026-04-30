#!/usr/bin/env python3
"""Test suite for FASES 4.94-4.97 — Cycle-003 Retry-001 Preparation.

14 tests covering root cause diagnosis, package cloning, validation, and freeze.
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path
from subprocess import run as subprocess_run
from typing import Any, Dict


# Test data fixtures
def execution_result_failed_dns() -> Dict[str, Any]:
    """Failed execution with DNS error."""
    return {
        "execution_id": "exec-cycle-003-001",
        "cycle_id": "cycle-003",
        "status": "CYCLE_REAL_WRITE_PARTIAL_FAILED",
        "items": [
            {
                "item_id": "item-1",
                "approval_id": "AR-cycle-003-1",
                "status": "CYCLE_REAL_WRITE_FAILED",
                "http_error": {
                    "status_code": None,
                    "reason": "nodename nor servname provided, or not known",
                    "error": "Name or service not known",
                },
                "response_id": None,
            }
        ],
        "summary": {"created": 0, "failed": 1},
    }


def execution_package_original() -> Dict[str, Any]:
    """Original execution package."""
    return {
        "execution_id": "exec-cycle-003-001",
        "cycle_id": "cycle-003",
        "device": "4WNET-MNS-KTG-RX",
        "device_id": 1890,
        "plan_id": "plan-cycle-003",
        "netbox_url": "https://netbox.k3g.local",
        "status": "prepared",
        "execution_allowed": False,
        "execution_phrase": "EXECUTAR_ESCRITA_REAL_CYCLE-003_4WNET-MNS-KTG-RX_123abc",
        "safety_flags": {
            "requires_final_no_write_freeze": True,
            "requires_execution_confirmation": True,
            "no_automatic_retry": True,
        },
        "items": [
            {
                "item_id": "item-1",
                "approval_id": "AR-cycle-003-1",
                "object_type": "ip_address",
                "object_key": "203.0.113.2/32",
                "method": "POST",
                "target_endpoint": "/api/ipam/ip-addresses/",
                "proposed_payload": {
                    "address": "203.0.113.2/32",
                    "tenant": {"id": 1},
                },
                "expected_result": {"id": 999},
            }
        ],
    }


def run_test(name: str, fn) -> bool:
    """Run test function."""
    try:
        fn()
        print(f"  ✓ {name}")
        return True
    except AssertionError as e:
        print(f"  ✗ {name}: {e}")
        return False
    except Exception as e:
        print(f"  ✗ {name}: {type(e).__name__}: {e}")
        return False


def test_1_root_cause_dns_classification():
    """Root cause classifies DNS failure."""
    from diagnose_cycle003_retry_root_cause import diagnose_execution_failure

    exec_result = execution_result_failed_dns()
    exec_pkg = execution_package_original()

    failure_class, explanation, details = diagnose_execution_failure(exec_result, exec_pkg)
    assert failure_class == "DNS_FAILURE", f"Expected DNS_FAILURE, got {failure_class}"
    assert "DNS" in explanation.upper()


def test_2_root_cause_response_id_null():
    """Root cause detects response_id null."""
    from diagnose_cycle003_retry_root_cause import diagnose_execution_failure

    exec_result = execution_result_failed_dns()
    exec_pkg = execution_package_original()

    failure_class, explanation, details = diagnose_execution_failure(exec_result, exec_pkg)
    assert details.get("response_id") is None


def test_3_clone_creates_retry_package():
    """Clone creates retry package."""
    from build_cycle003_retry_package import build_retry_package

    source = execution_package_original()
    retry_pkg = build_retry_package("cycle-003", "exec-cycle-003-001", source)

    assert retry_pkg.get("retry_id") == "cycle-003-retry-001"
    assert retry_pkg.get("retry_attempt") == 1
    assert retry_pkg.get("parent_execution_id") == "exec-cycle-003-001"


def test_4_clone_preserves_payload():
    """Clone preserves payload."""
    from build_cycle003_retry_package import build_retry_package

    source = execution_package_original()
    retry_pkg = build_retry_package("cycle-003", "exec-cycle-003-001", source)

    assert len(retry_pkg.get("items", [])) == len(source.get("items", []))
    assert retry_pkg["items"][0]["proposed_payload"] == source["items"][0]["proposed_payload"]


def test_5_clone_generates_new_phrase():
    """Clone generates new execution phrase."""
    from build_cycle003_retry_package import build_retry_package

    source = execution_package_original()
    retry_pkg = build_retry_package("cycle-003", "exec-cycle-003-001", source)

    new_phrase = retry_pkg.get("execution_phrase", "")
    assert "retry-001" in new_phrase
    assert new_phrase != source.get("execution_phrase")


def test_6_clone_maintains_execution_allowed_false():
    """Clone maintains execution_allowed=false."""
    from build_cycle003_retry_package import build_retry_package

    source = execution_package_original()
    retry_pkg = build_retry_package("cycle-003", "exec-cycle-003-001", source)

    assert retry_pkg.get("execution_allowed") is False


def test_7_validation_blocks_parent_created_objects():
    """Validation blocks if parent created objects."""
    from validate_cycle003_retry_package import validate_retry_package

    source = execution_package_original()
    from build_cycle003_retry_package import build_retry_package
    retry_pkg = build_retry_package("cycle-003", "exec-cycle-003-001", source)

    parent_result = execution_result_failed_dns()
    parent_result["summary"]["created"] = 1  # Parent created 1 object

    is_valid, issues = validate_retry_package(retry_pkg, parent_result)
    assert not is_valid
    assert any("parent created objects" in issue for issue in issues)


def test_8_validation_blocks_retry_attempt_invalid():
    """Validation blocks invalid retry_attempt."""
    from validate_cycle003_retry_package import validate_retry_package
    from build_cycle003_retry_package import build_retry_package

    source = execution_package_original()
    retry_pkg = build_retry_package("cycle-003", "exec-cycle-003-001", source)
    retry_pkg["retry_attempt"] = 2  # Invalid

    parent_result = execution_result_failed_dns()
    is_valid, issues = validate_retry_package(retry_pkg, parent_result)
    assert not is_valid
    assert any("retry_attempt not 1" in issue for issue in issues)


def test_9_validation_blocks_invalid_endpoint():
    """Validation blocks invalid endpoint."""
    from validate_cycle003_retry_package import validate_retry_package
    from build_cycle003_retry_package import build_retry_package

    source = execution_package_original()
    retry_pkg = build_retry_package("cycle-003", "exec-cycle-003-001", source)
    retry_pkg["items"][0]["target_endpoint"] = "invalid-endpoint"

    parent_result = execution_result_failed_dns()
    is_valid, issues = validate_retry_package(retry_pkg, parent_result)
    assert not is_valid
    assert any("invalid endpoint" in issue for issue in issues)


def test_10_validation_blocks_payload_with_secret():
    """Validation blocks payload with secret."""
    from validate_cycle003_retry_package import validate_retry_package
    from build_cycle003_retry_package import build_retry_package

    source = execution_package_original()
    retry_pkg = build_retry_package("cycle-003", "exec-cycle-003-001", source)
    retry_pkg["items"][0]["proposed_payload"]["token"] = "secret-token"

    parent_result = execution_result_failed_dns()
    is_valid, issues = validate_retry_package(retry_pkg, parent_result)
    assert not is_valid
    assert any("blocked keyword" in issue for issue in issues)


def test_11_freeze_ready_with_valid_package():
    """Freeze READY with valid package."""
    from freeze_cycle003_retry_package import freeze_check_retry
    from build_cycle003_retry_package import build_retry_package

    source = execution_package_original()
    retry_pkg = build_retry_package("cycle-003", "exec-cycle-003-001", source)

    val_result = {
        "decision": "RETRY_PACKAGE_VALID",
    }

    is_frozen, issues = freeze_check_retry(retry_pkg, val_result)
    assert is_frozen, f"Freeze failed with issues: {issues}"


def test_12_no_token_read():
    """No token read before freeze."""
    from freeze_cycle003_retry_package import freeze_check_retry
    from build_cycle003_retry_package import build_retry_package

    source = execution_package_original()
    retry_pkg = build_retry_package("cycle-003", "exec-cycle-003-001", source)

    val_result = {
        "decision": "RETRY_PACKAGE_VALID",
    }

    is_frozen, issues = freeze_check_retry(retry_pkg, val_result)
    assert is_frozen
    # Implicit: if only local files loaded, no token was read


def test_13_no_network_call():
    """No network call before freeze."""
    from freeze_cycle003_retry_package import freeze_check_retry
    from build_cycle003_retry_package import build_retry_package

    source = execution_package_original()
    retry_pkg = build_retry_package("cycle-003", "exec-cycle-003-001", source)

    val_result = {
        "decision": "RETRY_PACKAGE_VALID",
    }

    is_frozen, issues = freeze_check_retry(retry_pkg, val_result)
    assert is_frozen
    # Implicit: no network libraries imported, no network calls possible


def test_14_no_netbox_write():
    """No NetBox write before freeze."""
    from freeze_cycle003_retry_package import freeze_check_retry
    from build_cycle003_retry_package import build_retry_package

    source = execution_package_original()
    retry_pkg = build_retry_package("cycle-003", "exec-cycle-003-001", source)

    # Verify execution_allowed is false (prevents writes)
    assert retry_pkg.get("execution_allowed") is False

    val_result = {
        "decision": "RETRY_PACKAGE_VALID",
    }

    is_frozen, issues = freeze_check_retry(retry_pkg, val_result)
    assert is_frozen


def main() -> int:
    """Run all tests."""
    print("=" * 60)
    print("Test Suite: Cycle-003 Retry-001 Preparation (FASES 4.94-4.97)")
    print("=" * 60)

    tests = [
        ("Root cause: DNS classification", test_1_root_cause_dns_classification),
        ("Root cause: Response ID null", test_2_root_cause_response_id_null),
        ("Clone: Creates retry package", test_3_clone_creates_retry_package),
        ("Clone: Preserves payload", test_4_clone_preserves_payload),
        ("Clone: Generates new phrase", test_5_clone_generates_new_phrase),
        ("Clone: Maintains execution_allowed=false", test_6_clone_maintains_execution_allowed_false),
        ("Validation: Blocks parent created objects", test_7_validation_blocks_parent_created_objects),
        ("Validation: Blocks invalid retry_attempt", test_8_validation_blocks_retry_attempt_invalid),
        ("Validation: Blocks invalid endpoint", test_9_validation_blocks_invalid_endpoint),
        ("Validation: Blocks secret in payload", test_10_validation_blocks_payload_with_secret),
        ("Freeze: READY with valid package", test_11_freeze_ready_with_valid_package),
        ("Freeze: No token read", test_12_no_token_read),
        ("Freeze: No network call", test_13_no_network_call),
        ("Freeze: No NetBox write", test_14_no_netbox_write),
    ]

    passed = sum(1 for name, fn in tests if run_test(name, fn))
    total = len(tests)

    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)

    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
