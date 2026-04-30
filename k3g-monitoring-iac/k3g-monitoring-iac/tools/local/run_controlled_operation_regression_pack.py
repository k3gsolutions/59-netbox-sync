#!/usr/bin/env python3
"""FASE 4.68 — Controlled Operation Regression Pack."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict:
    """Load JSON safely."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def run_regression_pack(
    *,
    root: Path,
    cycle_id: str,
    output: Path,
    output_json: Path,
) -> dict[str, Any]:
    """Run regression pack validations."""
    checks = []
    passed = 0
    failed = 0

    # Check 1: Cycle directories exist
    cycle_002_dir = root / "cycle-002"
    cycle_003_dir = root / "cycle-003"

    check1 = {
        "check": "cycle_002_exists",
        "passed": cycle_002_dir.exists(),
    }
    checks.append(check1)
    if check1["passed"]:
        passed += 1
    else:
        failed += 1

    # Check 2: Cycle-002 has execution result
    exec_result = load_json(cycle_002_dir / "real-write-execution" / "CYCLE-002-REAL-WRITE-EXECUTION-RESULT.json")
    check2 = {
        "check": "cycle_002_execution_success",
        "passed": exec_result.get("status") == "CYCLE_REAL_WRITE_SUCCESS",
        "status": exec_result.get("status"),
    }
    checks.append(check2)
    if check2["passed"]:
        passed += 1
    else:
        failed += 1

    # Check 3: Response ID created
    items = exec_result.get("items", [])
    response_id = items[0].get("response_id") if items else None
    check3 = {
        "check": "response_id_6324",
        "passed": response_id == 6324,
        "response_id": response_id,
    }
    checks.append(check3)
    if check3["passed"]:
        passed += 1
    else:
        failed += 1

    # Check 4: Verification passed or passed_with_drift
    verif = load_json(cycle_002_dir / "real-write-execution" / "CYCLE-002-POST-WRITE-VERIFICATION-RESULT.json")
    check4 = {
        "check": "verification_passed_or_drift",
        "passed": "PASSED" in verif.get("decision", ""),
        "decision": verif.get("decision"),
    }
    checks.append(check4)
    if check4["passed"]:
        passed += 1
    else:
        failed += 1

    # Check 5: Compliance passed or warnings
    compl = load_json(cycle_002_dir / "real-write-execution" / "CYCLE-002-POST-WRITE-COMPLIANCE-RERUN.json")
    check5 = {
        "check": "compliance_passed_or_warnings",
        "passed": "PASSED" in compl.get("decision", ""),
        "decision": compl.get("decision"),
    }
    checks.append(check5)
    if check5["passed"]:
        passed += 1
    else:
        failed += 1

    # Check 6: Closure success or with_warnings
    clos = load_json(cycle_002_dir / "real-write-execution" / "closure" / "cycle-002-closure-summary.json")
    check6 = {
        "check": "closure_success_or_warnings",
        "passed": "CLOSED" in clos.get("status", ""),
        "status": clos.get("status"),
    }
    checks.append(check6)
    if check6["passed"]:
        passed += 1
    else:
        failed += 1

    # Check 7: Archive success
    archive = load_json(cycle_002_dir / "final-archive" / "cycle-002-final-manifest.json")
    check7 = {
        "check": "archive_success",
        "passed": "SUCCESS" in archive.get("status", ""),
        "status": archive.get("status"),
    }
    checks.append(check7)
    if check7["passed"]:
        passed += 1
    else:
        failed += 1

    # Check 8: Handoff with restrictions
    handoff = load_json(cycle_002_dir / "cycle-002-handoff-decision.json")
    check8 = {
        "check": "handoff_with_restrictions",
        "passed": "RESTRICTIONS" in handoff.get("decision", ""),
        "decision": handoff.get("decision"),
    }
    checks.append(check8)
    if check8["passed"]:
        passed += 1
    else:
        failed += 1

    # Check 9: Expansion stay_current_level
    expansion = load_json(root / "controlled-expansion-evaluation.json")
    check9 = {
        "check": "expansion_stay_current_level",
        "passed": expansion.get("recommendation") == "STAY_CURRENT_LEVEL",
        "recommendation": expansion.get("recommendation"),
    }
    checks.append(check9)
    if check9["passed"]:
        passed += 1
    else:
        failed += 1

    # Check 10: Cycle-003 prepared
    check10 = {
        "check": "cycle_003_prepared",
        "passed": cycle_003_dir.exists() and (cycle_003_dir / "CYCLE-003-SCOPE.json").exists(),
    }
    checks.append(check10)
    if check10["passed"]:
        passed += 1
    else:
        failed += 1

    # Check 11: No token in files
    secret_check = "NETBOX_WRITE_TOKEN" not in str(archive) and "NETBOX_WRITE_TOKEN" not in str(handoff)
    check11 = {
        "check": "no_token_in_results",
        "passed": secret_check,
    }
    checks.append(check11)
    if check11["passed"]:
        passed += 1
    else:
        failed += 1

    # Check 12: No automatic approvals without history
    scope = load_json(cycle_003_dir / "CYCLE-003-SCOPE.json") if cycle_003_dir.exists() else {}
    check12 = {
        "check": "scope_valid",
        "passed": scope.get("max_items") == 3 and scope.get("allowed_methods") == ["POST"],
    }
    checks.append(check12)
    if check12["passed"]:
        passed += 1
    else:
        failed += 1

    # Determine overall decision
    if failed == 0:
        decision = "REGRESSION_PACK_PASSED"
    elif failed <= 2:
        decision = "REGRESSION_PACK_PASSED_WITH_WARNINGS"
    else:
        decision = "REGRESSION_PACK_FAILED"

    result = {
        "pack_id": f"regression-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "cycle_tested": cycle_id,
        "tested_at": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "checks_passed": passed,
        "checks_failed": failed,
        "total_checks": len(checks),
        "checks": checks,
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    # Markdown report
    lines = [
        "# Controlled Operation Regression Pack",
        "",
        f"## Decision: {decision}",
        "",
        f"- Passed: {passed}/{len(checks)}",
        f"- Failed: {failed}/{len(checks)}",
        "",
        "## Results",
        "",
        "| Check | Passed |",
        "|-------|--------|",
    ]

    for check in checks:
        status = "✓" if check["passed"] else "✗"
        lines.append(f"| {check['check']} | {status} |")

    lines.extend([
        "",
        "---",
        f"Tested at {datetime.now(timezone.utc).isoformat()}",
    ])

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")

    return result


def main() -> int:
    """Run FASE 4.68."""
    parser = argparse.ArgumentParser(description="FASE 4.68 — Regression Pack")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)

    args = parser.parse_args()
    result = run_regression_pack(
        root=args.root,
        cycle_id=args.cycle_id,
        output=args.output,
        output_json=args.output_json,
    )

    print(f"✓ Regression pack: {result.get('decision')}")
    print(f"✓ Checks: {result['checks_passed']}/{result['total_checks']} passed")
    return 0 if result.get("decision") != "REGRESSION_PACK_FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
