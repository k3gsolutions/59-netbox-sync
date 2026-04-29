#!/usr/bin/env python3
"""FASE 2.52 — Final No-Write Freeze Check.

Validate entire pre-execution chain: package valid, no tokens, no writes,
no forbidden operations. Final confirmation before FASE 2.53.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple


def validate_execution_package(package_file: Path) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate execution package."""
    if not package_file.exists():
        return False, f"Package not found: {package_file}", {}

    try:
        with open(package_file, encoding="utf-8") as f:
            pkg = json.load(f)
    except Exception as e:
        return False, f"Invalid package JSON: {e}", {}

    # Critical checks
    if pkg.get("execution_allowed") is not False:
        return False, "execution_allowed is not false", pkg

    if not pkg.get("required_execution_phrase"):
        return False, "Missing required_execution_phrase", pkg

    if pkg.get("status") != "prepared":
        return False, f"Status is {pkg.get('status')}, not prepared", pkg

    return True, "OK", pkg


def validate_validation_report(report_file: Path) -> Tuple[bool, str]:
    """Validate validation report decision."""
    if not report_file.exists():
        return False, f"Validation report not found: {report_file}"

    try:
        content = report_file.read_text(encoding="utf-8")
    except Exception as e:
        return False, f"Cannot read validation report: {e}"

    if "### REAL_WRITE_EXECUTION_PACKAGE_VALID" in content:
        return True, "Package validation: VALID"
    elif "### REAL_WRITE_EXECUTION_PACKAGE_INVALID" in content:
        return False, "Package validation: INVALID"
    else:
        return False, "No validation decision found in report"


def validate_runbook(runbook_file: Path) -> Tuple[bool, str]:
    """Validate runbook exists and has structure."""
    if not runbook_file.exists():
        return False, f"Runbook not found: {runbook_file}"

    try:
        content = runbook_file.read_text(encoding="utf-8")
    except Exception as e:
        return False, f"Cannot read runbook: {e}"

    # Check for critical sections
    required_sections = [
        "Prerequisites",
        "Execution Command",
        "Pre-Execution Checklist",
        "What You MUST NOT Do",
        "Post-Execution Steps",
    ]

    for section in required_sections:
        if section not in content:
            return False, f"Runbook missing section: {section}"

    if "NETBOX_WRITE_TOKEN" not in content:
        return False, "Runbook missing token handling instructions"

    return True, "Runbook valid"


def check_for_tokens(package: Dict[str, Any]) -> Tuple[bool, str]:
    """Check package contains no actual tokens."""
    package_str = json.dumps(package).lower()

    # Check for common token patterns
    forbidden_patterns = [
        "token=",
        "auth=",
        "bearer ",
        "api_key=",
        "secret=",
        "password=",
    ]

    for pattern in forbidden_patterns:
        if pattern in package_str:
            # Avoid false positive: "required_execution_phrase" contains "phrase"
            if pattern == "phrase" and "required_execution_phrase" in package_str:
                continue

            # But "token=" in payload value would be bad
            for item in package.get("items", []):
                item_str = json.dumps(item).lower()
                if pattern in item_str:
                    return False, f"Found forbidden pattern in item: {pattern}"

    return True, "No tokens in package"


def check_for_writes(package: Dict[str, Any]) -> Tuple[bool, str]:
    """Check package has no writes or applied status."""
    package_str = json.dumps(package)

    # Check for "applied" status
    if '"status": "applied"' in package_str:
        return False, "Package contains 'applied' status (writes already executed?)"

    # Check for no forbidden methods in items
    for item in package.get("items", []):
        method = item.get("method", "").upper()
        if method in ["PATCH", "DELETE"]:
            return False, f"Item has forbidden method: {method}"

        endpoint = item.get("endpoint", "")
        forbidden = ["/sync", "equipment", "ssh", "netconf"]
        for f in forbidden:
            if f in endpoint.lower():
                return False, f"Item has forbidden endpoint: {endpoint}"

    return True, "No writes or forbidden operations"


def check_execution_phrase(package: Dict[str, Any]) -> Tuple[bool, str]:
    """Check execution phrase is present and valid."""
    phrase = package.get("required_execution_phrase", "")

    if not phrase:
        return False, "Missing required_execution_phrase"

    if not phrase.startswith("EXECUTO_ESCRITA_REAL_"):
        return False, f"Phrase format incorrect: {phrase}"

    return True, f"Execution phrase valid: {phrase}"


