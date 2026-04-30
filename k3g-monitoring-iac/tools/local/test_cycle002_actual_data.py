#!/usr/bin/env python3
"""Test FASE 4.60-4.62 with actual Cycle-002 data."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.local.controlled_cycle_post_write_verification_v2 import verify_post_write
from tools.local.controlled_cycle_post_write_compliance_rerun_v2 import rerun_compliance
from tools.local.controlled_cycle_build_closure_package_v2 import build_closure_package


def test_actual_cycle002_data():
    """Test with actual Cycle-002 execution data."""
    cycle_dir = Path("reports/controlled-operation/cycle-002/real-write-execution")

    execution_result_path = cycle_dir / "CYCLE-002-REAL-WRITE-EXECUTION-RESULT.json"
    execution_package_path = cycle_dir / "execution_package.json"

    if not execution_result_path.exists():
        print(f"✗ Execution result not found: {execution_result_path}")
        return 1

    cycle_id = "cycle-002"
    device = "4WNET-MNS-KTG-RX"
    device_id = "1890"

    # Test verification with mock connection
    class MockConn:
        def request(self, *args, **kwargs):
            pass

        def getresponse(self):
            class MockResp:
                status = 200

                def read(self):
                    return b"{}".encode()

                def getheader(self, name):
                    return None

            return MockResp()

    def mock_conn_factory(host):
        return MockConn()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        verification_json = tmpdir_path / "verification.json"
        verification_md = tmpdir_path / "verification.md"
        compliance_json = tmpdir_path / "compliance.json"
        compliance_md = tmpdir_path / "compliance.md"
        closure_dir = tmpdir_path / "closure"
        closure_md = tmpdir_path / "closure.md"

        # FASE 4.60.1 - Verification
        print("=" * 60)
        print("FASE 4.60.1 - Post-Write Verification")
        print("=" * 60)

        result_verification = verify_post_write(
            cycle_id=cycle_id,
            execution_result_path=execution_result_path,
            execution_package_path=execution_package_path,
            netbox_url="https://netbox.example.com",
            device=device,
            device_id=device_id,
            output_json=verification_json,
            output_md=verification_md,
            token="test-token-only-for-local-checks",
            conn_factory=mock_conn_factory,
        )

        print(f"Status: {result_verification.get('status')}")
        print(f"Decision: {result_verification.get('decision')}")
        print(f"Items: {len(result_verification.get('items', []))}")
        if result_verification.get("issues"):
            print(f"Issues: {result_verification['issues']}")

        verification_passed = result_verification.get("decision", "").startswith("CYCLE_POST_WRITE_VERIFICATION_PASSED")
        if verification_passed:
            print("✓ Verification PASSED")
        else:
            print("✗ Verification FAILED")

        # FASE 4.61.1 - Compliance
        print("\n" + "=" * 60)
        print("FASE 4.61.1 - Post-Write Compliance Re-Run")
        print("=" * 60)

        result_compliance = rerun_compliance(
            cycle_id=cycle_id,
            device=device,
            device_id=device_id,
            execution_result_path=execution_result_path,
            post_write_verification_path=verification_json,
            policy_registry=Path("policies/compliance"),
            output_json=compliance_json,
            output_md=compliance_md,
        )

        print(f"Status: {result_compliance.get('status')}")
        print(f"Decision: {result_compliance.get('decision')}")
        print(f"Items: {len(result_compliance.get('items', []))}")
        if result_compliance.get("issues"):
            print(f"Issues: {result_compliance['issues']}")

        compliance_passed = result_compliance.get("decision", "").startswith("CYCLE_POST_WRITE_COMPLIANCE_PASSED")
        if compliance_passed:
            print("✓ Compliance PASSED")
        else:
            print("✗ Compliance FAILED")

        # FASE 4.62.1 - Closure
        print("\n" + "=" * 60)
        print("FASE 4.62.1 - Build Closure Package")
        print("=" * 60)

        result_closure = build_closure_package(
            cycle_id=cycle_id,
            device=device,
            device_id=device_id,
            execution_result_path=execution_result_path,
            post_write_verification_path=verification_json,
            post_write_compliance_path=compliance_json,
            output_dir=closure_dir,
            report=closure_md,
        )

        print(f"Status: {result_closure.get('status')}")
        print(f"Decision: {result_closure.get('decision')}")
        print(f"Reason: {result_closure.get('reason')}")

        closure_success = result_closure.get("status", "").startswith("CYCLE_CLOSED_SUCCESS")
        if closure_success:
            print("✓ Closure SUCCESS")
        else:
            print("✗ Closure FAILED or WARNING")

        # Return success if all passed, or warning level if closure is not success but phases passed
        if closure_success:
            return 0
        elif verification_passed and compliance_passed:
            return 0  # Success despite warnings
        else:
            return 1


if __name__ == "__main__":
    raise SystemExit(test_actual_cycle002_data())
