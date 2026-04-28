#!/usr/bin/env python3
"""Apply batch staged NetBox objects (controlled, item-by-item)."""

import argparse
import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import urllib.request
    import urllib.error
except ImportError:
    print("Error: Standard library urllib not available", file=sys.stderr)
    sys.exit(1)


def load_batch_plan(file_path: str) -> Dict:
    """Load BatchApplyPlan JSON."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ValueError(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")


def load_apply_plan(file_path: str) -> Dict:
    """Load ApplyPlan JSON."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ValueError(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")


def validate_batch_plan_for_apply(
    batch_plan: Dict,
    expected_device: str,
    expected_device_id: int,
    allowed_object_keys: List[str],
) -> Tuple[bool, List[str]]:
    """Validate batch plan before applying."""
    errors: List[str] = []

    if batch_plan.get("device") != expected_device:
        errors.append(
            f"Batch device mismatch: expected {expected_device}, got {batch_plan.get('device')}"
        )
    if batch_plan.get("device_id") != expected_device_id:
        errors.append(
            f"Batch device_id mismatch: expected {expected_device_id}, got {batch_plan.get('device_id')}"
        )

    items = batch_plan.get("items", [])
    if not items:
        errors.append("Batch has no items")

    for i, item in enumerate(items):
        object_key = item.get("object_key")
        if not object_key:
            errors.append(f"Item {i}: CRITICAL missing object_key")
            continue

        if object_key not in allowed_object_keys:
            errors.append(f"Item {i}: object_key not in allowlist: {object_key}")

        # Check critical fields
        critical_fields = ["method", "target_endpoint", "device_id"]
        for field in critical_fields:
            if item.get(field) is None:
                errors.append(f"Item {i}: CRITICAL missing '{field}'")

        # Check method and endpoint values
        if item.get("method") != "POST":
            errors.append(f"Item {i}: method must be POST (got: {item.get('method')})")
        if item.get("target_endpoint") != "/api/dcim/interfaces/":
            errors.append(f"Item {i}: unexpected target_endpoint: {item.get('target_endpoint')}")

        if item.get("device") != expected_device:
            errors.append(
                f"Item {i}: device mismatch: {item.get('device')} vs expected {expected_device}"
            )

        if item.get("device_id") != expected_device_id:
            errors.append(
                f"Item {i}: device_id mismatch: {item.get('device_id')} vs expected {expected_device_id}"
            )

        staged_payload = item.get("staged_payload")
        if not isinstance(staged_payload, dict) or not staged_payload:
            errors.append(f"Item {i}: CRITICAL missing or empty staged_payload")
            continue

        # Validate payload completeness
        payload_required = ["device", "name", "type"]
        for field in payload_required:
            if staged_payload.get(field) is None:
                errors.append(f"Item {i}: payload.{field} is None or missing")

        payload_device = staged_payload.get("device")
        payload_name = staged_payload.get("name")

        if payload_device != expected_device_id:
            errors.append(
                f"Item {i}: staged_payload.device mismatch: {payload_device} vs expected {expected_device_id}"
            )
        if payload_name != object_key:
            errors.append(
                f"Item {i}: staged_payload.name mismatch: {payload_name} vs object_key {object_key}"
            )

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
    object_key: str,
) -> Tuple[bool, Optional[Dict]]:
    """Check if object already exists via GET."""
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


def check_tags_exist(
    netbox_url: str,
    token: str,
    tag_names: List[str],
) -> Tuple[bool, List[str]]:
    """Check if tags exist in NetBox."""
    if not tag_names:
        return True, []

    missing = []
    for tag_name in tag_names:
        try:
            endpoint = f"{netbox_url}/api/extras/tags/?name={tag_name}"
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
                if not results:
                    missing.append(tag_name)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                missing.append(tag_name)
            else:
                raise ValueError(f"Tag check failed for '{tag_name}' ({e.code}): {e.reason}")
        except Exception as e:
            raise ValueError(f"Tag check failed for '{tag_name}': {e}")

    return len(missing) == 0, missing


def extract_tag_names(payload: Dict) -> List[str]:
    """Extract tag names from staged payload."""
    tags = payload.get("tags", [])
    tag_names = []
    for tag in tags:
        if isinstance(tag, dict):
            tag_names.append(tag.get("name", ""))
        elif isinstance(tag, str):
            tag_names.append(tag)
    return [t for t in tag_names if t]


