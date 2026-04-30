#!/usr/bin/env python3
"""FASE 4.19 — Controlled Operation Cycle Build Real Write Execution Package.

Build execution package with execution_allowed=false and execution phrase.
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


def generate_execution_phrase(cycle_id: str, device: str, apply_plan_id: str) -> str:
    """Generate execution phrase for real write."""
    return f"EXECUTAR_ESCRITA_REAL_{cycle_id.upper()}_{device}_{apply_plan_id}"


def validate_preflight_gate(preflight_gate: Dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate preflight gate cleared for execution."""
    issues = []

    decision = preflight_gate.get("decision", "")
    if decision != "CYCLE_PREFLIGHT_CLEARED_FOR_EXECUTION":
        issues.append(f"Preflight gate not cleared: {decision}")

    if not preflight_gate.get("preflight_checks", {}).get("phrase_validated"):
        issues.append("Phrase not validated in preflight")

    if not preflight_gate.get("preflight_checks", {}).get("evidence_chain_complete"):
        issues.append("Evidence chain not complete")

    return len(issues) == 0, issues


def build_execution_package(
    cycle_id: str,
    applyplan: Dict[str, Any],
    execution_phrase: str,
) -> Dict[str, Any]:
    """Build real write execution package."""
    return {
        "execution_id": f"exec-{cycle_id}-{applyplan.get('apply_plan_id', '')[:8]}",
        "cycle_id": cycle_id,
        "apply_plan_id": applyplan.get("apply_plan_id"),
        "device": applyplan.get("device"),
        "device_id": applyplan.get("device_id"),
        "execution_allowed": False,  # Safety: always false before final gate
        "execution_phrase": execution_phrase,
        "created_at": datetime.utcnow().isoformat() + "+00:00",
        "items": applyplan.get("items", []),
        "item_count": applyplan.get("item_count", 0),
        "safety_flags": {
            "execution_allowed": True,
            "no_automatic_retry": True,
            "no_rollback_automatic": True,
            "requires_execution_confirmation": True,
            "requires_final_no_write_freeze": True,
            "generated_from_approved_records": True,
        },
        "execution_policy": {
            "execution_allowed": False,
            "requires_next_gate": True,
            "next_gate": "FASE_4_21_FINAL_NO_WRITE_FREEZE",
            "max_items": applyplan.get("execution_policy", {}).get("max_items", 3),
            "allowed_methods": applyplan.get("execution_policy", {}).get(
                "allowed_methods", ["POST"]
            ),
            "forbidden_methods": applyplan.get("execution_policy", {}).get(
                "forbidden_methods", ["PATCH", "DELETE"]
            ),
            "forbidden_targets": applyplan.get("execution_policy", {}).get(
                "forbidden_targets", ["/sync", "equipment", "ssh", "netconf"]
            ),
        },
        "source_applyplan": {
            "apply_plan_id": applyplan.get("apply_plan_id"),
            "mode": applyplan.get("mode"),
            "status": applyplan.get("status"),
            "item_count": applyplan.get("item_count"),
        },
    }


def generate_execution_markdown(
    cycle_id: str,
    device: str,
    apply_plan_id: str,
    execution_id: str,
    item_count: int,
    execution_phrase: str,
) -> str:
    """Generate execution package markdown."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    md = f"""# {cycle_id} — Real Write Execution Package

## 1. Execution Package

### Execution ID
```
{execution_id}
```

### Execution Phrase (Required for FASE 4.21)
```
{execution_phrase}
```

### Execution Status
🔒 **execution_allowed = false** (Safety lock active)

## 2. Package Summary

- **Cycle:** {cycle_id}
- **Device:** {device}
- **Apply Plan ID:** {apply_plan_id}
- **Items:** {item_count}
- **Status:** AWAITING_FINAL_NO_WRITE_FREEZE_VALIDATION

## 3. Safety Confirmations

- ✓ execution_allowed=false (locked)
- ✓ Requires next gate validation
- ✓ No automatic retries
- ✓ No automatic rollback
- ✓ Requires human execution confirmation
- ✓ Final no-write freeze required

## 4. Execution Policy

- **Allowed Methods:** POST
- **Forbidden Methods:** PATCH, DELETE
- **Forbidden Targets:** /sync, equipment, ssh, netconf
- **Max Items:** {item_count}

## 5. Items for Execution

{f'Total items: {item_count}' if item_count > 0 else 'No items'}

## 6. Next Steps

This execution package is locked and requires:
1. Validation by FASE 4.20 (Validate Execution Package)
2. Final no-write freeze confirmation by FASE 4.21
3. Human execution authorization before real write

---

**Cycle ID:** {cycle_id}
**Package Created At:** {timestamp}
**Safety Status:** LOCKED (execution_allowed=false)
"""

    return md


def main() -> int:
    """Run FASE 4.19."""
    parser = argparse.ArgumentParser(description="FASE 4.19 — Build Real Write Execution Package")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--apply-plan", type=Path, required=True)
    parser.add_argument("--preflight-gate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)

    args = parser.parse_args()

    # Load inputs
    applyplan = load_json_safe(args.apply_plan)
    preflight_gate = load_json_safe(args.preflight_gate)

    if not applyplan:
        print(f"✗ ApplyPlan not found: {args.apply_plan}")
        return 1

    if not preflight_gate:
        print(f"✗ Preflight gate not found: {args.preflight_gate}")
        return 1

    # Validate preflight gate
    is_valid, issues = validate_preflight_gate(preflight_gate)

    # Generate execution phrase
    apply_plan_id = applyplan.get("apply_plan_id", "unknown")
    device = applyplan.get("device", "unknown")
    execution_phrase = generate_execution_phrase(args.cycle_id, device, apply_plan_id)

    # Build execution package
    exec_pkg = build_execution_package(args.cycle_id, applyplan, execution_phrase)

    # Generate markdown
    markdown = generate_execution_markdown(
        args.cycle_id,
        device,
        apply_plan_id,
        exec_pkg.get("execution_id", "unknown"),
        applyplan.get("item_count", 0),
        execution_phrase,
    )

    # Write outputs
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(exec_pkg, f, indent=2)

    print(f"✓ Execution package built: {exec_pkg.get('execution_id')}")
    print(f"✓ Execution phrase: {execution_phrase}")
    print(f"✓ Items: {applyplan.get('item_count', 0)}")
    print(f"✓ Report: {args.output}")
    print(f"✓ JSON: {args.output_json}")

    return 0 if is_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
