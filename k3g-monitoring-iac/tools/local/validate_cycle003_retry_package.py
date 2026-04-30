#!/usr/bin/env python3
"""FASE 4.96 — Cycle-003 Retry-001 Package Validation.

Validate retry package structure and safety before freeze gate.
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


def validate_retry_package(
    retry_pkg: Dict[str, Any],
    parent_result: Dict[str, Any],
) -> tuple[bool, list[str]]:
    """Validate 14 retry package checks."""
    issues = []

    # 1. retry_id present
    if not retry_pkg.get("retry_id"):
        issues.append("1. retry_id missing")

    # 2. retry_attempt = 1
    if retry_pkg.get("retry_attempt") != 1:
        issues.append(f"2. retry_attempt not 1: {retry_pkg.get('retry_attempt')}")

    # 3. parent_execution_id present
    if not retry_pkg.get("parent_execution_id"):
        issues.append("3. parent_execution_id missing")

    # 4. parent failed
    parent_status = parent_result.get("status", "")
    if "FAILED" not in parent_status and "PARTIAL_FAILED" not in parent_status:
        issues.append(f"4. parent not failed: {parent_status}")

    # 5. parent created 0 objects
    if parent_result.get("summary", {}).get("created", 0) > 0:
        issues.append("5. parent created objects (cannot retry)")

    # 6. execution_allowed = false
    if retry_pkg.get("execution_allowed") is not False:
        issues.append("6. execution_allowed not false")

    # 7. requires_final_no_write_freeze
    if not retry_pkg.get("safety_flags", {}).get("requires_final_no_write_freeze"):
        issues.append("7. requires_final_no_write_freeze not true")

    # 8. requires_execution_confirmation
    if not retry_pkg.get("safety_flags", {}).get("requires_execution_confirmation"):
        issues.append("8. requires_execution_confirmation not true")

    # 9. no_automatic_retry
    if not retry_pkg.get("safety_flags", {}).get("no_automatic_retry"):
        issues.append("9. no_automatic_retry not true")

    # 10. execution_phrase present
    if not retry_pkg.get("execution_phrase"):
        issues.append("10. execution_phrase missing")

    # 11. items not empty
    items = retry_pkg.get("items", [])
    if not items:
        issues.append("11. items empty")

    # 12. items have valid endpoints
    for idx, item in enumerate(items):
        endpoint = item.get("target_endpoint", "")
        if not endpoint.startswith("/api/"):
            issues.append(f"12. item[{idx}] invalid endpoint: {endpoint}")

    # 13. items have no secrets
    blocked = ["token", "password", "secret", "api_key", "bearer"]
    for idx, item in enumerate(items):
        payload_str = json.dumps(item.get("proposed_payload", {})).lower()
        for b in blocked:
            if b in payload_str:
                issues.append(f"13. item[{idx}] contains blocked keyword: {b}")

    # 14. no secrets in package
    pkg_str = json.dumps(retry_pkg).lower()
    for b in blocked:
        if b in pkg_str:
            issues.append(f"14. package contains blocked keyword: {b}")

    return len(issues) == 0, issues


def main() -> int:
    """Run FASE 4.96."""
    parser = argparse.ArgumentParser(
        description="FASE 4.96 — Validate Cycle-003 Retry-001 Package"
    )
    parser.add_argument("--retry-package", type=Path, required=True)
    parser.add_argument("--parent-result", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)

    args = parser.parse_args()

    # Load inputs
    retry_pkg = load_json_safe(args.retry_package)
    parent_result = load_json_safe(args.parent_result)

    if not retry_pkg:
        print(f"✗ Retry package not found: {args.retry_package}")
        return 1

    if not parent_result:
        print(f"✗ Parent result not found: {args.parent_result}")
        return 1

    # Validate
    is_valid, issues = validate_retry_package(retry_pkg, parent_result)

    # Decision
    if is_valid:
        decision = "RETRY_PACKAGE_VALID"
    elif len(issues) <= 2:
        decision = "RETRY_PACKAGE_VALID_WITH_WARNINGS"
    else:
        decision = "RETRY_PACKAGE_INVALID"

    # Build result
    result = {
        "validated_at": datetime.utcnow().isoformat() + "+00:00",
        "retry_id": retry_pkg.get("retry_id"),
        "decision": decision,
        "validation_issues": issues if issues else [],
        "items_count": len(retry_pkg.get("items", [])),
        "parent_execution_id": retry_pkg.get("parent_execution_id"),
        "parent_status": parent_result.get("status"),
    }

    # Write JSON
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    # Write markdown
    markdown = f"""# Cycle-{retry_pkg.get("parent_cycle_id")} — Retry-001 Package Validation

## Status
{"✓" if is_valid else "⚠" if len(issues) <= 2 else "✗"} {decision}

## Summary
- Retry ID: {retry_pkg.get("retry_id")}
- Parent Execution: {retry_pkg.get("parent_execution_id")}
- Items: {len(retry_pkg.get("items", []))}
- Parent Status: {parent_result.get("status")}

## Validation Results
"""

    if issues:
        markdown += "### Issues\n"
        for issue in issues:
            markdown += f"- {issue}\n"
    else:
        markdown += "✓ All 14 checks passed\n"

    markdown += f"""
## Next Phase
FASE 4.97 — Retry-001 Final No-Write Freeze
"""

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(markdown, encoding="utf-8")

    status_msg = "✓ Valid" if is_valid else f"⚠ {len(issues)} issues"
    print(f"✓ Package validated: {status_msg}")
    print(f"✓ Decision: {decision}")
    print(f"✓ Result: {args.output_json}")

    return 0 if decision != "RETRY_PACKAGE_INVALID" else 1


if __name__ == "__main__":
    raise SystemExit(main())
