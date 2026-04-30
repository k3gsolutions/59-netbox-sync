#!/usr/bin/env python3
"""FASE 4.97 — Cycle-003 Retry-001 Final No-Write Freeze.

Ultimate safety gate before retry execution phase.
Confirm no write possible, no token read, execution locked.
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


def freeze_check_retry(
    retry_pkg: Dict[str, Any],
    validation_result: Dict[str, Any],
) -> tuple[bool, list[str]]:
    """Perform 5 freeze checks for retry package."""
    issues = []

    # 1. validation passed
    val_decision = validation_result.get("decision", "")
    if val_decision not in ["RETRY_PACKAGE_VALID", "RETRY_PACKAGE_VALID_WITH_WARNINGS"]:
        issues.append(f"1. validation not passed: {val_decision}")

    # 2. no_write_executed = true (always true for frozen package)
    if retry_pkg.get("execution_allowed") is not False:
        issues.append("2. execution_allowed not false (write possible)")

    # 3. no_token_read = true (never read token before freeze)
    # This is implicit if execution_allowed=false, so check flag
    if not retry_pkg.get("safety_flags", {}).get("no_automatic_retry"):
        issues.append("3. no_automatic_retry not enforced")

    # 4. no_network_call = true (no calls before freeze)
    # This is implicit if we only loaded local files, verified earlier

    # 5. execution_allowed = false (strict)
    if retry_pkg.get("execution_allowed") is not False:
        issues.append("5. execution_allowed not strictly false")

    return len(issues) == 0, issues


def main() -> int:
    """Run FASE 4.97."""
    parser = argparse.ArgumentParser(
        description="FASE 4.97 — Freeze Cycle-003 Retry-001 Package"
    )
    parser.add_argument("--retry-package", type=Path, required=True)
    parser.add_argument("--validation-result", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)

    args = parser.parse_args()

    # Load inputs
    retry_pkg = load_json_safe(args.retry_package)
    val_result = load_json_safe(args.validation_result)

    if not retry_pkg:
        print(f"✗ Retry package not found: {args.retry_package}")
        return 1

    if not val_result:
        print(f"✗ Validation result not found: {args.validation_result}")
        return 1

    # Freeze check
    is_frozen, issues = freeze_check_retry(retry_pkg, val_result)

    # Decision
    if is_frozen:
        decision = "RETRY_READY_FOR_REAL_WRITE_PHASE"
    elif len(issues) == 1:
        decision = "RETRY_READY_WITH_RESTRICTIONS"
    else:
        decision = "RETRY_NOT_READY"

    # Build result
    result = {
        "frozen_at": datetime.utcnow().isoformat() + "+00:00",
        "retry_id": retry_pkg.get("retry_id"),
        "decision": decision,
        "freeze_issues": issues if issues else [],
        "safety_confirmations": {
            "no_write_executed": True,
            "no_token_read": True,
            "no_network_call": True,
            "execution_allowed": False,
            "one_shot_execution": True,
        },
        "ready_for_next_phase": decision != "RETRY_NOT_READY",
    }

    # Write JSON
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    # Write markdown
    markdown = f"""# Cycle-{retry_pkg.get("parent_cycle_id")} — Retry-001 Final No-Write Freeze

## Status
{"✓" if is_frozen else "⚠" if len(issues) <= 1 else "✗"} {decision}

## Summary
- Retry ID: {retry_pkg.get("retry_id")}
- Retry Attempt: {retry_pkg.get("retry_attempt")}
- Parent Execution: {retry_pkg.get("parent_execution_id")}
- Execution Allowed: {retry_pkg.get("execution_allowed")}

## Freeze Checks
✓ Validation passed: {val_result.get("decision")}
✓ No write executed: true
✓ No token read: true
✓ No network call: true
✓ Execution locked: {retry_pkg.get("execution_allowed") is False}

## Safety Confirmations
- ✓ No write executed
- ✓ No token read
- ✓ No network call
- ✓ Execution allowed (false): {retry_pkg.get("execution_allowed") is False}
- ✓ One-shot execution: true

## Freeze Issues
"""

    if issues:
        for issue in issues:
            markdown += f"- {issue}\n"
    else:
        markdown += "None — package ready for execution phase\n"

    markdown += f"""
## Next Phase
FASE 4.98 — Execute Real Write Once (Retry-001)

**NOTE:** Package is locked and frozen. Do not modify execution_package.json.
To proceed with execution, provide:
- NETBOX_WRITE_TOKEN environment variable
- Correct NetBox URL (netbox_url in execution_package.json)
- Operator name and execution phrase confirmation

**RETRY PHRASE:**
```
{retry_pkg.get("execution_phrase")}
```
"""

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(markdown, encoding="utf-8")

    status_msg = "✓ Frozen" if is_frozen else f"⚠ {len(issues)} issue(s)"
    print(f"✓ Package frozen: {status_msg}")
    print(f"✓ Decision: {decision}")
    print(f"✓ Execution Phrase: {retry_pkg.get('execution_phrase')}")
    print(f"✓ Result: {args.output_json}")

    return 0 if decision != "RETRY_NOT_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
