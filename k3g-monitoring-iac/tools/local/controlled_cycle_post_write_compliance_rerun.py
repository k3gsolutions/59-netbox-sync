#!/usr/bin/env python3
"""FASE 4.24 — Controlled Operation Cycle Post-Write Compliance Re-Run.

Local read-only compliance checks post-write. No NetBox calls.
"""

from __future__ import annotations

import argparse
import json
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


def validate_compliance(
    exec_result: Dict[str, Any],
    verification_result: Dict[str, Any],
    device: str,
) -> tuple[str, list[str]]:
    """Validate compliance post-write (local read-only)."""
    issues = []

    # Check execution successful
    if "SUCCESS" not in exec_result.get("status", ""):
        if "ABORTED" in exec_result.get("status", ""):
            return "CYCLE_POST_WRITE_COMPLIANCE_NOT_APPLICABLE", issues
        issues.append("Execution not successful")

    # Check verification passed
    if verification_result.get("status") == "CYCLE_POST_WRITE_VERIFICATION_FAILED":
        issues.append("Verification failed")
    elif "DRIFT" in verification_result.get("status", ""):
        issues.append("Verification found drift")

    # Check items created
    exec_items = exec_result.get("items", [])
    if not exec_items:
        issues.append("No items in execution result")
        return "CYCLE_POST_WRITE_COMPLIANCE_NOT_APPLICABLE", issues

    # Local compliance check: simple structure validation
    for item in exec_items:
        if "CREATED" not in item.get("status", ""):
            issues.append(f"Item {item.get('item_id')} not created")

    # Determine status
    if len(issues) == 0:
        return "CYCLE_POST_WRITE_COMPLIANCE_PASSED", issues
    elif any("drift" in i.lower() for i in issues):
        return "CYCLE_POST_WRITE_COMPLIANCE_PASSED_WITH_WARNINGS", issues
    else:
        return "CYCLE_POST_WRITE_COMPLIANCE_FAILED", issues


def main() -> int:
    """Run FASE 4.24."""
    parser = argparse.ArgumentParser(
        description="FASE 4.24 — Post-Write Compliance Re-Run"
    )
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--execution-result", type=Path, required=True)
    parser.add_argument("--post-write-verification", type=Path, required=True)
    parser.add_argument("--policy-registry", type=Path, default=None)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)

    args = parser.parse_args()

    # Load results (read-only)
    exec_result = load_json_safe(args.execution_result)
    verif_result = load_json_safe(args.post_write_verification)

    # Validate compliance (local only)
    status, issues = validate_compliance(exec_result, verif_result, args.device)

    # Build result
    result = {
        "cycle_id": args.cycle_id,
        "device": args.device,
        "device_id": args.device_id,
        "status": status,
        "compliance_checked_at": datetime.utcnow().isoformat() + "+00:00",
        "execution_status": exec_result.get("status"),
        "verification_status": verif_result.get("status"),
        "summary": {
            "total_items": len(exec_result.get("items", [])),
            "passed": 0 if status == "CYCLE_POST_WRITE_COMPLIANCE_FAILED" else len(exec_result.get("items", [])),
            "warnings": len([i for i in issues if "drift" in i.lower()]),
            "failures": len([i for i in issues if "drift" not in i.lower()]),
        },
        "issues": issues,
    }

    # Write JSON
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    # Write markdown
    emoji = "✓" if status == "CYCLE_POST_WRITE_COMPLIANCE_PASSED" else "⚠" if "WARNINGS" in status else "✗" if "FAILED" in status else "⊘"
    markdown = f"""# Cycle-{args.cycle_id} — Post-Write Compliance Re-Run

## Status
{emoji} {status}

## Summary
- Device: {args.device}
- Execution Status: {exec_result.get('status')}
- Verification Status: {verif_result.get('status')}
- Total Items: {len(exec_result.get('items', []))}

## Compliance Checks
"""

    if len(issues) == 0:
        markdown += "All checks passed.\n"
    else:
        for issue in issues:
            markdown += f"- {issue}\n"

    markdown += """
## Next Phase
FASE 4.25 — Closure Package

Note: This compliance check is read-only and local. No NetBox calls made.
"""

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(markdown, encoding="utf-8")

    print(f"✓ Compliance re-run: {status}")
    print(f"✓ Issues: {len(issues)}")

    return 0 if "PASSED" in status else 1


if __name__ == "__main__":
    raise SystemExit(main())
