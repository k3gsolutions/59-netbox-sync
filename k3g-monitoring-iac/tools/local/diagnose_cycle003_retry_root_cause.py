#!/usr/bin/env python3
"""FASE 4.94 — Cycle-003 Retry Root Cause Confirmation.

Diagnose root cause of Cycle-003 real-write execution failure.
Classify failure type and generate report for retry decision.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def load_json_safe(file_path: Path) -> Dict[str, Any]:
    """Load JSON file safely."""
    if not file_path.exists():
        return {}
    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def diagnose_execution_failure(
    execution_result: Dict[str, Any],
    execution_package: Dict[str, Any],
) -> tuple[str, str, Dict[str, Any]]:
    """Diagnose root cause of execution failure.

    Returns: (failure_class, explanation, details)
    """
    details = {}

    # Extract execution info
    status = execution_result.get("status", "")
    items = execution_result.get("items", [])

    # No items executed indicates pre-execution failure
    if not items:
        details["reason"] = "No items in execution result"
        return "UNKNOWN", "No items executed, cannot diagnose", details

    # Check first (and only) item
    first_item = items[0]
    http_error = first_item.get("http_error", {})
    status_code = http_error.get("status_code")
    reason = http_error.get("reason", "")
    error_msg = http_error.get("error", "")

    details["http_error"] = http_error
    details["item_status"] = first_item.get("status")
    details["response_id"] = first_item.get("response_id")
    details["endpoint"] = first_item.get("endpoint")

    # Classify failure
    error_text = f"{reason} {error_msg}".lower()

    # DNS failure
    if any(x in error_text for x in ["name or service not known", "nxdomain", "getaddrinfo failed", "nodename nor servname"]):
        details["root_cause"] = "DNS resolution failed for target hostname"
        details["target_host"] = execution_package.get("netbox_url", "unknown")
        return "DNS_FAILURE", f"DNS resolution failed: {error_msg}", details

    # URL composition/connectivity failure
    if any(x in error_text for x in ["connection refused", "timeout", "connection reset", "unreachable"]):
        return "NETBOX_UNREACHABLE", f"NetBox unreachable: {error_msg}", details

    # Token missing
    if any(x in error_text for x in ["unauthorized", "403", "401", "authentication"]):
        return "TOKEN_MISSING", "Authentication failed (token missing or invalid)", details

    # Payload invalid
    if status_code in [400, 422]:
        return "PAYLOAD_INVALID", f"Payload validation failed: {error_msg}", details

    # Unknown
    return "UNKNOWN", f"Unclassified error: {error_msg}", details


def main() -> int:
    """Run FASE 4.94."""
    parser = argparse.ArgumentParser(
        description="FASE 4.94 — Diagnose Cycle-003 Retry Root Cause"
    )
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--execution-result", type=Path, required=True)
    parser.add_argument("--execution-package", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)

    args = parser.parse_args()

    # Load input files
    exec_result = load_json_safe(args.execution_result)
    exec_package = load_json_safe(args.execution_package)

    if not exec_result:
        print(f"✗ Execution result not found: {args.execution_result}")
        return 1

    if not exec_package:
        print(f"✗ Execution package not found: {args.execution_package}")
        return 1

    # Diagnose
    failure_class, explanation, details = diagnose_execution_failure(exec_result, exec_package)

    # Build result JSON
    result = {
        "diagnosed_at": datetime.utcnow().isoformat() + "+00:00",
        "cycle_id": args.cycle_id,
        "execution_id": exec_result.get("execution_id"),
        "failure_class": failure_class,
        "explanation": explanation,
        "parent_status": exec_result.get("status"),
        "items_executed": len(exec_result.get("items", [])),
        "items_created": exec_result.get("summary", {}).get("created", 0),
        "items_failed": exec_result.get("summary", {}).get("failed", 0),
        "retry_recommendation": "SAFE_TO_RETRY" if failure_class in ["DNS_FAILURE", "NETBOX_UNREACHABLE"] else "REVIEW_REQUIRED",
        "details": details,
    }

    # Write JSON
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    # Write markdown
    markdown = f"""# Cycle-{args.cycle_id} — Retry Root Cause Analysis

## Failure Class
**{failure_class}**

## Explanation
{explanation}

## Summary
- Execution ID: {exec_result.get("execution_id")}
- Parent Status: {exec_result.get("status")}
- Items Executed: {len(exec_result.get("items", []))}
- Items Created: {exec_result.get("summary", {}).get("created", 0)}
- Items Failed: {exec_result.get("summary", {}).get("failed", 0)}

## Details
"""

    if details.get("http_error"):
        markdown += f"""
### HTTP Error
- Status Code: {details["http_error"].get("status_code")}
- Reason: {details["http_error"].get("reason")}
- Error: {details["http_error"].get("error")}
"""

    if details.get("root_cause"):
        markdown += f"""
### Root Cause
- {details["root_cause"]}
- Target: {details.get("target_host", "unknown")}
"""

    markdown += f"""
## Retry Recommendation
**{result["retry_recommendation"]}**

If failure class is DNS_FAILURE or NETBOX_UNREACHABLE:
- Verify NetBox hostname/URL is correct
- Ensure network connectivity to NetBox
- Provide valid NETBOX_WRITE_TOKEN environment variable
- Re-run FASE 4.95 (Retry Package Clone)

## Next Phase
FASE 4.95 — Cycle-003 Retry-001 Package Clone
"""

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(markdown, encoding="utf-8")

    print(f"✓ Root cause diagnosed: {failure_class}")
    print(f"✓ Recommendation: {result['retry_recommendation']}")
    print(f"✓ Result: {args.output_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
