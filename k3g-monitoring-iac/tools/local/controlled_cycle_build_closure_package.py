#!/usr/bin/env python3
"""FASE 4.25 — Controlled Operation Cycle Build Closure Package.

Consolidate all cycle results and determine final status.
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


def determine_closure_decision(
    exec_status: str,
    verif_status: str,
    compliance_status: str,
) -> str:
    """Determine final closure decision."""
    # NOT_APPLICABLE - execution was aborted
    if "ABORTED" in exec_status or "NOT_APPLICABLE" in exec_status:
        return "CYCLE_CLOSED_NOT_APPLICABLE"

    # ACTION_REQUIRED - failures
    if "FAILED" in exec_status or "FAILED" in verif_status or "FAILED" in compliance_status:
        return "CYCLE_CLOSED_ACTION_REQUIRED"

    # WITH_WARNINGS - success but some drift/warnings
    if (
        "DRIFT" in verif_status
        or "WARNINGS" in compliance_status
    ):
        return "CYCLE_CLOSED_WITH_WARNINGS"

    # SUCCESS - all passed (no drift, no warnings)
    if (
        "SUCCESS" in exec_status
        and "PASSED" in verif_status
        and "PASSED" in compliance_status
    ):
        return "CYCLE_CLOSED_SUCCESS"

    return "CYCLE_CLOSED_WITH_WARNINGS"


def main() -> int:
    """Run FASE 4.25."""
    parser = argparse.ArgumentParser(description="FASE 4.25 — Build Closure Package")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--execution-result", type=Path, required=True)
    parser.add_argument("--post-write-verification", type=Path, required=True)
    parser.add_argument("--post-write-compliance", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)

    args = parser.parse_args()

    # Load all results
    exec_result = load_json_safe(args.execution_result)
    verif_result = load_json_safe(args.post_write_verification)
    compliance_result = load_json_safe(args.post_write_compliance)

    # Determine closure decision
    decision = determine_closure_decision(
        exec_result.get("status", ""),
        verif_result.get("status", ""),
        compliance_result.get("status", ""),
    )

    # Build closure summary
    closure_summary = {
        "cycle_id": args.cycle_id,
        "device": args.device,
        "device_id": args.device_id,
        "decision": decision,
        "closed_at": datetime.utcnow().isoformat() + "+00:00",
        "execution": {
            "status": exec_result.get("status"),
            "operator": exec_result.get("operator"),
            "created": exec_result.get("summary", {}).get("created", 0),
            "failed": exec_result.get("summary", {}).get("failed", 0),
        },
        "verification": {
            "status": verif_result.get("status"),
            "verified": verif_result.get("summary", {}).get("verified", 0),
            "drift": verif_result.get("summary", {}).get("drift", 0),
        },
        "compliance": {
            "status": compliance_result.get("status"),
            "passed": compliance_result.get("summary", {}).get("passed", 0),
            "warnings": compliance_result.get("summary", {}).get("warnings", 0),
        },
    }

    # Write closure summary
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_file = args.output_dir / f"cycle-{args.cycle_id.lower()}-closure-summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(closure_summary, f, indent=2)

    # Generate closure report
    emoji = {
        "CYCLE_CLOSED_SUCCESS": "✓",
        "CYCLE_CLOSED_WITH_WARNINGS": "⚠",
        "CYCLE_CLOSED_ACTION_REQUIRED": "✗",
        "CYCLE_CLOSED_NOT_APPLICABLE": "⊘",
    }.get(decision, "?")

    markdown = f"""# Cycle-{args.cycle_id} — Closure Package

## Final Decision
{emoji} **{decision}**

## Cycle Summary
- Device: {args.device} ({args.device_id})
- Closed At: {closure_summary['closed_at']}

## Execution Phase (FASE 4.22)
- Status: {exec_result.get('status')}
- Operator: {exec_result.get('operator')}
- Created: {exec_result.get('summary', {}).get('created', 0)}
- Failed: {exec_result.get('summary', {}).get('failed', 0)}

## Verification Phase (FASE 4.23)
- Status: {verif_result.get('status')}
- Verified: {verif_result.get('summary', {}).get('verified', 0)}
- Drift: {verif_result.get('summary', {}).get('drift', 0)}
- Failed: {verif_result.get('summary', {}).get('failed', 0)}

## Compliance Phase (FASE 4.24)
- Status: {compliance_result.get('status')}
- Passed: {compliance_result.get('summary', {}).get('passed', 0)}
- Warnings: {compliance_result.get('summary', {}).get('warnings', 0)}

## Decision Rationale
"""

    if decision == "CYCLE_CLOSED_SUCCESS":
        markdown += "✓ Execution succeeded, verification passed, compliance passed. Cycle complete."
    elif decision == "CYCLE_CLOSED_WITH_WARNINGS":
        markdown += "⚠ Execution succeeded, but verification/compliance found warnings. Review before next cycle."
    elif decision == "CYCLE_CLOSED_ACTION_REQUIRED":
        markdown += "✗ Failures detected in execution, verification, or compliance. Action required before next cycle."
    elif decision == "CYCLE_CLOSED_NOT_APPLICABLE":
        markdown += "⊘ Execution was aborted at preflight. No write attempted. No closure actions needed."

    markdown += f"""

## Artifacts
- Execution Result: {args.execution_result}
- Verification Result: {args.post_write_verification}
- Compliance Result: {args.post_write_compliance}
- Closure Summary: {summary_file}

## Next Steps
1. Review decision rationale
2. If ACTION_REQUIRED: investigate failures
3. If SUCCESS or WITH_WARNINGS: cycle can be archived
4. Update operational metrics

---
Cycle-{args.cycle_id} closure completed at {closure_summary['closed_at']}
"""

    # Write report
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(markdown, encoding="utf-8")

    print(f"✓ Closure package: {decision}")
    print(f"✓ Summary: {summary_file}")
    print(f"✓ Report: {args.report}")

    return 0 if "SUCCESS" in decision or "NOT_APPLICABLE" in decision else (0 if "WARNINGS" in decision else 1)


if __name__ == "__main__":
    raise SystemExit(main())
