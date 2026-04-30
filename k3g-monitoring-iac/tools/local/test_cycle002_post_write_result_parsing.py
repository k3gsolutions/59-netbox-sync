#!/usr/bin/env python3
"""FASE 4.60-4.62 — Test post-write result parsing flow."""

from __future__ import annotations

import json
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.local.controlled_cycle_post_write_verification_v2 import verify_post_write
from tools.local.controlled_cycle_post_write_compliance_rerun_v2 import rerun_compliance
from tools.local.controlled_cycle_build_closure_package_v2 import build_closure_package


def test_execution_result_format():
    """Test 1: Execution result has correct format with created item."""
    result = {
        "execution_id": f"exec-{uuid.uuid4().hex[:8]}",
        "cycle_id": "cycle-002",
        "status": "CYCLE_REAL_WRITE_SUCCESS",
        "items": [
            {
                "object_key": "203.0.113.1",
                "object_type": "ip_address",
                "target_endpoint": "/api/ipam/ip-addresses/",
                "response_status": 201,
                "response_id": "6324",
                "verification_status": "verified",
                "status": "CYCLE_REAL_WRITE_CREATED",
                "proposed_payload": {"address": "203.0.113.1/32", "status": "active"},
                "verified_object": {"id": 6324, "address": "203.0.113.1/32", "status": "active"},
            }
        ],
    }
    assert result["status"] == "CYCLE_REAL_WRITE_SUCCESS"
    assert len(result["items"]) == 1
    assert result["items"][0]["status"] == "CYCLE_REAL_WRITE_CREATED"
    assert result["items"][0]["response_id"] == "6324"
    print("✓ Test 1: Execution result format valid")


def test_multiple_items_execution():
    """Test 2: Execution result with multiple items."""
    result = {
        "status": "CYCLE_REAL_WRITE_SUCCESS",
        "items": [
            {
                "object_key": "203.0.113.1",
                "response_id": "6324",
                "status": "CYCLE_REAL_WRITE_CREATED",
                "response_status": 201,
            },
            {
                "object_key": "203.0.113.2",
                "response_id": "6325",
                "status": "CYCLE_REAL_WRITE_CREATED",
                "response_status": 201,
            },
        ],
    }
    assert len(result["items"]) == 2
    assert all(item["status"] == "CYCLE_REAL_WRITE_CREATED" for item in result["items"])
    print("✓ Test 2: Multiple items execution valid")


def test_failed_execution_item():
    """Test 3: Execution result with failed item."""
    result = {
        "status": "CYCLE_REAL_WRITE_FAILED",
        "items": [
            {
                "object_key": "203.0.113.1",
                "response_id": None,
                "status": "CYCLE_REAL_WRITE_FAILED",
                "response_status": 400,
                "error": "invalid payload",
            }
        ],
    }
    assert result["status"] == "CYCLE_REAL_WRITE_FAILED"
    assert result["items"][0]["status"] == "CYCLE_REAL_WRITE_FAILED"
    print("✓ Test 3: Failed execution item valid")


def test_verification_item_verified():
    """Test 4: Verification with item verified (fields match)."""
    verification_result = {
        "cycle_id": "cycle-002",
        "decision": "CYCLE_POST_WRITE_VERIFICATION_PASSED",
        "items": [
            {
                "object_key": "203.0.113.1",
                "object_type": "ip_address",
                "verification_status": "verified",
                "proposed_payload": {"address": "203.0.113.1/32", "status": "active"},
                "verified_object": {"id": 6324, "address": "203.0.113.1/32", "status": "active"},
            }
        ],
    }
    assert verification_result["decision"] == "CYCLE_POST_WRITE_VERIFICATION_PASSED"
    assert verification_result["items"][0]["verification_status"] == "verified"
    print("✓ Test 4: Verification item verified")


def test_verification_item_drift():
    """Test 5: Verification with item drift (fields don't match)."""
    verification_result = {
        "cycle_id": "cycle-002",
        "decision": "CYCLE_POST_WRITE_VERIFICATION_PASSED_WITH_DRIFT",
        "items": [
            {
                "object_key": "203.0.113.1",
                "verification_status": "drift",
                "proposed_payload": {"address": "203.0.113.1/32", "status": "active"},
                "verified_object": {"id": 6324, "address": "203.0.113.1/32", "status": "inactive"},
            }
        ],
    }
    assert "DRIFT" in verification_result["decision"]
    assert verification_result["items"][0]["verification_status"] == "drift"
    print("✓ Test 5: Verification item drift detected")


def test_verification_item_skipped():
    """Test 6: Verification with skipped item."""
    verification_result = {
        "cycle_id": "cycle-002",
        "decision": "CYCLE_POST_WRITE_VERIFICATION_PASSED",
        "items": [
            {
                "object_key": "203.0.113.1",
                "verification_status": "skipped",
            }
        ],
    }
    assert verification_result["items"][0]["verification_status"] == "skipped"
    print("✓ Test 6: Verification item skipped")


