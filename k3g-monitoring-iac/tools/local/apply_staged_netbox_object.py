#!/usr/bin/env python3
"""Apply staged NetBox object (first real write, dry-run by default)."""

import argparse
import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple
import hashlib

try:
    import urllib.request
    import urllib.error
except ImportError:
    print("Error: Standard library urllib not available", file=sys.stderr)
    sys.exit(1)


def load_apply_plan(file_path: str) -> Dict:
    """Load ApplyPlan JSON."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ValueError(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")


def validate_prerequisites(plan: Dict) -> Tuple[bool, list]:
    """Validate ApplyPlan prerequisites."""
    errors = []

    # readiness_status
    if plan.get("readiness_status") != "ready":
        errors.append(f"readiness_status must be 'ready' (got: {plan.get('readiness_status')})")

    # action
    if plan.get("action") != "safe_create_staged":
        errors.append(f"action must be 'safe_create_staged' (got: {plan.get('action')})")

    # object_type
    if plan.get("object_type") != "interface":
        errors.append(f"object_type must be 'interface' (got: {plan.get('object_type')})")

    # method
    if plan.get("method") != "POST":
        errors.append(f"method must be 'POST' (got: {plan.get('method')})")

    # Blocked reasons
    if plan.get("blocked_reasons"):
        errors.append(f"ApplyPlan has blocked reasons: {', '.join(plan.get('blocked_reasons'))}")

    # Payload validation
    payload_str = json.dumps(plan.get("staged_payload", {}))
    forbidden = ["password", "token", "secret", "api_key", "ssh"]
    if any(p in payload_str.lower() for p in forbidden):
        errors.append("Payload contains forbidden patterns (secrets)")

    return len(errors) == 0, errors


def check_token_provided() -> Tuple[bool, str]:
    """Check write token from environment."""
    token = os.environ.get("NETBOX_WRITE_TOKEN")
    if not token:
        return False, "NETBOX_WRITE_TOKEN environment variable not set"
    return True, token


def preflight_check(
    netbox_url: str,
    token: str,
    device_id: int,
    object_key: str
) -> Tuple[bool, Optional[Dict]]:
    """Check if object already exists via GET."""
    # Build query
    query = f"?device_id={device_id}&name={object_key}"
    endpoint = f"{netbox_url}/api/dcim/interfaces/{query}"

    try:
        req = urllib.request.Request(
            endpoint,
            headers={
                "Authorization": f"Token {token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )
        req.get_method = lambda: "GET"

        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            results = data.get("results", [])
            if results:
                return False, results[0]  # Object exists
            return True, None  # Object doesn't exist
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return True, None  # Not found (OK)
        else:
            raise ValueError(f"NetBox API error ({e.code}): {e.reason}")
    except Exception as e:
        raise ValueError(f"Preflight check failed: {e}")


def apply_staged_object(
    netbox_url: str,
    token: str,
    payload: Dict,
    dry_run: bool = True
) -> Tuple[bool, Dict]:
    """Apply staged object to NetBox via POST."""
    if dry_run:
        return True, {
            "status_code": 201,
            "id": None,
            "message": "DRY RUN: Would create interface",
            "dry_run": True
        }

    # Real POST
    endpoint = f"{netbox_url}/api/dcim/interfaces/"
    payload_json = json.dumps(payload).encode("utf-8")

    try:
        req = urllib.request.Request(
            endpoint,
            data=payload_json,
            headers={
                "Authorization": f"Token {token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )
        req.get_method = lambda: "POST"

        with urllib.request.urlopen(req) as response:
            result_data = json.loads(response.read().decode())
            return True, {
                "status_code": response.status,
                "id": result_data.get("id"),
                "message": f"Created interface (id={result_data.get('id')})",
                "dry_run": False,
                "response": result_data
            }
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        return False, {
            "status_code": e.code,
            "message": f"NetBox error ({e.code}): {error_body}",
            "dry_run": False
        }
    except Exception as e:
        return False, {
            "status_code": None,
            "message": f"Error: {e}",
            "dry_run": False
        }


def render_apply_result(
    plan: Dict,
    result: Dict,
    operator: str,
    dry_run: bool
) -> str:
    """Render apply result as Markdown."""
    lines = []
    approval_id = plan.get("approval_id", "unknown")[:8]
    device = plan.get("device")
    object_key = plan.get("object_key")

    # Header
    lines.append(f"# Staged Apply Result — {approval_id}")
    lines.append("")
    lines.append(f"**Device:** {device}")
    lines.append(f"**Object:** {plan.get('object_type')} / {object_key}")
    lines.append(f"**Operator:** {operator}")
    lines.append(f"**Timestamp:** {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"**Dry-Run:** {dry_run}")
    lines.append("")

    # Result
    status_code = result.get("status_code")
    lines.append("## Result")
    lines.append("")
    if dry_run:
        lines.append("🟡 **DRY RUN** (no actual write)")
    elif status_code == 201:
        lines.append("🟢 **SUCCESS** (201 Created)")
        lines.append(f"- NetBox ID: {result.get('id')}")
        lines.append(f"- Message: {result.get('message')}")
    else:
        lines.append(f"❌ **FAILED** ({status_code})")
        lines.append(f"- Message: {result.get('message')}")
    lines.append("")

    # Next Steps
    lines.append("## Next Steps")
    lines.append("")
    if dry_run:
        lines.append("1. Review this dry-run result")
        lines.append("2. If OK, execute with --confirm-real-write")
        lines.append("3. Provide NETBOX_WRITE_TOKEN environment variable")
    elif status_code == 201:
        lines.append("1. ✅ Interface created as staged in NetBox")
        lines.append("2. ✅ Requires manual activation")
        lines.append("3. Re-run compliance to validate")
        lines.append("4. Compare before/after")
    else:
        lines.append("1. ❌ Apply failed")
        lines.append("2. Review error message above")
        lines.append("3. Do not retry without investigation")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Apply staged NetBox object (first real write, dry-run by default)"
    )
    parser.add_argument("--plan", required=True, help="ApplyPlan JSON file")
    parser.add_argument("--netbox-url", required=True, help="NetBox base URL")
    parser.add_argument("--confirm-approval-id", required=True, help="Approval ID confirmation")
    parser.add_argument("--operator", required=True, help="Operator name")
    parser.add_argument(
        "--confirm-real-write",
        action="store_true",
        help="EXPLICIT confirmation for real write (without this, only dry-run)"
    )
    parser.add_argument("--output-dir", help="Output directory for result")
    args = parser.parse_args()

    try:
        # Load ApplyPlan
        plan = load_apply_plan(args.plan)

        # Validate approval_id
        if plan.get("approval_id")[:8] != args.confirm_approval_id[:8]:
            raise ValueError(
                f"Approval ID mismatch: "
                f"plan={plan.get('approval_id')[:8]}, "
                f"confirmed={args.confirm_approval_id[:8]}"
            )

        # Validate prerequisites
        valid, errors = validate_prerequisites(plan)
        if not valid:
            print("❌ Validation failed:")
            for error in errors:
                print(f"  - {error}")
            return 1

        # Determine if real write or dry-run
        dry_run = not args.confirm_real_write

        if not dry_run:
            print("")
            print("=" * 70)
            print("REAL NETBOX WRITE ENABLED FOR ONE STAGED OBJECT ONLY")
            print("=" * 70)
            print("")

            # Check token
            has_token, token_or_error = check_token_provided()
            if not has_token:
                print(f"❌ {token_or_error}", file=sys.stderr)
                return 1
            token = token_or_error

            # Preflight check
            print("Running preflight check...")
            object_exists, existing = preflight_check(
                args.netbox_url,
                token,
                plan.get("device_id"),
                plan.get("object_key")
            )

            if not object_exists:
                print(f"❌ Object already exists in NetBox: {existing}")
                return 1

            print("✓ Preflight check passed")
            print("")

            # Apply
            print("Applying staged object...")
            success, result = apply_staged_object(
                args.netbox_url,
                token,
                plan.get("staged_payload"),
                dry_run=False
            )

            if not success:
                print(f"❌ Apply failed: {result.get('message')}", file=sys.stderr)
                return 1

            print(f"✓ Apply successful: {result.get('message')}")

        else:
            # Dry-run
            print("Running in DRY-RUN mode (no write)")
            print("To execute real write, provide --confirm-real-write flag")
            print("and set NETBOX_WRITE_TOKEN environment variable")
            print("")
            success, result = apply_staged_object(
                args.netbox_url,
                "fake-token",
                plan.get("staged_payload"),
                dry_run=True
            )

        # Render result
        markdown = render_apply_result(plan, result, args.operator, dry_run)

        # Save result
        output_dir = Path(args.output_dir) if args.output_dir else Path("reports/pilot-device-compliance/approvals/applied")
        output_dir.mkdir(parents=True, exist_ok=True)

        approval_id = plan.get("approval_id", "unknown")[:8]
        result_file = output_dir / f"apply-result-{approval_id}.md"
        with open(result_file, "w", encoding="utf-8") as f:
            f.write(markdown)

        print(f"✓ Result saved: {result_file}")
        print("")
        print(markdown)

        return 0 if success else 1

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
