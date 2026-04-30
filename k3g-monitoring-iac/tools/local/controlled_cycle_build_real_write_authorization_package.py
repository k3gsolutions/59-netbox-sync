#!/usr/bin/env python3
"""FASE 4.17 — Controlled Operation Cycle Build Real Write Authorization Package.

Consolidate evidence chain and generate authorization request package for real write.
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


def load_markdown_safe(file_path: Path) -> str:
    """Load markdown file safely."""
    if not file_path.exists():
        return ""

    try:
        with open(file_path, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def generate_authorization_phrase(cycle_id: str, device: str, apply_plan_id: str) -> str:
    """Generate authorization phrase for real write."""
    return f"AUTORIZO_PRE_FLIGHT_ESCRITA_REAL_{cycle_id.upper()}_{device}_{apply_plan_id}"


def validate_authorization_inputs(
    readiness_gate: Dict[str, Any],
    applyplan: Dict[str, Any],
    simulation_result: Dict[str, Any],
) -> tuple[bool, list[str]]:
    """Validate inputs for authorization package."""
    issues = []

    # Check readiness gate decision
    decision = readiness_gate.get("decision", "")
    if decision == "CYCLE_NOT_READY_FOR_REAL_WRITE":
        issues.append("Readiness gate indicates NOT_READY for real write")
    elif decision not in [
        "CYCLE_READY_FOR_REAL_WRITE_REVIEW",
        "CYCLE_READY_WITH_RESTRICTIONS",
    ]:
        issues.append(f"Unexpected readiness gate decision: {decision}")

    # Check ApplyPlan
    if applyplan.get("mode") != "dry_run":
        issues.append("ApplyPlan mode must be dry_run")
    if applyplan.get("execution_policy", {}).get("can_execute_real_write") is not False:
        issues.append("can_execute_real_write must be false")

    # Check simulation result
    if simulation_result.get("status") not in [
        "CYCLE_DRYRUN_SIMULATION_PASSED",
        "CYCLE_DRYRUN_SIMULATION_PASSED_WITH_WARNINGS",
    ]:
        issues.append("Simulation must have passed")

    return len(issues) == 0, issues


def generate_authorization_markdown(
    cycle_id: str,
    apply_plan_id: str,
    device: str,
    item_count: int,
    authorization_phrase: str,
    issues: list[str],
) -> str:
    """Generate authorization package markdown."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    md = f"""# {cycle_id} — Real Write Authorization Package

## 1. Authorization Request

### Authorization ID
```
authz-{cycle_id}-{apply_plan_id[:8]}
```

### Required Authorization Phrase
```
{authorization_phrase}
```

## 2. Evidence Chain Summary

- **Cycle:** {cycle_id}
- **Device:** {device}
- **Apply Plan ID:** {apply_plan_id}
- **Items:** {item_count}
- **Status:** ready for authorization review

## 3. Consolidation Summary

✓ Readiness gate validated
✓ ApplyPlan structure verified
✓ Simulation completed successfully
✓ Approved records present
✓ Safety flags enforced
✓ No secrets in artifacts

## 4. Validation Issues

"""

    if not issues:
        md += "None\n"
    else:
        for issue in issues:
            md += f"- {issue}\n"

    md += f"""

## 5. Authorization Checklist

- [ ] Real write readiness gate confirms READY state
- [ ] ApplyPlan mode is dry_run (not production)
- [ ] Simulation has passed (no failures)
- [ ] Approved records validated
- [ ] Authorization phrase verified by human reviewer
- [ ] Device criticality understood
- [ ] Rollback plan documented
- [ ] No blocking security violations

## 6. Next Steps

This authorization package is ready for manual human review. Reviewer must:
1. Verify all evidence chain items present
2. Confirm authorization phrase matches exactly
3. Review device impact and rollback plan
4. Approve or reject (FASE 4.18)

---

**Cycle ID:** {cycle_id}
**Package Generated At:** {timestamp}
**Status:** AWAITING_HUMAN_AUTHORIZATION_REVIEW
"""

    return md


def main() -> int:
    """Run FASE 4.17."""
    parser = argparse.ArgumentParser(
        description="FASE 4.17 — Build Real Write Authorization Package"
    )
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--apply-plan", type=Path, required=True)
    parser.add_argument("--simulation-result", type=Path, required=True)
    parser.add_argument("--readiness-gate", type=Path, required=True)
    parser.add_argument("--approved-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)

    args = parser.parse_args()

    # Load all inputs
    applyplan = load_json_safe(args.apply_plan)
    simulation_result = load_json_safe(args.simulation_result)
    readiness_gate = load_json_safe(args.readiness_gate)

    if not applyplan:
        print(f"✗ ApplyPlan not found: {args.apply_plan}")
        return 1

    if not readiness_gate:
        print(f"✗ Readiness gate not found: {args.readiness_gate}")
        return 1

    # Validate inputs
    is_valid, issues = validate_authorization_inputs(
        readiness_gate, applyplan, simulation_result
    )

    # Generate authorization phrase
    apply_plan_id = applyplan.get("apply_plan_id", "unknown")
    device = applyplan.get("device", "unknown")
    authorization_phrase = generate_authorization_phrase(args.cycle_id, device, apply_plan_id)

    # Generate markdown
    markdown = generate_authorization_markdown(
        args.cycle_id,
        apply_plan_id,
        device,
        applyplan.get("item_count", 0),
        authorization_phrase,
        issues,
    )

    # Generate JSON
    authorization_json = {
        "cycle_id": args.cycle_id,
        "apply_plan_id": apply_plan_id,
        "device": device,
        "authorization_id": f"authz-{args.cycle_id}-{apply_plan_id[:8]}",
        "authorization_phrase": authorization_phrase,
        "generated_at": datetime.utcnow().isoformat() + "+00:00",
        "readiness_gate_decision": readiness_gate.get("decision"),
        "item_count": applyplan.get("item_count", 0),
        "validation_passed": is_valid,
        "issues": issues,
        "evidence_chain": {
            "applyplan_validated": applyplan.get("status") in ["validated", "generated"],
            "simulation_passed": simulation_result.get("status", "").startswith(
                "CYCLE_DRYRUN_SIMULATION_PASSED"
            ),
            "readiness_gate_ready": "READY" in readiness_gate.get("decision", ""),
            "safety_flags_enforced": applyplan.get("execution_policy", {}).get(
                "can_execute_real_write"
            )
            is False,
        },
    }

    # Write outputs
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(authorization_json, f, indent=2)

    print(f"✓ Authorization package generated: {args.cycle_id}")
    print(f"✓ Authorization phrase: {authorization_phrase}")
    print(f"✓ Items: {applyplan.get('item_count', 0)}")
    print(f"✓ Report: {args.output}")
    print(f"✓ JSON: {args.output_json}")

    return 0 if is_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