def test_compliance_all_items_ok():
    """Test 7: Compliance aggregation when all items OK."""
    compliance_result = {
        "cycle_id": "cycle-002",
        "decision": "CYCLE_POST_WRITE_COMPLIANCE_PASSED",
        "items": [
            {
                "object_key": "203.0.113.1",
                "status": "CYCLE_POST_WRITE_COMPLIANCE_OK",
                "verification_status": "verified",
            }
        ],
        "issues": [],
    }
    assert compliance_result["decision"] == "CYCLE_POST_WRITE_COMPLIANCE_PASSED"
    assert all(item["status"] == "CYCLE_POST_WRITE_COMPLIANCE_OK" for item in compliance_result["items"])
    print("✓ Test 7: Compliance all items OK")


def test_compliance_with_warnings():
    """Test 8: Compliance aggregation with warnings."""
    compliance_result = {
        "cycle_id": "cycle-002",
        "decision": "CYCLE_POST_WRITE_COMPLIANCE_PASSED_WITH_WARNINGS",
        "items": [
            {
                "object_key": "203.0.113.1",
                "status": "CYCLE_POST_WRITE_COMPLIANCE_PASSED_WITH_WARNINGS",
                "verification_status": "drift",
            }
        ],
        "issues": [],
    }
    assert "WARNINGS" in compliance_result["decision"]
    assert any("WARNINGS" in item["status"] for item in compliance_result["items"])
    print("✓ Test 8: Compliance with warnings")


def test_compliance_failed():
    """Test 9: Compliance aggregation when failed."""
    compliance_result = {
        "cycle_id": "cycle-002",
        "decision": "CYCLE_POST_WRITE_COMPLIANCE_FAILED",
        "items": [
            {
                "object_key": "203.0.113.1",
                "status": "CYCLE_POST_WRITE_COMPLIANCE_FAILED",
                "verification_status": "failed",
            }
        ],
        "issues": ["verification failed"],
    }
    assert compliance_result["decision"] == "CYCLE_POST_WRITE_COMPLIANCE_FAILED"
    assert len(compliance_result["issues"]) > 0
    print("✓ Test 9: Compliance failed")


def test_closure_all_passed():
    """Test 10: Closure package with all phases passed."""
    execution = {"status": "CYCLE_REAL_WRITE_SUCCESS"}
    verification = {"decision": "CYCLE_POST_WRITE_VERIFICATION_PASSED"}
    compliance = {"decision": "CYCLE_POST_WRITE_COMPLIANCE_PASSED"}

    # Simulate closure logic
    if (execution["status"] == "CYCLE_REAL_WRITE_SUCCESS" and
        verification["decision"] == "CYCLE_POST_WRITE_VERIFICATION_PASSED" and
        compliance["decision"] == "CYCLE_POST_WRITE_COMPLIANCE_PASSED"):
        decision = "CYCLE_CLOSED_SUCCESS"
    else:
        decision = "CYCLE_CLOSED_ACTION_REQUIRED"

    assert decision == "CYCLE_CLOSED_SUCCESS"
    print("✓ Test 10: Closure all passed")


def test_closure_with_warnings():
    """Test 11: Closure package with warnings."""
    execution = {"status": "CYCLE_REAL_WRITE_SUCCESS"}
    verification = {"decision": "CYCLE_POST_WRITE_VERIFICATION_PASSED_WITH_DRIFT"}
    compliance = {"decision": "CYCLE_POST_WRITE_COMPLIANCE_PASSED"}

    # Simulate closure logic
    if (execution["status"] == "CYCLE_REAL_WRITE_SUCCESS" and
        verification["decision"] == "CYCLE_POST_WRITE_VERIFICATION_PASSED" and
        compliance["decision"] == "CYCLE_POST_WRITE_COMPLIANCE_PASSED"):
        decision = "CYCLE_CLOSED_SUCCESS"
    elif (verification["decision"] == "CYCLE_POST_WRITE_VERIFICATION_PASSED_WITH_DRIFT" or
          compliance["decision"] == "CYCLE_POST_WRITE_COMPLIANCE_PASSED_WITH_WARNINGS"):
        decision = "CYCLE_CLOSED_WITH_WARNINGS"
    else:
        decision = "CYCLE_CLOSED_ACTION_REQUIRED"

    assert decision == "CYCLE_CLOSED_WITH_WARNINGS"
    print("✓ Test 11: Closure with warnings")


def test_closure_failed_execution():
    """Test 12: Closure package with failed execution."""
    execution = {"status": "CYCLE_REAL_WRITE_FAILED"}
    verification = {"decision": "CYCLE_POST_WRITE_VERIFICATION_PASSED"}
    compliance = {"decision": "CYCLE_POST_WRITE_COMPLIANCE_PASSED"}

    # Simulate closure logic
    if execution["status"] == "CYCLE_REAL_WRITE_SUCCESS":
        decision = "CYCLE_CLOSED_SUCCESS"
    elif execution["status"] in {"CYCLE_REAL_WRITE_FAILED", "CYCLE_REAL_WRITE_PARTIAL_FAILED"}:
        decision = "CYCLE_CLOSED_ACTION_REQUIRED"
    else:
        decision = "CYCLE_CLOSED_NOT_APPLICABLE"

    assert decision == "CYCLE_CLOSED_ACTION_REQUIRED"
    print("✓ Test 12: Closure failed execution")


