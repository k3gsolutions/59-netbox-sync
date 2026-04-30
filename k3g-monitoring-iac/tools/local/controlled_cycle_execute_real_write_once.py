#!/usr/bin/env python3
"""FASE 4.22 — Controlled Operation Cycle Execute Real Write Once.

First authorized write phase. One-shot execution, no retries, strict preflight.
Token via NETBOX_WRITE_TOKEN environment variable only.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
import urllib.request
import urllib.error


def load_json_safe(file_path: Path) -> Dict[str, Any]:
    """Load JSON file safely."""
    if not file_path.exists():
        return {}
    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def validate_preflight(
    exec_pkg: Dict[str, Any],
    freeze_result: Dict[str, Any],
    token: str,
    provided_phrase: str,
    operator: str,
    netbox_url: str,
    confirm_flag: bool = False,
) -> tuple[bool, list[str]]:
    """Validate 22 preflight checks before real write."""
    issues = []

    # 0. confirm flag present (before other checks)
    if not confirm_flag:
        issues.append("0. --confirm-real-write-once flag required")

    # 1. execution_package exists
    if not exec_pkg.get("execution_id"):
        issues.append("1. execution_package missing execution_id")

    # 2. cycle_id
    if not exec_pkg.get("cycle_id"):
        issues.append("2. cycle_id missing")

    # 3. status prepared
    if exec_pkg.get("status") not in ["prepared", "CYCLE_EXECUTION_PACKAGE_VALID"]:
        issues.append(f"3. status not prepared: {exec_pkg.get('status')}")

    # 4. execution_allowed false
    if exec_pkg.get("execution_allowed") is not False:
        issues.append("4. execution_allowed not false")

    # 5. token_required_in_next_phase
    if not exec_pkg.get("safety_flags", {}).get("requires_final_no_write_freeze"):
        issues.append("5. requires_final_no_write_freeze not true")

    # 6. explicit_confirm_required
    if not exec_pkg.get("safety_flags", {}).get("requires_execution_confirmation"):
        issues.append("6. requires_execution_confirmation not true")

    # 7. one_shot_execution
    if not exec_pkg.get("safety_flags", {}).get("no_automatic_retry"):
        issues.append("7. no_automatic_retry not true")

    # 8. execution_phrase exists
    required_phrase = exec_pkg.get("execution_phrase", "")
    if not required_phrase:
        issues.append("8. execution_phrase missing")

    # 9. phrase matches exactly
    elif provided_phrase != required_phrase:
        issues.append(f"9. execution_phrase mismatch")

    # 10. operator present
    if not operator:
        issues.append("10. operator required")

    # 11. token in environment
    if not token:
        issues.append("11. NETBOX_WRITE_TOKEN not in environment")

    # 12. netbox_url https
    if not netbox_url.startswith("https://"):
        issues.append("12. netbox_url must be https://")

    # 13. freeze result exists
    if not freeze_result.get("decision"):
        issues.append("13. freeze result missing decision")

    # 14. freeze decision ready
    if freeze_result.get("decision") not in [
        "CYCLE_FINAL_NO_WRITE_FREEZE_CLEARED",
    ]:
        issues.append(f"14. freeze not cleared: {freeze_result.get('decision')}")

    # 15. items not empty
    items = exec_pkg.get("items", [])
    if not items:
        issues.append("15. items empty")

    # 16. max_items <= 3
    if len(items) > 3:
        issues.append(f"16. item_count {len(items)} exceeds max 3")

    # 17-21. item validation
    for idx, item in enumerate(items):
        # 17. all methods POST
        if item.get("method") != "POST":
            issues.append(f"17. item[{idx}] method not POST: {item.get('method')}")

        # 18. no PATCH/DELETE
        if item.get("method") in ["PATCH", "DELETE"]:
            issues.append(f"18. item[{idx}] forbidden method: {item.get('method')}")

        # 19. no forbidden endpoints
        endpoint = item.get("target_endpoint", "").lower()
        forbidden = ["/sync", "equipment", "ssh", "netconf"]
        for f in forbidden:
            if f in endpoint:
                issues.append(f"19. item[{idx}] forbidden endpoint: {f}")

        # 20. no token in payload
        payload_str = json.dumps(item.get("proposed_payload", {})).lower()
        blocked = ["token", "password", "secret", "api_key", "bearer"]
        for b in blocked:
            if b in payload_str:
                issues.append(f"20. item[{idx}] blocked keyword in payload: {b}")

    # 22. overall package no secrets
    pkg_str = json.dumps(exec_pkg).lower()
    for b in blocked:
        if b in pkg_str:
            issues.append(f"22. package contains blocked keyword: {b}")

    return len(issues) == 0, issues


def execute_item_post(
    netbox_url: str,
    endpoint: str,
    payload: Dict[str, Any],
    token: str,
) -> tuple[bool, Any]:
    """Execute POST for single item (no logging of token)."""
    url = f"{netbox_url}{endpoint}"

    # Prepare request
    json_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=json_data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Token {token}",  # Token header never logged
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            response_data = json.loads(response.read().decode("utf-8"))
            return True, response_data
    except urllib.error.HTTPError as e:
        try:
            error_data = json.loads(e.read().decode("utf-8"))
        except Exception:
            error_data = {"status_code": e.code, "reason": e.reason}
        return False, error_data
    except Exception as e:
        return False, {"error": str(e)}


def verify_item_get(
    netbox_url: str,
    endpoint: str,
    response_id: Any,
    token: str,
) -> tuple[bool, Any]:
    """Verify created item via GET (verification only)."""
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
    """Run FASE 4.22."""
    parser = argparse.ArgumentParser(
        description="FASE 4.22 — Execute Real Write Once"
    )
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--execution-package", type=Path, required=True)
    parser.add_argument("--operator", required=True)
    parser.add_argument("--confirm-execution-phrase", required=True)
    parser.add_argument(
        "--confirm-real-write-once",
        action="store_true",
        help="Must be present to allow real write",
    )
    parser.add_argument("--netbox-url", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    parser.add_argument("--freeze-result", type=Path, default=None)

    args = parser.parse_args()

    # Get token from environment (never via argument)
    token = os.environ.get("NETBOX_WRITE_TOKEN", "")

    # Load execution package
    exec_pkg = load_json_safe(args.execution_package)
    if not exec_pkg:
        print(f"✗ Execution package not found: {args.execution_package}")
        return 1

    # Load freeze result (default path if not provided)
    freeze_path = args.freeze_result
    if not freeze_path:
        freeze_path = Path(
            f"k3g-monitoring-iac/reports/controlled-operation/{args.cycle_id}/real-write-execution/{args.cycle_id}-final-no-write-freeze-check.json"
        )
    freeze_result = load_json_safe(freeze_path) if freeze_path else {}

    # Validate all 22 preflight checks
    is_ready, issues = validate_preflight(
        exec_pkg,
        freeze_result,
        token,
        args.confirm_execution_phrase,
        args.operator,
        args.netbox_url,
        args.confirm_real_write_once,
    )

    if not is_ready:
        # Preflight failed - abort before any write
        status = "CYCLE_REAL_WRITE_ABORTED_PREFLIGHT_FAILED"
        result = {
            "execution_id": exec_pkg.get("execution_id", "unknown"),
            "cycle_id": args.cycle_id,
            "status": status,
            "started_at": datetime.utcnow().isoformat() + "+00:00",
            "finished_at": datetime.utcnow().isoformat() + "+00:00",
            "operator": args.operator,
            "no_write_attempted": True,
            "one_shot_execution": True,
            "retry_attempted": False,
            "rollback_attempted": False,
            "token_logged": False,
            "token_saved": False,
            "items": [],
            "preflight_issues": issues,
            "safety_confirmations": {
                "token_not_logged": True,
                "token_not_saved": True,
                "no_sync_called": True,
                "no_patch_delete": True,
                "no_equipment_access": True,
                "one_shot_only": True,
            },
        }

        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        markdown = f"""# Cycle-{args.cycle_id} — Real Write Execution Aborted