def render_result(
    batch_plan: Dict,
    results: List[Dict],
    operator: str,
    dry_run: bool,
    batch_status: str,
) -> str:
    """Render batch apply result as Markdown."""
    lines = []

    batch_id = batch_plan.get("batch_id", "unknown")[:8]
    device = batch_plan.get("device")
    total_items = batch_plan.get("total_items", 0)

    # Header
    lines.append(f"# Batch Staged Apply Result — {batch_id}")
    lines.append("")
    lines.append(f"**Device:** {device}")
    lines.append(f"**Total Items:** {total_items}")
    lines.append(f"**Operator:** {operator}")
    lines.append(f"**Timestamp:** {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"**Mode:** {'DRY-RUN (no writes)' if dry_run else 'REAL WRITE'}")
    lines.append(f"**Real Write Executed:** {'No (simulation only)' if dry_run else 'NOT IMPLEMENTED - aborted'}")
    lines.append("")

    # Status
    lines.append("## Result")
    lines.append("")
    if dry_run:
        lines.append("🟡 **DRY RUN** (simulation only, no actual write)")
    elif batch_status == "batch_applied":
        lines.append("🟢 **SUCCESS** (all items created in NetBox)")
    elif batch_status == "batch_blocked":
        if any(r.get("status") == "apply_not_implemented" for r in results):
            lines.append("🔴 **NOT IMPLEMENTED** (real write not yet implemented in this script)")
        else:
            lines.append("🔴 **BLOCKED** (validation failed, no write attempted)")
    elif batch_status == "batch_partial_failed":
        lines.append("🟠 **PARTIAL FAILURE** (some items failed)")
    else:
        lines.append(f"⚠️ **{batch_status}**")
    lines.append("")

    # Item results
    lines.append("## Items")
    lines.append("")
    for i, result in enumerate(results, 1):
        object_key = result.get("object_key")
        status = result.get("status")
        message = result.get("message")
        netbox_id = result.get("netbox_id")

        if status == "would_create":
            icon = "○"
            status_text = "WOULD CREATE (DRY RUN)"
            id_text = "(no ID in dry-run)"
        elif status == "success":
            icon = "✓"
            status_text = f"CREATED (id={netbox_id})"
        elif status == "apply_not_implemented":
            icon = "⚠"
            status_text = "APPLY NOT IMPLEMENTED"
        elif status == "blocked":
            icon = "❌"
            status_text = "BLOCKED"
        elif status == "failed":
            icon = "✗"
            status_text = "FAILED"
        elif status == "ready":
            icon = "○"
            status_text = "READY (preflight passed)"
        else:
            icon = "❓"
            status_text = status

        lines.append(f"{icon} **{i}. {object_key}:** {status_text}")
        if message:
            lines.append(f"   {message}")
        lines.append("")

    # Next steps
    lines.append("## Next Steps")
    lines.append("")
    if dry_run:
        lines.append("1. Review dry-run result")
        lines.append("2. If OK, execute with --confirm-real-write-batch")
        lines.append("3. Provide NETBOX_WRITE_TOKEN environment variable")
    elif batch_status == "batch_applied":
        lines.append("1. ✅ All items created as staged in NetBox")
        lines.append("2. ✅ Verify in NetBox UI")
        lines.append("3. Re-run compliance to validate")
        lines.append("4. Compare before/after")
    elif batch_status == "batch_partial_failed":
        lines.append("1. ⚠ Batch stopped after failure")
        lines.append("2. Review error message above")
        lines.append("3. Do not retry without investigation")
    else:
        lines.append("1. Review blockers above")
        lines.append("2. Fix issues and retry")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Apply batch staged NetBox objects (controlled, item-by-item)"
    )
    parser.add_argument("--batch-plan", required=True, help="BatchApplyPlan JSON file")
    parser.add_argument("--netbox-url", required=True, help="NetBox base URL")
    parser.add_argument("--confirm-batch-id", required=True, help="Batch ID confirmation")
    parser.add_argument("--operator", required=True, help="Operator name")
    parser.add_argument(
        "--confirm-real-write-batch",
        action="store_true",
        help="EXPLICIT confirmation for real write",
    )
    parser.add_argument("--expected-device", required=True, help="Expected device name for this batch")
    parser.add_argument("--expected-device-id", required=True, type=int, help="Expected device ID for this batch")
    parser.add_argument(
        "--allowed-object-keys",
        nargs="+",
        required=True,
        help="Explicit allowlist of object_key values permitted in this batch",
    )
    parser.add_argument("--output-dir", help="Output directory for result")
    args = parser.parse_args()

    try:
        # Load batch plan
        batch_plan = load_batch_plan(args.batch_plan)

        # Validate batch_id
        if batch_plan.get("batch_id")[:8] != args.confirm_batch_id[:8]:
            raise ValueError(
                f"Batch ID mismatch: "
                f"plan={batch_plan.get('batch_id')[:8]}, "
                f"confirmed={args.confirm_batch_id[:8]}"
            )

        # Validate batch plan device identity and allowlist
        valid_batch, batch_errors = validate_batch_plan_for_apply(
            batch_plan,
            expected_device=args.expected_device,
            expected_device_id=args.expected_device_id,
            allowed_object_keys=args.allowed_object_keys,
        )
        if not valid_batch:
            print("❌ Batch plan validation failed:")
            for error in batch_errors:
                print(f"  - {error}")
            return 1

        # Determine dry-run or real write
        dry_run = not args.confirm_real_write_batch

        # Get token if real write
        token = None
        if not dry_run:
            has_token, token_or_error = check_token_provided()
            if not has_token:
                print(f"❌ {token_or_error}", file=sys.stderr)
                return 1
            token = token_or_error
            print("")
            print("=" * 70)
            print("REAL NETBOX WRITE ENABLED FOR BATCH STAGED APPLY")
            print("=" * 70)
            print("")

        # Process each item
        items = batch_plan.get("items", [])
        results = []
        batch_status = "batch_applied" if items else "batch_blocked"

        if not dry_run:
            print(f"Running preflight checks for {len(items)} items...")
            print("")

        # Preflight check all items (all-or-none)
        for i, item in enumerate(items, 1):
            object_key = item.get("object_key")
            device_id = batch_plan.get("device_id")
            staged_payload = item.get("staged_payload", {})

            # Payload consistency validation before any POST
            payload_device = staged_payload.get("device")
            payload_name = staged_payload.get("name")
            print(f"[{i}/{len(items)}] {object_key}: payload.name={payload_name}, payload.device={payload_device}")

            if object_key not in args.allowed_object_keys:
                results.append({
                    "object_key": object_key,
                    "status": "blocked",
                    "message": "object_key not in allowlist",
                })
                batch_status = "batch_blocked"
                break

            if payload_name != object_key:
                results.append({
                    "object_key": object_key,
                    "status": "blocked",
                    "message": "Payload name does not match object_key",
                })
                batch_status = "batch_blocked"
                break

            if payload_device != args.expected_device_id:
                results.append({
                    "object_key": object_key,
                    "status": "blocked",
                    "message": "Payload device ID does not match expected device_id",
                })
                batch_status = "batch_blocked"
                break

            if not dry_run:
                print(f"  Validated staged_payload, now running preflight...")

                try:
                    # Check if object exists
                    object_ok, existing = preflight_check(
                        args.netbox_url,
                        token,
                        device_id,
                        object_key
                    )

                    if not object_ok:
                        print(f"  ❌ Object already exists in NetBox")
                        results.append({
                            "object_key": object_key,
                            "status": "blocked",
                            "message": "Object already exists",
                        })
                        batch_status = "batch_blocked"
                        break

                    print(f"  ✓ Preflight passed")
                    results.append({
                        "object_key": object_key,
                        "status": "ready",
                        "message": "Ready for apply",
                    })

                except ValueError as e:
                    print(f"  ❌ Preflight check failed: {e}")
                    results.append({
                        "object_key": object_key,
                        "status": "blocked",
                        "message": str(e),
                    })
                    batch_status = "batch_blocked"
                    break

        print("")

        # If any preflight failed, don't proceed with applies
        if batch_status == "batch_blocked" and not dry_run:
            print("❌ Preflight checks failed, aborting batch (all-or-none policy)")
            markdown = render_result(batch_plan, results, args.operator, dry_run, batch_status)
            output_dir = Path(args.output_dir) if args.output_dir else Path("reports/pilot-device-compliance/approvals/applied")
            output_dir.mkdir(parents=True, exist_ok=True)
            batch_id = batch_plan.get("batch_id", "unknown")[:8]
            result_file = output_dir / f"batch-apply-result-{batch_id}.md"
            with open(result_file, "w", encoding="utf-8") as f:
                f.write(markdown)
            print(f"✓ Result saved: {result_file}")
            print("")
            print(markdown)
            return 1

        # Dry-run or real apply (only if preflight passed)
        if dry_run:
            print("Running in DRY-RUN mode (no actual writes)")
            print(f"Would apply {len(items)} items")
            results = []
            for item in items:
                results.append({
                    "object_key": item.get("object_key"),
                    "status": "would_create",
                    "message": "Would create (DRY RUN, no ID assigned)",
                    "netbox_id": None,
                })
        else:
            print(f"Applying {len(items)} items...")
            print("❌ CRITICAL: Real batch write is NOT IMPLEMENTED in this script")
            print("   Aborting to prevent false success reports")
            print()

            # Mark all items as NOT_IMPLEMENTED
            for i, item in enumerate(results, 1):
                item["status"] = "apply_not_implemented"
                item["message"] = "Real batch write is not implemented in this version"
                item["netbox_id"] = None

            batch_status = "batch_blocked"

        # Render result
        markdown = render_result(batch_plan, results, args.operator, dry_run, batch_status)

        # Save result
        output_dir = Path(args.output_dir) if args.output_dir else Path("reports/pilot-device-compliance/approvals/applied")
        output_dir.mkdir(parents=True, exist_ok=True)
        batch_id = batch_plan.get("batch_id", "unknown")[:8]
        result_file = output_dir / f"batch-apply-result-{batch_id}.md"
        with open(result_file, "w", encoding="utf-8") as f:
            f.write(markdown)

        print(f"✓ Result saved: {result_file}")
        print("")
        print(markdown)

        return 0 if batch_status in ("batch_applied", "batch_preflight_passed") else 1

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