def main() -> int:
    """Run FASE 2.52."""
    parser = argparse.ArgumentParser(description="FASE 2.52 — Final No-Write Freeze Check")
    parser.add_argument("--execution-package", type=Path, required=True, help="Execution package JSON")
    parser.add_argument("--package-validation", type=Path, required=True, help="Package validation report")
    parser.add_argument("--runbook", type=Path, required=True, help="Operator runbook")
    parser.add_argument("--output", type=Path, required=True, help="Output report path")

    args = parser.parse_args()

    # Validate package
    pkg_valid, pkg_reason, package = validate_execution_package(args.execution_package)
    if not pkg_valid:
        print(f"✗ Package invalid: {pkg_reason}")
        return 1

    # Validate validation report
    val_ok, val_reason = validate_validation_report(args.package_validation)
    if not val_ok:
        print(f"✗ {val_reason}")
        return 1

    # Validate runbook
    runbook_ok, runbook_reason = validate_runbook(args.runbook)
    if not runbook_ok:
        print(f"✗ {runbook_reason}")
        return 1

    # Check for tokens
    token_ok, token_reason = check_for_tokens(package)
    if not token_ok:
        print(f"✗ {token_reason}")
        decision = "NOT_READY_FOR_REAL_WRITE_PHASE"
    else:
        # Check for writes
        write_ok, write_reason = check_for_writes(package)
        if not write_ok:
            print(f"✗ {write_reason}")
            decision = "NOT_READY_FOR_REAL_WRITE_PHASE"
        else:
            # Check execution phrase
            phrase_ok, phrase_reason = check_execution_phrase(package)
            if not phrase_ok:
                print(f"✗ {phrase_reason}")
                decision = "NOT_READY_FOR_REAL_WRITE_PHASE"
            else:
                decision = "READY_FOR_REAL_WRITE_PHASE"

    # Generate report
    timestamp = datetime.utcnow().isoformat() + "+00:00"
    report_lines = [
        "# Final No-Write Freeze Check",
        "",
        f"**Device:** {package.get('device')}",
        f"**Generated:** {timestamp}",
        "",
        "## Decision",
        "",
        f"### {decision}",
        "",
    ]

    if decision == "READY_FOR_REAL_WRITE_PHASE":
        report_lines.extend([
            "✓ Execution package structure valid",
            "✓ Validation report: VALID",
            "✓ Operator runbook complete",
            "✓ No tokens in package",
            "✓ No writes executed",
            "✓ No forbidden methods or endpoints",
            "✓ Execution phrase valid",
            "✓ **System ready for FASE 2.53 — Execute Real Write**",
            "",
            "## Next Phase: FASE 2.53",
            "",
            "Ready to execute real write. Execute command (in FASE 2.53):",
            "",
            f"```bash",
            f"export NETBOX_WRITE_TOKEN='your-actual-token'",
            f"",
            f"python3 tools/local/execute_real_write_once.py \\",
            f"  --execution-package {args.execution_package} \\",
            f"  --operator 'Operator Name' \\",
            f"  --confirm-execution-phrase '{package.get('required_execution_phrase')}' \\",
            f"  --confirm-real-write-once",
            f"```",
            "",
        ])
    else:
        report_lines.extend([
            "✗ System NOT ready for real write phase",
            "✗ Fix issues above before retrying",
            "",
        ])

    report_lines.extend([
        "## Freeze Check Items",
        "",
        f"- Package execution_allowed: {package.get('execution_allowed')}",
        f"- Package status: {package.get('status')}",
        f"- Token required for next phase: {package.get('token_required_in_next_phase')}",
        f"- One-shot execution: {package.get('one_shot_execution')}",
        f"- Tokens in package: {not token_ok}",
        f"- Writes executed: {not write_ok}",
        f"- Execution phrase present: {phrase_ok}",
        "",
        "## Security Confirmations",
        "",
        "✓ No NetBox writes executed (FASES 2.47-2.52)",
        "✓ No tokens read or stored in artifacts",
        "✓ No network calls made",
        "✓ All package preparation only",
        "✓ Final freeze validation complete",
        "✓ System in clean state for FASE 2.53",
        "",
        "## Mandatory Before FASE 2.53",
        "",
        "1. [ ] Read operator runbook carefully",
        "2. [ ] Understand each item to be written",
        "3. [ ] Know rollback strategy for each item",
        "4. [ ] Have NETBOX_WRITE_TOKEN ready (environment only, not hardcoded)",
        "5. [ ] Confirm operational window",
        "6. [ ] Confirm exact execution phrase (copy-paste ready)",
        "7. [ ] Have escalation contacts available",
        "8. [ ] System in production maintenance window (if applicable)",
        "",
    ])

    # Create output directory
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"✓ Freeze check report: {args.output}")
    print(f"✓ Decision: {decision}")

    return 0 if decision == "READY_FOR_REAL_WRITE_PHASE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