## Status
✗ CYCLE_REAL_WRITE_ABORTED_PREFLIGHT_FAILED

## Reason
Preflight validation failed. No write attempted.

## Issues
"""
        for issue in issues:
            markdown += f"- {issue}\n"

        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(markdown, encoding="utf-8")

        print(f"✗ Preflight failed: {len(issues)} issues")
        return 1

    # Preflight passed - execute writes
    items = exec_pkg.get("items", [])
    executed_items = []
    created_count = 0
    failed_count = 0

    start_time = datetime.utcnow().isoformat() + "+00:00"

    for item in items:
        endpoint = item.get("target_endpoint", "")
        payload = item.get("proposed_payload", {})
        item_id = item.get("item_id", "unknown")

        # Execute POST
        post_ok, post_result = execute_item_post(
            args.netbox_url, endpoint, payload, token
        )

        if not post_ok:
            # First failure stops execution (no retries)
            executed_items.append(
                {
                    "item_id": item_id,
                    "approval_id": item.get("approval_id"),
                    "object_type": item.get("object_type"),
                    "object_key": item.get("object_key"),
                    "endpoint": endpoint,
                    "status": "CYCLE_REAL_WRITE_FAILED",
                    "http_error": post_result,
                }
            )
            failed_count += 1
            break  # Stop on first failure

        # Verify via GET
        response_id = post_result.get("id")
        if not response_id:
            executed_items.append(
                {
                    "item_id": item_id,
                    "approval_id": item.get("approval_id"),
                    "object_type": item.get("object_type"),
                    "object_key": item.get("object_key"),
                    "endpoint": endpoint,
                    "status": "CYCLE_REAL_WRITE_CREATED_UNVERIFIED",
                    "response_id": None,
                }
            )
            created_count += 1
            continue

        verify_ok, verify_result = verify_item_get(
            args.netbox_url, endpoint, response_id, token
        )

        if verify_ok:
            executed_items.append(
                {
                    "item_id": item_id,
                    "approval_id": item.get("approval_id"),
                    "object_type": item.get("object_type"),
                    "object_key": item.get("object_key"),
                    "endpoint": endpoint,
                    "response_id": response_id,
                    "status": "CYCLE_REAL_WRITE_CREATED",
                    "verification_status": "verified",
                }
            )
            created_count += 1
        else:
            executed_items.append(
                {
                    "item_id": item_id,
                    "approval_id": item.get("approval_id"),
                    "object_type": item.get("object_type"),
                    "object_key": item.get("object_key"),
                    "endpoint": endpoint,
                    "response_id": response_id,
                    "status": "CYCLE_REAL_WRITE_CREATED",
                    "verification_status": "verification_failed",
                    "verification_error": verify_result,
                }
            )
            created_count += 1

    # Determine final status
    finish_time = datetime.utcnow().isoformat() + "+00:00"
    if failed_count > 0:
        status = "CYCLE_REAL_WRITE_PARTIAL_FAILED"
    elif created_count == len(items):
        status = "CYCLE_REAL_WRITE_SUCCESS"
    else:
        status = "CYCLE_REAL_WRITE_FAILED"

    # Build result
    result = {
        "execution_id": exec_pkg.get("execution_id"),
        "cycle_id": args.cycle_id,
        "device": exec_pkg.get("device"),
        "device_id": exec_pkg.get("device_id"),
        "operator": args.operator,
        "started_at": start_time,
        "finished_at": finish_time,
        "status": status,
        "no_write_attempted": False,
        "one_shot_execution": True,
        "retry_attempted": False,
        "rollback_attempted": False,
        "token_logged": False,
        "token_saved": False,
        "items": executed_items,
        "summary": {
            "total_items": len(items),
            "created": created_count,
            "failed": failed_count,
        },
        "safety_confirmations": {
            "token_not_logged": True,
            "token_not_saved": True,
            "no_sync_called": True,
            "no_patch_delete": True,
            "no_equipment_access": True,
            "one_shot_only": True,
        },
    }

    # Write JSON
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    # Write markdown
    markdown = f"""# Cycle-{args.cycle_id} — Real Write Execution Result

