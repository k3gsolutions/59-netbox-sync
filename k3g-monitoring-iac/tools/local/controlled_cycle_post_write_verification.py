#!/usr/bin/env python3
"""FASE 4.23 — Controlled Operation Cycle Post-Write Verification.

Verify created objects via GET only. No writes.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
import urllib.request


def load_json_safe(file_path: Path) -> Dict[str, Any]:
    """Load JSON file safely."""
    if not file_path.exists():
        return {}
    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def verify_item_get(
    netbox_url: str,
    endpoint: str,
    response_id: Any,
    token: str,
) -> tuple[bool, Any]:
    """Verify item via GET only."""
    url = f"{netbox_url}{endpoint}{response_id}/"

    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Accept": "application/json",
            "Authorization": f"Token {token}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            response_data = json.loads(response.read().decode("utf-8"))
            return True, response_data
    except Exception as e:
        return False, {"error": str(e)}


def main() -> int:
    """Run FASE 4.23."""
    parser = argparse.ArgumentParser(
        description="FASE 4.23 — Post-Write Verification"
    )
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--execution-result", type=Path, required=True)
    parser.add_argument("--execution-package", type=Path, required=True)
    parser.add_argument("--netbox-url", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)

    args = parser.parse_args()

    # Get token
    token = os.environ.get("NETBOX_WRITE_TOKEN", "")

    # Load execution result
    exec_result = load_json_safe(args.execution_result)
    exec_pkg = load_json_safe(args.execution_package)

    # Check if execution was aborted (preflight failed)
    if "ABORTED" in exec_result.get("status", ""):
        status = "CYCLE_POST_WRITE_VERIFICATION_NOT_APPLICABLE"
        result = {
            "cycle_id": args.cycle_id,
            "device": args.device,
            "status": status,
            "verified_at": datetime.utcnow().isoformat() + "+00:00",
            "summary": {
                "total_items": 0,
                "verified": 0,
                "drift": 0,
                "failed": 0,
                "skipped": len(exec_result.get("items", [])),
            },
            "items": [],
        }

        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        markdown = f"""# Cycle-{args.cycle_id} — Post-Write Verification

## Status
⊘ CYCLE_POST_WRITE_VERIFICATION_NOT_APPLICABLE

Execution was aborted. No verification needed.
"""
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(markdown, encoding="utf-8")

        return 0

    # Verify each created item
    executed_items = exec_result.get("items", [])
    verified_items = []
    verified_count = 0
    drift_count = 0
    failed_count = 0

    for item in executed_items:
        response_id = item.get("response_id")
        if not response_id:
            verified_items.append(
                {
                    "item_id": item.get("item_id"),
                    "status": "CYCLE_VERIFICATION_SKIPPED",
                    "reason": "no_response_id",
                }
            )
            continue

        endpoint = item.get("endpoint", "")
        verify_ok, verify_result = verify_item_get(
            args.netbox_url, endpoint, response_id, token
        )

        if not verify_ok:
            verified_items.append(
                {
                    "item_id": item.get("item_id"),
                    "response_id": response_id,
                    "status": "CYCLE_VERIFICATION_FAILED",
                    "error": verify_result,
                }
            )
            failed_count += 1
            continue

        # Check basic fields
        expected_payload = None
        for pkg_item in exec_pkg.get("items", []):
            if pkg_item.get("item_id") == item.get("item_id"):
                expected_payload = pkg_item.get("proposed_payload", {})
                break

        drift = []
        if expected_payload:
            for key, expected_value in expected_payload.items():
                actual_value = verify_result.get(key)
                if actual_value != expected_value:
                    drift.append({
                        "field": key,
                        "expected": expected_value,
                        "actual": actual_value,
                    })

        if drift:
            verified_items.append(
                {
                    "item_id": item.get("item_id"),
                    "response_id": response_id,
                    "status": "CYCLE_VERIFIED_WITH_DRIFT",
                    "drift_fields": drift,
                }
            )
            drift_count += 1
        else:
            verified_items.append(
                {
                    "item_id": item.get("item_id"),
                    "response_id": response_id,
                    "status": "CYCLE_VERIFIED_OK",
                }
            )
            verified_count += 1

    # Determine overall status
    if failed_count > 0:
        status = "CYCLE_POST_WRITE_VERIFICATION_FAILED"
    elif drift_count > 0:
        status = "CYCLE_POST_WRITE_VERIFICATION_PASSED_WITH_DRIFT"
    else:
        status = "CYCLE_POST_WRITE_VERIFICATION_PASSED"

    # Build result
    result = {
        "cycle_id": args.cycle_id,
        "device": args.device,
        "device_id": args.device_id,
        "status": status,
        "verified_at": datetime.utcnow().isoformat() + "+00:00",
        "summary": {
            "total_items": len(executed_items),
            "verified": verified_count,
            "drift": drift_count,
            "failed": failed_count,
            "skipped": 0,
        },
        "items": verified_items,
    }

    # Write JSON
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    # Write markdown
    emoji = "✓" if status == "CYCLE_POST_WRITE_VERIFICATION_PASSED" else "⚠" if "DRIFT" in status else "✗"
    markdown = f"""# Cycle-{args.cycle_id} — Post-Write Verification

## Status
{emoji} {status}

## Summary
- Device: {args.device}
- Total Items: {len(executed_items)}
- Verified OK: {verified_count}
- Drift: {drift_count}
- Failed: {failed_count}

## Verification Results
"""

    for item in verified_items:
        markdown += f"""
### {item.get('item_id')}
- Status: {item.get('status')}
"""
        if item.get('drift_fields'):
            markdown += "- Drift Fields:\n"
            for drift in item.get('drift_fields', []):
                markdown += f"  - {drift.get('field')}: {drift.get('expected')} → {drift.get('actual')}\n"

    markdown += """
## Next Phase
FASE 4.24 — Compliance Re-Run
"""

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(markdown, encoding="utf-8")

    print(f"✓ Post-write verification: {status}")
    print(f"✓ Verified: {verified_count}")
    print(f"✓ Drift: {drift_count}")
    print(f"✓ Failed: {failed_count}")

    return 0 if status == "CYCLE_POST_WRITE_VERIFICATION_PASSED" else (0 if "DRIFT" in status else 1)


if __name__ == "__main__":
    raise SystemExit(main())