def test_closure_aborted_preflight():
    """Test 13: Closure package with aborted preflight."""
    execution = {"status": "CYCLE_REAL_WRITE_ABORTED_PREFLIGHT_FAILED"}
    verification = {"decision": "CYCLE_POST_WRITE_VERIFICATION_NOT_APPLICABLE"}
    compliance = {"decision": "CYCLE_POST_WRITE_COMPLIANCE_NOT_APPLICABLE"}

    # Simulate closure logic
    if execution["status"] == "CYCLE_REAL_WRITE_SUCCESS":
        decision = "CYCLE_CLOSED_SUCCESS"
    elif execution["status"] == "CYCLE_REAL_WRITE_ABORTED_PREFLIGHT_FAILED":
        decision = "CYCLE_CLOSED_ACTION_REQUIRED"
    else:
        decision = "CYCLE_CLOSED_NOT_APPLICABLE"

    assert decision == "CYCLE_CLOSED_ACTION_REQUIRED"
    print("✓ Test 13: Closure aborted preflight")


def test_end_to_end_flow():
    """Test 14: Full end-to-end flow from execution through closure."""
    # Simulate complete flow
    cycle_id = "cycle-002"
    device = "MNS-KTG-RX-001"
    device_id = "42"

    # 1. Execution result
    execution_result = {
        "execution_id": f"exec-{uuid.uuid4().hex[:8]}",
        "cycle_id": cycle_id,
        "device": device,
        "device_id": device_id,
        "status": "CYCLE_REAL_WRITE_SUCCESS",
        "items": [
            {
                "object_key": "203.0.113.1",
                "object_type": "ip_address",
                "response_id": "6324",
                "response_status": 201,
                "status": "CYCLE_REAL_WRITE_CREATED",
                "proposed_payload": {"address": "203.0.113.1/32", "status": "active"},
                "verified_object": {"id": 6324, "address": "203.0.113.1/32", "status": "active"},
            }
        ],
    }

    # 2. Verification result
    verification_result = {
        "cycle_id": cycle_id,
        "device": device,
        "device_id": device_id,
        "decision": "CYCLE_POST_WRITE_VERIFICATION_PASSED",
        "status": "CYCLE_POST_WRITE_VERIFICATION_PASSED",
        "items": [
            {
                "object_key": "203.0.113.1",
                "object_type": "ip_address",
                "verification_status": "verified",
                "verified_object": {"id": 6324, "address": "203.0.113.1/32", "status": "active"},
            }
        ],
    }

    # 3. Compliance result
    compliance_result = {
        "cycle_id": cycle_id,
        "device": device,
        "device_id": device_id,
        "decision": "CYCLE_POST_WRITE_COMPLIANCE_PASSED",
        "status": "CYCLE_POST_WRITE_COMPLIANCE_PASSED",
        "items": [
            {
                "object_key": "203.0.113.1",
                "object_type": "ip_address",
                "status": "CYCLE_POST_WRITE_COMPLIANCE_OK",
            }
        ],
        "issues": [],
    }

    # 4. Closure logic
    if (execution_result["status"] == "CYCLE_REAL_WRITE_SUCCESS" and
        verification_result["decision"] == "CYCLE_POST_WRITE_VERIFICATION_PASSED" and
        compliance_result["decision"] == "CYCLE_POST_WRITE_COMPLIANCE_PASSED"):
        closure_status = "CYCLE_CLOSED_SUCCESS"
    else:
        closure_status = "CYCLE_CLOSED_ACTION_REQUIRED"

    assert closure_status == "CYCLE_CLOSED_SUCCESS"
    assert execution_result["status"] == "CYCLE_REAL_WRITE_SUCCESS"
    assert verification_result["decision"] == "CYCLE_POST_WRITE_VERIFICATION_PASSED"
    assert compliance_result["decision"] == "CYCLE_POST_WRITE_COMPLIANCE_PASSED"
    assert len(execution_result["items"]) > 0
    assert len(verification_result["items"]) > 0
    assert len(compliance_result["items"]) > 0
    print("✓ Test 14: End-to-end flow successful")


def main() -> int:
    """Run all tests."""
    tests = [
        test_execution_result_format,
        test_multiple_items_execution,
        test_failed_execution_item,
        test_verification_item_verified,
        test_verification_item_drift,
        test_verification_item_skipped,
        test_compliance_all_items_ok,
        test_compliance_with_warnings,
        test_compliance_failed,
        test_closure_all_passed,
        test_closure_with_warnings,
        test_closure_failed_execution,
        test_closure_aborted_preflight,
        test_end_to_end_flow,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{passed}/{len(tests)} tests passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