## Status
{("✓" if status == "CYCLE_REAL_WRITE_SUCCESS" else "⚠" if "PARTIAL" in status else "✗")} {status}

## Summary
- Operator: {args.operator}
- Device: {exec_pkg.get('device')}
- Started: {start_time}
- Finished: {finish_time}
- Total Items: {len(items)}
- Created: {created_count}
- Failed: {failed_count}

## Items Executed
"""

    for item in executed_items:
        markdown += f"""
### {item.get('item_id')}
- Approval: {item.get('approval_id')}
- Type: {item.get('object_type')}
- Key: {item.get('object_key')}
- Endpoint: {item.get('endpoint')}
- Response ID: {item.get('response_id', 'N/A')}
- Status: {item.get('status')}
- Verification: {item.get('verification_status', 'N/A')}
"""

    markdown += """
## Safety Confirmations
- ✓ Token not logged
- ✓ Token not saved
- ✓ No /sync called
- ✓ No PATCH/DELETE
- ✓ No equipment access
- ✓ One-shot only

## Next Phase
FASE 4.23 — Post-Write Verification
"""

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(markdown, encoding="utf-8")

    print(f"✓ Real write execution: {status}")
    print(f"✓ Created: {created_count}/{len(items)}")
    print(f"✓ Failed: {failed_count}/{len(items)}")
    print(f"✓ Result: {args.output_json}")

    return 0 if status == "CYCLE_REAL_WRITE_SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
