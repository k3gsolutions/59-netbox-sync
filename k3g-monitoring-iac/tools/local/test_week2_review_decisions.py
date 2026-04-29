#!/usr/bin/env python3
"""Test Week 2 review decision routes and services (FASE 2.35)."""

from __future__ import annotations

import json
import tempfile
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from webui.services.week2_decision_handler import Week2Decision, save_decision, load_decisions
from tools.local.validate_week2_review_decisions import validate_week2_review_decisions


def test_week2_decision_validation() -> None:
    """Test Week2Decision validation."""
    print("TEST: Week2Decision validation")

    # Valid approval decision
    d1 = Week2Decision(
        item_id="item-1",
        reviewer="alice",
        decision="approve_for_approval_record",
        reason="Item valid",
        approval_record_allowed=True,
    )
    valid, msg = d1.validate()
    assert valid, f"Expected valid, got: {msg}"
    print("  ✓ Valid approval decision")

    # Invalid — missing reviewer
    d2 = Week2Decision(
        item_id="item-2",
        reviewer="",
        decision="approve_for_approval_record",
        approval_record_allowed=True,
    )
    valid, msg = d2.validate()
    assert not valid and "reviewer" in msg, f"Expected reviewer error, got: {msg}"
    print("  ✓ Catches missing reviewer")

    # Invalid — approve without flag
    d3 = Week2Decision(
        item_id="item-3",
        reviewer="alice",
        decision="approve_for_approval_record",
        approval_record_allowed=False,
    )
    valid, msg = d3.validate()
    assert not valid and "approval_record_allowed" in msg, f"Expected flag error, got: {msg}"
    print("  ✓ Catches missing approval_record_allowed flag")

    # Valid request_changes
    d4 = Week2Decision(
        item_id="item-4",
        reviewer="bob",
        decision="request_changes",
        notes="Needs adjustment",
    )
    valid, msg = d4.validate()
    assert valid, f"Expected valid request_changes, got: {msg}"
    print("  ✓ Valid request_changes decision")

    # Invalid — request_changes without notes
    d5 = Week2Decision(
        item_id="item-5",
        reviewer="bob",
        decision="request_changes",
    )
    valid, msg = d5.validate()
    assert not valid and "notes" in msg, f"Expected notes error, got: {msg}"
    print("  ✓ Catches missing notes in request_changes")


def test_save_and_load_decisions() -> None:
    """Test saving and loading decisions."""
    print("\nTEST: Save and load decisions")

    with tempfile.TemporaryDirectory() as tmpdir:
        review_dir = Path(tmpdir) / "week2-review"

        # Save decision
        d = Week2Decision(
            item_id="draft-1",
            reviewer="charlie",
            decision="approve_for_approval_record",
            reason="Verified",
            approval_record_allowed=True,
        )
        success, msg = save_decision(d, review_dir)
        assert success, f"Expected save success, got: {msg}"
        print("  ✓ Decision saved")

        # Check CSV exists
        csv_path = review_dir / "week2-review-decisions.csv"
        assert csv_path.exists(), "CSV file not created"
        print("  ✓ CSV file created")

        # Check audit JSON exists
        audit_dir = review_dir / "audit"
        audit_files = list(audit_dir.glob("*.json")) if audit_dir.exists() else []
        assert len(audit_files) > 0, "Audit file not created"
        print("  ✓ Audit JSON created")

        # Load decisions
        decisions = load_decisions(review_dir)
        assert len(decisions) == 1, f"Expected 1 decision, got {len(decisions)}"
        assert decisions[0]["item_id"] == "draft-1"
        print("  ✓ Decisions loaded from CSV")


def test_validate_decisions() -> None:
    """Test decision validation."""
    print("\nTEST: Validate decisions")

    with tempfile.TemporaryDirectory() as tmpdir:
        review_dir = Path(tmpdir) / "week2-review"

        # Save valid decision
        d = Week2Decision(
            item_id="item-valid",
            reviewer="dave",
            decision="approve_for_approval_record",
            reason="OK",
            approval_record_allowed=True,
        )
        save_decision(d, review_dir)

        # Validate
        all_valid, report = validate_week2_review_decisions(review_dir)
        assert all_valid, f"Expected valid decisions, got errors: {report['errors']}"
        assert report["valid"] == 1
        assert report["status"] == "valid"
        print("  ✓ Valid decisions pass validation")


def test_security_checks() -> None:
    """Test security properties."""
    print("\nTEST: Security checks")

    d = Week2Decision(
        item_id="secure-item",
        reviewer="eve",
        decision="reject",
        reason="Security check",
    )

    # Decision object must not have NetBox fields
    assert not hasattr(d, "netbox_write")
    assert not hasattr(d, "token")
    print("  ✓ No NetBox/token fields in decision")

    # Validated decision must have security assertions
    with tempfile.TemporaryDirectory() as tmpdir:
        review_dir = Path(tmpdir) / "week2-review"
        save_decision(d, review_dir)

        # Check audit for security flags
        audit_dir = review_dir / "audit"
        audit_files = list(audit_dir.glob("*.json"))
        assert len(audit_files) > 0
        with open(audit_files[0]) as f:
            audit = json.load(f)
        assert audit["security"]["no_netbox_write"] == True
        assert audit["security"]["no_token"] == True
        assert audit["security"]["no_apply"] == True
        assert audit["security"]["no_approval_record_auto"] == True
        print("  ✓ Audit contains security flags")


def main() -> int:
    """Run tests."""
    try:
        test_week2_decision_validation()
        test_save_and_load_decisions()
        test_validate_decisions()
        test_security_checks()

        print("\n" + "="*60)
        print("✓ All Week2 decision tests pass")
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


def test_fastapi_routes() -> None:
    """Test FastAPI routes (FASE 2.35)."""
    print("\nTEST: FastAPI week2 review routes")

    try:
        from fastapi.testclient import TestClient
    except Exception as e:
        print(f"  ⊘ Skipped (TestClient unavailable: {e})")
        return

    from webui.app import app

    client = TestClient(app)
    device = "4WNET-MNS-KTG-RX"

    # GET /service-engagement/{device}/week2-review/items
    resp = client.get(f"/service-engagement/{device}/week2-review/items")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert "items" in data
    assert "count" in data
    print("  ✓ GET /service-engagement/{device}/week2-review/items returns 200")

    # GET non-existent item
    resp = client.get(f"/service-engagement/{device}/week2-review/items/nonexistent-item")
    assert resp.status_code == 404, f"Expected 404 for nonexistent item, got {resp.status_code}"
    print("  ✓ GET non-existent item returns 404")

    # POST decision without reviewer
    resp = client.post(
        f"/service-engagement/{device}/week2-review/items/test-item/decision",
        json={"decision": "approve_for_approval_record"},
    )
    assert resp.status_code == 400, f"Expected 400 for missing reviewer, got {resp.status_code}"
    data = resp.json()
    assert "error" in data
    assert "reviewer" in data["error"]
    print("  ✓ POST decision without reviewer returns 400")

    # POST decision without decision field
    resp = client.post(
        f"/service-engagement/{device}/week2-review/items/test-item/decision",
        json={"reviewer": "test_user"},
    )
    assert resp.status_code == 400, f"Expected 400 for missing decision, got {resp.status_code}"
    data = resp.json()
    assert "error" in data
    print("  ✓ POST decision without decision field returns 400")

    print("  ✓ All FastAPI route tests pass")

